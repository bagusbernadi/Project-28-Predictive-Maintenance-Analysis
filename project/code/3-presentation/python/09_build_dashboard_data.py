"""Langkah 11 (bagian data): ringkas hasil analisis menjadi CSV kecil untuk dashboard (tanpa data mentah)."""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import RES_ANALYSIS, RES_PRESENT  # noqa: E402

R = lambda n: pd.read_csv(RES_ANALYSIS / f"{n}.csv")
ev, fr = R("rule_eval"), R("final_rule").iloc[0]
rt, fm, wb, tr = R("rate_by_type"), R("failure_modes"), R("wear_bucket"), R("torque_rpm")
rt.to_csv(RES_PRESENT / "dash_rate_type.csv", index=False)
fm.to_csv(RES_PRESENT / "dash_modes.csv", index=False)
wb.to_csv(RES_PRESENT / "dash_wear.csv", index=False)
tr.to_csv(RES_PRESENT / "dash_heatmap.csv", index=False)
g = ev[(ev.period == "all") & ev.rule_name.isin(["tool wear >= T", "torque >= T", "tool wear x torque >= P"])].copy()
g["ambang"] = g.threshold.str.extract(r"(\d+)").astype(int)
g[["rule_name", "ambang", "tp", "fp", "fn", "tn", "precision", "recall", "alert_share", "accuracy"]].to_csv(RES_PRESENT / "dash_rule_grid.csv", index=False)
bl = ev[(ev.rule_name.str.startswith("baseline")) & (ev.period == "all")].iloc[0]
kp = {"runs": 10000, "failures": int(rt.failures.iloc[-1]), "failure_rate": float(rt.failures_rate.iloc[-1]), "baseline_accuracy": float(bl.accuracy),
      "final_rule": fr.threshold, "final_precision_test": float(fr.precision_test), "final_recall_test": float(fr.recall_test), "final_alert_test": float(fr.alert_share_test), "final_accuracy_test": float(fr.accuracy_test)}
pd.DataFrame([kp]).to_csv(RES_PRESENT / "dash_summary.csv", index=False)
print("dash_*.csv:", len(list(RES_PRESENT.glob("dash_*.csv"))))
