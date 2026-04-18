"""
score_lineups.py
----------------
Scores every five-man lineup using NET_RATING and PIE, adjusted by a
possession-based confidence multiplier.

Confidence multiplier:
    - 50 possessions  → 0.75x
    - 200 possessions → 1.00x
    - Linear scale between, capped at 1.0 above 200

Output: data/lineups_scored.csv
"""

from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path("data")

# ── Load ──────────────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_DIR / "lineups_advanced.csv")

# ── Confidence multiplier ─────────────────────────────────────────────────────
# Linear scale: 0.75 at <=50 poss, 1.0 at >=200 poss
def confidence(poss):
    return np.clip(0.75 + 0.25 * (poss - 50) / (200 - 50), 0.75, 1.0)

df["CONF_MULT"] = confidence(df["POSS"]).round(4)

# ── Score ─────────────────────────────────────────────────────────────────────
# Combine NET_RATING and PIE — NET_RATING does most of the work,
# PIE adds a small secondary signal. Weights can be tuned later.
NET_WEIGHT = 0.8
PIE_WEIGHT = 0.2

# PIE is on a different scale (~0.5 = average), normalize it to be
# comparable to NET_RATING (centered at 0, similar spread)
pie_mean = df["PIE"].mean()
pie_std  = df["PIE"].std()
df["PIE_NORMALIZED"] = ((df["PIE"] - pie_mean) / pie_std) * df["NET_RATING"].std()

df["RAW_SCORE"]  = (NET_WEIGHT * df["NET_RATING"] + PIE_WEIGHT * df["PIE_NORMALIZED"]).round(3)
df["FINAL_SCORE"] = (df["RAW_SCORE"] * df["CONF_MULT"]).round(3)

# ── Select and sort output columns ────────────────────────────────────────────
out = df[[
    "TEAM_ABBREVIATION", "GROUP_NAME",
    "POSS", "MIN",
    "OFF_RATING", "DEF_RATING", "NET_RATING", "PIE",
    "CONF_MULT", "RAW_SCORE", "FINAL_SCORE",
]].sort_values("FINAL_SCORE", ascending=False).reset_index(drop=True)

out.index += 1  # rank starts at 1

# ── Save ──────────────────────────────────────────────────────────────────────
out.to_csv(DATA_DIR / "lineups_scored.csv", index_label="RANK")
print(f"Saved {len(out)} lineups → data/lineups_scored.csv")

# ── Preview ───────────────────────────────────────────────────────────────────
print("\nTop 10 lineups (all teams):")
print(out.head(10).to_string())