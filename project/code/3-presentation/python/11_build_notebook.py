"""Langkah 12 (notebook): susun analysis.ipynb dari CSV hasil lalu eksekusi tanpa error."""
import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import RES_PRESENT, ROOT  # noqa: E402

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
    md("# Project 28: Predictive Maintenance Failure Analysis\nNotebook ini membaca CSV hasil di `project/results/` (dibuat skrip 01 sampai 10). Data AI4I 2020 (UCI 601) adalah data sintetis; angka dampak berlabel *estimated* dan *simulated*."),
    code("from pathlib import Path\nimport pandas as pd, matplotlib.pyplot as plt\npd.set_option('display.width', 200); pd.set_option('display.max_columns', 30)\nRES = next(p for p in (Path('..'), Path('results'), Path('project/results')) if (p / '2-analysis').exists())\nR = lambda f: pd.read_csv(next(RES.rglob(f + '.csv')))"),
    md("## Q13. Kualitas data\nTidak ada sel kosong atau duplikat; ada label yang tidak konsisten (lihat tabel)."),
    code("dq = R('data_quality'); print(dq.to_string(index=False)); R('label_issues').groupby('masalah').size()"),
    md("## Q1. Failure rate keseluruhan dan per tipe (interval Wilson 95%)"),
    code("t = R('rate_by_type'); print(t.round(4).to_string(index=False)); R('h2_type_tests').round(5)"),
    md("## Q2. Jenis kegagalan (Pareto)\nSatu run bisa punya lebih dari satu jenis, jadi porsi dihitung dari kejadian jenis."),
    code("fm = R('failure_modes'); print(fm.round(4).to_string(index=False)); fm.plot.bar(x='failure_mode', y='share_of_flags', legend=False, title='Porsi jenis kegagalan'); plt.show()"),
    md("## Q3. Tool wear dan titik naiknya risiko (H1)"),
    code("w = R('wear_bucket'); w.plot.bar(x='wear_bucket', y='failures_rate', legend=False, title='Failure rate per bucket tool wear'); plt.show(); R('h1_wear_scan').round(5).iloc[::4]"),
    md("## Q4. Torque x rpm (heatmap; sel dengan kurang dari 30 run ditandai tidak andal)"),
    code("h = R('torque_rpm'); h['rate'] = h.failures_rate.where(h.reliable); print(h.pivot(index='torque_bucket', columns='rpm_bucket', values='rate').round(3))"),
    md("## Q5 sampai Q7. Selisih suhu (HDF), power (PWF), dan tool wear x torque per tipe (OSF)"),
    code("print(R('temp_diff_hdf').round(4).iloc[:, :8].to_string(index=False)); print(R('power_pwf').round(4).iloc[:, :6].to_string(index=False)); R('h5_type_thresholds')"),
    md("## Hipotesis H1 sampai H5"),
    code("R('hypotheses')[['id', 'verdict', 'p_value', 'bukti']]"),
    md("## Q8 sampai Q10. Aturan ambang: precision, recall, proporsi peringatan, dibanding baseline"),
    code("s = R('rule_selection'); s = s[(s.batas_alert_share == 0.10) & (s.period != 'all')]; print(s[['rule_name', 'period', 'precision', 'recall', 'alert_share', 'accuracy']].round(3).to_string(index=False)); R('final_rule_by_type').round(3)"),
    md("## Q11 dan Q12. Trade-off dan estimasi dampak (estimated, simulated)"),
    code("print(R('tradeoff').tail(2).to_string(index=False)); i = R('impact'); i[i.skenario == 'titik'][['downtime_per_kegagalan_h', 'porsi_tercegah', 'downtime_terhindari_kotor_h', 'jam_inspeksi_h', 'downtime_terhindari_bersih_h']]"),
    md("## Q14. Perbandingan dengan dokumentasi UCI dan cek silang"),
    code("print(R('doc_comparison').to_string(index=False)); print(R('crosscheck_sql_pandas').status.value_counts()); print(R('crosscheck_excel').status.value_counts())"),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
out = RES_PRESENT / "analysis.ipynb"
NotebookClient(nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(RES_PRESENT)}}).execute()
nbf.write(nb, out)
errs = [o for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []) if o.output_type == "error"]
assert not errs
print("notebook dieksekusi:", len(nb.cells), "sel")
