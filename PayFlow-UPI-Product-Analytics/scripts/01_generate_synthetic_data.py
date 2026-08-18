"""
01_generate_synthetic_data.py

Generates a synthetic but behaviorally realistic dataset for PayFlow, a
fictional UPI-based payments app modeled on real Indian UPI product patterns
(PhonePe / Google Pay / Paytm class apps).

Why synthetic data: no public dataset covering UPI-level transaction and
funnel behavior exists for external analysts. Instead of using a proxy
dataset (e.g. e-commerce data relabeled as "fintech"), this script encodes
explicit, documented assumptions about user behavior and generates data from
them. Every number reported in the README is computed from the CSVs this
script produces, not invented after the fact.

Assumptions are listed in docs/assumptions.md.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

SEED = 42
rng = np.random.default_rng(SEED)

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. TIME WINDOW
# ---------------------------------------------------------------------------
SIM_START = datetime(2026, 1, 1)
SIM_END = datetime(2026, 6, 30)
N_MONTHS = 6
MONTH_STARTS = [SIM_START + pd.DateOffset(months=i) for i in range(N_MONTHS)]

# ---------------------------------------------------------------------------
# 2. USER ACQUISITION
# ---------------------------------------------------------------------------
# Monthly signup volume: modest organic base + marketing push ramping up
# mid-period (mirrors a real growth-stage fintech running quarterly campaigns)
MONTHLY_SIGNUPS = [6200, 6800, 9400, 10100, 8700, 9300]  # sums to 50,500
TOTAL_USERS = sum(MONTHLY_SIGNUPS)

CHANNELS = ["organic", "referral", "paid_ads", "partner_bank"]
CHANNEL_WEIGHTS = [0.40, 0.25, 0.20, 0.15]

CITY_TIERS = ["Tier 1", "Tier 2", "Tier 3"]
CITY_WEIGHTS = [0.35, 0.40, 0.25]

DEVICE_OS = ["Android", "iOS"]
DEVICE_WEIGHTS = [0.87, 0.13]

AGE_BRACKETS = ["18-24", "25-34", "35-44", "45-54", "55+"]
AGE_WEIGHTS = [0.22, 0.38, 0.24, 0.11, 0.05]

user_rows = []
uid = 100000
for month_idx, (month_start, n_signups) in enumerate(zip(MONTH_STARTS, MONTHLY_SIGNUPS)):
    month_end = month_start + pd.DateOffset(months=1) - pd.Timedelta(days=1)
    days_in_month = (month_end - month_start).days + 1
    # signups slightly front-loaded early in month (salary-day / campaign effect)
    day_offsets = rng.triangular(0, 3, days_in_month - 1, n_signups).astype(int)
    signup_dates = [month_start + timedelta(days=int(d)) for d in day_offsets]

    channels = rng.choice(CHANNELS, size=n_signups, p=CHANNEL_WEIGHTS)
    tiers = rng.choice(CITY_TIERS, size=n_signups, p=CITY_WEIGHTS)
    devices = rng.choice(DEVICE_OS, size=n_signups, p=DEVICE_WEIGHTS)
    ages = rng.choice(AGE_BRACKETS, size=n_signups, p=AGE_WEIGHTS)

    for i in range(n_signups):
        user_rows.append({
            "user_id": uid,
            "signup_date": signup_dates[i],
            "signup_month": month_start.strftime("%Y-%m"),
            "acquisition_channel": channels[i],
            "city_tier": tiers[i],
            "device_os": devices[i],
            "age_bracket": ages[i],
        })
        uid += 1

users = pd.DataFrame(user_rows)

# ---------------------------------------------------------------------------
# 3. ONBOARDING FUNNEL
# ---------------------------------------------------------------------------
# Stage-wise conversion probabilities, each conditional on reaching the prior
# stage. Referral users convert slightly better (trust transfer); paid_ads
# users convert slightly worse (colder intent). partner_bank users convert
# best (pre-vetted, bank already trusts them).
BASE_STAGE_RATES = {
    "otp_verified": 0.92,
    "bank_linked": 0.85,
    "upi_pin_set": 0.93,
    "kyc_completed": 0.78,
    "first_txn_attempted": 0.88,
    "first_txn_success": 0.95,
}
CHANNEL_MODIFIER = {
    "organic": 0.0,
    "referral": 0.03,
    "paid_ads": -0.05,
    "partner_bank": 0.06,
}

STAGES = ["signup_started"] + list(BASE_STAGE_RATES.keys())

funnel_rows = []
user_channel = users.set_index("user_id")["acquisition_channel"].to_dict()
user_signup = users.set_index("user_id")["signup_date"].to_dict()

for _, row in users.iterrows():
    u = row["user_id"]
    t = row["signup_date"]
    mod = CHANNEL_MODIFIER[row["acquisition_channel"]]
    funnel_rows.append({"user_id": u, "event_name": "signup_started",
                         "event_timestamp": t, "stage_order": 0})
    reached = True
    for order, (stage, base_p) in enumerate(BASE_STAGE_RATES.items(), start=1):
        if not reached:
            break
        p = min(max(base_p + mod, 0.05), 0.99)
        if rng.random() < p:
            # each stage happens some minutes/hours/days after the previous
            delay_hours = rng.exponential(scale=6 if order <= 3 else 30)
            t = t + timedelta(hours=float(delay_hours))
            funnel_rows.append({"user_id": u, "event_name": stage,
                                 "event_timestamp": t, "stage_order": order})
        else:
            reached = False

funnel = pd.DataFrame(funnel_rows)

# ---------------------------------------------------------------------------
# 4. POST-ACTIVATION USER SEGMENTS (behavioral archetypes)
# ---------------------------------------------------------------------------
# Only users who reached first_txn_success are "activated" and can transact
# further. Assign each activated user a behavioral archetype that drives
# transaction frequency going forward.
activated_users = funnel.loc[funnel.event_name == "first_txn_success", "user_id"].unique()
activated_users = pd.Index(activated_users)

ARCHETYPES = ["power", "regular", "casual", "at_risk"]
ARCHETYPE_WEIGHTS = [0.15, 0.35, 0.30, 0.20]
archetype_map = pd.Series(
    rng.choice(ARCHETYPES, size=len(activated_users), p=ARCHETYPE_WEIGHTS),
    index=activated_users,
)

# Monthly transaction-count distribution per archetype (Poisson lambda)
ARCHETYPE_LAMBDA = {"power": 22, "regular": 9, "casual": 2.5, "at_risk": 0.8}
# Probability an archetype keeps transacting into month N after activation
# (drives retention curve). at_risk decays fast; power barely decays.
ARCHETYPE_DECAY = {"power": 0.04, "regular": 0.10, "casual": 0.18, "at_risk": 0.42}

MERCHANT_CATEGORIES = ["Groceries", "Food Delivery", "Bill Payments", "Recharge",
                        "Shopping", "Travel", "Fuel", "Entertainment", "Rent", "Other"]
MERCHANT_WEIGHTS = [0.18, 0.15, 0.14, 0.10, 0.12, 0.06, 0.09, 0.06, 0.05, 0.05]

FAILURE_REASONS = ["Bank server timeout", "Insufficient balance",
                    "Incorrect UPI PIN", "Daily limit exceeded", "Payee bank down"]
FAILURE_WEIGHTS = [0.32, 0.27, 0.18, 0.13, 0.10]

txn_rows = []
tid = 500000
activation_time = funnel.loc[funnel.event_name == "first_txn_success"].set_index("user_id")["event_timestamp"]

for u in activated_users:
    arche = archetype_map[u]
    lam = ARCHETYPE_LAMBDA[arche]
    decay = ARCHETYPE_DECAY[arche]
    start_t = activation_time[u]
    # simulate month-by-month from activation to SIM_END
    cursor = start_t
    month_i = 0
    still_active = True
    while cursor < SIM_END and still_active:
        n_txns_this_month = rng.poisson(lam=max(lam * ((1 - decay) ** month_i), 0.05))
        if month_i == 0:
            # activation month must contain at least the triggering "first
            # successful transaction" -- a user can't be "activated" with
            # zero recorded transactions
            n_txns_this_month = max(n_txns_this_month, 1)
        for _ in range(int(n_txns_this_month)):
            offset_days = rng.uniform(0, 30)
            ts = cursor + timedelta(days=float(offset_days))
            if ts > SIM_END:
                continue
            is_p2m = rng.random() < 0.47
            if is_p2m:
                amount = float(np.round(rng.lognormal(mean=6.2, sigma=0.9), 2))
                category = rng.choice(MERCHANT_CATEGORIES, p=MERCHANT_WEIGHTS)
            else:
                amount = float(np.round(rng.lognormal(mean=5.6, sigma=0.8), 2))
                category = "P2P Transfer"
            amount = float(np.clip(amount, 10, 200000))
            failed = rng.random() < 0.035
            status = "FAILED" if failed else "SUCCESS"
            failure_reason = rng.choice(FAILURE_REASONS, p=FAILURE_WEIGHTS) if failed else None
            txn_rows.append({
                "transaction_id": tid,
                "user_id": u,
                "txn_timestamp": ts,
                "txn_type": "P2M" if is_p2m else "P2P",
                "merchant_category": category,
                "amount_inr": amount,
                "status": status,
                "failure_reason": failure_reason,
            })
            tid += 1
        # chance the user churns entirely after this month
        if rng.random() < decay * 0.5:
            still_active = False
        cursor = cursor + pd.DateOffset(months=1)
        month_i += 1

transactions = pd.DataFrame(txn_rows)

# ---------------------------------------------------------------------------
# 5. A/B TEST: SIMPLIFIED KYC FLOW EXPERIMENT
# ---------------------------------------------------------------------------
# Ran on users who signed up in month 4 (April 2026) only, 50/50 split.
# Treatment = redesigned single-screen KYC vs Control = original 3-step KYC.
# Metric: reached first_txn_success within 24 hours of signup_started.
april_users = users[users.signup_month == "2026-04"].copy()
april_users["ab_group"] = rng.choice(["control", "treatment"], size=len(april_users), p=[0.5, 0.5])

# baseline (control) prob of activating within 24h ~ 0.41; treatment gets a
# genuine but modest lift from friction reduction ~ +6.5pp
CONTROL_P = 0.41
TREATMENT_LIFT = 0.065

def activated_within_24h(user_id):
    events = funnel[(funnel.user_id == user_id)]
    if "first_txn_success" not in events.event_name.values:
        return False
    start = events.loc[events.event_name == "signup_started", "event_timestamp"].iloc[0]
    end = events.loc[events.event_name == "first_txn_success", "event_timestamp"].iloc[0]
    return (end - start) <= pd.Timedelta(hours=24)

# We don't want to just reuse the deterministic funnel outcome (that funnel
# was generated independent of A/B group). Instead, layer the A/B effect as
# its own Bernoulli draw representing "activation within 24h", independent
# experiment table -- this keeps the experiment analyzable on its own without
# needing to regenerate the whole funnel per-arm.
ab_rows = []
for _, r in april_users.iterrows():
    p = CONTROL_P if r["ab_group"] == "control" else CONTROL_P + TREATMENT_LIFT
    converted = rng.random() < p
    ab_rows.append({
        "user_id": r["user_id"],
        "ab_group": r["ab_group"],
        "signup_date": r["signup_date"],
        "acquisition_channel": r["acquisition_channel"],
        "activated_within_24h": converted,
    })
ab_test = pd.DataFrame(ab_rows)

# ---------------------------------------------------------------------------
# 6. WRITE OUTPUTS
# ---------------------------------------------------------------------------
users.to_csv(OUT_DIR / "users.csv", index=False)
funnel.to_csv(OUT_DIR / "funnel_events.csv", index=False)
transactions.to_csv(OUT_DIR / "transactions.csv", index=False)
ab_test.to_csv(OUT_DIR / "ab_test_kyc_flow.csv", index=False)

print(f"users: {len(users):,} rows -> users.csv")
print(f"funnel_events: {len(funnel):,} rows -> funnel_events.csv")
print(f"transactions: {len(transactions):,} rows -> transactions.csv")
print(f"ab_test_kyc_flow: {len(ab_test):,} rows -> ab_test_kyc_flow.csv")
print(f"activated users: {len(activated_users):,} / {TOTAL_USERS:,} total signups")
