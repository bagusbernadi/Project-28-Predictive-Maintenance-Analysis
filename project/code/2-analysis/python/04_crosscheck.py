"""Langkah 10 (bagian 1): cek silang hasil SQL vs hitungan pandas langsung dari CSV mentah."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "1-data-preparation" / "python"))
from importlib import import_module  # noqa: E402

from common import MODES, RES_ANALYSIS  # noqa: E402

load_raw = import_module("01_load_audit").load_raw
df, _, _ = load_raw()
df["power_w"] = df.torque_nm * df.rpm * 2 * np.pi / 60
df["dt"] = df.process_temp_k - df.air_temp_k
rd = lambda n: pd.read_csv(RES_ANALYSIS / f"{n}.csv")
checks = []


def cmp(name, a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    checks.append((name, len(a), float(np.abs(a - b).max()), "PASS" if np.array_equal(a, b) else "FAIL"))


t = rd("rate_by_type")
g = df.groupby("type").machine_failure.agg(["count", "sum"]).reindex(["L", "M", "H"])
cmp("failure rate per tipe: n", t.n[:3], g["count"]); cmp("failure rate per tipe: gagal", t.failures[:3], g["sum"])
fm = rd("failure_modes").set_index("failure_mode")
for m in MODES:
    cmp(f"jenis {m.upper()}: flag dan flag dengan gagal", [fm.loc[m.upper(), "flags"], fm.loc[m.upper(), "flags_with_failure"]], [df[m].sum(), df[(df[m] == 1) & (df.machine_failure == 1)].shape[0]])
w = rd("wear_bucket")
b = (df.tool_wear_min // 25 * 25).clip(upper=250)
gw = df.groupby(b).machine_failure.agg(["count", "sum"])
cmp("bucket tool wear: n", w.n, gw["count"]); cmp("bucket tool wear: gagal", w.failures, gw["sum"])
tr = rd("torque_rpm")
tb = pd.cut(df.torque_nm, [-1, 30, 40, 50, 60, 1e9], right=False, labels=["<30", "30-39", "40-49", "50-59", "60+"])
rb = pd.cut(df.rpm, [0, 1400, 1500, 1600, 1800, 1e9], right=False, labels=["<1400", "1400-1499", "1500-1599", "1600-1799", "1800+"])
gt = df.groupby([tb, rb], observed=True).machine_failure.agg(["count", "sum"]).reset_index()
gt.columns = ["torque_bucket", "rpm_bucket", "n", "failures"]
mrg = tr.merge(gt.astype({"torque_bucket": str, "rpm_bucket": str}), on=["torque_bucket", "rpm_bucket"], suffixes=("", "_pd"))
cmp("heatmap torque x rpm: n", mrg.n, mrg.n_pd); cmp("heatmap torque x rpm: gagal", mrg.failures, mrg.failures_pd)
hd = rd("temp_diff_hdf")
cmp("selisih suhu: total HDF dan n", [hd.hdf.sum(), hd.n.sum()], [df.hdf.sum(), len(df)])
cmp("selisih suhu: HDF pada rpm < 1380", [hd.hdf_rpm_lt_1380.sum()], [df[df.rpm < 1380].hdf.sum()])
pw = rd("power_pwf")
cmp("power: total PWF dan n", [pw.pwf.sum(), pw.n.sum()], [df.pwf.sum(), len(df)])
cmp("power: PWF di luar 3.500-9.000 W", [pw[pw.power_bucket.str[0].isin(["a", "f"])].pwf.sum()], [df[(df.power_w < 3500) | (df.power_w > 9000)].pwf.sum()])
os_ = rd("osf_by_type")
cmp("OSF per tipe", os_.groupby("type").osf.sum().reindex(["H", "L", "M"]), df.groupby("type").osf.sum().reindex(["H", "L", "M"]))
cmp("OSF: jumlah run per tipe", os_.groupby("type").n.sum().reindex(["H", "L", "M"]), df.groupby("type").size().reindex(["H", "L", "M"]))
pd.DataFrame(checks, columns=["pemeriksaan", "nilai_dibandingkan", "selisih_maks", "status"]).to_csv(RES_ANALYSIS / "crosscheck_sql_pandas.csv", index=False)
assert all(c[3] == "PASS" for c in checks), [c for c in checks if c[3] != "PASS"]
print(len(checks), "pemeriksaan SQL vs pandas PASS")
