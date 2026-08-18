"""
02_funnel_analysis.py

Computes onboarding funnel conversion (signup -> activated transactor) both
overall and by acquisition channel, using pandas. Outputs a summary CSV and
a seaborn funnel chart.
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
PROC.mkdir(parents=True, exist_ok=True)
VIZ.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")

users = pd.read_csv(RAW / "users.csv")
funnel = pd.read_csv(RAW / "funnel_events.csv")

STAGE_ORDER = [
    "signup_started", "otp_verified", "bank_linked", "upi_pin_set",
    "kyc_completed", "first_txn_attempted", "first_txn_success",
]
STAGE_LABELS = {
    "signup_started": "Signup Started",
    "otp_verified": "OTP Verified",
    "bank_linked": "Bank Account Linked",
    "upi_pin_set": "UPI PIN Set",
    "kyc_completed": "KYC Completed",
    "first_txn_attempted": "First Txn Attempted",
    "first_txn_success": "First Txn Success (Activated)",
}

# distinct users reaching each stage
reached = funnel.groupby("event_name")["user_id"].nunique().reindex(STAGE_ORDER)
total_signups = reached["signup_started"]

funnel_summary = pd.DataFrame({
    "stage": [STAGE_LABELS[s] for s in STAGE_ORDER],
    "users_reached": reached.values,
    "pct_of_total": (reached.values / total_signups * 100).round(2),
})
funnel_summary["step_conversion_pct"] = (
    reached.values / reached.shift(1).values * 100
).round(2)
funnel_summary.loc[0, "step_conversion_pct"] = 100.0

funnel_summary.to_csv(PROC / "funnel_summary.csv", index=False)

overall_conversion = reached["first_txn_success"] / total_signups * 100
print("=== OVERALL FUNNEL (signup -> activated) ===")
print(funnel_summary.to_string(index=False))
print(f"\nOverall signup -> activation conversion: {overall_conversion:.2f}%")
print(f"Biggest single drop-off: ", end="")
biggest_drop = funnel_summary.iloc[1:].sort_values("step_conversion_pct").iloc[0]
print(f"{biggest_drop['stage']} ({biggest_drop['step_conversion_pct']:.2f}% step conversion)")

# ---------------------------------------------------------------------------
# Funnel by acquisition channel
# ---------------------------------------------------------------------------
funnel_with_channel = funnel.merge(users[["user_id", "acquisition_channel"]], on="user_id")
by_channel = (
    funnel_with_channel.groupby(["acquisition_channel", "event_name"])["user_id"]
    .nunique()
    .unstack(fill_value=0)
    .reindex(columns=STAGE_ORDER)
)
by_channel_conv = by_channel.div(by_channel["signup_started"], axis=0) * 100
by_channel_conv = by_channel_conv.round(2)
by_channel_conv.to_csv(PROC / "funnel_by_channel.csv")

print("\n=== ACTIVATION RATE (signup -> first_txn_success) BY CHANNEL ===")
channel_activation = by_channel_conv["first_txn_success"].sort_values(ascending=False)
print(channel_activation.to_string())

# ---------------------------------------------------------------------------
# Chart 1: Overall funnel bar chart
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 6.5))
colors = sns.color_palette("crest", n_colors=len(STAGE_ORDER))
bars = ax.barh(funnel_summary["stage"][::-1], funnel_summary["pct_of_total"][::-1], color=colors[::-1])
for bar, pct, n in zip(bars, funnel_summary["pct_of_total"][::-1], funnel_summary["users_reached"][::-1]):
    ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2,
            f"{pct:.1f}%  ({n:,})", va="center", fontsize=11)
ax.set_xlabel("% of Total Signups Reaching Stage")
ax.set_title("PayFlow Onboarding Funnel — Signup to Activated Transactor\n(Jan–Jun 2026, n=50,500 signups)")
ax.set_xlim(0, 115)
plt.tight_layout()
plt.savefig(VIZ / "01_onboarding_funnel.png", dpi=150)
plt.close()

# ---------------------------------------------------------------------------
# Chart 2: Activation rate by channel
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5.5))
channel_activation.plot(kind="bar", ax=ax, color=sns.color_palette("crest", n_colors=4))
ax.set_ylabel("Signup → Activation Rate (%)")
ax.set_xlabel("Acquisition Channel")
ax.set_title("Activation Rate by Acquisition Channel")
ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
for i, v in enumerate(channel_activation.values):
    ax.text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=11)
plt.tight_layout()
plt.savefig(VIZ / "02_activation_by_channel.png", dpi=150)
plt.close()

print("\nSaved: visuals/01_onboarding_funnel.png, visuals/02_activation_by_channel.png")
print("Saved: data/processed/funnel_summary.csv, data/processed/funnel_by_channel.csv")
