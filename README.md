# NBA Lineup Optimizer

An interactive tool that recommends optimal five-man lineup combinations for any NBA team based on opponent tendencies, home/away splits, and in-game scenarios. Built using official NBA Stats API data from the 2024-25 regular season.

---

## How to Run

### 1. Install dependencies
`pip install nba_api pandas numpy streamlit`

### 2. Collect data
`python nba_pipeline.py`

Pulls all lineup, team tendency, and opponent shooting data from the NBA Stats API. Saves all files to `/data`.

### 3. Collect home/away splits
`python fetch_location_splits.py`

Pulls lineup data filtered by location (Home/Away) separately. Saves `lineups_home.csv` and `lineups_away.csv` to `/data`.

### 4. Launch the app
`python -m streamlit run app.py`

---

## File Overview

| File | Purpose |
|---|---|
| `nba_pipeline.py` | Main data collection script, pulls all data from NBA Stats API |
| `fetch_home_away.py` | Pulls home and away lineup splits separately |
| `app.py` | Streamlit app, the interactive tool |

### Data files

| File | Contents |
|---|---|
| `data/lineups.csv` | All five-man lineups, overall, with base + advanced stats |
| `data/lineups_home.csv` | Five-man lineups filtered to home games only |
| `data/lineups_away.csv` | Five-man lineups filtered to away games only |
| `data/team_tendencies.csv` | Team-level advanced stats used to build opponent profiles |
| `data/opp_shooting.csv` | Where each team allows opponents to shoot from |
| `data/teams.csv` | Team ID and abbreviation reference table |