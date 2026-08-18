# Product Thinking

This section exists because a Product Analyst portfolio project should read
like it was scoped by someone who understands *why* the analysis matters to
the business, not just someone who can run pandas and SQL. Everything below
was defined before touching the data, then tested against what the data
actually showed.

## 1. Business Problem
PayFlow (a fictional UPI payments app) has strong top-of-funnel signups
(driven by referral incentives and paid acquisition) but leadership suspects
a large share of new users never become habitual transactors — meaning
acquisition spend isn't converting into the recurring, low-cost-to-serve
transaction volume that makes a UPI app's unit economics work. Unlike
e-commerce, UPI apps monetize indirectly (float, merchant discount rate on
P2M, cross-sell into lending/insurance) — so *activation* and *retained
transaction frequency*, not signup count, are what actually matter.

## 2. User Problem
New users sign up expecting to pay in one tap, but KYC and bank-linking
friction (multiple redirects, manual entry, waiting on OTPs from two
different systems — the bank's and the app's) creates a gap between intent
and first successful payment. Every extra step is a point where a user gives
up and reverts to their existing payment app.

## 3. Product Goals
1. Increase the % of signups that become **activated transactors** (reach a
   successful first transaction)
2. Increase **repeat transaction frequency** in the first 90 days, since
   habit formation in payments apps is set early or not at all
3. Identify which acquisition channels produce durable, transacting users —
   not just cheap signups

## 4. Hypotheses (tested or testable against this dataset)
| # | Hypothesis | Status in this project |
|---|---|---|
| H1 | KYC completion is the single biggest onboarding drop-off point | **Confirmed** — see Funnel Analysis |
| H2 | Paid-ads users convert to activation at a meaningfully lower rate than referral/organic, despite similar signup volume | **Confirmed** — see Funnel by Channel |
| H3 | A small segment of power users drives a disproportionate share of transaction value (Pareto pattern) | **Confirmed** — see Segmentation |
| H4 | Simplifying KYC to a single screen measurably improves 24h activation | **Tested via A/B experiment** — see A/B Test Analysis |

## 5. North Star Metric
**Monthly Transacting Users (MTU)** — the count of unique users completing
at least one successful transaction in a calendar month.

Chosen over raw signups or MAU (app opens) because MTU is the closest proxy
to actual value delivered: a user who opens the app but doesn't transact
generates no merchant discount revenue and no float, and doesn't build the
payment habit that drives long-term retention.

### Input Metrics (levers the product team can pull)
- Signup → Activation conversion rate (funnel)
- KYC completion rate specifically (largest identified drop-off)
- Activation rate by acquisition channel (spend allocation lever)
- Repeat transaction rate within 30/60/90 days of activation

### Output Metrics (what the business ultimately cares about)
- Monthly Transacting Users (MTU) — North Star
- Gross Transaction Value (GTV)
- Revenue-relevant proxy: P2M transaction share (P2M carries merchant
  discount rate revenue; P2P generally does not)

## 6. What I'd Do Next As a PM/Analyst
- Ship the simplified KYC flow to 100% of traffic (A/B result is significant
  with a tight, business-relevant confidence interval)
- Reallocate a portion of paid-ads budget toward referral, given the
  activation-rate gap found in the funnel-by-channel analysis
- Build a targeted re-engagement flow for the "At-Risk" RFM segment
  specifically (users who *were* frequent and are going quiet) — this
  segment is cheaper to win back than a cold acquisition and, in this data,
  still represents 17.5% of total GTV at risk
- Instrument a proper day-0 vs day-30 KYC completion funnel in production to
  see whether users complete KYC later than modeled here (this simulation
  assumes KYC either completes shortly after signup or doesn't at all)
