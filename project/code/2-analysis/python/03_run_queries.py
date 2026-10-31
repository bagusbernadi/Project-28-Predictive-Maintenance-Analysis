"""Langkah 6 sampai 7: jalankan query SQL (DuckDB), tambahkan failure rate dan interval Wilson 95% di Python, tulis CSV hasil."""
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd
from statsmodels.stats.proportion import proportion_confint

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import DB_PATH, RES_ANALYSIS, SQL_ANALYSIS  # noqa: E402


def wilson(df, k, n):
    lo, hi = proportion_confint(df[k], df[n], alpha=0.05, method="wilson")
    df[f"{k}_rate"], df[f"{k}_lo"], df[f"{k}_hi"] = (df[k] / df[n]).round(8), lo.round(8), hi.round(8)
    return df


def run_all():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    sql = (SQL_ANALYSIS / "03_queries.sql").read_text()
    out = {}
    for name, q in re.findall(r"-- name: (\w+)\n(.*?)(?=\n-- name:|\Z)", sql, re.S):
        out[name] = con.execute(q).df()
    con.close()
    return out


if __name__ == "__main__":
    r = run_all()
    wilson(r["rate_by_type"], "failures", "n")
    tot = pd.DataFrame([{"type": "Semua", "n": int(r["rate_by_type"].n.sum()), "failures": int(r["rate_by_type"].failures.sum())}])
    wilson(tot, "failures", "n")
    r["rate_by_type"] = pd.concat([r["rate_by_type"], tot], ignore_index=True)
    fm = r["failure_modes"]
    nf = int(tot.failures[0])
    fm["share_of_failures"] = (fm.flags_with_failure / nf).round(8)        # per run gagal; bisa tumpang tindih
    fm["share_of_flags"] = (fm.flags_with_failure / fm.flags_with_failure.sum()).round(8)   # untuk Pareto (jumlah 100%)
    fm["cum_share"] = fm.share_of_flags.cumsum().round(8)
    wilson(r["wear_bucket"], "failures", "n")
    tr = wilson(r["torque_rpm"], "failures", "n")
    tr["reliable"] = tr.n >= 30
    r["torque_rpm"] = tr
    wilson(r["temp_diff_hdf"], "hdf", "n")
    wilson(r["power_pwf"], "pwf", "n")
    wilson(r["osf_by_type"], "osf", "n")
    for k, df in r.items():
        df.to_csv(RES_ANALYSIS / f"{k}.csv", index=False)
    print({k: len(v) for k, v in r.items()})
