"""
02_simulate_bracket.py
-----------------------
Run the full 2026 NCAA Tournament simulation and save results.

Usage:
    python scripts/02_simulate_bracket.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from src.collectors.bracket_collector import BracketCollector
from src.collectors.celebrity_brackets import CelebrityBrackets
from src.collectors.season_results import SeasonResults
from src.bracket.simulator import BracketSimulator

RESULTS_PATH = "data/processed/simulation_results.csv"
BRACKET_PATH = "data/processed/predicted_bracket.json"


def main():
    # --- Load teams ---
    print("Loading 2026 bracket data...")
    collector = BracketCollector()
    teams = collector.load_bracket()
    print(f"  {len(teams)} teams loaded across {teams['Region'].nunique()} regions")

    # --- Load season game results ---
    print("\nLoading season game results...")
    season = SeasonResults()
    if season.is_empty:
        print("  No game data found in data/raw/games/ — using efficiency stats only.")
        print("  Drop CSV files there to enable head-to-head and common opponent analysis.")
    else:
        print(f"  {len(season.games)} games loaded.")

    # --- Load celebrity brackets ---
    print("\nLoading celebrity brackets...")
    cb = CelebrityBrackets()
    print(cb.summary())
    consensus = cb.get_consensus_picks()

    # --- Simulate ---
    print("\nSimulating tournament...")
    sim = BracketSimulator(teams, celebrity_picks=consensus, season_results=season)
    results = sim.simulate()

    # --- Print bracket ---
    sim.print_bracket()

    # --- Save results ---
    os.makedirs("data/processed", exist_ok=True)
    df = sim.to_dataframe()
    df.to_csv(RESULTS_PATH, index=False)
    print(f"\nSaved {len(df)} game predictions to {RESULTS_PATH}")

    # --- Save bracket JSON (for web app) ---
    import json
    bracket_json = build_bracket_json(df, teams)
    with open(BRACKET_PATH, "w") as f:
        json.dump(bracket_json, f, indent=2)
    print(f"Saved bracket JSON to {BRACKET_PATH}")

    # --- Summary ---
    champ = df[df["round_num"] == 6].iloc[0]["winner"]
    ff = df[df["round_num"] == 5]["winner"].tolist()
    e8 = df[df["round_num"] == 4]["winner"].tolist()
    print(f"\n{'='*50}")
    print(f"  NATIONAL CHAMPION:  {champ}")
    print(f"  FINAL FOUR:         {ff}")
    print(f"  ELITE EIGHT:        {e8}")
    print(f"{'='*50}")


def build_bracket_json(results_df: pd.DataFrame, teams_df: pd.DataFrame) -> dict:
    """Converts simulation results into a nested JSON for the web app."""
    rounds = {}
    for rn in sorted(results_df["round_num"].unique()):
        round_name = results_df[results_df["round_num"] == rn].iloc[0]["round_name"]
        games = []
        for _, row in results_df[results_df["round_num"] == rn].iterrows():
            games.append({
                "team_a":     row["team_a"],
                "team_b":     row["team_b"],
                "winner":     row["winner"],
                "win_prob":   row["win_prob_a"],
                "confidence": row["confidence"],
                "region":     row["region"],
                "seed_a":     int(teams_df.set_index("Team").loc[row["team_a"], "Seed"]) if row["team_a"] in teams_df["Team"].values else None,
                "seed_b":     int(teams_df.set_index("Team").loc[row["team_b"], "Seed"]) if row["team_b"] in teams_df["Team"].values else None,
            })
        rounds[str(rn)] = {"round_name": round_name, "games": games}

    team_stats = teams_df.to_dict(orient="records")
    return {"rounds": rounds, "teams": team_stats}


if __name__ == "__main__":
    main()
