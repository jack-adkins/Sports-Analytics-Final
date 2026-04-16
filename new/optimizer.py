"""
NBA Lineup Optimizer — Matchup Scoring Model
=============================================
Given a home team and an opponent, scores every lineup the home
team has used this season based on how well it matches up against
that specific opponent's tendencies.

Usage:
    python optimizer.py

Outputs:
    - Ranked lineup recommendations printed to terminal
    - data/recommendations_<TEAM>_vs_<OPP>.csv
"""

import pandas as pd
import numpy as np

# ── Load Data ─────────────────────────────────────────────────────────────────

lineups     = pd.read_csv("data/lineups.csv")
tendencies  = pd.read_csv("data/team_tendencies.csv")
opp_shooting = pd.read_csv("data/opp_shooting.csv")
teams_df    = pd.read_csv("data/teams.csv")

# ── Team Selection ────────────────────────────────────────────────────────────

HOME_TEAM = "BOS"   # Change to any team abbreviation
OPPONENT  = "NYK"   # Change to any opponent abbreviation

# ── Helper: get team ID from abbreviation ─────────────────────────────────────

def get_team_id(abbr):
    match = teams_df[teams_df["abbreviation"] == abbr]
    if match.empty:
        raise ValueError(f"Team abbreviation '{abbr}' not found. Check teams.csv for valid abbreviations.")
    return match.iloc[0]["team_id"]

home_id = get_team_id(HOME_TEAM)
opp_id  = get_team_id(OPPONENT)

print("=" * 60)
print(f"  NBA Lineup Optimizer")
print(f"  {HOME_TEAM} vs {OPPONENT}")
print("=" * 60)

# ── Step 1: Filter home team lineups ─────────────────────────────────────────

home_lineups = lineups[lineups["TEAM_ID"] == home_id].copy()
print(f"\n[1/4] Home team lineups: {len(home_lineups)} qualified lineups for {HOME_TEAM}")

if home_lineups.empty:
    print(f"  ERROR: No lineups found for {HOME_TEAM}. Check the abbreviation.")
    exit()

# ── Step 2: Build opponent tendency profile ───────────────────────────────────

opp_tendency = tendencies[tendencies["TEAM_ID"] == opp_id]
opp_shoot    = opp_shooting[opp_shooting["TEAM_ID"] == opp_id]

if opp_tendency.empty:
    print(f"  ERROR: No tendency data found for {OPPONENT}.")
    exit()

opp = opp_tendency.iloc[0]
print(f"\n[2/4] Opponent tendency profile for {OPPONENT}:")
print(f"  OFF_RATING:  {opp.get('OFF_RATING', 'N/A'):.1f}")
print(f"  DEF_RATING:  {opp.get('DEF_RATING', 'N/A'):.1f}")
print(f"  PACE:        {opp.get('PACE', 'N/A'):.1f}")
print(f"  EFG_PCT:     {opp.get('EFG_PCT', 'N/A'):.3f}")
print(f"  TM_TOV_PCT:  {opp.get('TM_TOV_PCT', 'N/A'):.1f}")
print(f"  OREB_PCT:    {opp.get('OREB_PCT', 'N/A'):.3f}")

# Opponent shooting zones
if not opp_shoot.empty:
    os = opp_shoot.iloc[0]
    fg2_freq = os.get("FG2A_FREQUENCY", 0.5)
    fg3_freq = os.get("FG3A_FREQUENCY", 0.5)
    opp_paint_heavy = fg2_freq > 0.6   # Opponent heavily uses paint
    opp_three_heavy = fg3_freq > 0.4   # Opponent heavily uses threes
else:
    opp_paint_heavy = False
    opp_three_heavy = False

# ── Step 3: Build matchup scoring weights ─────────────────────────────────────
#
# The weights adjust based on what the opponent emphasizes.
# If they are paint-heavy → prioritize our DEF_RATING (rim protection)
# If they are three-heavy → prioritize our PACE control and EFG_PCT
# If they are high pace   → prioritize our transition defense (DEF_RATING)
# If they are high OFF    → prioritize our DEF_RATING even more
#
print(f"\n[3/4] Building matchup weights for {OPPONENT}...")

opp_pace      = opp.get("PACE", 100)
opp_off       = opp.get("OFF_RATING", 110)
opp_tov       = opp.get("TM_TOV_PCT", 13)
opp_oreb      = opp.get("OREB_PCT", 0.25)

# Base weights
w_net_rating  = 0.30   # Overall lineup quality always matters
w_def_rating  = 0.25   # Defensive quality
w_off_rating  = 0.20   # Offensive quality
w_pace        = 0.10   # Pace control
w_pie         = 0.10   # Player Impact Estimate (overall efficiency)
w_efg         = 0.05   # Shooting efficiency

# Adjust weights based on opponent tendencies
if opp_paint_heavy:
    print(f"  Opponent is paint-heavy (FG2 freq: {fg2_freq:.0%}) -> boosting DEF_RATING weight")
    w_def_rating += 0.10
    w_off_rating -= 0.05
    w_pie        -= 0.05

if opp_three_heavy:
    print(f"  Opponent is three-heavy (FG3 freq: {fg3_freq:.0%}) -> boosting EFG_PCT and PACE weight")
    w_efg        += 0.08
    w_pace       += 0.05
    w_net_rating -= 0.08
    w_off_rating -= 0.05

if opp_pace > 102:
    print(f"  Opponent plays fast (PACE: {opp_pace:.1f}) -> boosting DEF_RATING weight")
    w_def_rating += 0.05
    w_pie        -= 0.05

