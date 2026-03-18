"""
predictor.py
------------
Predicts the winner of a matchup using this season's data:

Priority order:
  1. Direct head-to-head results this season (strongest signal)
  2. Common opponent analysis (how both teams fared vs shared opponents)
  3. Season efficiency stats (NetRtg, ORtg, DRtg, SOS, Tempo, Luck)
  4. Seed-based prior (weakest — only used when stats are similar)
  5. Celebrity bracket consensus (small ensemble weight)

Win probability formula (logistic):
  P(A wins) = sigmoid(
      w_h2h   * h2h_score        +   # direct matchup result
      w_copp  * common_opp_diff  +   # common opponent comparison
      w_net   * Δnet_rtg         +   # season efficiency
      w_sos   * Δsos             +   # strength of schedule
      w_luck  * Δluck            +   # luck regression signal
      w_tempo * Δtempo           +   # pace matchup
      w_seed  * seed_prior_logit +   # seed-based historical prior
      w_celeb * celeb_logit          # celebrity consensus
  )
"""

from __future__ import annotations
import math
from typing import Optional, TYPE_CHECKING
import pandas as pd

if TYPE_CHECKING:
    from src.collectors.season_results import SeasonResults

# ---------------------------------------------------------------------------
# Historical seed matchup win rates (1985–2024 empirical)
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

# Model weights
# When h2h data is available it dominates; efficiency fills in the gaps.
WEIGHTS = {
    "h2h":       0.35,   # direct head-to-head result this season
    "common_opp": 0.20,  # common opponent margin comparison
    "net_rtg":   0.18,   # net efficiency rating delta
    "sos":       0.10,   # strength of schedule delta
    "off_rtg":   0.04,   # offensive rating delta
    "def_rtg":   0.04,   # defensive rating delta (inverted)
    "luck":      0.03,   # luck (negative — regress lucky teams)
    "tempo":     0.01,   # pace mismatch
    "seed":      0.04,   # seed-based historical prior
    "celebrity": 0.01,   # celebrity bracket consensus
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
        celebrity_weight: float = WEIGHTS["celebrity"],
    ):
        self.season_results = season_results
        self.teams_df = teams_df
        self.celebrity_weight = celebrity_weight

    def predict(
        self,
        team_a: pd.Series,
        team_b: pd.Series,
        celebrity_pick: Optional[str] = None,
    ) -> dict:
        """
        Returns:
          winner       - predicted winning team name
          win_prob_a   - P(team_a wins) ∈ [0, 1]
          win_prob     - P(winner wins) ∈ [0.5, 1]
          confidence   - 'low' | 'medium' | 'high'
          factors      - breakdown of each signal
        """
        name_a = team_a.name
        name_b = team_b.name

        # ---- 1. Head-to-head signal ----
        h2h_score = 0.0
        h2h_games = []
        if self.season_results and not self.season_results.is_empty:
            h2h_score = self.season_results.h2h_advantage(name_a, name_b)
            h2h_games = self.season_results.get_h2h(name_a, name_b)

        # ---- 2. Common opponent signal ----
        common_opp_diff = 0.0
        if (self.season_results and not self.season_results.is_empty
                and self.teams_df is not None):
            raw = self.season_results.common_opponent_advantage(
                name_a, name_b, self.teams_df
            )
            # Normalize: ~10pt margin difference ≈ logit(0.7)
            common_opp_diff = _logit(0.5 + raw / 40)

        # ---- 3. Season efficiency signals ----
        d_net   = team_a["NetRtg"]     - team_b["NetRtg"]
        d_off   = team_a["ORtg"]       - team_b["ORtg"]
        d_def   = -(team_a["DRtg"]    - team_b["DRtg"])  # lower DRtg is better
        d_sos   = team_a["SOS_NetRtg"] - team_b["SOS_NetRtg"]
        d_luck  = team_a["Luck"]       - team_b["Luck"]
        d_tempo = team_a["AdjT"]       - team_b["AdjT"]

        # ---- 4. Seed prior ----
        seed_p     = _seed_prior(int(team_a["Seed"]), int(team_b["Seed"]))
        seed_logit = _logit(seed_p)

        # ---- 5. Celebrity consensus ----
        celeb_logit = 0.0
        if celebrity_pick is not None:
            celeb_p = 0.65 if celebrity_pick == name_a else 0.35
            celeb_logit = _logit(celeb_p)

        # ---- Weighted score → probability ----
        # Scale factors so they live in a comparable range in logit space
        score = (
            WEIGHTS["h2h"]        * h2h_score      * 3.0   +
            WEIGHTS["common_opp"] * common_opp_diff         +
            WEIGHTS["net_rtg"]    * d_net           * 0.25  +
            WEIGHTS["sos"]        * d_sos           * 0.35  +
            WEIGHTS["off_rtg"]    * d_off           * 0.20  +
            WEIGHTS["def_rtg"]    * d_def           * 0.20  +
            WEIGHTS["luck"]       * (-d_luck)       * 1.00  +
            WEIGHTS["tempo"]      * d_tempo         * 0.05  +
            WEIGHTS["seed"]       * seed_logit               +
            self.celebrity_weight * celeb_logit
        )

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
                "h2h_games":        len(h2h_games),
                "h2h_score":        round(h2h_score, 3),
                "common_opp_diff":  round(common_opp_diff, 3),
                "net_rtg_diff":     round(d_net, 2),
                "sos_diff":         round(d_sos, 2),
                "seed_prior":       round(seed_p, 3),
                "celeb_pick":       celebrity_pick,
            },
        }
