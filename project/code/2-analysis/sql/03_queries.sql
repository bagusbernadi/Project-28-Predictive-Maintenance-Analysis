-- Setiap query diawali baris "-- name: <nama>"; hasilnya ditulis ke results/2-analysis/<nama>.csv oleh 03_run_queries.py.
-- name: rate_by_type
SELECT type, count(*) AS n, sum(machine_failure) AS failures FROM features GROUP BY type ORDER BY CASE type WHEN 'L' THEN 1 WHEN 'M' THEN 2 ELSE 3 END;
-- name: failure_modes
SELECT m.failure_mode, count(*) AS flags, sum(m.machine_failure) AS flags_with_failure, count(*) - sum(m.machine_failure) AS flags_without_failure
FROM failure_mode_long m GROUP BY m.failure_mode ORDER BY flags_with_failure DESC, failure_mode;
-- name: wear_bucket
SELECT wear_bucket, count(*) AS n, sum(f.machine_failure) AS failures, sum(r.twf) AS twf, sum(r.osf) AS osf
FROM features f JOIN raw_ai4i r USING (udi) GROUP BY wear_bucket ORDER BY wear_bucket;
-- name: torque_rpm
SELECT torque_bucket, rpm_bucket, count(*) AS n, sum(machine_failure) AS failures FROM features GROUP BY torque_bucket, rpm_bucket ORDER BY torque_bucket, rpm_bucket;
-- name: temp_diff_hdf
SELECT CASE WHEN temp_diff_k < 8.0 THEN 'a: < 8,0' WHEN temp_diff_k < 8.6 THEN 'b: 8,0-8,5' WHEN temp_diff_k < 9.6 THEN 'c: 8,6-9,5' WHEN temp_diff_k < 10.6 THEN 'd: 9,6-10,5' WHEN temp_diff_k < 11.6 THEN 'e: 10,6-11,5' ELSE 'f: >= 11,6' END AS diff_bucket,
  count(*) AS n, sum(r.hdf) AS hdf, sum(f.machine_failure) AS failures,
  sum(CASE WHEN r.rpm < 1380 THEN 1 ELSE 0 END) AS n_rpm_lt_1380, sum(CASE WHEN r.rpm < 1380 THEN r.hdf ELSE 0 END) AS hdf_rpm_lt_1380
FROM features f JOIN raw_ai4i r USING (udi) GROUP BY diff_bucket ORDER BY diff_bucket;
-- name: power_pwf
SELECT CASE WHEN power_w < 3500 THEN 'a: < 3.500 W' WHEN power_w < 5000 THEN 'b: 3.500-4.999' WHEN power_w < 6500 THEN 'c: 5.000-6.499' WHEN power_w < 8000 THEN 'd: 6.500-7.999' WHEN power_w <= 9000 THEN 'e: 8.000-9.000' ELSE 'f: > 9.000 W' END AS power_bucket,
  count(*) AS n, sum(r.pwf) AS pwf, sum(f.machine_failure) AS failures
FROM features f JOIN raw_ai4i r USING (udi) GROUP BY power_bucket ORDER BY power_bucket;
-- name: osf_by_type
SELECT f.type, CASE WHEN r.tool_wear_min < 150 THEN 'a: < 150' WHEN r.tool_wear_min < 200 THEN 'b: 150-199' WHEN r.tool_wear_min < 230 THEN 'c: 200-229' ELSE 'd: >= 230' END AS wear_group,
  CASE WHEN r.torque_nm < 40 THEN 'a: < 40' WHEN r.torque_nm < 50 THEN 'b: 40-49' WHEN r.torque_nm < 60 THEN 'c: 50-59' ELSE 'd: >= 60' END AS torque_group,
  count(*) AS n, sum(r.osf) AS osf, sum(f.machine_failure) AS failures
FROM features f JOIN raw_ai4i r USING (udi) GROUP BY ALL ORDER BY 1, 2, 3;
