-- Fitur turunan, kelompok kondisi (bucket), dan kegagalan per jenis.
-- Power (W) = torque (Nm) x rpm x 2*pi/60.
CREATE OR REPLACE TABLE features AS
SELECT udi, type, machine_failure,
  process_temp_k - air_temp_k AS temp_diff_k,
  torque_nm * rpm * 2 * pi() / 60 AS power_w,
  tool_wear_min * torque_nm AS wear_x_torque,
  CASE WHEN tool_wear_min >= 250 THEN '250+' ELSE lpad(CAST((tool_wear_min // 25) * 25 AS VARCHAR), 3, '0') || '-' || CAST((tool_wear_min // 25) * 25 + 24 AS VARCHAR) END AS wear_bucket,
  CASE WHEN torque_nm < 30 THEN '<30' WHEN torque_nm < 40 THEN '30-39' WHEN torque_nm < 50 THEN '40-49' WHEN torque_nm < 60 THEN '50-59' ELSE '60+' END AS torque_bucket,
  CASE WHEN rpm < 1400 THEN '<1400' WHEN rpm < 1500 THEN '1400-1499' WHEN rpm < 1600 THEN '1500-1599' WHEN rpm < 1800 THEN '1600-1799' ELSE '1800+' END AS rpm_bucket
FROM raw_ai4i;

CREATE OR REPLACE TABLE failure_mode_long AS
SELECT udi, 'TWF' AS failure_mode, machine_failure FROM raw_ai4i WHERE twf = 1
UNION ALL SELECT udi, 'HDF', machine_failure FROM raw_ai4i WHERE hdf = 1
UNION ALL SELECT udi, 'PWF', machine_failure FROM raw_ai4i WHERE pwf = 1
UNION ALL SELECT udi, 'OSF', machine_failure FROM raw_ai4i WHERE osf = 1
UNION ALL SELECT udi, 'RNF', machine_failure FROM raw_ai4i WHERE rnf = 1;

CREATE OR REPLACE TABLE rule_eval (
  rule_name VARCHAR, threshold VARCHAR, period VARCHAR, tp INTEGER, fp INTEGER, fn INTEGER, tn INTEGER,
  precision DOUBLE, recall DOUBLE, alert_share DOUBLE
);
