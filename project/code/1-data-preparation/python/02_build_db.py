"""Langkah 4 dan 5: muat data ke DuckDB (constraint aktif), buat fitur turunan, bucket, dan failure_mode_long."""
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import DB_PATH, RES_PREP, SQL_PREP  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module  # noqa: E402

load_raw = import_module("01_load_audit").load_raw

if __name__ == "__main__":
    df, _, _ = load_raw()
    DB_PATH.unlink(missing_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute((SQL_PREP / "01_schema.sql").read_text())
    con.register("df_raw", df)
    con.execute("INSERT INTO raw_ai4i SELECT * FROM df_raw")
    con.execute((SQL_PREP / "02_features.sql").read_text())
    # uji constraint: baris salah harus ditolak
    tests = [("type di luar L/M/H", "INSERT INTO raw_ai4i VALUES (99991,'X1','Z',300,310,1500,40,10,0,0,0,0,0,0)"),
             ("udi ganda", "INSERT INTO raw_ai4i VALUES (1,'X2','L',300,310,1500,40,10,0,0,0,0,0,0)"),
             ("product_id ganda", "INSERT INTO raw_ai4i SELECT 99992,product_id,'L',300,310,1500,40,10,0,0,0,0,0,0 FROM raw_ai4i LIMIT 1"),
             ("suhu udara tidak masuk akal", "INSERT INTO raw_ai4i VALUES (99993,'X3','L',900,310,1500,40,10,0,0,0,0,0,0)"),
             ("rpm nol", "INSERT INTO raw_ai4i VALUES (99994,'X4','L',300,310,0,40,10,0,0,0,0,0,0)"),
             ("torque negatif", "INSERT INTO raw_ai4i VALUES (99995,'X5','L',300,310,1500,-5,10,0,0,0,0,0,0)"),
             ("tool wear negatif", "INSERT INTO raw_ai4i VALUES (99996,'X6','L',300,310,1500,40,-1,0,0,0,0,0,0)"),
             ("machine_failure bukan 0/1", "INSERT INTO raw_ai4i VALUES (99997,'X7','L',300,310,1500,40,10,2,0,0,0,0,0)"),
             ("flag jenis kegagalan bukan 0/1", "INSERT INTO raw_ai4i VALUES (99998,'X8','L',300,310,1500,40,10,0,3,0,0,0,0)"),
             ("kolom wajib kosong", "INSERT INTO raw_ai4i VALUES (99999,'X9','L',NULL,310,1500,40,10,0,0,0,0,0,0)")]
    out = []
    for name, sql in tests:
        try:
            con.execute(sql)
            out.append((name, "diterima"))
        except duckdb.Error:
            out.append((name, "ditolak"))
    pd.DataFrame(out, columns=["test", "outcome"]).to_csv(RES_PREP / "constraint_tests.csv", index=False)
    chk = [("jumlah baris raw_ai4i = 10000", con.execute("SELECT count(*) FROM raw_ai4i").fetchone()[0] - 10000),
           ("features sebaris dengan raw", con.execute("SELECT count(*) FROM features f LEFT JOIN raw_ai4i r USING (udi) WHERE r.udi IS NULL").fetchone()[0]),
           ("bucket tool wear tidak kosong", con.execute("SELECT count(*) FROM features WHERE wear_bucket IS NULL").fetchone()[0]),
           ("failure_mode_long = jumlah flag", con.execute("SELECT (SELECT count(*) FROM failure_mode_long) - (SELECT sum(twf+hdf+pwf+osf+rnf) FROM raw_ai4i)").fetchone()[0]),
           ("power negatif atau nol", con.execute("SELECT count(*) FROM features WHERE power_w <= 0").fetchone()[0])]
    pd.DataFrame(chk, columns=["check", "violations"]).to_csv(RES_PREP / "consistency_checks.csv", index=False)
    rows = [(t, con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]) for t in ("raw_ai4i", "features", "failure_mode_long", "rule_eval")]
    pd.DataFrame(rows, columns=["tabel", "baris"]).to_csv(RES_PREP / "table_rows.csv", index=False)
    con.close()
    print("db dibuat:", rows)
