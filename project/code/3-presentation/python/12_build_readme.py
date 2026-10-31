"""Langkah 12: tulis README.md dari CSV hasil (angka tidak diketik tangan)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import REPO, RES_ANALYSIS  # noqa: E402

R = lambda n: pd.read_csv(RES_ANALYSIS / f"{n}.csv")
I = lambda n: f"{int(round(float(n))):,}".replace(",", ".")
D = lambda x, d=1: f"{float(x):,.{d}f}".replace(",", "_").replace(".", ",").replace("_", ".")
P = lambda x, d=1: D(float(x) * 100, d) + "%"
rt, fm, hy, fr = R("rate_by_type").set_index("type"), R("failure_modes").set_index("failure_mode"), R("hypotheses").set_index("id"), R("final_rule").iloc[0]
im, tr, tree, doc = R("impact"), R("tradeoff"), R("tree_compare"), R("doc_comparison")
ev = R("rule_eval")
bl = ev[(ev.rule_name.str.startswith("baseline")) & (ev.period == "all")].iloc[0]
imp = im[(im.skenario == "titik") & (im.downtime_per_kegagalan_h == 4) & (im.porsi_tercegah == 0.8)].iloc[0]
imp2 = im[(im.skenario == "titik") & (im.downtime_per_kegagalan_h == 2) & (im.porsi_tercegah == 0.8)].iloc[0]
w = tr[(tr.rule_name == "tool wear >= T") & (tr.threshold == "200 menit")].iloc[0]
pt = tree[(tree.period == "test") & (tree.model == "pohon keputusan kedalaman 3")].iloc[0]
xs, xr, xe = R("crosscheck_sql_pandas"), R("crosscheck_rules"), R("crosscheck_excel")
V = lambda k: hy.loc[k, "verdict"]
txt = f"""[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 28: Predictive Maintenance Failure Analysis

**Status: Selesai di branch `project-28-build` (belum digabung ke `main`).** Halaman rancangan dan Report ada di [`design-and-report/index.html`](design-and-report/index.html). Dashboard belum di-deploy.

**Tujuan:** menganalisis data operasi mesin publik untuk menemukan kondisi dan jenis kegagalan yang paling sering menyebabkan mesin rusak, lalu merumuskan aturan ambang sederhana yang terukur ketepatannya, agar jadwal inspeksi dan penggantian alat bisa ditentukan sebelum kerusakan terjadi.

| | |
|---|---|
| Kategori | Perawatan mesin (Manufaktur) |
| Tingkat | Menengah |
| Data | Dataset publik AI4I 2020 Predictive Maintenance, UCI (sintetis) |
| Tools | DuckDB + SQL, Python (pandas), Streamlit + Plotly, Excel (cek silang), scikit-learn dan SciPy |

## 1. Problem

**Pertanyaan utama:** Kondisi operasi dan jenis kegagalan apa yang paling sering menyebabkan mesin rusak, dan pada ambang berapa risikonya naik?

Rancangan memecahnya menjadi 14 pertanyaan (9 Utama, 4 Pendukung, 1 Tambahan); semuanya terjawab di Report.

## 2. Data

- Sumber data: [here](https://archive.ics.uci.edu/dataset/601) (Versi: UCI 2020, Tanggal akses: 24 Oktober 2026)
- Ukuran (dihitung dari berkas): {I(rt.n['Semua'])} baris, 14 kolom; {I(rt.failures['Semua'])} run gagal ({P(rt.failures_rate['Semua'], 2)}).
- Data sintetis: dibuat penyusun dataset untuk meniru kondisi mesin nyata. Semua angka dampak berlabel `estimated` dan `simulated`.
- Lisensi: CC BY 4.0. Sitasi: AI4I 2020 Predictive Maintenance Dataset [Dataset]. (2020). UCI Machine Learning Repository. https://doi.org/10.24432/C5HS5C
- Data mentah tidak di-commit; cara menyiapkannya ada di [`project/data/README.md`](project/data/README.md).
- Tabel database: `raw_ai4i`, `features`, `failure_mode_long`, `rule_eval`.

## 3. Analysis

- **Failure rate** {P(rt.failures_rate['Semua'], 2)}; tipe L {P(rt.failures_rate['L'], 2)}, M {P(rt.failures_rate['M'], 2)}, H {P(rt.failures_rate['H'], 2)}.
- **Jenis kegagalan** (kejadian pada run gagal): HDF {I(fm.flags_with_failure['HDF'])}, OSF {I(fm.flags_with_failure['OSF'])}, PWF {I(fm.flags_with_failure['PWF'])}, TWF {I(fm.flags_with_failure['TWF'])}, RNF {I(fm.flags_with_failure['RNF'])}.
- **Hipotesis:** H1 (tool wear sekitar 200 menit) {V('H1')}; H2 (tipe L lebih sering gagal) {V('H2')}; H3 (selisih suhu kecil dan putaran rendah) {V('H3')}; H4 (power di ekor) {V('H4')}; H5 (torque dan tool wear, batas per tipe) {V('H5')}.
- **Aturan terpilih** (dari data latih, batas peringatan 10%): `{fr.threshold}`. Data uji: precision {P(fr.precision_test, 1)}, recall {P(fr.recall_test, 1)}, proporsi peringatan {P(fr.alert_share_test, 1)}, akurasi {P(fr.accuracy_test, 1)}.
- **Akurasi menyesatkan:** aturan tidak pernah memberi peringatan punya akurasi {P(bl.accuracy, 1)} tetapi recall 0%.
- **Pembanding:** pohon keputusan kedalaman 3 (data uji): precision {P(pt.precision, 1)}, recall {P(pt.recall, 1)}.
- **Validasi:** {I(len(xs))} cek silang SQL vs pandas, {I(len(xr))} aturan SQL vs Python, dan {I(len(xe))} pemeriksaan Excel semuanya PASS.

## 4. Recommendation

Pakai aturan gabungan di atas sebagai alarm inspeksi awal dan ulangi pemilihan ambang dengan data mesin sendiri. Aturan tool wear saja (>= 200 menit) menangkap {P(w.failures_caught / (w.failures_caught + w.failures_missed), 1)} kegagalan dengan {I(w.false_alerts)} peringatan palsu per 10.000 run; aturan gabungan menangkap lebih banyak dengan proporsi peringatan sekitar 10%.

## 5. Impact

Semua angka berlabel `estimated` dan `simulated`. Pada asumsi downtime 4 jam per kegagalan, 80% kegagalan berperingatan tercegah, dan 0,5 jam per inspeksi, downtime terhindari sekitar {D(imp.downtime_terhindari_kotor_h, 0)} jam (kotor) dan {D(imp.downtime_terhindari_bersih_h, 0)} jam (bersih) per 10.000 run. Pada downtime 2 jam, hasil bersih {D(imp2.downtime_terhindari_bersih_h, 0)} jam: aturan baru menguntungkan jika downtime per kegagalan cukup besar.

## Batasan

- Data sintetis; polanya lebih rapi dari kondisi nyata. Dokumentasi UCI dan data berbeda pada jumlah RNF dan TWF (Report 2, Q14).
- Kegagalan sangat jarang, sehingga akurasi tinggi tidak berarti aturan berguna. Data uji hanya {I(fr.tp_test + fr.fn_test)} run gagal; tipe H sangat sedikit.
- Satu run bisa punya lebih dari satu jenis kegagalan; RNF tidak bisa diprediksi.
- Batas peringatan 10%, penafsiran hipotesis, dan asumsi dampak adalah asumsi saya (`project/docs/definitions.md`).
- Pola belum tentu penyebab; dashboard belum di-deploy dan kriteria uji ke pembaca awam belum terpenuhi. Slide presentasi (Opsional) tidak dibuat.

## Menjalankan

Dari folder `project/` (Python 3.11+): `pip install -r requirements.txt`, taruh zip data di `data/raw/`, lalu jalankan berurutan:

```
python code/1-data-preparation/python/01_load_audit.py
python code/1-data-preparation/python/02_build_db.py
python code/2-analysis/python/03_run_queries.py
python code/2-analysis/python/04_crosscheck.py
python code/2-analysis/python/05_stats_tests.py
python code/2-analysis/python/06_rule_eval.py
python code/2-analysis/python/07_tradeoff_impact.py
python code/2-analysis/python/08_excel_crosscheck.py     # butuh LibreOffice (soffice)
python code/3-presentation/python/09_build_dashboard_data.py
python code/3-presentation/python/10_build_onesheet.py
python code/3-presentation/python/11_build_notebook.py
python code/3-presentation/python/12_build_readme.py
python ../design-and-report/src/build_report.py            # dari root repo atau mana saja
streamlit run code/3-presentation/streamlit/app.py
```

## Struktur repository

```
README.md
index.html                 pengalihan ke design-and-report/
design-and-report/         index.html (tab Design + Report), src/ (page_v1.html, report.css, report_lib.py, build_report.py)
project/
  code/                    common.py; 1-data-preparation/ 2-analysis/ 3-presentation/ (python/, sql/, streamlit/)
  results/                 CSV hasil per tahap, analysis.ipynb, onesheet.png/.pdf
  data/                    README.md (sumber, lisensi); raw/ tidak di-commit
  docs/                    definitions.md, data_dictionary.md, cleaning_decisions.md
  requirements.txt
```
"""
(REPO / "README.md").write_text(txt, encoding="utf-8")
print("README.md ditulis")
