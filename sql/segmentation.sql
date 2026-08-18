-- segmentation.sql
-- RFM (Recency, Frequency, Monetary) segmentation using SQL window functions
-- (NTILE for quartile scoring). Mirrors scripts/04_user_segmentation.py.

WITH rfm_base AS (
  SELECT
    user_id,
    DATE_DIFF(DATE('2026-06-30'), DATE(MAX(txn_timestamp)), DAY) AS recency_days,
    COUNT(*) AS frequency,
    SUM(amount_inr) AS monetary_inr
  FROM `YOUR_GCP_PROJECT_ID.payflow_analytics.transactions`
  WHERE status = 'SUCCESS'
  GROUP BY user_id
),
rfm_scored AS (
  SELECT
    *,
    -- recency: lower days-since-last-txn = better = higher score
    5 - NTILE(4) OVER (ORDER BY recency_days) AS r_score,
    NTILE(4) OVER (ORDER BY frequency)        AS f_score,
    NTILE(4) OVER (ORDER BY monetary_inr)     AS m_score
  FROM rfm_base
),
rfm_labeled AS (
  SELECT
    *,
    CASE
      WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Power Users'
      WHEN r_score >= 3 AND f_score >= 2 THEN 'Regular Users'
      WHEN r_score <= 2 AND f_score >= 3 THEN 'At-Risk (was frequent, going quiet)'
      WHEN r_score = 1 AND f_score <= 2 THEN 'Dormant / Churned'
      ELSE 'Casual / New'
    END AS segment
  FROM rfm_scored
)
SELECT
  segment,
  COUNT(*) AS users,
  ROUND(AVG(recency_days), 1) AS avg_recency_days,
  ROUND(AVG(frequency), 1) AS avg_frequency,
  ROUND(AVG(monetary_inr), 1) AS avg_monetary_inr,
  ROUND(SUM(monetary_inr), 1) AS total_gtv_inr,
  ROUND(COUNT(*) / SUM(COUNT(*)) OVER () * 100, 1) AS pct_of_activated_users,
  ROUND(SUM(monetary_inr) / SUM(SUM(monetary_inr)) OVER () * 100, 1) AS pct_of_total_gtv
FROM rfm_labeled
GROUP BY segment
ORDER BY users DESC;
