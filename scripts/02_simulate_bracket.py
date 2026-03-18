"""
02_simulate_bracket.py
-----------------------
Run the full 2026 NCAA Tournament simulation.

Data used:
  - data/raw/bracket/march_madness_2026_68_teams_verified.csv   (68-team stats)
  - data/raw/bracket/march_madness_2026_parsed_game_logs.csv    (full season H2H)
  - data/raw/celebrity_brackets/*.csv                           (9 expert brackets)

Usage:
    python scripts/02_simulate_bracket.py
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.collectors.bracket_collector import BracketCollector
from src.collectors.season_results import SeasonResults
from src.collectors.celebrity_brackets import CelebrityBrackets
from src.bracket.simulator import BracketSimulator

RESULTS_CSV  = "data/processed/simulation_results.csv"
BRACKET_JSON = "data/processed/predicted_bracket.json"


def main():
    # ── Teams ────────────────────────────────────────────────────────
    print("Loading 2026 bracket data...")
    collector = BracketCollector()
    teams = collector.load_bracket()
    print(f"  {len(teams)} teams across {teams['Region'].nunique()} regions")

    # ── Season game logs ─────────────────────────────────────────────
    print("\nLoading season game logs...")
    season = SeasonResults()
    if season.is_empty:
        print("  WARNING: No game data — predictions use efficiency stats only.")
    else:
        h2h_count = len(season.games[season.games["OpponentClean"].isin(
            set(season.games["Team"].unique())
        )])
        print(f"  {len(season.games):,} games loaded")
        print(f"  {h2h_count} head-to-head games between tournament teams")

    # ── Celebrity brackets ───────────────────────────────────────────
    print("\nLoading celebrity brackets...")
    cb = CelebrityBrackets()
    print(cb.summary())

    # ── Simulate ─────────────────────────────────────────────────────
    print("\nSimulating tournament...\n")
    sim = BracketSimulator(teams, season_results=season, celebrity_brackets=cb)
    sim.simulate()
    sim.print_bracket()

    # ── Save outputs ─────────────────────────────────────────────────
    os.makedirs("data/processed", exist_ok=True)
    df = sim.to_dataframe()
    df.to_csv(RESULTS_CSV, index=False)
    print(f"\nSaved {len(df)} game predictions → {RESULTS_CSV}")

    bracket_json = _build_bracket_json(df, teams)
    with open(BRACKET_JSON, "w") as f:
        json.dump(bracket_json, f, indent=2)
    print(f"Saved bracket JSON → {BRACKET_JSON}")

    # ── Final summary ─────────────────────────────────────────────────
    champ = df[df["round_num"] == 6].iloc[0]["winner"]
    ff    = df[df["round_num"] == 5]["winner"].tolist()
    e8    = df[df["round_num"] == 4]["winner"].tolist()
    print(f"\n{'='*55}")
    print(f"  NATIONAL CHAMPION : {champ}")
    print(f"  FINAL FOUR        : {', '.join(ff)}")
    print(f"  ELITE EIGHT       : {', '.join(e8)}")
    print(f"\n  Celebrity champion votes:")
    for team, n in cb.champion_votes.most_common():
        print(f"    {team}: {n}/9")
    print(f"{'='*55}")


def _build_bracket_json(results_df, teams_df):
    rounds = {}
    team_idx = teams_df.set_index("Team")
    for rn in sorted(results_df["round_num"].unique()):
        rname = results_df[results_df["round_num"] == rn].iloc[0]["round_name"]
        games = []
        for _, row in results_df[results_df["round_num"] == rn].iterrows():
            def seed_of(name):
                return int(team_idx.loc[name, "Seed"]) if name in team_idx.index else None
            games.append({
                "team_a":          row["team_a"],
                "team_b":          row["team_b"],
                "winner":          row["winner"],
                "win_prob":        row["win_prob_a"],
                "confidence":      row["confidence"],
                "region":          row["region"],
                "seed_a":          seed_of(row["team_a"]),
                "seed_b":          seed_of(row["team_b"]),
                "h2h_games":       row["factors"]["h2h_games"],
                "h2h_score":       row["factors"]["h2h_score"],
                "celebrity_pick":  row["factors"]["celebrity_pick"],
                "celebrity_agree": row["factors"]["celebrity_agree"],
            })
        rounds[str(rn)] = {"round_name": rname, "games": games}
    return {"rounds": rounds, "teams": teams_df.to_dict(orient="records")}


if __name__ == "__main__":
    main()
