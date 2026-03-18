"""
name_normalizer.py
------------------
Canonical name mappings for all three data sources:
  game log OpponentClean  →  bracket Team names
  all-teams CSV Team      →  bracket Team names
  celebrity pick Winner   →  bracket Team names

Bracket Team names (from march_madness_2026_68_teams_verified.csv /
march_madness_2026_parsed_game_logs.csv "Team" column) are canonical.
"""

# ---------------------------------------------------------------------------
# Game log: OpponentClean variants → canonical bracket name
# ---------------------------------------------------------------------------
GAME_LOG_OPP_MAP: dict[str, str] = {
    "Michigan State":     "Michigan St.",
    "Ohio State":         "Ohio St.",
    "North Dakota State": "North Dakota St.",
    "Tennessee State":    "Tennessee St.",
    "Utah State":         "Utah St.",
    "Wright State":       "Wright St.",
    "Kennesaw State":     "Kennesaw St.",
    "Iowa State":         "Iowa St.",
    "Miami (OH)":         "Miami (Ohio)",
    "Queens (NC)":        "Queens (N.C.)",
    "St. John's (NY)":    "St. John's",
    "California Baptist": "Cal Baptist",
    "Connecticut":        "UConn",
}

# ---------------------------------------------------------------------------
# All-teams stats CSV: Team column variants → canonical bracket name
# ---------------------------------------------------------------------------
ALL_TEAMS_MAP: dict[str, str] = {
    "Connecticut": "UConn",
    "Miami FL":    "Miami (FL)",
    "Miami OH":    "Miami (Ohio)",
    "N.C. State":  "NC State",
}

# ---------------------------------------------------------------------------
# Celebrity bracket CSVs: Winner column variants → canonical bracket name
# Many abbreviations / shortened names appear in these picks
# ---------------------------------------------------------------------------
CELEBRITY_MAP: dict[str, str] = {
    # State name → abbreviation
    "Iowa State":         "Iowa St.",
    "Ohio State":         "Ohio St.",
    "Michigan State":     "Michigan St.",
    "North Dakota State": "North Dakota St.",
    "Tennessee State":    "Tennessee St.",
    "Utah State":         "Utah St.",
    "Wright State":       "Wright St.",
    "Kennesaw State":     "Kennesaw St.",
    # Short forms used in celebrity CSVs
    "N Dakota St":        "North Dakota St.",
    "Kennesaw St":        "Kennesaw St.",
    "Wright St":          "Wright St.",
    "Michigan St":        "Michigan St.",
    "Iowa State":         "Iowa St.",
    "St John's":          "St. John's",
    "CA Baptist":         "Cal Baptist",
    "Hawai'i":            "Hawaii",
    # Miami context: West bracket matchups use "Miami" = Miami (FL)
    "Miami":              "Miami (FL)",
    # Connecticut
    "Connecticut":        "UConn",
    # First Four placeholders — map to eventual representative
    # (winner is decided by simulation; we skip these picks)
    "PV/LEH":             "__first_four__",
    "M-OH/SMU":           "__first_four__",
    "TEX/NCSU":           "__first_four__",
    "UMBC/HOW":           "__first_four__",
}


def _fix_apostrophe(name: str) -> str:
    return name.replace("\u2019", "'").replace("\u2018", "'").strip()


def normalize_game_log_opp(name: str) -> str:
    name = _fix_apostrophe(name)
    return GAME_LOG_OPP_MAP.get(name, name)


def normalize_all_teams(name: str) -> str:
    name = _fix_apostrophe(name)
    return ALL_TEAMS_MAP.get(name, name)


def normalize_celebrity(name: str) -> str:
    name = _fix_apostrophe(name)
    return CELEBRITY_MAP.get(name, name)
