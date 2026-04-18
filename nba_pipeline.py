"""
NBA Lineup Optimizer — Data Pipeline
"""

import time
import os
import pandas as pd
from nba_api.stats.endpoints import (
    leaguedashlineups,
    leaguedashteamstats,
    teamdashboardbygeneralsplits,
    leaguedashoppptshot,
)
from nba_api.stats.static import teams
import nba_api.library.http as nba_http

# ── Patch headers ─────────────────────────────────────────────────────────────

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

# ── Config ────────────────────────────────────────────────────────────────────

SEASON = "2024-25"
MIN_POSSESSIONS = 50
DATA_DIR = "data"
SLEEP = 2.0

os.makedirs(DATA_DIR, exist_ok=True)

# ── Step 1: Team reference table ──────────────────────────────────────────────

def build_team_table():
    print("\n[1/4] Building team reference table...")
    all_teams = teams.get_teams()
    df = pd.DataFrame(all_teams)[["id", "full_name", "abbreviation", "nickname"]]
    df.rename(columns={"id": "team_id", "full_name": "team_name"}, inplace=True)
    df.to_csv(f"{DATA_DIR}/teams.csv", index=False)
    print(f"  Saved {len(df)} teams -> {DATA_DIR}/teams.csv")
    return df

# ── Step 2: 5-man lineup data ─────────────────────────────────────────────────

def build_lineup_data():
    print("\n[2/4] Fetching 5-man lineup data...")
    time.sleep(SLEEP)

    try:
        base = leaguedashlineups.LeagueDashLineups(
            season=SEASON,
            group_quantity=5,
            per_mode_detailed="Per100Possessions",
            season_type_all_star="Regular Season",
            timeout=30,
        ).get_data_frames()[0]
        print(f"  v  Base stats ({len(base)} rows)")
    except Exception as e:
        print(f"  x  ERROR base: {e}")
        base = pd.DataFrame()

    time.sleep(SLEEP)

    try:
        advanced = leaguedashlineups.LeagueDashLineups(
            season=SEASON,
            group_quantity=5,
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="Per100Possessions",
            season_type_all_star="Regular Season",
            timeout=30,
        ).get_data_frames()[0]
        print(f"  v  Advanced stats ({len(advanced)} rows)")
    except Exception as e:
        print(f"  x  ERROR advanced: {e}")
        advanced = pd.DataFrame()

    if not advanced.empty and not base.empty:
        merge_cols = [c for c in advanced.columns if c not in base.columns]
        result = base.merge(advanced[["GROUP_ID"] + merge_cols], on="GROUP_ID", how="left")
    elif not advanced.empty:
        result = advanced
    elif not base.empty:
        result = base
    else:
        print("  WARNING: No lineup data returned.")
        return pd.DataFrame()

    if "MIN" in result.columns:
        result["EST_POSSESSIONS"] = (result["MIN"] / 48) * 100
        result = result[result["EST_POSSESSIONS"] >= MIN_POSSESSIONS]

    result.to_csv(f"{DATA_DIR}/lineups.csv", index=False)
    print(f"  Saved {len(result)} qualified lineups -> {DATA_DIR}/lineups.csv")
    print(f"  Columns: {result.columns.tolist()}")
    return result

# ── Step 3: Team tendency profiles ───────────────────────────────────────────

def build_team_tendencies():
    print("\n[3/4] Fetching team tendency profiles...")
    time.sleep(SLEEP)

    try:
        base = leaguedashteamstats.LeagueDashTeamStats(
            season=SEASON,
            per_mode_detailed="PerGame",
            season_type_all_star="Regular Season",
            timeout=30,
        ).get_data_frames()[0]
        print(f"  v  Base team stats ({len(base)} rows)")
    except Exception as e:
        print(f"  x  ERROR base: {e}")
        base = pd.DataFrame()

    time.sleep(SLEEP)

    try:
        advanced = leaguedashteamstats.LeagueDashTeamStats(
            season=SEASON,
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
            season_type_all_star="Regular Season",
            timeout=30,
        ).get_data_frames()[0]
        print(f"  v  Advanced team stats ({len(advanced)} rows)")
    except Exception as e:
        print(f"  x  ERROR advanced: {e}")
        advanced = pd.DataFrame()

    time.sleep(SLEEP)

    try:
        opp_shooting = leaguedashoppptshot.LeagueDashOppPtShot(
            season=SEASON,
            per_mode_detailed="PerGame",
            season_type_all_star="Regular Season",
            timeout=30,
        ).get_data_frames()[0]
        opp_shooting.to_csv(f"{DATA_DIR}/opp_shooting.csv", index=False)
        print(f"  v  Opp shooting ({len(opp_shooting)} rows)")
    except Exception as e:
        print(f"  x  ERROR opp shooting: {e}")

    if not advanced.empty and not base.empty:
        merge_cols = [c for c in advanced.columns if c not in base.columns]
        result = base.merge(advanced[["TEAM_ID"] + merge_cols], on="TEAM_ID", how="left")
    elif not advanced.empty:
        result = advanced
    elif not base.empty:
        result = base
    else:
        print("  WARNING: No team tendency data returned.")
        return pd.DataFrame()

    result.to_csv(f"{DATA_DIR}/team_tendencies.csv", index=False)
    print(f"  Saved {len(result)} team profiles -> {DATA_DIR}/team_tendencies.csv")
    print(f"  Columns: {result.columns.tolist()}")
    return result

# ── Step 4: Matchup data ──────────────────────────────────────────────────────

def build_matchup_data(team_df):
    print("\n[4/4] Fetching per-team matchup splits...")

    all_splits = []
    for idx, row in team_df.iterrows():
        team_id = row["team_id"]
        abbr = row["abbreviation"]
        print(f"  [{idx+1}/{len(team_df)}] {abbr}...", end=" ", flush=True)
        time.sleep(SLEEP)

        try:
            splits = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
                team_id=team_id,
                season=SEASON,
                measure_type_detailed_defense="Advanced",
                per_mode_detailed="PerGame",
                season_type_all_star="Regular Season",
                timeout=30,
            ).get_data_frames()[0]
            splits["TEAM_ID"] = team_id
            splits["TEAM_ABBREVIATION"] = abbr
            all_splits.append(splits)
            print("v")
        except Exception as e:
            print(f"x {e}")

    if all_splits:
        combined = pd.concat(all_splits, ignore_index=True)
        combined.to_csv(f"{DATA_DIR}/matchup_data.csv", index=False)
        print(f"\n  Saved matchup splits for {len(all_splits)} teams -> {DATA_DIR}/matchup_data.csv")
        return combined

    return pd.DataFrame()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  NBA Lineup Optimizer -- Data Pipeline")
    print(f"  Season: {SEASON}  |  Min Possessions: {MIN_POSSESSIONS}")
    print("=" * 60)

    team_df     = build_team_table()
    lineup_df   = build_lineup_data()
    tendency_df = build_team_tendencies()
    matchup_df  = build_matchup_data(team_df)

    print("\n" + "=" * 60)
    print("  Pipeline complete! Files saved to /data/")
    print("=" * 60)

    print("\nData Summary:")
    print(f"  Teams:          {len(team_df)}")
    print(f"  Lineups:        {len(lineup_df) if not lineup_df.empty else 0}")
    print(f"  Team profiles:  {len(tendency_df) if not tendency_df.empty else 0}")
    print(f"  Matchup splits: {len(matchup_df) if not matchup_df.empty else 0} rows")

if __name__ == "__main__":
    main()