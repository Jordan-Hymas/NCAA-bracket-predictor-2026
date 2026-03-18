# Game Results Data Format

Drop CSV files here to enable head-to-head and common opponent analysis.

## Required Columns

| Column | Type | Description |
|---|---|---|
| `home_team` | str | Home team name (match names in bracket CSV) |
| `away_team` | str | Away team name |
| `home_score` | int | Points scored by home team |
| `away_score` | int | Points scored by away team |
| `neutral` | bool | True if played at neutral site |
| `date` | str | Optional: game date (YYYY-MM-DD) |

## Example

```csv
date,home_team,away_team,home_score,away_score,neutral
2025-11-04,Duke,Kansas,87,72,false
2025-11-08,Arizona,Gonzaga,91,85,true
```

## Important

- Team names must match the `Team` column in `march_madness_2026_68_teams_verified.csv`
- Include ALL teams (not just tournament teams) for best common-opponent coverage
- Multiple files are supported — all CSVs in this directory are loaded and merged
- Neutral site games should have `neutral=true` for accurate home/away adjustment
