"""
season_results.py
-----------------
Loads the full 2026 season game logs and computes:

  1. Head-to-head records between any two tournament teams
  2. Common opponent margin comparisons (neutral-adjusted)

Primary data source:
  data/raw/bracket/march_madness_2026_parsed_game_logs.csv

Schema:
  TeamNumber, Team, Game, Date, DateISO, Time, Type, Loc, Location,
  Opponent, OpponentClean, OpponentRankShown, OpponentConf, OpponentSRS,
  Result, TeamScore, OpponentScore, ScoreMargin, OT, Wins, Losses,
  Streak, Arena

Loc encoding:
  NaN / empty  →  Home game for Team
  '@'           →  Away game for Team
  'N'           →  Neutral site

Neutral-adjusted margin:
  Home  →  raw_margin - HOME_ADV   (they had an advantage, remove it)
  Away  →  raw_margin + HOME_ADV   (opponent had advantage, add it back)
  Neutral → raw_margin as-is
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Optional

import pandas as pd

from src.utils.name_normalizer import normalize_game_log_opp

GAME_LOG_PATH = "data/raw/bracket/march_madness_2026_parsed_game_logs.csv"
HOME_ADV = 3.5   # standard college basketball home court advantage (points)
MARGIN_CAP = 25  # cap blowout margins so they don't dominate


class SeasonResults:
    def __init__(self, path: str = GAME_LOG_PATH):
        self.games = self._load(path)

        # Index: team → {opponent → [neutral-adjusted margins]}
        # Margin > 0 means the outer-key team outperformed opponent
        self._margins: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        # All tournament team names (the "Team" column)
        self._tournament_teams: set[str] = set()

        if not self.games.empty:
            self._tournament_teams = set(self.games["Team"].unique())
            self._build_index()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self, path: str) -> pd.DataFrame:
        if not os.path.exists(path):
            print(f"  [SeasonResults] Game log not found: {path}")
            return pd.DataFrame()
        df = pd.read_csv(path)
        df["OpponentClean"] = df["OpponentClean"].astype(str).apply(normalize_game_log_opp)
        df["neutral_margin"] = df.apply(self._neutral_margin, axis=1)
        return df

    @staticmethod
    def _neutral_margin(row) -> float:
        """Adjust raw ScoreMargin to a neutral-site equivalent."""
        loc = str(row["Loc"]).strip()
        raw = float(row["ScoreMargin"]) if pd.notna(row["ScoreMargin"]) else 0.0
        raw = max(-MARGIN_CAP, min(MARGIN_CAP, raw))  # cap blowouts
        if loc == "N":
            return raw
        elif loc == "@":
            return raw + HOME_ADV   # team was away; remove opponent's home edge
        else:
            return raw - HOME_ADV   # team was home; remove their own edge

    # ------------------------------------------------------------------
    # Index building
    # ------------------------------------------------------------------

    def _build_index(self) -> None:
        """
        Build _margins[team][opponent] = [neutral_adjusted_margins].
        For every game: record from the Team's perspective.
        """
        for _, row in self.games.iterrows():
            team = row["Team"]
            opp  = row["OpponentClean"]
            margin = row["neutral_margin"]
            self._margins[team][opp].append(margin)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        return self.games.empty

    def get_h2h_games(self, team_a: str, team_b: str) -> list[dict]:
        """
        Return all games team_a played against team_b this season.
        Each dict: {winner, margin, neutral_margin}
        """
        games = []
        for _, row in self.games.iterrows():
            if row["Team"] == team_a and row["OpponentClean"] == team_b:
                games.append({
                    "winner":         team_a if row["Result"] == "W" else team_b,
                    "margin":         abs(float(row["ScoreMargin"] or 0)),
                    "neutral_margin": row["neutral_margin"],
                    "loc":            str(row["Loc"]).strip(),
                })
        return games

    def h2h_advantage(self, team_a: str, team_b: str) -> float:
        """
        Returns a score in [-1, +1]:
          +1  →  team_a dominates team_b
          -1  →  team_b dominates
           0  →  no games played
        Accounts for margin of victory (capped at MARGIN_CAP).
        """
        games = self.get_h2h_games(team_a, team_b)
        if not games:
            return 0.0

        total = 0.0
        for g in games:
            sign = 1.0 if g["winner"] == team_a else -1.0
            # margin contribution: 0 pt diff = 0.6, full cap = 1.0
            m = abs(g["neutral_margin"]) / MARGIN_CAP
            total += sign * (0.6 + 0.4 * min(m, 1.0))
        # Normalize so one game can contribute at most ±1.0
        return max(-1.0, min(1.0, total / max(1, len(games))))

    def common_opponent_advantage(self, team_a: str, team_b: str) -> float:
        """
        Compare team_a and team_b via shared opponents.

        Returns a margin differential (points):
          > 0  →  team_a outperformed team_b vs common opponents
          < 0  →  team_b outperformed
          0.0  →  no common opponents or no game data

        Weights each common opponent by |OpponentSRS| so wins over
        strong teams matter more than wins over weak ones.
        """
        if self.is_empty:
            return 0.0

        margins_a = self._margins.get(team_a, {})
        margins_b = self._margins.get(team_b, {})
        common = set(margins_a) & set(margins_b)

        if not common:
            return 0.0

        # Average OpponentSRS for each common opponent (proxy for strength)
        opp_srs: dict[str, float] = {}
        for opp in common:
            srs_vals = self.games[self.games["OpponentClean"] == opp]["OpponentSRS"].dropna()
            opp_srs[opp] = abs(float(srs_vals.mean())) if len(srs_vals) > 0 else 5.0

        total_weight = 0.0
        weighted_diff = 0.0
        for opp in common:
            avg_a = sum(margins_a[opp]) / len(margins_a[opp])
            avg_b = sum(margins_b[opp]) / len(margins_b[opp])
            # Weight: stronger opponents count more (floor at 1.0)
            w = max(1.0, opp_srs[opp])
            weighted_diff += w * (avg_a - avg_b)
            total_weight += w

        if total_weight == 0:
            return 0.0
        return weighted_diff / total_weight

    def summary(self, team_a: str, team_b: str) -> str:
        """Human-readable H2H + common opponent summary for two teams."""
        games = self.get_h2h_games(team_a, team_b)
        co = self.common_opponent_advantage(team_a, team_b)
        lines = [f"Season matchup: {team_a} vs {team_b}"]
        if games:
            for g in games:
                lines.append(
                    f"  H2H: {g['winner']} won by {g['margin']:.0f} "
                    f"(neutral-adj: {g['neutral_margin']:+.1f})"
                )
        else:
            lines.append("  H2H: No direct games this season")
        lines.append(f"  Common opponent advantage: {co:+.2f} pts (+ favors {team_a})")
        return "\n".join(lines)
