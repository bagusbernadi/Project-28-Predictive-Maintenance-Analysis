-- Skema database project 28 (DuckDB). Tabel raw_ai4i dimuat apa adanya dengan nama kolom baku.
CREATE OR REPLACE TABLE raw_ai4i (
  udi INTEGER PRIMARY KEY,
  product_id VARCHAR NOT NULL UNIQUE,
  type VARCHAR NOT NULL CHECK (type IN ('L','M','H')),
  air_temp_k DOUBLE NOT NULL CHECK (air_temp_k BETWEEN 250 AND 350),
  process_temp_k DOUBLE NOT NULL CHECK (process_temp_k BETWEEN 250 AND 400),
  rpm INTEGER NOT NULL CHECK (rpm > 0),
  torque_nm DOUBLE NOT NULL CHECK (torque_nm >= 0),
  tool_wear_min INTEGER NOT NULL CHECK (tool_wear_min >= 0),
  machine_failure INTEGER NOT NULL CHECK (machine_failure IN (0,1)),
  twf INTEGER NOT NULL CHECK (twf IN (0,1)),
  hdf INTEGER NOT NULL CHECK (hdf IN (0,1)),
  pwf INTEGER NOT NULL CHECK (pwf IN (0,1)),
  osf INTEGER NOT NULL CHECK (osf IN (0,1)),
  rnf INTEGER NOT NULL CHECK (rnf IN (0,1))
);
