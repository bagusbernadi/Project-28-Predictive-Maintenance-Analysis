[← Back to portfolio](https://bagusbernadi.github.io/)

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
- Ukuran (dihitung dari berkas): 10.000 baris, 14 kolom; 339 run gagal (3,39%).
- Data sintetis: dibuat penyusun dataset untuk meniru kondisi mesin nyata. Semua angka dampak berlabel `estimated` dan `simulated`.
- Lisensi: CC BY 4.0. Sitasi: AI4I 2020 Predictive Maintenance Dataset [Dataset]. (2020). UCI Machine Learning Repository. https://doi.org/10.24432/C5HS5C
- Data mentah tidak di-commit; cara menyiapkannya ada di [`project/data/README.md`](project/data/README.md).
- Tabel database: `raw_ai4i`, `features`, `failure_mode_long`, `rule_eval`.

## 3. Analysis

- **Failure rate** 3,39%; tipe L 3,92%, M 2,77%, H 2,09%.
- **Jenis kegagalan** (kejadian pada run gagal): HDF 115, OSF 98, PWF 95, TWF 46, RNF 1.
- **Hipotesis:** H1 (tool wear sekitar 200 menit) Terbukti; H2 (tipe L lebih sering gagal) Terbukti; H3 (selisih suhu kecil dan putaran rendah) Terbukti; H4 (power di ekor) Terbukti; H5 (torque dan tool wear, batas per tipe) Sebagian.
- **Aturan terpilih** (dari data latih, batas peringatan 10%): `wear x torque: L=11000, M=10500, H=11000 minNm | suhu-rpm: 9.5 K, 1380 rpm | torque: 55 Nm`. Data uji: precision 26,5%, recall 79,4%, proporsi peringatan 10,2%, akurasi 91,8%.
- **Akurasi menyesatkan:** aturan tidak pernah memberi peringatan punya akurasi 96,6% tetapi recall 0%.
- **Pembanding:** pohon keputusan kedalaman 3 (data uji): precision 96,3%, recall 51,0%.
- **Validasi:** 17 cek silang SQL vs pandas, 2 aturan SQL vs Python, dan 15 pemeriksaan Excel semuanya PASS.

## 4. Recommendation

Pakai aturan gabungan di atas sebagai alarm inspeksi awal dan ulangi pemilihan ambang dengan data mesin sendiri. Aturan tool wear saja (>= 200 menit) menangkap 36,3% kegagalan dengan 678 peringatan palsu per 10.000 run; aturan gabungan menangkap lebih banyak dengan proporsi peringatan sekitar 10%.

## 5. Impact

Semua angka berlabel `estimated` dan `simulated`. Pada asumsi downtime 4 jam per kegagalan, 80% kegagalan berperingatan tercegah, dan 0,5 jam per inspeksi, downtime terhindari sekitar 864 jam (kotor) dan 354 jam (bersih) per 10.000 run. Pada downtime 2 jam, hasil bersih -78 jam: aturan baru menguntungkan jika downtime per kegagalan cukup besar.

## Batasan

- Data sintetis; polanya lebih rapi dari kondisi nyata. Dokumentasi UCI dan data berbeda pada jumlah RNF dan TWF (Report 2, Q14).
- Kegagalan sangat jarang, sehingga akurasi tinggi tidak berarti aturan berguna. Data uji hanya 102 run gagal; tipe H sangat sedikit.
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
