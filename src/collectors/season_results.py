"""
season_results.py
-----------------
Loads and processes full-season game results for all teams (not just
tournament teams). This enables:
  1. Direct head-to-head lookup: did Team A beat Team B this year?
  2. Common opponent analysis: A beat C by +12, B lost to C by -4 → A +16 vs B
  3. Win quality scoring: weight wins by opponent strength

Expected input CSV schema (one row per game):
  date, home_team, away_team, home_score, away_score, neutral (bool)

Drop game result files in: data/raw/games/

Supported formats:
  - KenPom CSV export (use kenpom_games.csv)
  - Sports-Reference team game logs (*_games.csv)
  - Manual CSV matching the schema above
"""

import os
import glob
import pandas as pd
from collections import defaultdict
from typing import Optional

GAMES_DIR = "data/raw/games"


class SeasonResults:
    def __init__(self, games_df: Optional[pd.DataFrame] = None):
        if games_df is not None:
            self.games = games_df
        else:
            self.games = self._load_games()

        self._h2h: dict[tuple[str, str], list[dict]] = defaultdict(list)
        self._common_opp_cache: dict[tuple[str, str], float] = {}
        if not self.games.empty:
            self._build_h2h_index()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_games(self) -> pd.DataFrame:
        """Load all CSV game files from GAMES_DIR."""
        if not os.path.isdir(GAMES_DIR):
            return pd.DataFrame()
        files = glob.glob(f"{GAMES_DIR}/*.csv")
        if not files:
            return pd.DataFrame()
        dfs = []
        for f in files:
            try:
                dfs.append(pd.read_csv(f))
            except Exception:
                pass
        if not dfs:
            return pd.DataFrame()
        df = pd.concat(dfs, ignore_index=True)
        return self._normalize(df)

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure required columns exist and types are correct."""
        df.columns = df.columns.str.strip().str.lower()
        required = {"home_team", "away_team", "home_score", "away_score"}
        if not required.issubset(df.columns):
            return pd.DataFrame()
        df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
        df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")
        df = df.dropna(subset=["home_score", "away_score"])
        if "neutral" not in df.columns:
            df["neutral"] = False
        df["margin"] = df["home_score"] - df["away_score"]
        return df

    # ------------------------------------------------------------------
    # Index
    # ------------------------------------------------------------------

    def _build_h2h_index(self) -> None:
        for _, row in self.games.iterrows():
            home, away = row["home_team"], row["away_team"]
            margin = row["margin"]  # positive = home won
            neutral = bool(row.get("neutral", False))
            record = {
                "winner": home if margin > 0 else away,
                "loser":  away if margin > 0 else home,
                "margin": abs(margin),
                "neutral": neutral,
            }
            self._h2h[(home, away)].append(record)
            self._h2h[(away, home)].append(record)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_h2h(self, team_a: str, team_b: str) -> list[dict]:
        """Return all games between team_a and team_b this season."""
        return self._h2h.get((team_a, team_b), [])

    def h2h_advantage(self, team_a: str, team_b: str) -> float:
        """
        Returns a score in [-1, 1]:
          +1  = A beat B every time (large margins)
          -1  = B beat A every time
           0  = no games or split
        """
        games = self.get_h2h(team_a, team_b)
        if not games:
            return 0.0
        total = 0.0
        for g in games:
            sign = 1 if g["winner"] == team_a else -1
            # Cap margin effect at 20 points
            margin_weight = min(g["margin"], 20) / 20
            total += sign * (0.6 + 0.4 * margin_weight)
        return max(-1.0, min(1.0, total / len(games)))

    def common_opponent_advantage(
        self, team_a: str, team_b: str, teams_df: pd.DataFrame
    ) -> float:
        """
        Compare A and B via shared opponents.
        Returns a net margin differential (positive favors A).
        Each common opponent game: A_margin_vs_opp - B_margin_vs_opp
        Normalized by opponent strength (SOS).
        """
        cache_key = (team_a, team_b)
        if cache_key in self._common_opp_cache:
            return self._common_opp_cache[cache_key]

        if self.games.empty:
            return 0.0

        def margins_vs(team: str) -> dict[str, float]:
            """Map opponent -> average scoring margin for 'team'."""
            result: dict[str, list[float]] = defaultdict(list)
            for _, row in self.games.iterrows():
                if row["home_team"] == team:
                    result[row["away_team"]].append(row["margin"])
                elif row["away_team"] == team:
                    result[row["home_team"]].append(-row["margin"])
            return {opp: sum(v) / len(v) for opp, v in result.items()}

        margins_a = margins_vs(team_a)
        margins_b = margins_vs(team_b)
        common = set(margins_a) & set(margins_b)

        if not common:
            self._common_opp_cache[cache_key] = 0.0
            return 0.0

        # Weight each common opponent by their strength (SOS as proxy)
        team_idx = teams_df.set_index("Team") if "Team" in teams_df.columns else teams_df
        diffs = []
        for opp in common:
            diff = margins_a[opp] - margins_b[opp]
            # Weight by opponent quality if available
            if opp in team_idx.index:
                opp_strength = team_idx.loc[opp, "NetRtg"] if "NetRtg" in team_idx.columns else 0
                weight = max(0.3, 1 + opp_strength / 40)
            else:
                weight = 0.5
            diffs.append(diff * weight)

        result = sum(diffs) / len(diffs) if diffs else 0.0
        self._common_opp_cache[cache_key] = result
        return result

    @property
    def is_empty(self) -> bool:
        return self.games.empty or len(self.games) == 0
