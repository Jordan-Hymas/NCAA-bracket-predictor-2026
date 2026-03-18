"""
simulator.py
------------
Simulates the full 2026 NCAA Tournament bracket.

Bracket structure (standard NCAA seeding):
  First Four  → play-in for specific 11 and 16 seeds
  Round of 64 → 1v16, 8v9, 5v12, 4v13, 6v11, 3v14, 7v10, 2v15 per region
  Round of 32 → winners of R64 matchups
  Sweet 16    → winners of R32 matchups
  Elite 8     → winners of S16 matchups
  Final Four  → East vs West winner, South vs Midwest winner
  Championship→ Final Four winners

Output: list of dicts, one per game, with full context.
"""

import pandas as pd
from typing import Optional, TYPE_CHECKING
from src.models.predictor import GamePredictor

if TYPE_CHECKING:
    from src.collectors.season_results import SeasonResults

# Standard R64 seed bracket slots per region (seed_top vs seed_bottom)
R64_SEED_PAIRS = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]

# First Four matchups: (seed, region, team1, team2)
# The winner takes that seed slot in the R64
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

# Final Four pairings: which region winners face each other
FINAL_FOUR_PAIRS = [("East", "West"), ("South", "Midwest")]


class BracketSimulator:
    def __init__(
        self,
        teams_df: pd.DataFrame,
        celebrity_picks: Optional[dict[str, str]] = None,
        season_results: Optional["SeasonResults"] = None,
    ):
        """
        teams_df        - cleaned 68-team DataFrame from BracketCollector
        celebrity_picks - dict mapping "TeamA vs TeamB" → predicted winner
        season_results  - SeasonResults object with full-season game data;
                          enables head-to-head and common-opponent signals
        """
        self.teams = teams_df.set_index("Team")
        self.predictor = GamePredictor(
            season_results=season_results,
            teams_df=teams_df,
        )
        self.celebrity_picks = celebrity_picks or {}
        self.results: list[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def simulate(self) -> list[dict]:
        """Run the full tournament simulation. Returns list of game dicts."""
        self.results = []

        # --- First Four ---
        ff_winners: dict[tuple[int, str], str] = {}
        for seed, region, t1, t2 in FIRST_FOUR:
            result = self._play(t1, t2, round_num=0, region=region,
                                label=f"First Four: {t1} vs {t2}")
            ff_winners[(seed, region)] = result["winner"]

        # --- Build R64 brackets per region ---
        regional_brackets: dict[str, list[str]] = {}
        for region in ("East", "West", "South", "Midwest"):
            regional_brackets[region] = self._build_regional_r64(region, ff_winners)

        # --- Simulate rounds 1-4 (R64 → Elite 8) per region ---
        regional_champions: dict[str, str] = {}
        for region, slot_teams in regional_brackets.items():
            champ = self._simulate_region(region, slot_teams)
            regional_champions[region] = champ

        # --- Final Four ---
        ff_game_winners = []
        for r1, r2 in FINAL_FOUR_PAIRS:
            t1, t2 = regional_champions[r1], regional_champions[r2]
            result = self._play(t1, t2, round_num=5,
                                label=f"Final Four: {r1} vs {r2}")
            ff_game_winners.append(result["winner"])

        # --- Championship ---
        self._play(ff_game_winners[0], ff_game_winners[1], round_num=6,
                   label="National Championship")

        return self.results

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.results)

    def print_bracket(self) -> None:
        current_round = -1
        for game in self.results:
            rn = game["round_num"]
            if rn != current_round:
                print(f"\n{'='*60}")
                print(f"  {ROUND_NAMES[rn].upper()}")
                print(f"{'='*60}")
                current_round = rn
            prob = game["win_prob"]
            conf = game["confidence"]
            print(f"  {game['team_a']:25s} vs {game['team_b']:25s}"
                  f"  →  {game['winner']:25s}  ({prob:.1%}, {conf})")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_regional_r64(
        self,
        region: str,
        ff_winners: dict[tuple[int, str], str],
    ) -> list[str]:
        """
        Returns 16 team names in bracket order for R64:
        index 0 = 1-seed, index 1 = 16-seed, index 2 = 8-seed, ... etc.
        Slots follow R64_SEED_PAIRS order.
        """
        region_teams = self.teams[self.teams["Region"].str.title() == region]

        def get_team(seed: int) -> str:
            # Check if this slot was decided by a First Four game
            ff_winner = ff_winners.get((seed, region))
            if ff_winner:
                return ff_winner
            matches = region_teams[region_teams["Seed"] == seed]
            # Exclude First Four losers (both teams in FF had that seed)
            ff_in_region = [t for s, r, t1, t2 in FIRST_FOUR
                            if s == seed and r == region
                            for t in (t1, t2)]
            if ff_in_region:
                # The non-FF teams for this seed slot don't exist (FF fills it)
                return ff_winner or matches.index[0]
            if len(matches) == 1:
                return matches.index[0]
            return matches.index[0]

        bracket = []
        for s1, s2 in R64_SEED_PAIRS:
            bracket.append(get_team(s1))
            bracket.append(get_team(s2))
        return bracket  # 16 teams: [1seed, 16seed, 8seed, 9seed, ...]

    def _simulate_region(self, region: str, slot_teams: list[str]) -> str:
        """
        Simulate rounds 1-4 for one region.
        slot_teams: 16 teams in bracket order (pairs: 0v1, 2v3, 4v5, ...)
        Returns the regional champion name.
        """
        current_round = list(slot_teams)
        for round_num in range(1, 5):  # R64=1, R32=2, S16=3, E8=4
            next_round = []
            for i in range(0, len(current_round), 2):
                t1, t2 = current_round[i], current_round[i + 1]
                result = self._play(t1, t2, round_num=round_num, region=region)
                next_round.append(result["winner"])
            current_round = next_round
        return current_round[0]

    def _play(
        self,
        team_a_name: str,
        team_b_name: str,
        round_num: int,
        region: str = "",
        label: str = "",
    ) -> dict:
        """Predict one game, store result, return result dict."""
        a = self._get_team(team_a_name)
        b = self._get_team(team_b_name)

        game_key = f"{team_a_name} vs {team_b_name}"
        celeb_pick = self.celebrity_picks.get(game_key)

        result = self.predictor.predict(a, b, celebrity_pick=celeb_pick)
        result.update({
            "round_num":   round_num,
            "round_name":  ROUND_NAMES[round_num],
            "region":      region,
            "game_label":  label or game_key,
        })
        self.results.append(result)
        return result

    def _get_team(self, name: str) -> pd.Series:
        if name in self.teams.index:
            return self.teams.loc[name]
        # Fuzzy fallback: case-insensitive
        match = [t for t in self.teams.index if t.lower() == name.lower()]
        if match:
            return self.teams.loc[match[0]]
        raise KeyError(f"Team not found in data: '{name}'")
