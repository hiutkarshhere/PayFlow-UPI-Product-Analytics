-- ab_test.sql
-- Simplified-KYC-flow experiment results. SQL computes the raw conversion
-- rates and lift; the z-test itself is done in Python (scripts/05_ab_test_analysis.py)
-- since BigQuery Standard SQL has no native two-proportion z-test function --
-- in practice this is exactly the split most teams use: SQL for aggregation,
-- Python/stats package for the significance test.

SELECT
  ab_group,
  COUNT(*) AS users,
  SUM(CAST(activated_within_24h AS INT64)) AS conversions,
  ROUND(SUM(CAST(activated_within_24h AS INT64)) / COUNT(*) * 100, 2) AS conversion_rate_pct
FROM `YOUR_GCP_PROJECT_ID.payflow_analytics.ab_test_kyc_flow`
GROUP BY ab_group
ORDER BY ab_group;

-- Lift, in the same query, for a quick sanity check before jumping to Python:
WITH rates AS (
  SELECT
    ab_group,
    SUM(CAST(activated_within_24h AS INT64)) / COUNT(*) AS conv_rate
  FROM `YOUR_GCP_PROJECT_ID.payflow_analytics.ab_test_kyc_flow`
  GROUP BY ab_group
)
SELECT
  ROUND((MAX(IF(ab_group = 'treatment', conv_rate, NULL)) -
         MAX(IF(ab_group = 'control', conv_rate, NULL))) * 100, 2) AS absolute_lift_pp,
  ROUND((MAX(IF(ab_group = 'treatment', conv_rate, NULL)) /
         MAX(IF(ab_group = 'control', conv_rate, NULL)) - 1) * 100, 1) AS relative_lift_pct
FROM rates;
