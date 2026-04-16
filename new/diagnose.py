"""
Diagnostic script — figures out correct parameter names for your nba_api version
"""
import inspect
from nba_api.stats.endpoints import leaguedashteamstats, leaguedashlineups

print("=== LeagueDashTeamStats parameters ===")
sig = inspect.signature(leaguedashteamstats.LeagueDashTeamStats.__init__)
for name, param in sig.parameters.items():
    if name != "self":
        print(f"  {name} = {param.default}")

print("\n=== LeagueDashLineups parameters ===")
sig2 = inspect.signature(leaguedashlineups.LeagueDashLineups.__init__)
for name, param in sig2.parameters.items():
    if name != "self":
        print(f"  {name} = {param.default}")