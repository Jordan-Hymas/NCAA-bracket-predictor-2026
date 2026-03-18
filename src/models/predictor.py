"""
predictor.py
------------
Predicts game winners using a layered evidence model:

  Priority 1 — Head-to-head results this season (strongest signal)
  Priority 2 — Common opponent margin comparison (neutral-adjusted)
  Priority 3 — Season efficiency stats (NetRtg, ORtg, DRtg, SOS, Luck)
  Priority 4 — Celebrity bracket consensus (9 ESPN/media experts)
  Priority 5 — Seed-based historical prior (1985–2024 empirical rates)

All signals are converted to logit space and summed with learned weights,
then passed through sigmoid to produce P(team_a wins).
"""

from __future__ import annotations

import math
import random
from typing import Optional, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from src.collectors.season_results import SeasonResults

# ---------------------------------------------------------------------------
# Empirical seed-matchup win rates (1985–2024)
# ---------------------------------------------------------------------------
SEED_WIN_RATES: dict[tuple[int, int], float] = {
    (1, 16): 0.991, (2, 15): 0.940, (3, 14): 0.851, (4, 13): 0.793,
    (5, 12): 0.647, (6, 11): 0.622, (7, 10): 0.601, (8,  9): 0.514,
    (1,  8): 0.856, (1,  9): 0.839, (2,  7): 0.792, (2, 10): 0.750,
    (3,  6): 0.694, (3, 11): 0.672, (4,  5): 0.583, (4, 12): 0.704,
    (1,  5): 0.783, (1, 12): 0.850, (2,  6): 0.720, (2, 11): 0.740,
    (3,  7): 0.636, (4,  8): 0.592, (1,  4): 0.740, (1,  6): 0.769,
    (2,  3): 0.599, (1,  2): 0.586, (1,  3): 0.636,
}

# ---------------------------------------------------------------------------
# Model weights — how much each signal contributes in logit space
# ---------------------------------------------------------------------------
W = {
    "h2h":        0.32,  # direct H2H result this season
    "common_opp": 0.22,  # common opponent margin differential
    "net_rtg":    0.18,  # season net efficiency rating
    "sos":        0.09,  # strength of schedule
    "off_rtg":    0.04,  # offensive rating
    "def_rtg":    0.04,  # defensive rating (inverted)
    "luck":       0.03,  # luck (negative signal — regress lucky teams)
    "tempo":      0.01,  # pace mismatch
    "celebrity":  0.05,  # per-matchup expert consensus
    "seed":       0.02,  # historical seed prior (weak in stat-rich model)
}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _logit(p: float) -> float:
    p = max(0.001, min(0.999, p))
    return math.log(p / (1 - p))


def _seed_prior(seed_a: int, seed_b: int) -> float:
    lo, hi = min(seed_a, seed_b), max(seed_a, seed_b)
    base = SEED_WIN_RATES.get((lo, hi), 0.5)
    return base if seed_a <= seed_b else 1 - base


class GamePredictor:
    def __init__(
        self,
        season_results: Optional["SeasonResults"] = None,
        teams_df: Optional[pd.DataFrame] = None,
        noise_std: float = 0.0,
    ):
        self.sr = season_results
        self.teams_df = teams_df
        self.noise_std = noise_std
        self._cache: dict = {}   # base score cache for fast MC re-use

    def predict(
        self,
        team_a: pd.Series,
        team_b: pd.Series,
        round_num: int = 1,
        celebrity_pick: Optional[str] = None,
        celebrity_agreement: float = 0.5,
    ) -> dict:
        """
        Returns:
          team_a, team_b    — input team names
          winner            — predicted winner
          win_prob_a        — P(team_a wins) ∈ [0, 1]
          win_prob          — P(winner wins) ∈ [0.5, 1]
          confidence        — 'low' | 'medium' | 'high'
          factors           — per-signal breakdown dict
        """
        name_a, name_b = team_a.name, team_b.name

        # ── 1. Head-to-head ──────────────────────────────────────────
        h2h_score   = 0.0
        h2h_game_ct = 0
        if self.sr and not self.sr.is_empty:
            h2h_score   = self.sr.h2h_advantage(name_a, name_b)
            h2h_game_ct = len(self.sr.get_h2h_games(name_a, name_b))

        # ── 2. Common opponents ───────────────────────────────────────
        co_diff = 0.0
        if self.sr and not self.sr.is_empty:
            co_raw  = self.sr.common_opponent_advantage(name_a, name_b)
            # ~15 pt diff → logit(0.8); normalize and convert to logit
            co_diff = _logit(0.5 + max(-0.45, min(0.45, co_raw / 30)))

        # ── 3. Efficiency stats ───────────────────────────────────────
        d_net   = team_a["NetRtg"]     - team_b["NetRtg"]
        d_off   = team_a["ORtg"]       - team_b["ORtg"]
        d_def   = -(team_a["DRtg"]    - team_b["DRtg"])   # lower = better
        d_sos   = team_a["SOS_NetRtg"] - team_b["SOS_NetRtg"]
        d_luck  = team_a["Luck"]       - team_b["Luck"]
        d_tempo = team_a["AdjT"]       - team_b["AdjT"]

        # ── 4. Celebrity consensus ────────────────────────────────────
        celeb_logit = 0.0
        if celebrity_pick is not None:
            # agreement ∈ [0.5, 1.0] → P ∈ [0.55, 0.80] for the picked team
            raw_p  = 0.5 + (celebrity_agreement - 0.5) * 0.6
            celeb_p = raw_p if celebrity_pick == name_a else 1 - raw_p
            celeb_logit = _logit(celeb_p)

        # ── 5. Seed prior ─────────────────────────────────────────────
        seed_p     = _seed_prior(int(team_a["Seed"]), int(team_b["Seed"]))
        seed_logit = _logit(seed_p)

        # ── Weighted sum ──────────────────────────────────────────────
        score = (
            W["h2h"]        * h2h_score  * 3.0   +
            W["common_opp"] * co_diff            +
            W["net_rtg"]    * d_net      * 0.22  +
            W["sos"]        * d_sos      * 0.30  +
            W["off_rtg"]    * d_off      * 0.18  +
            W["def_rtg"]    * d_def      * 0.18  +
            W["luck"]       * (-d_luck)  * 0.80  +
            W["tempo"]      * d_tempo    * 0.04  +
            W["celebrity"]  * celeb_logit        +
            W["seed"]       * seed_logit
        )

        # Add Gaussian noise for Monte Carlo simulations
        if self.noise_std:
            score += random.gauss(0, self.noise_std)

        win_prob_a = _sigmoid(score)
        winner     = name_a if win_prob_a >= 0.5 else name_b
        win_prob   = win_prob_a if winner == name_a else 1 - win_prob_a
        confidence = "low" if win_prob < 0.58 else "medium" if win_prob < 0.72 else "high"

        return {
            "team_a":     name_a,
            "team_b":     name_b,
            "winner":     winner,
            "win_prob_a": round(win_prob_a, 4),
            "win_prob":   round(win_prob, 4),
            "confidence": confidence,
            "factors": {
                "h2h_games":        h2h_game_ct,
                "h2h_score":        round(h2h_score, 3),
                "common_opp_pts":   round(self.sr.common_opponent_advantage(name_a, name_b)
                                         if self.sr else 0, 2),
                "net_rtg_diff":     round(d_net, 2),
                "sos_diff":         round(d_sos, 2),
                "seed_prior":       round(seed_p, 3),
                "celebrity_pick":   celebrity_pick,
                "celebrity_agree":  round(celebrity_agreement, 2),
            },
        }