if opp_off > 115:
    print(f"  Opponent is high-powered offense (OFF_RATING: {opp_off:.1f}) -> boosting DEF_RATING weight")
    w_def_rating += 0.05
    w_net_rating -= 0.05

# Normalize weights to sum to 1
total = w_net_rating + w_def_rating + w_off_rating + w_pace + w_pie + w_efg
w_net_rating /= total
w_def_rating /= total
w_off_rating /= total
w_pace       /= total
w_pie        /= total
w_efg        /= total

print(f"\n  Final weights:")
print(f"    NET_RATING:  {w_net_rating:.2f}")
print(f"    DEF_RATING:  {w_def_rating:.2f}")
print(f"    OFF_RATING:  {w_off_rating:.2f}")
print(f"    PACE:        {w_pace:.2f}")
print(f"    PIE:         {w_pie:.2f}")
print(f"    EFG_PCT:     {w_efg:.2f}")

# ── Step 4: Score each lineup ─────────────────────────────────────────────────

def normalize(series):
    """Normalize a series to 0-1 scale."""
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series([0.5] * len(series), index=series.index)
    return (series - min_val) / (max_val - min_val)

# DEF_RATING is inverted — lower is better
home_lineups = home_lineups.copy()
home_lineups["DEF_RATING_INV"] = -home_lineups["DEF_RATING"]

# Normalize each metric
home_lineups["n_NET"]  = normalize(home_lineups["NET_RATING"])
home_lineups["n_DEF"]  = normalize(home_lineups["DEF_RATING_INV"])
home_lineups["n_OFF"]  = normalize(home_lineups["OFF_RATING"])
home_lineups["n_PIE"]  = normalize(home_lineups["PIE"])
home_lineups["n_EFG"]  = normalize(home_lineups["EFG_PCT"]) if "EFG_PCT" in home_lineups.columns else 0.5

# PACE: if opponent is fast, reward lineups with lower pace (they slow it down)
# if opponent is slow, reward lineups with higher pace (they can push tempo)
if opp_pace > 100:
    home_lineups["n_PACE"] = normalize(-home_lineups["PACE"])  # reward slower lineups
else:
    home_lineups["n_PACE"] = normalize(home_lineups["PACE"])   # reward faster lineups

# Compute matchup score
home_lineups["MATCHUP_SCORE"] = (
    w_net_rating * home_lineups["n_NET"]  +
    w_def_rating * home_lineups["n_DEF"]  +
    w_off_rating * home_lineups["n_OFF"]  +
    w_pace       * home_lineups["n_PACE"] +
    w_pie        * home_lineups["n_PIE"]  +
    w_efg        * home_lineups["n_EFG"]
)

# Scale to 0-100 for readability
home_lineups["MATCHUP_SCORE"] = (home_lineups["MATCHUP_SCORE"] * 100).round(1)

# ── Step 5: Usage gap analysis ────────────────────────────────────────────────

# Estimate usage share from minutes
total_min = home_lineups["MIN"].sum()
home_lineups["USAGE_PCT"] = (home_lineups["MIN"] / total_min * 100).round(1)

# Expected usage based on matchup score rank
home_lineups["SCORE_RANK"]  = home_lineups["MATCHUP_SCORE"].rank(ascending=False, na_option="bottom").fillna(999).astype(int)
home_lineups["USAGE_RANK"]  = home_lineups["USAGE_PCT"].rank(ascending=False, na_option="bottom").fillna(999).astype(int)
home_lineups["RANK_GAP"]    = home_lineups["USAGE_RANK"] - home_lineups["SCORE_RANK"]

# Flag lineups
def flag(row):
    if row["RANK_GAP"] > 10:
        return "UNDERUSED"
    elif row["RANK_GAP"] < -10:
        return "OVERUSED"
    else:
        return "OK"

home_lineups["STATUS"] = home_lineups.apply(flag, axis=1)

# ── Step 6: Output results ────────────────────────────────────────────────────

cols_out = ["GROUP_NAME", "MIN", "USAGE_PCT", "NET_RATING", "OFF_RATING",
            "DEF_RATING", "PACE", "PIE", "MATCHUP_SCORE", "STATUS"]
cols_out = [c for c in cols_out if c in home_lineups.columns]

results = home_lineups[cols_out].sort_values("MATCHUP_SCORE", ascending=False).reset_index(drop=True)

print(f"\n[4/4] Top 10 Recommended Lineups for {HOME_TEAM} vs {OPPONENT}:")
print("=" * 60)
pd.set_option("display.max_colwidth", 50)
pd.set_option("display.width", 200)
print(results.head(10).to_string(index=True))

print(f"\nOverused Lineups (playing too much given matchup):")
overused = results[results["STATUS"] == "OVERUSED"][["GROUP_NAME", "MIN", "USAGE_PCT", "MATCHUP_SCORE"]]
print(overused.head(5).to_string(index=False) if not overused.empty else "  None flagged.")

print(f"\nUnderused Lineups (not playing enough given matchup):")
underused = results[results["STATUS"] == "UNDERUSED"][["GROUP_NAME", "MIN", "USAGE_PCT", "MATCHUP_SCORE"]]
print(underused.head(5).to_string(index=False) if not underused.empty else "  None flagged.")

# Save to CSV
out_path = f"data/recommendations_{HOME_TEAM}_vs_{OPPONENT}.csv"
results.to_csv(out_path, index=False)
print(f"\nFull results saved -> {out_path}")
print("=" * 60)