# NCAA Bracket Predictor 2026

AI-powered 2026 NCAA Men's Basketball Tournament bracket predictor — full prediction engine backed by real season game data, advanced efficiency stats, and 9 ESPN/media expert brackets, with an interactive web app.

---

## How the Predictions Work

Every game prediction combines five layers of evidence. The model converts each signal to a probability in logit space, weights them, then produces a final win probability via sigmoid.

### Signal Layers (in priority order)

| Weight | Signal | How it's used |
|---|---|---|
| **32%** | Head-to-head results | Did A beat B this season? Win/margin at neutral-adjusted site. If yes, this dominates. |
| **22%** | Common opponents | Both teams played team C — compare their neutral-adjusted margins, weighted by opponent strength (OpponentSRS). |
| **18%** | Net efficiency rating | Season-long points scored minus allowed per 100 possessions, adjusted for opponents. |
| **9%** | Strength of schedule | Average quality of every opponent faced. Prevents inflated mid-major stats. |
| **5%** | Celebrity consensus | 9 ESPN/media experts — per-matchup vote + agreement ratio. |
| **8%** | ORtg / DRtg / Luck | Offensive/defensive splits and regression signal (lucky teams are penalized). |
| **4%** | Tempo | Pace mismatch adjustment. |
| **2%** | Seed prior | 40 years of empirical seed-matchup win rates (1985–2024). Weakest signal — only matters when everything else is even. |

### Key Stats Explained

| Stat | What it measures | Range (2026 field) |
|---|---|---|
| **NetRtg** | Points scored minus allowed per 100 possessions | Duke 38.9 (best) → Prairie View -10.7 (lowest) |
| **ORtg** | Offensive efficiency per 100 possessions | Purdue 131.6 (highest) |
| **DRtg** | Defensive efficiency per 100 possessions (lower = better) | Duke 89.0 (best defense) |
| **AdjT** | Possessions per 40 minutes (tempo) | Alabama 73.1 (fastest) → Saint Mary's 65.2 (slowest) |
| **SOS_NetRtg** | Average opponent quality across all games | Alabama 16.75 (hardest) → High Point -9.23 (easiest) |
| **NCSOS_NetRtg** | Non-conference schedule strength | Separates real quality from conference-bubble teams |
| **Luck** | How much W-L record exceeds efficiency prediction | High luck = regression risk in March |

### Neutral-Site Adjustment

Every game in the season logs is adjusted to a neutral-site equivalent before comparing margins:
- **Home game:** raw margin − 3.5 pts (remove home court advantage)
- **Away game:** raw margin + 3.5 pts (account for road disadvantage)
- **Neutral:** no adjustment

This means Duke beating Michigan by 5 at a neutral site is worth more than beating them by 9 at home.

---

## Data Sources

| File | Contents | Rows |
|---|---|---|
| `data/raw/bracket/march_madness_2026_68_teams_verified.csv` | 68 tournament teams + full efficiency stats | 68 |
| `data/raw/bracket/march_madness_2026_parsed_game_logs.csv` | Every game played by all 68 teams this season | 2,103 |
| `data/raw/bracket/ncaa_mens_d1_2026_all_teams_stats.csv` | Full D1 stats (all teams, not just tournament) | 360+ |
| `data/raw/celebrity_brackets/*.csv` | 9 ESPN/media expert bracket picks | 9 files |

### Celebrity Experts Loaded
Dick Vitale · Jay Bilas · Hannah Storm · Eric Moody · Jay Harris · Jon Crispin · Kevin Negandhi · Mike Clay · Phil Murphy

---

## 2026 Predictions

| Round | Prediction | Key factor |
|---|---|---|
| **National Champion** | **Duke** | Beat Michigan 68–63 at neutral site (Feb 21) |
| **Final Four** | Duke, Arizona, Florida, Michigan | All have top-5 NetRtg + strong H2H records |
| **Elite Eight** | Duke, UConn, Arizona, Purdue, Florida, Illinois, Michigan, Iowa St. | |

