"""
Fetches home and away lineup splits for all 30 teams
and saves them to data/lineups_home.csv and data/lineups_away.csv
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
MIN_POSSESSIONS = 20  # Lower threshold for splits since sample size is smaller
SLEEP = 2.0

def fetch_location_lineups(location):
    """location: 'Home' or 'Road'"""
    print(f"\nFetching {location} advanced lineup stats...")
    time.sleep(SLEEP)
    try:
        adv = leaguedashlineups.LeagueDashLineups(
            season=SEASON,
            group_quantity=5,
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="Per100Possessions",
            season_type_all_star="Regular Season",
            location_nullable=location,
            timeout=30,
        ).get_data_frames()[0]
        print(f"  v  {len(adv)} rows")
    except Exception as e:
        print(f"  x  ERROR advanced: {e}")
        adv = pd.DataFrame()

    time.sleep(SLEEP)
    print(f"Fetching {location} base lineup stats...")
    try:
        base = leaguedashlineups.LeagueDashLineups(
            season=SEASON,
            group_quantity=5,
            per_mode_detailed="Per100Possessions",
            season_type_all_star="Regular Season",
            location_nullable=location,
            timeout=30,
        ).get_data_frames()[0]
        print(f"  v  {len(base)} rows")
    except Exception as e:
        print(f"  x  ERROR base: {e}")
        base = pd.DataFrame()

    if adv.empty:
        return pd.DataFrame()

    # Merge base shooting cols onto advanced
    if not base.empty:
        base_only_cols = [c for c in base.columns if c not in adv.columns]
        merged = adv.merge(
            base[["GROUP_NAME", "TEAM_ID"] + base_only_cols],
            on=["GROUP_NAME", "TEAM_ID"],
            how="left"
        )
    else:
        merged = adv

    # Filter by possessions
    merged["EST_POSSESSIONS"] = (merged["MIN"] / 48) * 100
    merged = merged[merged["EST_POSSESSIONS"] >= MIN_POSSESSIONS]
    merged["LOCATION"] = location

    print(f"  After filter: {len(merged)} lineups")

    # Ratings check
    nan_count = merged[["NET_RATING", "OFF_RATING", "DEF_RATING"]].isna().sum().to_dict()
    print(f"  NaN in ratings: {nan_count}")

    return merged

# Fetch both locations
home_df = fetch_location_lineups("Home")
away_df = fetch_location_lineups("Road")

if not home_df.empty:
    home_df.to_csv("data/lineups_home.csv", index=False)
    print(f"\nSaved {len(home_df)} home lineups -> data/lineups_home.csv")

if not away_df.empty:
    away_df.to_csv("data/lineups_away.csv", index=False)
    print(f"Saved {len(away_df)} away lineups -> data/lineups_away.csv")

# Quick preview
if not home_df.empty and not away_df.empty:
    print("\nSample comparison (BOS lineups):")
    bos_home = home_df[home_df["TEAM_ABBREVIATION"] == "BOS"][["GROUP_NAME", "NET_RATING", "OFF_RATING", "DEF_RATING", "MIN"]].head(3)
    bos_away = away_df[away_df["TEAM_ABBREVIATION"] == "BOS"][["GROUP_NAME", "NET_RATING", "OFF_RATING", "DEF_RATING", "MIN"]].head(3)
    print("HOME:")
    print(bos_home.to_string())
    print("AWAY:")
    print(bos_away.to_string())

print("\nDone! Ready to update app.py with location feature.")