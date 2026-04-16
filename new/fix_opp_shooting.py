"""
Quick fix — pulls opp shooting data with correct parameter name
and appends it to the existing data folder
"""
import time
import pandas as pd
from nba_api.stats.endpoints import leaguedashoppptshot
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

import inspect
sig = inspect.signature(leaguedashoppptshot.LeagueDashOppPtShot.__init__)
print("LeagueDashOppPtShot parameters:")
for name, param in sig.parameters.items():
    if name != "self":
        print(f"  {name} = {param.default}")

time.sleep(2)

# Try with no extra params first
try:
    df = leaguedashoppptshot.LeagueDashOppPtShot(
        season="2024-25",
        timeout=30,
    ).get_data_frames()[0]
    df.to_csv("data/opp_shooting.csv", index=False)
    print(f"\nv Saved {len(df)} rows -> data/opp_shooting.csv")
    print(f"  Columns: {df.columns.tolist()}")
except Exception as e:
    print(f"\nx ERROR: {e}")