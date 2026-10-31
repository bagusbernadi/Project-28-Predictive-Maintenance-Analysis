"""Langkah 11 (bagian one-sheet): ringkasan satu halaman aturan inspeksi (PNG dan PDF), dari CSV hasil."""
import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import RES_ANALYSIS, RES_PRESENT  # noqa: E402

R = lambda n: pd.read_csv(RES_ANALYSIS / f"{n}.csv")
fr, wb, fm, bt = R("final_rule").iloc[0], R("wear_bucket"), R("failure_modes"), R("final_rule_by_type")
ev = R("rule_eval")
bl = ev[(ev.rule_name.str.startswith("baseline")) & (ev.period == "all")].iloc[0]
pc = lambda x: f"{x * 100:.1f}%".replace(".", ",")
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})
fig = plt.figure(figsize=(11.69, 8.27))
fig.text(.04, .94, "Aturan inspeksi mesin: tangkap kegagalan, batasi peringatan", fontsize=20, fontweight="bold", color="#174EA6")
fig.text(.04, .905, "Project 28 | AI4I 2020 (UCI 601), data sintetis; angka dampak estimated dan simulated", fontsize=10, color="#5F6368")
boxes = [("Failure rate", pc(R("rate_by_type").failures_rate.iloc[-1])), ("Recall (data uji)", pc(fr.recall_test)), ("Precision (data uji)", pc(fr.precision_test)), ("Peringatan (data uji)", pc(fr.alert_share_test))]
for i, (k, v) in enumerate(boxes):
    fig.text(.04 + i * .235, .835, v, fontsize=24, fontweight="bold", color="#1A73E8")
    fig.text(.04 + i * .235, .805, k, fontsize=10, color="#5F6368")
fig.text(.04, .755, "Aturan: beri peringatan jika salah satu terpenuhi", fontsize=12, fontweight="bold")
parts = fr.threshold.split(" | ")
for i, ptxt in enumerate(parts):
    fig.text(.05, .725 - i * .028, "• " + ptxt.replace("minNm", "min·Nm"), fontsize=10)
fig.text(.04, .625, f"Akurasi aturan ini {pc(fr.accuracy_test)} lebih rendah dari 'tidak pernah peringatan' ({pc(bl.accuracy)}), tetapi baseline menangkap 0% kegagalan.", fontsize=10, color="#B06000")
a1 = fig.add_axes([.06, .30, .26, .27]); a1.bar(wb.wear_bucket, wb.failures_rate * 100, color="#1A73E8"); a1.set_title("Failure rate per tool wear (menit; 250+ hanya 2 run)", fontsize=10, loc="left"); a1.tick_params(axis="x", rotation=60, labelsize=7); a1.set_ylabel("%")
a2 = fig.add_axes([.40, .30, .22, .27]); a2.bar(fm.failure_mode, fm.share_of_flags * 100, color="#E8710A"); a2.set_title("Porsi jenis kegagalan (%)", fontsize=10, loc="left")
t = bt[bt.period == "all"]
a3 = fig.add_axes([.70, .30, .25, .27]); xs = range(len(t)); a3.bar([x - .2 for x in xs], t.recall * 100, .4, label="Recall", color="#188038"); a3.bar([x + .2 for x in xs], t.precision * 100, .4, label="Precision", color="#9AA0A6")
a3.set_xticks(list(xs)); a3.set_xticklabels([f"Tipe {x}" for x in t.type]); a3.set_title("Aturan terpilih per tipe (semua data, %)", fontsize=10, loc="left"); a3.legend(fontsize=8, frameon=False)
fig.text(.04, .17, "Batasan: data sintetis; kegagalan acak (RNF) tidak bisa diprediksi; pola belum tentu penyebab; ambang perlu diuji di lapangan.", fontsize=9, color="#5F6368")
fig.text(.04, .14, "Sumber: UCI Machine Learning Repository, dataset 601 (CC BY 4.0). Sitasi: doi.org/10.24432/C5HS5C", fontsize=9, color="#5F6368")
fig.savefig(RES_PRESENT / "onesheet.png", dpi=150); fig.savefig(RES_PRESENT / "onesheet.pdf")
print("one-sheet dibuat")
