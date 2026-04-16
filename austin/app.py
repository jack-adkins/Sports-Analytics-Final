"""
NBA Lineup Optimizer — Streamlit App
"""

import pandas as pd
import numpy as np
import streamlit as st

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="NBA Lineup Optimizer",
    page_icon="🏀",
    layout="wide"
)

# ── Load Data ─────────────────────────────────────────────────────────────────

@st.cache_data
def load_data():
    lineups     = pd.read_csv("data/lineups.csv")
    tendencies  = pd.read_csv("data/team_tendencies.csv")
    opp_shooting = pd.read_csv("data/opp_shooting.csv")
    teams_df    = pd.read_csv("data/teams.csv")
    return lineups, tendencies, opp_shooting, teams_df

lineups, tendencies, opp_shooting, teams_df = load_data()

# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize(series):
    min_val, max_val = series.min(), series.max()
    if max_val == min_val:
        return pd.Series([0.5] * len(series), index=series.index)
    return (series - min_val) / (max_val - min_val)

def get_team_id(abbr):
    return teams_df[teams_df["abbreviation"] == abbr].iloc[0]["team_id"]

def run_optimizer(home_abbr, opp_abbr):
    home_id = get_team_id(home_abbr)
    opp_id  = get_team_id(opp_abbr)

    # Filter home lineups
    home_lineups = lineups[lineups["TEAM_ID"] == home_id].copy()
    required = ["NET_RATING", "OFF_RATING", "DEF_RATING", "PACE", "PIE"]
    available = [c for c in required if c in home_lineups.columns]
    home_lineups = home_lineups.dropna(subset=available)

    if home_lineups.empty:
        return None, None, None

    # Opponent profile
    opp = tendencies[tendencies["TEAM_ID"] == opp_id].iloc[0]
    opp_shoot = opp_shooting[opp_shooting["TEAM_ID"] == opp_id]

    opp_pace = opp.get("PACE", 100)
    opp_off  = opp.get("OFF_RATING", 110)

    fg2_freq = opp_shoot.iloc[0].get("FG2A_FREQUENCY", 0.5) if not opp_shoot.empty else 0.5
    fg3_freq = opp_shoot.iloc[0].get("FG3A_FREQUENCY", 0.5) if not opp_shoot.empty else 0.5
    opp_paint_heavy = fg2_freq > 0.6
    opp_three_heavy = fg3_freq > 0.4

    # Weights
    w_net = 0.30; w_def = 0.25; w_off = 0.20; w_pace = 0.10; w_pie = 0.10; w_efg = 0.05

    adjustments = []
    if opp_paint_heavy:
        w_def += 0.10; w_off -= 0.05; w_pie -= 0.05
        adjustments.append(f"🎯 Paint-heavy offense (FG2 freq: {fg2_freq:.0%}) → DEF_RATING weight boosted")
    if opp_three_heavy:
        w_efg += 0.08; w_pace += 0.05; w_net -= 0.08; w_off -= 0.05
        adjustments.append(f"🎯 Three-heavy offense (FG3 freq: {fg3_freq:.0%}) → EFG & PACE weight boosted")
    if opp_pace > 102:
        w_def += 0.05; w_pie -= 0.05
        adjustments.append(f"⚡ Fast pace ({opp_pace:.1f}) → DEF_RATING weight boosted")
    if opp_off > 115:
        w_def += 0.05; w_net -= 0.05
        adjustments.append(f"💥 High-powered offense ({opp_off:.1f} OFF RTG) → DEF_RATING weight boosted")

    total = w_net + w_def + w_off + w_pace + w_pie + w_efg
    w_net /= total; w_def /= total; w_off /= total
    w_pace /= total; w_pie /= total; w_efg /= total

    weights = {
        "NET_RATING": w_net, "DEF_RATING": w_def, "OFF_RATING": w_off,
        "PACE": w_pace, "PIE": w_pie, "EFG_PCT": w_efg
    }

    # Score lineups
    home_lineups["DEF_RATING_INV"] = -home_lineups["DEF_RATING"]
    home_lineups["n_NET"]  = normalize(home_lineups["NET_RATING"])
    home_lineups["n_DEF"]  = normalize(home_lineups["DEF_RATING_INV"])
    home_lineups["n_OFF"]  = normalize(home_lineups["OFF_RATING"])
    home_lineups["n_PIE"]  = normalize(home_lineups["PIE"])
    home_lineups["n_EFG"]  = normalize(home_lineups["EFG_PCT"]) if "EFG_PCT" in home_lineups.columns else 0.5
    home_lineups["n_PACE"] = normalize(-home_lineups["PACE"]) if opp_pace > 100 else normalize(home_lineups["PACE"])

    home_lineups["MATCHUP_SCORE"] = (
        w_net  * home_lineups["n_NET"]  +
        w_def  * home_lineups["n_DEF"]  +
        w_off  * home_lineups["n_OFF"]  +
        w_pace * home_lineups["n_PACE"] +
        w_pie  * home_lineups["n_PIE"]  +
        w_efg  * home_lineups["n_EFG"]
    ) * 100

    # Usage gap
    total_min = home_lineups["MIN"].sum()
    home_lineups["USAGE_PCT"] = (home_lineups["MIN"] / total_min * 100).round(1)
    home_lineups["SCORE_RANK"] = home_lineups["MATCHUP_SCORE"].rank(ascending=False, na_option="bottom").fillna(999).astype(int)
    home_lineups["USAGE_RANK"] = home_lineups["USAGE_PCT"].rank(ascending=False, na_option="bottom").fillna(999).astype(int)
    home_lineups["RANK_GAP"]   = home_lineups["USAGE_RANK"] - home_lineups["SCORE_RANK"]

    def flag(row):
        if row["RANK_GAP"] > 10:   return "UNDERUSED"
        elif row["RANK_GAP"] < -10: return "OVERUSED"
        else:                        return "OK"

    home_lineups["STATUS"] = home_lineups.apply(flag, axis=1)
    home_lineups["MATCHUP_SCORE"] = home_lineups["MATCHUP_SCORE"].round(1)

    results = home_lineups.sort_values("MATCHUP_SCORE", ascending=False).reset_index(drop=True)
    return results, opp, adjustments, weights

