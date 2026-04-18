"""
collect_data.py
---------------
Pulls NBA 2024-25 regular season data from the NBA Stats API and saves
it as CSVs in a /data folder. Run this once to build your local dataset.

What gets collected:
    1. lineups_base.csv     — five-man lineup combos (raw counting stats + plus/minus)
    2. lineups_advanced.csv — same lineups, advanced metrics (net rating, pace, eFG%, etc.)
    3. team_stats.csv       — team-level advanced stats (used to build opponent profiles)

Usage:
    python collect_data.py
"""

import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguedashlineups, leaguedashteamstats

SEASON = "2024-25"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def pull(label, endpoint_fn, **kwargs):
    """Call an endpoint, print status, return first DataFrame."""
    print(f"Pulling {label}...", end=" ", flush=True)
    df = endpoint_fn(**kwargs).get_data_frames()[0]
    print(f"{len(df)} rows")
    time.sleep(1)  # be polite to stats.nba.com
    return df


# ── 1. Five-man lineups (Base — counting stats) ───────────────────────────────
lineups_base = pull(
    "lineups (Base/Totals)",
    leaguedashlineups.LeagueDashLineups,
    season=SEASON,
    season_type_all_star="Regular Season",
    measure_type_detailed_defense="Base",
    per_mode_detailed="Totals",
    group_quantity=5,
)

# ── 2. Five-man lineups (Advanced — efficiency metrics) ───────────────────────
lineups_adv = pull(
    "lineups (Advanced/Per100)",
    leaguedashlineups.LeagueDashLineups,
    season=SEASON,
    season_type_all_star="Regular Season",
    measure_type_detailed_defense="Advanced",
    per_mode_detailed="Per100Possessions",
    group_quantity=5,
)

# ── 3. Team-level advanced stats ──────────────────────────────────────────────
team_stats = pull(
    "team stats (Advanced)",
    leaguedashteamstats.LeagueDashTeamStats,
    season=SEASON,
    season_type_all_star="Regular Season",
    measure_type_detailed_defense="Advanced",
    per_mode_detailed="PerGame",
)

# ── Save ──────────────────────────────────────────────────────────────────────
lineups_base.to_csv(DATA_DIR / "lineups_base.csv", index=False)
lineups_adv.to_csv(DATA_DIR / "lineups_advanced.csv", index=False)
team_stats.to_csv(DATA_DIR / "team_stats.csv", index=False)

print("\nDone. Files saved to /data:")
for f in sorted(DATA_DIR.glob("*.csv")):
    print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")

# ── Quick preview ─────────────────────────────────────────────────────────────
print("\nLineup columns (Base):")
print(list(lineups_base.columns))

print("\nLineup columns (Advanced):")
print(list(lineups_adv.columns))

print("\nTeam stats columns:")
print(list(team_stats.columns))