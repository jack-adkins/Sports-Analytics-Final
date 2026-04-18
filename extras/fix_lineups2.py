"""
Fix — skip the merge entirely, just use the advanced call directly
since it already contains all the columns we need
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

print("Fetching advanced lineup stats (contains all rating columns)...")
time.sleep(2)
adv = leaguedashlineups.LeagueDashLineups(
    season=SEASON,
    group_quantity=5,
    measure_type_detailed_defense="Advanced",
    per_mode_detailed="Per100Possessions",
    season_type_all_star="Regular Season",
    timeout=30,
).get_data_frames()[0]
print(f"  {len(adv)} rows")

# Also fetch base for shooting stats (FGM, FGA, etc.)
print("\nFetching base lineup stats...")
time.sleep(2)
base = leaguedashlineups.LeagueDashLineups(
    season=SEASON,
    group_quantity=5,
    per_mode_detailed="Per100Possessions",
    season_type_all_star="Regular Season",
    timeout=30,
).get_data_frames()[0]
print(f"  {len(base)} rows")

# Check GROUP_ID overlap
print(f"\nAdvanced GROUP_ID sample: {adv['GROUP_ID'].head(3).tolist()}")
print(f"Base GROUP_ID sample:     {base['GROUP_ID'].head(3).tolist()}")
overlap = len(set(adv['GROUP_ID']) & set(base['GROUP_ID']))
print(f"Overlapping GROUP_IDs: {overlap} out of {len(adv)}")

# Use advanced as primary, add shooting cols from base
base_only_cols = [c for c in base.columns if c not in adv.columns]
print(f"\nBase-only cols to add: {base_only_cols}")

if overlap > 0:
    merged = adv.merge(base[["GROUP_ID"] + base_only_cols], on="GROUP_ID", how="left")
else:
    # GROUP_IDs don't match — try merging on GROUP_NAME + TEAM_ID instead
    print("GROUP_IDs don't overlap — trying merge on GROUP_NAME + TEAM_ID...")
    merged = adv.merge(
        base[["GROUP_NAME", "TEAM_ID"] + base_only_cols],
        on=["GROUP_NAME", "TEAM_ID"],
        how="left"
    )

print(f"\nMerged: {len(merged)} rows")

# Add possessions filter
merged["EST_POSSESSIONS"] = (merged["MIN"] / 48) * 100
merged = merged[merged["EST_POSSESSIONS"] >= MIN_POSSESSIONS]
print(f"After possession filter: {len(merged)} rows")

# Ratings check
rating_cols = [c for c in ["GROUP_NAME", "TEAM_ABBREVIATION", "NET_RATING", "OFF_RATING", "DEF_RATING", "PACE", "PIE"] if c in merged.columns]
print(f"\nRatings check (first 5 rows):")
print(merged[rating_cols].head())
print(f"\nNaN count in ratings: {merged[['NET_RATING','OFF_RATING','DEF_RATING']].isna().sum().to_dict()}")

merged.to_csv("data/lineups.csv", index=False)
print(f"\nSaved {len(merged)} lineups -> data/lineups.csv")