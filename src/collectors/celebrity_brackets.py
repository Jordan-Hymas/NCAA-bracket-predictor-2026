"""
celebrity_brackets.py
---------------------
Loads all celebrity bracket CSVs from data/raw/celebrity_brackets/.

CSV schema (one row per game in the bracket):
  Region, Round, Matchup, Winner

Provides:
  - Per-matchup consensus: for each game (team_a vs team_b in a given round),
    how many celebrities picked each team?
  - Deep-run vote counts: how many celebrities have each team in the
    Final Four, Elite Eight, and as champion?
  - champion_votes, final_four_votes: Counter objects
"""

from __future__ import annotations

import os
import glob
from collections import defaultdict, Counter
from typing import Optional

import pandas as pd

from src.utils.name_normalizer import normalize_celebrity

CELEBRITY_DIR = "data/raw/celebrity_brackets"

# Map the CSV round names to our simulator round numbers
ROUND_NAME_TO_NUM = {
    "Round of 64":   1,
    "Round of 32":   2,
    "Sweet 16":      3,
    "Elite 8":       4,
    "Final Four":    5,
    "Championship":  6,
}


class CelebrityBrackets:
    def __init__(self, directory: str = CELEBRITY_DIR):
        self.directory = directory
        self.celebrities: list[str] = []

        # matchup_picks[(round_num, frozenset({team_a, team_b}))] = [winner, winner, ...]
        self._matchup_picks: dict[tuple, list[str]] = defaultdict(list)

        # vote counters for deep runs
        self.champion_votes:    Counter = Counter()
        self.final_four_votes:  Counter = Counter()
        self.elite_eight_votes: Counter = Counter()

        self._load_all()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        files = sorted(glob.glob(os.path.join(self.directory, "*.csv")))
        for fpath in files:
            name = (
                os.path.basename(fpath)
                .replace("_2026_bracket_picks.csv", "")
                .replace("_", " ")
                .title()
            )
            try:
                self._load_one(fpath, name)
                self.celebrities.append(name)
            except Exception as e:
                print(f"  [Celebrity] Could not load {fpath}: {e}")

    def _load_one(self, fpath: str, name: str) -> None:
        df = pd.read_csv(fpath)
        df.columns = df.columns.str.strip()

        for _, row in df.iterrows():
            round_name = str(row.get("Round", "")).strip()
            winner_raw = str(row.get("Winner", "")).strip()
            round_num  = ROUND_NAME_TO_NUM.get(round_name)

            if not winner_raw or winner_raw == "nan" or round_num is None:
                continue

            winner = normalize_celebrity(winner_raw)
            if winner == "__first_four__":
                continue  # skip First Four placeholder matchups

            # Parse matchup: "Duke vs Siena"
            matchup_raw = str(row.get("Matchup", ""))
            if " vs " not in matchup_raw:
                continue
            parts = matchup_raw.split(" vs ", 1)
            team_a = normalize_celebrity(parts[0].strip())
            team_b = normalize_celebrity(parts[1].strip())

            if team_a == "__first_four__" or team_b == "__first_four__":
                continue

            key = (round_num, frozenset({team_a, team_b}))
            self._matchup_picks[key].append(winner)

            # Track deep runs
            if round_num == 6:
                self.champion_votes[winner] += 1
            if round_num in (5, 6):
                # Both finalists count as Final Four
                self.final_four_votes[team_a] += 1
                self.final_four_votes[team_b] += 1
            if round_num in (4, 5, 6):
                self.elite_eight_votes[team_a] += 1
                self.elite_eight_votes[team_b] += 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_matchup_consensus(
        self,
        team_a: str,
        team_b: str,
        round_num: int,
    ) -> Optional[str]:
        """
        Returns the majority celebrity pick for this specific matchup,
        or None if no celebrity had this exact matchup.
        """
        key = (round_num, frozenset({team_a, team_b}))
        picks = self._matchup_picks.get(key, [])
        if not picks:
            # Try adjacent rounds (±1) — celebrities may have different bracket paths
            for delta in (-1, 1, -2, 2):
                alt_key = (round_num + delta, frozenset({team_a, team_b}))
                picks = self._matchup_picks.get(alt_key, [])
                if picks:
                    break
        if not picks:
            return None
        counts = Counter(picks)
        top = counts.most_common(1)[0]
        # Only return a pick if it's at least a plurality
        return top[0] if top[1] > 0 else None

    def get_celebrity_confidence(
        self,
        team_a: str,
        team_b: str,
        round_num: int,
    ) -> tuple[str | None, float]:
        """
        Returns (consensus_winner, agreement_ratio).
        agreement_ratio is fraction of celebrities who picked that winner.
        """
        key = (round_num, frozenset({team_a, team_b}))
        picks = self._matchup_picks.get(key, [])
        if not picks:
            return None, 0.5
        counts = Counter(picks)
        winner, n_picks = counts.most_common(1)[0]
        return winner, n_picks / len(picks)

    def summary(self) -> str:
        lines = [f"Celebrity brackets loaded: {len(self.celebrities)}"]
        lines.append(f"  Experts: {', '.join(self.celebrities)}")
        lines.append("\nChampion votes:")
        for team, n in self.champion_votes.most_common():
            lines.append(f"  {team}: {n}")
        lines.append("\nFinal Four votes (appearances):")
        for team, n in self.final_four_votes.most_common(8):
            lines.append(f"  {team}: {n}")
        return "\n".join(lines)
