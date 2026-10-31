"""Langkah 9: trade-off per ambang (Q11) dan estimasi downtime terhindari (Q12). Semua angka dampak: estimated dan simulated."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportion_confint

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import DOWNTIME_H, INSPECT_H, N_RUNS_SCENARIO, PREVENT, RES_ANALYSIS  # noqa: E402

ev = pd.read_csv(RES_ANALYSIS / "rule_eval.csv")
fr = pd.read_csv(RES_ANALYSIS / "final_rule.csv").iloc[0]
# ---- Q11: trade-off (semua 10.000 run); alat diganti terlalu cepat = peringatan palsu (fp)
rows = []
for rule in ("tool wear >= T", "torque >= T"):
    for r in ev[(ev.rule_name == rule) & (ev.period == "all")].itertuples():
        rows.append((rule, r.threshold, "all", r.tp, r.fn, r.fp, r.tp + r.fp))
for per in ("test", "all"):
    rows.append(("aturan terpilih (gabungan)", fr.threshold, per, fr[f"tp_{per}"], fr[f"fn_{per}"], fr[f"fp_{per}"], fr[f"tp_{per}"] + fr[f"fp_{per}"]))
tr = pd.DataFrame(rows, columns=["rule_name", "threshold", "period", "failures_caught", "failures_missed", "false_alerts", "alerts"])
tr[["failures_caught", "failures_missed", "false_alerts", "alerts"]] = tr[["failures_caught", "failures_missed", "false_alerts", "alerts"]].astype(int)
tr["false_alerts_per_caught"] = (tr.false_alerts / tr.failures_caught.replace(0, np.nan)).round(4)
tr.to_csv(RES_ANALYSIS / "tradeoff.csv", index=False)
# ---- Q12: dampak, dari konfusi data uji diskalakan ke 10.000 run
n_te = int(fr.tp_test + fr.fp_test + fr.fn_test + fr.tn_test)
sc = N_RUNS_SCENARIO / n_te
tp, fp, fn = fr.tp_test, fr.fp_test, fr.fn_test
lo, hi = proportion_confint(int(tp), int(tp + fn), alpha=0.05, method="wilson")
rows = []
for dh in DOWNTIME_H:
    for pv in PREVENT:
        for lab, rec in (("titik", tp / (tp + fn)), ("batas bawah (Wilson 95%)", lo), ("batas atas (Wilson 95%)", hi)):
            fail = (tp + fn) * sc
            caught = rec * fail
            old, new = fail / N_RUNS_SCENARIO, (fail - caught * pv) / N_RUNS_SCENARIO
            gross = (old - new) * N_RUNS_SCENARIO * dh
            alerts = caught + fp * sc
            insp = alerts * INSPECT_H
            rows.append((dh, pv, lab, rec, fail, caught, fp * sc, old, new, gross, insp, gross - insp, insp / (caught * pv) if caught else np.nan))
im = pd.DataFrame(rows, columns=["downtime_per_kegagalan_h", "porsi_tercegah", "skenario", "recall", "kegagalan_per_10000_run", "kegagalan_tertangkap", "peringatan_palsu", "failure_rate_lama", "failure_rate_baru",
                                 "downtime_terhindari_kotor_h", "jam_inspeksi_h", "downtime_terhindari_bersih_h", "downtime_impas_h"]).round(6)
im.to_csv(RES_ANALYSIS / "impact.csv", index=False)
print(tr.tail(2).to_string(index=False)); print(im[im.skenario == "titik"][["downtime_per_kegagalan_h", "porsi_tercegah", "downtime_terhindari_kotor_h", "jam_inspeksi_h", "downtime_terhindari_bersih_h", "downtime_impas_h"]].to_string(index=False))
