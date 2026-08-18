"""
04_user_segmentation.py

Segments activated users using an RFM-style framework (Recency, Frequency,
Monetary value) computed from real transaction behavior in the dataset, then
maps segments to actionable product recommendations. This is deliberately
built from raw transactions rather than reusing the archetype labels baked
into the generator -- i.e. the segmentation "rediscovers" behavioral groups
from data the way an analyst would on a real production table, without
peeking at ground truth.
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

sns.set_theme(style="whitegrid", context="talk")

txns = pd.read_csv(RAW / "transactions.csv", parse_dates=["txn_timestamp"])
txns = txns[txns.status == "SUCCESS"].copy()

ANALYSIS_DATE = pd.Timestamp("2026-06-30")

rfm = txns.groupby("user_id").agg(
    recency_days=("txn_timestamp", lambda s: (ANALYSIS_DATE - s.max()).days),
    frequency=("transaction_id", "count"),
    monetary_inr=("amount_inr", "sum"),
).reset_index()

# quantile scoring: 1 (worst) - 4 (best) for each dimension
rfm["r_score"] = pd.qcut(rfm["recency_days"], 4, labels=[4, 3, 2, 1]).astype(int)
rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
rfm["m_score"] = pd.qcut(rfm["monetary_inr"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]


def label_segment(row):
    if row["r_score"] >= 3 and row["f_score"] >= 3 and row["m_score"] >= 3:
        return "Power Users"
    if row["r_score"] >= 3 and row["f_score"] >= 2:
        return "Regular Users"
    if row["r_score"] <= 2 and row["f_score"] >= 3:
        return "At-Risk (was frequent, going quiet)"
    if row["r_score"] == 1 and row["f_score"] <= 2:
        return "Dormant / Churned"
    return "Casual / New"


rfm["segment"] = rfm.apply(label_segment, axis=1)

segment_summary = rfm.groupby("segment").agg(
    users=("user_id", "count"),
    avg_recency_days=("recency_days", "mean"),
    avg_frequency=("frequency", "mean"),
    avg_monetary_inr=("monetary_inr", "mean"),
    total_gtv_inr=("monetary_inr", "sum"),
).round(1).sort_values("users", ascending=False)

total_activated = rfm.shape[0]
segment_summary["pct_of_activated_users"] = (segment_summary["users"] / total_activated * 100).round(1)
segment_summary["pct_of_total_gtv"] = (segment_summary["total_gtv_inr"] / segment_summary["total_gtv_inr"].sum() * 100).round(1)

rfm.to_csv(PROC / "rfm_user_scores.csv", index=False)
segment_summary.to_csv(PROC / "segment_summary.csv")

print("=== SEGMENT SUMMARY ===")
print(segment_summary.to_string())

print(f"\nTotal activated users analyzed: {total_activated:,}")
print(f"Total GTV in window: Rs {rfm['monetary_inr'].sum():,.0f}")

top_segment = segment_summary.sort_values("total_gtv_inr", ascending=False).iloc[0]
print(f"\nHighest-value segment: {segment_summary.sort_values('total_gtv_inr', ascending=False).index[0]} "
      f"({top_segment['pct_of_activated_users']}% of users drive {top_segment['pct_of_total_gtv']}% of GTV)")

# ---------------------------------------------------------------------------
# Chart 1: Segment size vs GTV contribution
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
order = segment_summary.sort_values("pct_of_activated_users", ascending=False).index

colors = sns.color_palette("crest", n_colors=len(order))
axes[0].bar(order, segment_summary.loc[order, "pct_of_activated_users"], color=colors)
axes[0].set_title("% of Activated Users")
axes[0].set_ylabel("% of Users")
axes[0].tick_params(axis="x", rotation=35)
for label in axes[0].get_xticklabels():
    label.set_ha("right")

axes[1].bar(order, segment_summary.loc[order, "pct_of_total_gtv"], color=colors)
axes[1].set_title("% of Total GTV Contributed")
axes[1].set_ylabel("% of GTV")
axes[1].tick_params(axis="x", rotation=35)
for label in axes[1].get_xticklabels():
    label.set_ha("right")

fig.suptitle("User Base Size vs. Transaction Value Contribution by Segment")
plt.tight_layout()
plt.savefig(VIZ / "05_segment_users_vs_gtv.png", dpi=150)
plt.close()

# ---------------------------------------------------------------------------
# Chart 2: Frequency vs Monetary scatter colored by segment
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 7))
sample = rfm.sample(n=min(8000, len(rfm)), random_state=42)
sns.scatterplot(data=sample, x="frequency", y="monetary_inr", hue="segment",
                 palette="crest", alpha=0.55, s=28, ax=ax)
ax.set_yscale("log")
ax.set_xlabel("Transaction Frequency (count, Jan–Jun 2026)")
ax.set_ylabel("Total Monetary Value (Rs, log scale)")
ax.set_title("User Segments by Frequency & Monetary Value")
ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=10)
plt.tight_layout()
plt.savefig(VIZ / "06_rfm_scatter.png", dpi=150)
plt.close()

print("\nSaved: visuals/05_segment_users_vs_gtv.png, visuals/06_rfm_scatter.png")
print("Saved: data/processed/rfm_user_scores.csv, data/processed/segment_summary.csv")
