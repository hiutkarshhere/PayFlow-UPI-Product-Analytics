"""
03_cohort_retention.py

Builds a monthly signup-cohort retention matrix: of users who activated in
cohort month M, what % transacted at least once in month M, M+1, M+2, ...
This is the standard product-analytics retention curve (not to be confused
with the onboarding funnel, which is a one-time conversion path).
"""

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
VIZ = ROOT / "visuals"

sns.set_theme(style="white", context="talk")

users = pd.read_csv(RAW / "users.csv", parse_dates=["signup_date"])
txns = pd.read_csv(RAW / "transactions.csv", parse_dates=["txn_timestamp"])
txns = txns[txns.status == "SUCCESS"].copy()

funnel = pd.read_csv(RAW / "funnel_events.csv", parse_dates=["event_timestamp"])
activated = funnel[funnel.event_name == "first_txn_success"][["user_id", "event_timestamp"]]
activated = activated.rename(columns={"event_timestamp": "activation_date"})
activated["cohort_month"] = activated["activation_date"].dt.to_period("M")
# drop the sliver of activations that spilled into July from late-June
# signups with onboarding delay (n=88, not a real monthly cohort)
activated = activated[activated["cohort_month"] <= pd.Period("2026-06", freq="M")]

txns = txns.merge(activated[["user_id", "cohort_month"]], on="user_id", how="inner")
txns["txn_month"] = txns["txn_timestamp"].dt.to_period("M")
txns["month_index"] = (
    (txns["txn_month"].astype(int) - txns["cohort_month"].astype(int))
)
txns = txns[txns.month_index >= 0]

cohort_sizes = activated.groupby("cohort_month")["user_id"].nunique()

retention = (
    txns.groupby(["cohort_month", "month_index"])["user_id"]
    .nunique()
    .unstack(fill_value=0)
)
retention_pct = retention.div(cohort_sizes, axis=0) * 100
retention_pct = retention_pct.round(1)

# mask cells that fall beyond the observation window (data doesn't exist yet)
# rather than showing a misleading 0% for "not yet observed"
last_data_period = pd.Period("2026-06", freq="M")
for cohort in retention_pct.index:
    max_valid_month_index = (last_data_period - cohort).n
    for col in retention_pct.columns:
        if col > max_valid_month_index:
            retention_pct.loc[cohort, col] = np.nan

retention_pct.to_csv(PROC / "cohort_retention_matrix.csv")

print("=== COHORT SIZES (activated users per signup month) ===")
print(cohort_sizes.to_string())

print("\n=== RETENTION % MATRIX (rows=cohort month, cols=months since activation) ===")
print(retention_pct.to_string())

# blended retention curve across all cohorts (weighted by cohort size)
blended = (retention.sum(axis=0) / cohort_sizes.sum() * 100).round(1)
print("\n=== BLENDED RETENTION CURVE (all cohorts combined) ===")
print(blended.to_string())

blended.to_csv(PROC / "blended_retention_curve.csv", header=["retention_pct"])

# ---------------------------------------------------------------------------
# Chart 1: Retention heatmap
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 6))
mask = retention_pct.isna()
sns.heatmap(retention_pct, annot=True, fmt=".0f", cmap="crest", cbar_kws={"label": "% Retained"},
            linewidths=0.5, ax=ax, vmin=0, vmax=100)
ax.set_xlabel("Months Since Activation")
ax.set_ylabel("Signup Cohort")
ax.set_title("PayFlow Monthly Cohort Retention (% of activated users transacting)")
plt.tight_layout()
plt.savefig(VIZ / "03_cohort_retention_heatmap.png", dpi=150)
plt.close()

# ---------------------------------------------------------------------------
# Chart 2: Blended retention curve
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.plot(blended.index.astype(int), blended.values, marker="o", linewidth=2.5,
        color=sns.color_palette("crest", 6)[4])
ax.set_xlabel("Months Since Activation")
ax.set_ylabel("% of Activated Users Still Transacting")
ax.set_title("Blended Retention Curve — All Cohorts")
ax.set_ylim(0, 100)
for x, y in zip(blended.index.astype(int), blended.values):
    ax.annotate(f"{y:.0f}%", (x, y), textcoords="offset points", xytext=(0, 10), ha="center")
plt.tight_layout()
plt.savefig(VIZ / "04_blended_retention_curve.png", dpi=150)
plt.close()

print("\nSaved: visuals/03_cohort_retention_heatmap.png, visuals/04_blended_retention_curve.png")
print("Saved: data/processed/cohort_retention_matrix.csv, data/processed/blended_retention_curve.csv")
