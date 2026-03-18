"""
celebrity_brackets.py
---------------------
Collects and normalizes public celebrity bracket picks for 2026.

Sources:
  - ESPN Tournament Challenge (public celebrity entries)
  - Manual entries for well-known public brackets

Each celebrity bracket is stored as a dict: round -> list of predicted winners.
The consensus across celebrities is used as a prior in the game predictor.

Usage:
    from src.collectors.celebrity_brackets import CelebrityBrackets
    cb = CelebrityBrackets()
    picks = cb.get_consensus_picks()  # {matchup_key: most_picked_team}
"""

from __future__ import annotations
from collections import Counter
from typing import Optional
import json
import os

# ---------------------------------------------------------------------------
# Hand-entered 2026 celebrity bracket picks
# Format: name -> {round_name -> [ordered winners list]}
# Ordered as they appear round by round in the bracket
# ---------------------------------------------------------------------------
CELEBRITY_BRACKETS: dict[str, dict] = {
    # Example structure — populate as picks become available
    # "Barack Obama": {
    #     "champion": "Duke",
    #     "final_four": ["Duke", "Arizona", "Florida", "Michigan"],
    #     "elite_eight": [...],
    # },
}

# Path to store/cache celebrity bracket JSON files
CELEBRITY_DATA_DIR = "data/raw/celebrity_brackets"


class CelebrityBrackets:
    def __init__(self):
        self.brackets: dict[str, dict] = dict(CELEBRITY_BRACKETS)
        self._load_from_files()

    def _load_from_files(self) -> None:
        """Load any JSON bracket files dropped in the celebrity_brackets dir."""
        if not os.path.isdir(CELEBRITY_DATA_DIR):
            return
        for fname in os.listdir(CELEBRITY_DATA_DIR):
            if not fname.endswith(".json"):
                continue
            name = fname.replace(".json", "").replace("_", " ").title()
            with open(os.path.join(CELEBRITY_DATA_DIR, fname)) as f:
                try:
                    self.brackets[name] = json.load(f)
                except json.JSONDecodeError:
                    pass

    def add_bracket(self, celebrity_name: str, picks: dict) -> None:
        """
        Manually add a celebrity bracket.
        picks format:
          {
            "champion": "TeamName",
            "final_four": ["Team1", "Team2", "Team3", "Team4"],
            "elite_eight": ["T1", ..., "T8"],   # optional
          }
        """
        self.brackets[celebrity_name] = picks
        # Persist to file
        os.makedirs(CELEBRITY_DATA_DIR, exist_ok=True)
        fname = celebrity_name.lower().replace(" ", "_") + ".json"
        with open(os.path.join(CELEBRITY_DATA_DIR, fname), "w") as f:
            json.dump(picks, f, indent=2)

    def get_champion_votes(self) -> Counter:
        """Returns Counter of champion picks across all celebrities."""
        champs = [b["champion"] for b in self.brackets.values() if "champion" in b]
        return Counter(champs)

    def get_final_four_votes(self) -> Counter:
        """Returns Counter of Final Four picks."""
        ff = []
        for b in self.brackets.values():
            ff.extend(b.get("final_four", []))
        return Counter(ff)

    def get_consensus_picks(self) -> dict[str, str]:
        """
        Returns a flat dict of game_key -> consensus_pick.
        Used as the celebrity_picks input to BracketSimulator.

        For now uses champion + final four votes to influence key late-round games.
        """
        picks: dict[str, str] = {}
        if not self.brackets:
            return picks

        champion_votes = self.get_champion_votes()
        ff_votes = self.get_final_four_votes()

        # Weight champion vote most heavily
        if champion_votes:
            top_champ = champion_votes.most_common(1)[0][0]
            picks["__champion__"] = top_champ

        if ff_votes:
            top_ff = [team for team, _ in ff_votes.most_common(4)]
            picks["__final_four__"] = top_ff

        return picks

    def summary(self) -> str:
        lines = [f"Celebrity brackets loaded: {len(self.brackets)}"]
        for name, bracket in self.brackets.items():
            champ = bracket.get("champion", "?")
            ff = ", ".join(bracket.get("final_four", []))
            lines.append(f"  {name}: champion={champ}  ff=[{ff}]")
        return "\n".join(lines)
