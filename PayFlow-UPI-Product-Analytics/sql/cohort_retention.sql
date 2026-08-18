-- cohort_retention.sql
-- Monthly signup-cohort retention: of users activated in month M, what % of
-- them transacted in month M, M+1, M+2, ... Mirrors scripts/03_cohort_retention.py.

WITH activation AS (
  SELECT
    user_id,
    DATE_TRUNC(DATE(event_timestamp), MONTH) AS cohort_month
  FROM `YOUR_GCP_PROJECT_ID.payflow_analytics.funnel_events`
  WHERE event_name = 'first_txn_success'
    AND DATE(event_timestamp) <= '2026-06-30'
),
cohort_sizes AS (
  SELECT cohort_month, COUNT(DISTINCT user_id) AS cohort_size
  FROM activation
  GROUP BY cohort_month
),
txn_months AS (
  SELECT
    t.user_id,
    a.cohort_month,
    DATE_TRUNC(DATE(t.txn_timestamp), MONTH) AS txn_month
  FROM `YOUR_GCP_PROJECT_ID.payflow_analytics.transactions` t
  JOIN activation a USING (user_id)
  WHERE t.status = 'SUCCESS'
),
month_index AS (
  SELECT
    cohort_month,
    DATE_DIFF(txn_month, cohort_month, MONTH) AS months_since_activation,
    COUNT(DISTINCT user_id) AS retained_users
  FROM txn_months
  WHERE DATE_DIFF(txn_month, cohort_month, MONTH) >= 0
  GROUP BY cohort_month, months_since_activation
)
SELECT
  m.cohort_month,
  m.months_since_activation,
  m.retained_users,
  c.cohort_size,
  ROUND(m.retained_users / c.cohort_size * 100, 1) AS retention_pct
FROM month_index m
JOIN cohort_sizes c USING (cohort_month)
ORDER BY cohort_month, months_since_activation;