# ── UI ────────────────────────────────────────────────────────────────────────

st.title("🏀 NBA Lineup Optimizer")
st.markdown("*Opponent-specific lineup recommendations for any NBA matchup*")
st.divider()

# Team selection
all_abbrs = sorted(teams_df["abbreviation"].tolist())
col1, col2 = st.columns(2)
with col1:
    home_team = st.selectbox("🏠 Home Team", all_abbrs, index=all_abbrs.index("BOS"))
with col2:
    opp_team = st.selectbox("✈️ Opponent", all_abbrs, index=all_abbrs.index("NYK"))

if home_team == opp_team:
    st.warning("Please select two different teams.")
    st.stop()

# Run optimizer
result = run_optimizer(home_team, opp_team)
if result[0] is None:
    st.error(f"No lineup data found for {home_team}. Try another team.")
    st.stop()

results, opp, adjustments, weights = result

st.divider()

# ── Opponent Profile ──────────────────────────────────────────────────────────

st.subheader(f"📊 {opp_team} Tendency Profile")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("OFF Rating", f"{opp.get('OFF_RATING', 'N/A'):.1f}")
c2.metric("DEF Rating", f"{opp.get('DEF_RATING', 'N/A'):.1f}")
c3.metric("Pace",       f"{opp.get('PACE', 'N/A'):.1f}")
c4.metric("EFG%",       f"{opp.get('EFG_PCT', 'N/A'):.1%}")
c5.metric("TOV%",       f"{opp.get('TM_TOV_PCT', 'N/A'):.1f}")

if adjustments:
    st.markdown("**Matchup Adjustments Applied:**")
    for a in adjustments:
        st.markdown(f"- {a}")

# ── Weight Breakdown ──────────────────────────────────────────────────────────

with st.expander("⚖️ Scoring Weights for This Matchup"):
    wcols = st.columns(len(weights))
    for i, (k, v) in enumerate(weights.items()):
        wcols[i].metric(k, f"{v:.0%}")