### Celebrity Champion Consensus
| Team | Expert picks |
|---|---|
| Michigan | 3 / 9 (Moody, Harris, Crispin) |
| Arizona | 3 / 9 (Storm, Bilas, Negandhi) |
| Florida | 2 / 9 (Vitale, Murphy via different path) |
| Duke | 1 / 9 (Phil Murphy) |
| Miami (FL) | 1 / 9 (Mike Clay) |

> The model picks Duke over Michigan in the championship despite experts favoring Michigan 8/9, because Duke's direct H2H win carries 32% of the prediction weight — the strongest single signal in the model.

---

## Project Structure

```
NCAA-bracket-predictor/
├── data/
│   ├── raw/
│   │   ├── bracket/
│   │   │   ├── march_madness_2026_68_teams_verified.csv
│   │   │   ├── march_madness_2026_parsed_game_logs.csv
│   │   │   └── ncaa_mens_d1_2026_all_teams_stats.csv
│   │   ├── celebrity_brackets/          ← 9 expert CSV bracket picks
│   │   └── games/                       ← optional: additional game CSVs
│   └── processed/                       ← generated outputs (gitignored)
│       ├── simulation_results.csv
│       └── predicted_bracket.json
├── src/
│   ├── collectors/
│   │   ├── bracket_collector.py         ← loads 68-team stats CSV
│   │   ├── season_results.py            ← H2H + common opponent engine
│   │   └── celebrity_brackets.py        ← loads + normalizes all expert picks
│   ├── models/
│   │   └── predictor.py                 ← weighted logit prediction model
│   ├── bracket/
│   │   └── simulator.py                 ← simulates all 67 games
│   └── utils/
│       └── name_normalizer.py           ← maps name variants across data sources
├── scripts/
│   ├── 01_collect_bracket.py            ← validate bracket data
│   └── 02_simulate_bracket.py           ← run full simulation + print results
├── web/
│   ├── backend/
│   │   └── app.py                       ← FastAPI server
│   └── frontend/                        ← React + Vite bracket UI
│       └── src/
│           ├── components/
│           │   ├── Bracket.jsx          ← full interactive bracket
│           │   ├── Header.jsx           ← champion + Final Four banner
│           │   └── Sidebar.jsx          ← team stats + predictions + celebrity
│           └── App.jsx
├── bracket/
│   └── 2026_March_Madness_bracket.pdf  ← reference layout
├── requirements.txt
└── start.sh
```

---

## Setup

```bash
# 1. Create virtual environment (ARM Python — required on Apple Silicon)
/opt/homebrew/bin/python3 -m venv .venv

# 2. Install Python dependencies
.venv/bin/pip install -r requirements.txt

# 3. Install frontend dependencies
cd web/frontend && npm install && cd ../..
```

## Running

```bash
# Development: API on :8000, React dev server on :5173
./start.sh

# Production: builds React, serves everything from FastAPI on :8000
./start.sh --prod
```

### Run simulation manually
```bash
.venv/bin/python scripts/02_simulate_bracket.py
```
Outputs: `data/processed/simulation_results.csv` and `data/processed/predicted_bracket.json`

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/bracket` | GET | Full bracket JSON — all 67 game predictions with factors |
| `/api/teams` | GET | All 68 teams with efficiency stats |
| `/api/celebrity` | GET | Expert bracket summary, champion votes, Final Four votes |
| `/api/simulate` | GET | Re-run simulation, refresh `predicted_bracket.json` |

---

## Adding More Data

### Additional game results
Drop CSV files in `data/raw/games/` using the schema in `data/raw/games/FORMAT.md`.
The more complete the data (including non-tournament teams), the stronger the common opponent chains.

### Additional celebrity/expert brackets
Drop CSV files in `data/raw/celebrity_brackets/` using this schema:
```csv
Region,Round,Matchup,Winner
East,Round of 64,Duke vs Siena,Duke
...
Championship,Championship,Duke vs Michigan,Duke
```
The file is auto-loaded on next simulation run.
