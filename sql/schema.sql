-- schema.sql
-- Table definitions for the PayFlow synthetic UPI dataset.
-- Written for BigQuery Standard SQL (swap DATETIME/dataset prefix for MySQL
-- if loading locally -- see README "Running the SQL" section).

CREATE SCHEMA IF NOT EXISTS `YOUR_GCP_PROJECT_ID.payflow_analytics`;

CREATE OR REPLACE TABLE `YOUR_GCP_PROJECT_ID.payflow_analytics.users` (
  user_id               INT64 NOT NULL,
  signup_date           DATE NOT NULL,
  signup_month          STRING NOT NULL,
  acquisition_channel   STRING NOT NULL,   -- organic | referral | paid_ads | partner_bank
  city_tier             STRING NOT NULL,   -- Tier 1 | Tier 2 | Tier 3
  device_os             STRING NOT NULL,   -- Android | iOS
  age_bracket           STRING NOT NULL
);

CREATE OR REPLACE TABLE `YOUR_GCP_PROJECT_ID.payflow_analytics.funnel_events` (
  user_id           INT64 NOT NULL,
  event_name        STRING NOT NULL,   -- signup_started | otp_verified | bank_linked |
                                        -- upi_pin_set | kyc_completed | first_txn_attempted |
                                        -- first_txn_success
  event_timestamp   DATETIME NOT NULL,
  stage_order       INT64 NOT NULL
);

CREATE OR REPLACE TABLE `YOUR_GCP_PROJECT_ID.payflow_analytics.transactions` (
  transaction_id     INT64 NOT NULL,
  user_id            INT64 NOT NULL,
  txn_timestamp      DATETIME NOT NULL,
  txn_type           STRING NOT NULL,     -- P2P | P2M
  merchant_category  STRING,
  amount_inr         NUMERIC NOT NULL,
  status             STRING NOT NULL,     -- SUCCESS | FAILED
  failure_reason     STRING
);

CREATE OR REPLACE TABLE `YOUR_GCP_PROJECT_ID.payflow_analytics.ab_test_kyc_flow` (
  user_id                 INT64 NOT NULL,
  ab_group                STRING NOT NULL,  -- control | treatment
  signup_date              DATE NOT NULL,
  acquisition_channel      STRING NOT NULL,
  activated_within_24h     BOOL NOT NULL
);

-- Load with (replace YOUR_GCP_PROJECT_ID with your actual project):
--   bq load --source_format=CSV --skip_leading_rows=1 YOUR_GCP_PROJECT_ID:payflow_analytics.users        data/raw/users.csv
--   bq load --source_format=CSV --skip_leading_rows=1 YOUR_GCP_PROJECT_ID:payflow_analytics.funnel_events data/raw/funnel_events.csv
--   bq load --source_format=CSV --skip_leading_rows=1 YOUR_GCP_PROJECT_ID:payflow_analytics.transactions  data/raw/transactions.csv
--   bq load --source_format=CSV --skip_leading_rows=1 YOUR_GCP_PROJECT_ID:payflow_analytics.ab_test_kyc_flow data/raw/ab_test_kyc_flow.csv