st.divider()

# ── Top Lineups ───────────────────────────────────────────────────────────────

st.subheader(f"🏆 Top Lineup Recommendations — {home_team} vs {opp_team}")

display_cols = ["GROUP_NAME", "MIN", "USAGE_PCT", "NET_RATING",
                "OFF_RATING", "DEF_RATING", "PACE", "PIE", "MATCHUP_SCORE", "STATUS"]
display_cols = [c for c in display_cols if c in results.columns]

top10 = results[display_cols].head(10).copy()
top10.index = range(1, len(top10) + 1)
top10.columns = [c.replace("_", " ") for c in top10.columns]

def color_status(val):
    if val == "UNDERUSED":   return "background-color: #1a472a; color: white"
    elif val == "OVERUSED":  return "background-color: #6b1a1a; color: white"
    return ""

def color_score(val):
    try:
        v = float(val)
        if v >= 75:   return "color: #00ff88; font-weight: bold"
        elif v >= 50: return "color: #ffdd57"
        else:         return "color: #ff6b6b"
    except:
        return ""

styled = top10.style.map(color_status, subset=["STATUS"]) \
                    .map(color_score, subset=["MATCHUP SCORE"]) \
                    .format(precision=1)
st.dataframe(styled, use_container_width=True, height=420)

st.divider()

# ── Usage Gap Analysis ────────────────────────────────────────────────────────

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🔴 Overused Lineups")
    st.caption("Playing too much given this matchup")
    overused = results[results["STATUS"] == "OVERUSED"][
        ["GROUP_NAME", "MIN", "USAGE_PCT", "MATCHUP_SCORE"]
    ].head(5)
    if overused.empty:
        st.success("No significantly overused lineups detected.")
    else:
        overused.index = range(1, len(overused) + 1)
        overused.columns = ["Lineup", "MIN", "Usage %", "Matchup Score"]
        st.dataframe(overused, use_container_width=True)

with col_b:
    st.subheader("🟢 Underused Lineups")
    st.caption("Not playing enough given this matchup")
    underused = results[results["STATUS"] == "UNDERUSED"][
        ["GROUP_NAME", "MIN", "USAGE_PCT", "MATCHUP_SCORE"]
    ].head(5)
    if underused.empty:
        st.info("No significantly underused lineups detected.")
    else:
        underused.index = range(1, len(underused) + 1)
        underused.columns = ["Lineup", "MIN", "Usage %", "Matchup Score"]
        st.dataframe(underused, use_container_width=True)

st.divider()

# ── Game Plan Summary ─────────────────────────────────────────────────────────

st.subheader("📋 Game Plan Summary")

top_lineup   = results.iloc[0]["GROUP_NAME"]
top_score    = results.iloc[0]["MATCHUP_SCORE"]
over_count   = len(results[results["STATUS"] == "OVERUSED"])
under_count  = len(results[results["STATUS"] == "UNDERUSED"])

most_overused = results[results["STATUS"] == "OVERUSED"].iloc[0]["GROUP_NAME"] if over_count > 0 else None
most_underused = results[results["STATUS"] == "UNDERUSED"].iloc[0]["GROUP_NAME"] if under_count > 0 else None

summary = f"""
**Best Matchup Lineup:** {top_lineup} *(Score: {top_score})*

Against {opp_team}'s tendencies, this lineup projects as {home_team}'s strongest unit.
"""
if most_overused:
    summary += f"\n\n**⚠️ Reduce Usage:** {most_overused} — this lineup is being overplayed relative to its matchup score against {opp_team}."
if most_underused:
    summary += f"\n\n**✅ Increase Usage:** {most_underused} — this lineup is being underutilized and projects well against {opp_team}'s style."

st.markdown(summary)

# Download button
csv = results[display_cols].to_csv(index=False)
st.download_button(
    label="⬇️ Download Full Recommendations CSV",
    data=csv,
    file_name=f"recommendations_{home_team}_vs_{opp_team}.csv",
    mime="text/csv"
)