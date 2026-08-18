# Power BI Dashboard — Setup Guide

Power BI Desktop can't be generated headlessly from this environment, so
this folder gives you everything needed to build the dashboard yourself in
under 20 minutes: the data model, relationships, and every DAX measure
already written out. This mirrors how you'd actually hand off a data model
spec to someone building the report.

## 1. Get Data
`Get Data → Text/CSV`, import all four files from `data/raw/`:
- `users.csv`
- `funnel_events.csv`
- `transactions.csv`
- `ab_test_kyc_flow.csv`

Also import the pre-aggregated tables from `data/processed/` if you want the
Python-computed numbers to cross-check your DAX (recommended the first time,
so you can confirm your model matches — then you can drop these and drive
everything live from the raw tables):
- `funnel_summary.csv`
- `cohort_retention_matrix.csv`
- `segment_summary.csv`
- `ab_test_results.csv`

## 2. Data Model / Relationships
Star-schema shape, `users` as the hub:

```
users (user_id) ─── 1:M ─── funnel_events (user_id)
users (user_id) ─── 1:M ─── transactions (user_id)
users (user_id) ─── 1:M ─── ab_test_kyc_flow (user_id)
```

Also add a standalone **Date table** (Modeling → New Table):
```
DateTable = CALENDAR(DATE(2026,1,1), DATE(2026,6,30))
```
Mark it as a Date table, and relate `DateTable[Date]` to
`transactions[txn_timestamp]` (as a date) for time-intelligence functions.

## 3. Core DAX Measures

```dax
Total Signups = DISTINCTCOUNT(users[user_id])

Activated Users =
CALCULATE(
    DISTINCTCOUNT(funnel_events[user_id]),
    funnel_events[event_name] = "first_txn_success"
)

Activation Rate % =
DIVIDE([Activated Users], [Total Signups], 0) * 100

Monthly Transacting Users (MTU) =
CALCULATE(
    DISTINCTCOUNT(transactions[user_id]),
    transactions[status] = "SUCCESS"
)

Gross Transaction Value (GTV) =
CALCULATE(
    SUM(transactions[amount_inr]),
    transactions[status] = "SUCCESS"
)

Transaction Success Rate % =
DIVIDE(
    CALCULATE(COUNTROWS(transactions), transactions[status] = "SUCCESS"),
    COUNTROWS(transactions),
    0
) * 100

P2M Share % =
DIVIDE(
    CALCULATE(COUNTROWS(transactions), transactions[txn_type] = "P2M"),
    COUNTROWS(transactions),
    0
) * 100

-- A/B test measures
AB Control Rate % =
DIVIDE(
    CALCULATE(SUM(ab_test_kyc_flow[activated_within_24h]), ab_test_kyc_flow[ab_group] = "control"),
    CALCULATE(COUNTROWS(ab_test_kyc_flow), ab_test_kyc_flow[ab_group] = "control"),
    0
) * 100

AB Treatment Rate % =
DIVIDE(
    CALCULATE(SUM(ab_test_kyc_flow[activated_within_24h]), ab_test_kyc_flow[ab_group] = "treatment"),
    CALCULATE(COUNTROWS(ab_test_kyc_flow), ab_test_kyc_flow[ab_group] = "treatment"),
    0
) * 100

AB Lift (pp) = [AB Treatment Rate %] - [AB Control Rate %]
```

## 4. Recommended Pages
1. **Overview** — KPI cards (Total Signups, Activation Rate, MTU, GTV) +
   MTU trend line by month
2. **Funnel** — Funnel visual (built-in Power BI funnel chart) on
   `funnel_events`, plus a matrix of activation rate by
   `users[acquisition_channel]`
3. **Retention** — Matrix visual: rows = `cohort_month`, columns =
   `months_since_activation`, values = retention % (use
   `cohort_retention_matrix.csv` directly — cleanest way to reproduce the
   heatmap; apply conditional-formatting color scale to mimic the seaborn
   version)
4. **Segments** — Stacked bar or treemap on `segment_summary.csv`
   (users % vs. GTV % per segment — the Pareto story)
5. **A/B Test** — Two KPI cards (Control Rate, Treatment Rate) + a clustered
   column chart with the lift called out in a text box, referencing the
   p-value from `ab_test_results.csv`

## 5. Filters / Slicers Worth Adding
- `acquisition_channel`, `city_tier`, `device_os` as slicers on every page
- Date range slicer on the Date table for the Overview page

## Note on the .pbix File
A `.pbix` is a binary format that can't be authored outside Power BI
Desktop. Rather than fake one, this guide gives you the exact model and
formulas needed to build the real thing yourself — once built, export the
`.pbix` and drop it in this folder before pushing to GitHub (a screenshot or
two of the finished dashboard in the main README goes a long way for
recruiters skimming your repo).
