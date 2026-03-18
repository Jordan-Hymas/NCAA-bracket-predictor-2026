"""
bracket_collector.py
--------------------
Loads and cleans the 2026 NCAA Tournament team data from the verified CSV.
Enriches with First Four metadata and saves a canonical bracket CSV.
"""

import os
import pandas as pd

VERIFIED_CSV = "data/raw/bracket/march_madness_2026_68_teams_verified.csv"

# First Four matchups: (seed, region, team1, team2)
FIRST_FOUR_MATCHUPS = [
    (16, "MIDWEST", "UMBC",           "Howard"),
    (16, "SOUTH",   "Prairie View A&M", "Lehigh"),
    (11, "WEST",    "Texas",           "NC State"),
    (11, "MIDWEST", "Miami (Ohio)",    "SMU"),
]

# Build fast lookup: team_name -> opponent
_FF_OPPONENT: dict[str, str] = {}
for _seed, _region, _t1, _t2 in FIRST_FOUR_MATCHUPS:
    _FF_OPPONENT[_t1] = _t2
    _FF_OPPONENT[_t2] = _t1


class BracketCollector:
    def load_bracket(self, path: str = VERIFIED_CSV) -> pd.DataFrame:
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()

        # Normalize region to title-case
        df["Region"] = df["Region"].str.strip().str.title()

        # Parse wins/losses
        wl = df["W-L"].str.split("-", expand=True)
        df["Wins"] = wl[0].astype(int)
        df["Losses"] = wl[1].astype(int)

        # First Four flags
        df["first_four"] = df["Team"].isin(_FF_OPPONENT)
        df["first_four_game"] = df["Team"].map(_FF_OPPONENT).fillna("")

        df = df.sort_values(["Region", "Seed"]).reset_index(drop=True)
        return df

    def save_bracket(self, df: pd.DataFrame, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False)
        print(f"Saved {len(df)} rows to {path}")
