"""
web/backend/app.py
------------------
FastAPI backend for the 2026 NCAA Bracket Predictor.

Endpoints:
  GET /api/bracket          → full bracket JSON (rounds + teams)
  GET /api/teams            → 68 teams with stats
  GET /api/celebrity        → celebrity bracket summary
  POST /api/celebrity       → add a celebrity bracket pick
  GET /api/simulate         → re-run simulation, return fresh results
"""

import json
import os
import sys
import threading
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Allow importing from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.collectors.bracket_collector import BracketCollector
from src.collectors.celebrity_brackets import CelebrityBrackets
from src.collectors.season_results import SeasonResults
from src.bracket.simulator import BracketSimulator

# Module-level singletons so we don't reload on every request
_season_results: SeasonResults | None = None
_celebrity_brackets: CelebrityBrackets | None = None
_mc_cache: dict | None = None


def _get_season_results() -> SeasonResults:
    global _season_results
    if _season_results is None:
        _season_results = SeasonResults()
    return _season_results


def _get_celebrity_brackets() -> CelebrityBrackets:
    global _celebrity_brackets
    if _celebrity_brackets is None:
        _celebrity_brackets = CelebrityBrackets()
    return _celebrity_brackets

app = FastAPI(title="NCAA Bracket Predictor 2026", version="1.0.0")


def _run_mc(n: int = 100) -> dict:
    """Compute MC simulations and return result dict."""
    collector = BracketCollector()
    teams     = collector.load_bracket()
    season    = _get_season_results()
    cb        = _get_celebrity_brackets()
    champ_counts: dict = defaultdict(int)
    ff_counts:    dict = defaultdict(int)
    e8_counts:    dict = defaultdict(int)
    for _ in range(n):
        sim = BracketSimulator(teams, season_results=season, celebrity_brackets=cb, noise_std=0.7)
        sim.simulate()
        df  = sim.to_dataframe()
        champ_counts[df[df["round_num"] == 6].iloc[0]["winner"]] += 1
        for t in df[df["round_num"] == 5]["winner"].tolist(): ff_counts[t] += 1
        for t in df[df["round_num"] == 4]["winner"].tolist(): e8_counts[t] += 1
    all_teams = teams["Team"].tolist()
    return {
        "n": n,
        "champion":    {t: round(champ_counts.get(t, 0) / n, 4) for t in all_teams},
        "final_four":  {t: round(ff_counts.get(t, 0)   / n, 4) for t in all_teams},
        "elite_eight": {t: round(e8_counts.get(t, 0)   / n, 4) for t in all_teams},
    }


def _load_or_compute_mc(n: int = 100) -> dict:
    """Return MC odds from disk cache if available, else compute and save."""
    global _mc_cache
    if _mc_cache is not None:
        return _mc_cache
    if os.path.exists(MC_JSON_PATH):
        print("[MC] Loading from disk cache...")
        with open(MC_JSON_PATH) as f:
            _mc_cache = json.load(f)
        print("[MC] Loaded.")
        return _mc_cache
    print(f"[MC] Computing {n} simulations (this runs once and is cached)...")
    result = _run_mc(n)
    os.makedirs("data/processed", exist_ok=True)
    with open(MC_JSON_PATH, "w") as f:
        json.dump(result, f)
    _mc_cache = result
    print("[MC] Done — saved to disk.")
    return _mc_cache


@app.on_event("startup")
async def startup_event():
    """Pre-load MC odds at startup (from disk if cached, else compute in background)."""
    threading.Thread(target=_load_or_compute_mc, daemon=True).start()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BRACKET_JSON_PATH = "data/processed/predicted_bracket.json"
MC_JSON_PATH      = "data/processed/mc_odds.json"


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def _load_bracket_json() -> dict:
    if not os.path.exists(BRACKET_JSON_PATH):
        _run_simulation()
    with open(BRACKET_JSON_PATH) as f:
        return json.load(f)


def _run_simulation() -> dict:
    collector = BracketCollector()
    teams = collector.load_bracket()
    season = _get_season_results()
    cb = _get_celebrity_brackets()
    sim = BracketSimulator(teams, season_results=season, celebrity_brackets=cb)
    sim.simulate()
    df = sim.to_dataframe()

    # Build bracket JSON (same as script)
    rounds = {}
    for rn in sorted(df["round_num"].unique()):
        round_name = df[df["round_num"] == rn].iloc[0]["round_name"]
        games = []
        team_idx = teams.set_index("Team")
        for _, row in df[df["round_num"] == rn].iterrows():
            seed_a = int(team_idx.loc[row["team_a"], "Seed"]) if row["team_a"] in team_idx.index else None
            seed_b = int(team_idx.loc[row["team_b"], "Seed"]) if row["team_b"] in team_idx.index else None
            games.append({
                "team_a":     row["team_a"],
                "team_b":     row["team_b"],
                "winner":     row["winner"],
                "win_prob":   row["win_prob_a"],
                "confidence": row["confidence"],
                "region":     row["region"],
                "seed_a":     seed_a,
                "seed_b":     seed_b,
                "factors":    row["factors"],
            })
        rounds[str(rn)] = {"round_name": round_name, "games": games}

    result = {"rounds": rounds, "teams": teams.to_dict(orient="records")}
    os.makedirs("data/processed", exist_ok=True)
    with open(BRACKET_JSON_PATH, "w") as f:
        json.dump(result, f, indent=2)
    return result


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/bracket")
def get_bracket():
    return _load_bracket_json()


@app.get("/api/teams")
def get_teams():
    collector = BracketCollector()
    teams = collector.load_bracket()
    return teams.to_dict(orient="records")


@app.get("/api/celebrity")
def get_celebrity():
    cb = _get_celebrity_brackets()
    return {
        "count":            len(cb.celebrities),
        "experts":          cb.celebrities,
        "champion_votes":   dict(cb.champion_votes),
        "final_four_votes": dict(cb.final_four_votes),
        "elite_eight_votes":dict(cb.elite_eight_votes),
    }


@app.get("/api/monte-carlo")
def monte_carlo(n: int = 100, refresh: bool = False):
    """Return MC championship/FF/E8 odds. Results are cached to disk after first run."""
    global _mc_cache
    if refresh:
        _mc_cache = None
        if os.path.exists(MC_JSON_PATH):
            os.remove(MC_JSON_PATH)
    return _load_or_compute_mc(n)


@app.get("/api/simulate")
def resimulate():
    global _celebrity_brackets
    _celebrity_brackets = None  # force reload
    result = _run_simulation()
    games = sum(len(r["games"]) for r in result["rounds"].values())
    return {"status": "ok", "games_simulated": games}


# ---------------------------------------------------------------------------
# Serve React frontend (production build)
# ---------------------------------------------------------------------------

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "../frontend/dist")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=f"{FRONTEND_DIST}/assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        return FileResponse(f"{FRONTEND_DIST}/index.html")
