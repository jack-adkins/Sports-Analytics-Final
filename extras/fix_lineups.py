"""
Fix — re-fetches lineup data correctly by pulling advanced stats only
which contains all the ratings we need in a single call
"""
import time
import pandas as pd
from nba_api.stats.endpoints import leaguedashlineups
import nba_api.library.http as nba_http

nba_http.STATS_HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Referer": "https://www.nba.com/",
    "Connection": "keep-alive",
    "Origin": "https://www.nba.com",
}

SEASON = "2024-25"
MIN_POSSESSIONS = 50

print("Fetching base lineup stats...")
time.sleep(2)
base = leaguedashlineups.LeagueDashLineups(
    season=SEASON,
    group_quantity=5,
    per_mode_detailed="Per100Possessions",
    season_type_all_star="Regular Season",
    timeout=30,
).get_data_frames()[0]
print(f"  Base: {len(base)} rows, columns: {base.columns.tolist()}")

print("\nFetching advanced lineup stats...")
time.sleep(2)
adv = leaguedashlineups.LeagueDashLineups(
    season=SEASON,
    group_quantity=5,
    measure_type_detailed_defense="Advanced",
    per_mode_detailed="Per100Possessions",
    season_type_all_star="Regular Season",
    timeout=30,
).get_data_frames()[0]
print(f"  Advanced: {len(adv)} rows, columns: {adv.columns.tolist()}")

# Merge on GROUP_ID — keep all base cols, add new advanced cols
adv_new_cols = [c for c in adv.columns if c not in base.columns]
print(f"\nNew columns from advanced: {adv_new_cols}")

merged = base.merge(adv[["GROUP_ID"] + adv_new_cols], on="GROUP_ID", how="left")
print(f"Merged: {len(merged)} rows, columns: {merged.columns.tolist()}")

# Filter by possessions
merged["EST_POSSESSIONS"] = (merged["MIN"] / 48) * 100
merged = merged[merged["EST_POSSESSIONS"] >= MIN_POSSESSIONS]
print(f"After possession filter: {len(merged)} rows")

# Check ratings
print(f"\nRatings check (first 5 rows):")
rating_cols = [c for c in ["GROUP_NAME", "TEAM_ABBREVIATION", "NET_RATING", "OFF_RATING", "DEF_RATING", "PACE", "PIE"] if c in merged.columns]
print(merged[rating_cols].head())

# Save
merged.to_csv("data/lineups.csv", index=False)
print(f"\nSaved {len(merged)} lineups -> data/lineups.csv")