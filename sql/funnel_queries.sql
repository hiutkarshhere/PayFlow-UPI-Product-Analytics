-- funnel_queries.sql
-- Onboarding funnel: signup -> activated transactor, overall and by channel.
-- Mirrors scripts/02_funnel_analysis.py -- computed independently in SQL to
-- cross-check the pandas results (both should agree; this is exactly what
-- an interviewer means by "can you validate a metric two ways").

-- 1. Overall stage-by-stage funnel
WITH stage_users AS (
  SELECT
    event_name,
    COUNT(DISTINCT user_id) AS users_reached
  FROM `YOUR_GCP_PROJECT_ID.payflow_analytics.funnel_events`
  GROUP BY event_name
),
ordered AS (
  SELECT
    event_name,
    users_reached,
    CASE event_name
      WHEN 'signup_started'       THEN 0
      WHEN 'otp_verified'         THEN 1
      WHEN 'bank_linked'          THEN 2
      WHEN 'upi_pin_set'          THEN 3
      WHEN 'kyc_completed'        THEN 4
      WHEN 'first_txn_attempted'  THEN 5
      WHEN 'first_txn_success'    THEN 6
    END AS stage_order
  FROM stage_users
)
SELECT
  stage_order,
  event_name,
  users_reached,
  ROUND(users_reached / FIRST_VALUE(users_reached) OVER (ORDER BY stage_order) * 100, 2) AS pct_of_total,
  ROUND(users_reached / LAG(users_reached) OVER (ORDER BY stage_order) * 100, 2) AS step_conversion_pct
FROM ordered
ORDER BY stage_order;

-- 2. Activation rate by acquisition channel
WITH funnel_channel AS (
  SELECT
    f.user_id,
    f.event_name,
    u.acquisition_channel
  FROM `YOUR_GCP_PROJECT_ID.payflow_analytics.funnel_events` f
  JOIN `YOUR_GCP_PROJECT_ID.payflow_analytics.users` u USING (user_id)
),
signups AS (
  SELECT acquisition_channel, COUNT(DISTINCT user_id) AS total_signups
  FROM funnel_channel
  WHERE event_name = 'signup_started'
  GROUP BY acquisition_channel
),
activated AS (
  SELECT acquisition_channel, COUNT(DISTINCT user_id) AS activated_users
  FROM funnel_channel
  WHERE event_name = 'first_txn_success'
  GROUP BY acquisition_channel
)
SELECT
  s.acquisition_channel,
  s.total_signups,
  a.activated_users,
  ROUND(a.activated_users / s.total_signups * 100, 2) AS activation_rate_pct
FROM signups s
JOIN activated a USING (acquisition_channel)
ORDER BY activation_rate_pct DESC;
