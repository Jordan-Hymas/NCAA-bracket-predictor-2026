"""
01_collect_bracket.py
---------------------
Fetch and save the 2026 NCAA Tournament bracket.

Usage:
    python scripts/01_collect_bracket.py
"""

import sys
import os

# Allow running from project root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.collectors.bracket_collector import BracketCollector

OUTPUT_PATH = "data/raw/bracket/2026_bracket.csv"


def main():
    collector = BracketCollector()

    print("Fetching 2026 NCAA Tournament bracket...")
    df = collector.scrape_bracket(year=2026)

    collector.save_bracket(df, OUTPUT_PATH)

    # --- Summary ---
    print("\n=== Bracket Summary ===")
    print(f"Total teams : {len(df)}")
    print(f"Regions     : {sorted(df['region'].unique())}")
    print()
    for region, grp in df.groupby("region"):
        print(f"  {region:8s} — {len(grp):2d} teams  "
              f"(seeds {grp['seed'].min()}–{grp['seed'].max()})")
    ff = df[df["first_four"]]
    print(f"\nFirst Four teams ({len(ff)}):")
    for _, row in ff.iterrows():
        print(f"  seed={row['seed']:2d}  {row['region']:8s}  "
              f"{row['team']} vs {row['first_four_game']}")

    # --- Verification ---
    assert len(df) == 68, f"Expected 68 teams, got {len(df)}"
    assert df["region"].nunique() == 4, "Expected 4 regions"
    assert len(ff) == 8, f"Expected 8 First Four participants (4 games × 2), got {len(ff)}"

    top_seeds = df[df["seed"] == 1][["region", "team"]].set_index("region")["team"].to_dict()
    print(f"\nNo. 1 seeds: {top_seeds}")
    assert top_seeds.get("East") == "Duke", f"East 1-seed mismatch: {top_seeds.get('East')}"
    assert top_seeds.get("West") == "Arizona", f"West 1-seed mismatch: {top_seeds.get('West')}"
    assert top_seeds.get("Midwest") == "Michigan", f"Midwest 1-seed mismatch: {top_seeds.get('Midwest')}"
    assert top_seeds.get("South") == "Florida", f"South 1-seed mismatch: {top_seeds.get('South')}"

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
