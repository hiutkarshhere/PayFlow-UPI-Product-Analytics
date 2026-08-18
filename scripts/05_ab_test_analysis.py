"""
05_ab_test_analysis.py

Analyzes the simplified-KYC-flow experiment run on April 2026 signups.
Metric: % of users who reach first_txn_success within 24 hours of
signup_started ("activated_within_24h"). Uses a two-proportion z-test,
matching how this would actually be evaluated before a product/eng team
ships a change.
"""

import pandas as pd
import numpy as np
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
VIZ = ROOT / "visuals"

sns.set_theme(style="whitegrid", context="talk")

ab = pd.read_csv(RAW / "ab_test_kyc_flow.csv")

summary = ab.groupby("ab_group").agg(
    users=("user_id", "count"),
    conversions=("activated_within_24h", "sum"),
)
summary["conversion_rate_pct"] = (summary["conversions"] / summary["users"] * 100).round(2)
print("=== A/B TEST: SIMPLIFIED KYC FLOW (April 2026 signups) ===")
print(summary.to_string())

n_control = summary.loc["control", "users"]
n_treatment = summary.loc["treatment", "users"]
x_control = summary.loc["control", "conversions"]
x_treatment = summary.loc["treatment", "conversions"]

p_control = x_control / n_control
p_treatment = x_treatment / n_treatment

# two-proportion z-test
p_pool = (x_control + x_treatment) / (n_control + n_treatment)
se = np.sqrt(p_pool * (1 - p_pool) * (1 / n_control + 1 / n_treatment))
z = (p_treatment - p_control) / se
p_value = 2 * (1 - stats.norm.cdf(abs(z)))

lift_abs_pp = (p_treatment - p_control) * 100
lift_rel_pct = (p_treatment - p_control) / p_control * 100

# 95% CI on the difference
se_diff = np.sqrt(p_control * (1 - p_control) / n_control + p_treatment * (1 - p_treatment) / n_treatment)
ci_low = (p_treatment - p_control) - 1.96 * se_diff
ci_high = (p_treatment - p_control) + 1.96 * se_diff

print(f"\nControl (original 3-step KYC):    {p_control*100:.2f}%  (n={n_control:,})")
print(f"Treatment (simplified 1-screen):  {p_treatment*100:.2f}%  (n={n_treatment:,})")
print(f"Absolute lift: {lift_abs_pp:+.2f} pp   |   Relative lift: {lift_rel_pct:+.1f}%")
print(f"Z-statistic: {z:.3f}   |   p-value: {p_value:.5f}")
print(f"95% CI on absolute lift: [{ci_low*100:+.2f} pp, {ci_high*100:+.2f} pp]")
print(f"Statistically significant at alpha=0.05: {'YES' if p_value < 0.05 else 'NO'}")

# minimum detectable effect / sample size sanity check for the writeup
print(f"\nSample size used: {n_control + n_treatment:,} users "
      f"(April 2026 signup cohort, 50/50 split)")

result = {
    "control_n": n_control, "control_conversions": x_control, "control_rate_pct": round(p_control * 100, 2),
    "treatment_n": n_treatment, "treatment_conversions": x_treatment, "treatment_rate_pct": round(p_treatment * 100, 2),
    "absolute_lift_pp": round(lift_abs_pp, 2), "relative_lift_pct": round(lift_rel_pct, 1),
    "z_statistic": round(z, 3), "p_value": round(p_value, 5),
    "ci_95_low_pp": round(ci_low * 100, 2), "ci_95_high_pp": round(ci_high * 100, 2),
    "significant_at_0.05": bool(p_value < 0.05),
}
pd.DataFrame([result]).to_csv(PROC / "ab_test_results.csv", index=False)

# ---------------------------------------------------------------------------
# Chart: conversion rate with 95% CI error bars
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7.5, 6))
groups = ["Control\n(3-step KYC)", "Treatment\n(1-screen KYC)"]
rates = [p_control * 100, p_treatment * 100]
errs = [
    1.96 * np.sqrt(p_control * (1 - p_control) / n_control) * 100,
    1.96 * np.sqrt(p_treatment * (1 - p_treatment) / n_treatment) * 100,
]
colors = sns.color_palette("crest", n_colors=2)
bars = ax.bar(groups, rates, yerr=errs, capsize=8, color=colors, width=0.55)
for bar, rate in zip(bars, rates):
    ax.text(bar.get_x() + bar.get_width() / 2, rate + 2.5, f"{rate:.1f}%", ha="center", fontsize=13)
ax.set_ylabel("% Activated Within 24h")
ax.set_title(f"KYC Flow A/B Test — {'Significant' if p_value < 0.05 else 'Not Significant'} "
             f"(p={p_value:.4f})")
ax.set_ylim(0, max(rates) + 15)
plt.tight_layout()
plt.savefig(VIZ / "07_ab_test_results.png", dpi=150)
plt.close()

print("\nSaved: visuals/07_ab_test_results.png")
print("Saved: data/processed/ab_test_results.csv")
