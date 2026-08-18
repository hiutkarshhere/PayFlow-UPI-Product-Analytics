# Data Generation Assumptions

This project uses simulated data because no public dataset exposes UPI-app-level
funnel, transaction, and retention behavior at the granularity a Product
Analyst would actually work with inside a company. Every assumption below is
stated explicitly and encoded in `scripts/01_generate_synthetic_data.py` —
nothing in the README numbers is hand-picked after the fact; it's all
computed from the generated CSVs.

## Scope & Time Window
- Simulated period: **Jan 1, 2026 – Jun 30, 2026** (6 months)
- **50,500** new signups across the window, ramping up mid-period to mirror
  a growth-stage app running quarterly acquisition campaigns

## Acquisition Mix
| Channel | Share | Rationale |
|---|---|---|
| Organic | 40% | Word-of-mouth + app store discovery dominate in UPI category |
| Referral | 25% | UPI apps lean heavily on referral incentives (₹ cashback per invite) |
| Paid Ads | 20% | Performance marketing (Meta/Google UAC) |
| Partner Bank | 15% | Co-branded signup flows via partner bank apps |

City tier split (35% Tier 1 / 40% Tier 2 / 25% Tier 3) reflects UPI's real
growth pattern of outpacing metro-only adoption — Tier 2/3 India is where
transaction volume growth is fastest.

## Onboarding Funnel (stage-wise conversion)
| Stage | Base conversion (from prior stage) |
|---|---|
| Signup Started → OTP Verified | 92% |
| → Bank Account Linked | 85% |
| → UPI PIN Set | 93% |
| → KYC Completed | 78% |
| → First Transaction Attempted | 88% |
| → First Transaction Success | 95% |

Channel modifiers are applied on top (referral +3pp per stage, partner_bank
+6pp, paid_ads −5pp) to reflect that colder-intent paid traffic converts
worse than warm referral/partner traffic — this is a deliberate, testable
assumption, not noise.

## Post-Activation Behavior
Activated users are assigned one of four behavioral archetypes, each with a
transaction-frequency (Poisson λ) and month-over-month decay rate:

| Archetype | Share | Monthly txns (λ) | Decay rate |
|---|---|---|---|
| Power | 15% | 22 | 4%/month |
| Regular | 35% | 9 | 10%/month |
| Casual | 30% | 2.5 | 18%/month |
| At-risk | 20% | 0.8 | 42%/month |

**Important:** the segmentation analysis (script 04) does *not* use these
archetype labels directly — it re-derives segments from raw transaction
recency/frequency/monetary value the way an analyst would on a real
production table, without access to ground-truth labels. The fact that the
RFM segmentation recovers a similar structure (a small high-value cluster
driving most GTV) is a validation of the method, not circular reasoning.

## Transactions
- P2P vs P2M split: ~53% / 47%
- P2P amounts: log-normal, median ~₹270 (typical peer transfer)
- P2M amounts: log-normal, median ~₹490, heavier tail (bills, shopping, travel)
- Failure rate: 3.5%, distributed across bank server timeout (32%),
  insufficient balance (27%), incorrect PIN (18%), daily limit exceeded (13%),
  payee bank down (10%) — modeled on publicly reported NPCI failure-reason
  category shares, not exact published figures

## A/B Test (KYC Flow Simplification)
- Population: April 2026 signup cohort only (10,100 users), 50/50 split
- Metric: % activated (first successful transaction) within 24h of signup
- Assumed control baseline: 41% — a plausible baseline for a 3-step KYC flow
- Assumed treatment effect: +6.5pp from collapsing KYC into a single screen
  (friction reduction is one of the highest-leverage onboarding levers in
  fintech; a mid-single-digit-point lift is a realistic, defensible target
  rather than an inflated one)

## Known Limitation: Right-Censoring at the Window Edge
Of the 25,446 users who reach `first_txn_success` in the funnel, 24,222
(95.2%) have at least one transaction recorded in `transactions.csv`. The
remaining ~1,200 activated in the final hours of the June 30 observation
window, before any further transaction could be simulated within the window.
This is a standard right-censoring effect in behavioral data — it's called
out here rather than patched away, since recognizing and stating a
censoring boundary is itself part of doing this kind of analysis correctly
on a real warehouse.

## What This Simulation Does *Not* Claim
This is not real PhonePe/GPay/Paytm data and the numbers should not be cited
as such. It's a transparent, parameterized model built to practice and
demonstrate the analytical workflow — funnel construction, cohort retention,
segmentation, and A/B testing — end to end, the same way an analyst would on
a live production warehouse.
