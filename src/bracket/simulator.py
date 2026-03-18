"""
simulator.py
------------
Simulates the full 2026 NCAA Tournament bracket.

Bracket structure:
  First Four  → play-in for specific 11 and 16 seeds
  Round of 64 → 1v16, 8v9, 5v12, 4v13, 6v11, 3v14, 7v10, 2v15 per region
  Round of 32 → winners of R64 matchups
  Sweet 16    → winners of R32 matchups
  Elite 8     → winners of S16 matchups
  Final Four  → East vs West, South vs Midwest
  Championship→ Final Four winners

Output: list of dicts, one per game, with full prediction context.
"""

from __future__ import annotations

import pandas as pd
from typing import Optional, TYPE_CHECKING

from src.models.predictor import GamePredictor

if TYPE_CHECKING:
    from src.collectors.season_results import SeasonResults
    from src.collectors.celebrity_brackets import CelebrityBrackets

R64_SEED_PAIRS = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]

FIRST_FOUR = [
    (16, "Midwest", "UMBC",             "Howard"),
    (16, "South",   "Prairie View A&M", "Lehigh"),
    (11, "West",    "Texas",            "NC State"),
    (11, "Midwest", "Miami (Ohio)",     "SMU"),
]

ROUND_NAMES = {
    0: "First Four",
    1: "Round of 64",
    2: "Round of 32",
    3: "Sweet 16",
    4: "Elite 8",
    5: "Final Four",
    6: "Championship",
}

FINAL_FOUR_PAIRS = [("East", "West"), ("South", "Midwest")]


class BracketSimulator:
    def __init__(
        self,
        teams_df: pd.DataFrame,
        season_results: Optional["SeasonResults"] = None,
        celebrity_brackets: Optional["CelebrityBrackets"] = None,
    ):
        self.teams = teams_df.set_index("Team")
        self.predictor = GamePredictor(
            season_results=season_results,
            teams_df=teams_df,
        )
        self.cb = celebrity_brackets   # CelebrityBrackets instance
        self.results: list[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def simulate(self) -> list[dict]:
        self.results = []

        # First Four
        ff_winners: dict[tuple[int, str], str] = {}
        for seed, region, t1, t2 in FIRST_FOUR:
            result = self._play(t1, t2, round_num=0, region=region)
            ff_winners[(seed, region)] = result["winner"]

        # Build and simulate each region (R64 → Elite 8)
        regional_champions: dict[str, str] = {}
        for region in ("East", "West", "South", "Midwest"):
            slots = self._build_r64(region, ff_winners)
            regional_champions[region] = self._simulate_region(region, slots)

        # Final Four
        ff_winners_list = []
        for r1, r2 in FINAL_FOUR_PAIRS:
            t1, t2 = regional_champions[r1], regional_champions[r2]
            result = self._play(t1, t2, round_num=5, label=f"Final Four: {r1} vs {r2}")
            ff_winners_list.append(result["winner"])

        # Championship
        self._play(ff_winners_list[0], ff_winners_list[1],
                   round_num=6, label="National Championship")

        return self.results

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.results)

    def print_bracket(self) -> None:
        current_round = -1
        for game in self.results:
            rn = game["round_num"]
            if rn != current_round:
                print(f"\n{'='*65}")
                print(f"  {ROUND_NAMES[rn].upper()}")
                print(f"{'='*65}")
                current_round = rn
            prob  = game["win_prob"]
            conf  = game["confidence"]
            celeb = f"  [experts: {game['factors']['celebrity_pick']} {game['factors']['celebrity_agree']:.0%}]" \
                    if game["factors"]["celebrity_pick"] else ""
            h2h   = f"  [H2H: {game['factors']['h2h_games']} games, score={game['factors']['h2h_score']:+.2f}]" \
                    if game["factors"]["h2h_games"] > 0 else ""
            print(f"  {game['team_a']:26s} vs {game['team_b']:26s}"
                  f"  →  {game['winner']:26s}  ({prob:.1%}, {conf}){h2h}{celeb}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_r64(
        self,
        region: str,
        ff_winners: dict[tuple[int, str], str],
    ) -> list[str]:
        region_teams = self.teams[self.teams["Region"].str.title() == region]

        def get_team(seed: int) -> str:
            ff_winner = ff_winners.get((seed, region))
            if ff_winner:
                return ff_winner
            matches = region_teams[region_teams["Seed"] == seed]
            ff_in_region = {t for s, r, t1, t2 in FIRST_FOUR
                            if s == seed and r == region
                            for t in (t1, t2)}
            if ff_in_region:
                return ff_winner or matches.index[0]
            return matches.index[0] if len(matches) >= 1 else ""

        bracket = []
        for s1, s2 in R64_SEED_PAIRS:
            bracket.append(get_team(s1))
            bracket.append(get_team(s2))
        return bracket

    def _simulate_region(self, region: str, slots: list[str]) -> str:
        current = list(slots)
        for rn in range(1, 5):   # R64=1, R32=2, S16=3, E8=4
            nxt = []
            for i in range(0, len(current), 2):
                result = self._play(current[i], current[i + 1], round_num=rn, region=region)
                nxt.append(result["winner"])
            current = nxt
        return current[0]

    def _play(
        self,
        team_a_name: str,
        team_b_name: str,
        round_num: int,
        region: str = "",
        label: str = "",
    ) -> dict:
        a = self._get_team(team_a_name)
        b = self._get_team(team_b_name)

        # Look up per-matchup celebrity consensus for this exact game
        celeb_pick   = None
        celeb_agree  = 0.5
        if self.cb is not None:
            celeb_pick, celeb_agree = self.cb.get_celebrity_confidence(
                team_a_name, team_b_name, round_num
            )

        result = self.predictor.predict(
            a, b,
            round_num=round_num,
            celebrity_pick=celeb_pick,
            celebrity_agreement=celeb_agree,
        )
        result.update({
            "round_num":  round_num,
            "round_name": ROUND_NAMES[round_num],
            "region":     region,
            "game_label": label or f"{team_a_name} vs {team_b_name}",
        })
        self.results.append(result)
        return result

    def _get_team(self, name: str) -> pd.Series:
        if name in self.teams.index:
            return self.teams.loc[name]
        match = [t for t in self.teams.index if t.lower() == name.lower()]
        if match:
            return self.teams.loc[match[0]]
        raise KeyError(f"Team not found: '{name}'")
