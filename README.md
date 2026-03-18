# NCAA Bracket Predictor 2026

AI-powered 2026 NCAA Men's Basketball Tournament bracket predictor with a full interactive web app.

## How It Works

Predictions are built from three layers of evidence, applied in priority order:

| Priority | Signal | Description |
|---|---|---|
| 1 | **Head-to-head results** | Did these two teams play this season? Outcome + margin. |
| 2 | **Common opponents** | Both teams played Team C — compare margins to estimate A vs B. |
| 3 | **Season efficiency stats** | NetRtg, ORtg, DRtg, SOS, Tempo, Luck from the full season. |
| 4 | **Seed priors** | 40 years of empirical seed-matchup win rates (1985–2024). |
| 5 | **Celebrity brackets** | Public picks folded in as a small ensemble weight. |

### Key Stats

| Stat | What it measures |
|---|---|
| **NetRtg** | Points scored minus allowed per 100 possessions (best single predictor) |
| **ORtg** | Offensive efficiency per 100 possessions |
| **DRtg** | Defensive efficiency per 100 possessions (lower = better defense) |
| **AdjT** | Adjusted tempo — possessions per 40 minutes |
| **SOS_NetRtg** | Strength of schedule — average opponent quality |
| **NCSOS_NetRtg** | Non-conference schedule strength |
| **Luck** | How much W-L exceeds what efficiency metrics predict (regression risk) |

## Project Structure

```
NCAA-bracket-predictor/
├── data/
│   ├── raw/
│   │   ├── bracket/
│   │   │   └── march_madness_2026_68_teams_verified.csv   ← canonical team data
│   │   ├── games/          ← drop season game CSVs here for H2H analysis
│   │   └── celebrity_brackets/  ← JSON files per celebrity
│   └── processed/          ← generated outputs (gitignored)
├── src/
│   ├── collectors/
│   │   ├── bracket_collector.py    ← loads team stats
│   │   ├── season_results.py       ← H2H + common opponent engine
│   │   └── celebrity_brackets.py  ← celebrity pick storage
│   ├── models/
│   │   └── predictor.py    ← game prediction model
│   └── bracket/
│       └── simulator.py    ← full tournament simulator (67 games)
├── scripts/
│   ├── 01_collect_bracket.py   ← load + validate bracket data
│   └── 02_simulate_bracket.py  ← run full simulation
├── web/
│   ├── backend/
│   │   └── app.py          ← FastAPI: /api/bracket, /api/teams, /api/celebrity
│   └── frontend/           ← React + Vite bracket UI
├── requirements.txt
└── start.sh
```

## Setup

```bash
# 1. Create virtual environment (uses ARM Python on Apple Silicon)
/opt/homebrew/bin/python3 -m venv .venv

# 2. Install Python dependencies
.venv/bin/pip install -r requirements.txt

# 3. Install frontend dependencies
cd web/frontend && npm install && cd ../..
```

## Running

```bash
# Development (API on :8000, React dev server on :5173)
./start.sh

# Production (builds React, serves everything from FastAPI on :8000)
./start.sh --prod
```

## Adding Season Game Data

Drop CSV files in `data/raw/games/` to enable head-to-head and common opponent analysis.
See `data/raw/games/FORMAT.md` for the expected schema.

The more complete the game data (including non-tournament teams), the better the
common opponent comparisons. Once loaded, the model automatically shifts weight
toward the H2H signal.

## Adding Celebrity Brackets

**Via web UI:** Open the app → Celebrity tab → fill in the form.

**Via JSON file:** Create `data/raw/celebrity_brackets/{name}.json`:
```json
{
  "champion": "Duke",
  "final_four": ["Duke", "Arizona", "Florida", "Michigan"],
  "elite_eight": ["Duke", "UConn", "Arizona", "Purdue", "Florida", "Houston", "Michigan", "Iowa St."]
}
```

**Via API:**
```bash
curl -X POST http://localhost:8000/api/celebrity \
  -H "Content-Type: application/json" \
  -d '{"name":"Barack Obama","champion":"Duke","final_four":["Duke","Arizona","Florida","Michigan"]}'
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/bracket` | Full bracket JSON with all 67 game predictions |
| `GET /api/teams` | All 68 teams with stats |
| `GET /api/celebrity` | Celebrity bracket summary and vote counts |
| `POST /api/celebrity` | Add a celebrity bracket pick |
| `GET /api/simulate` | Re-run simulation, returns fresh results |

## 2026 Predictions

| Round | Prediction |
|---|---|
| Champion | **Duke** |
| Final Four | Duke, Arizona, Florida, Michigan |
| Elite Eight | Duke, Michigan St., Arizona, Purdue, Florida, Houston, Michigan, Iowa St. |

*Predictions update automatically when new game data or celebrity brackets are added.*

---

> Data source: `march_madness_2026_68_teams_verified.csv` — 68 teams with full season efficiency metrics.
