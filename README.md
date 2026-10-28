[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 28: Predictive Maintenance Failure Analysis

**Status: Design (rancangan).** Halaman rancangan ada di [`index.html`](index.html). Analisis, dashboard, dan angka hasil belum dikerjakan, sehingga bagian Analysis, Recommendation, dan Impact di bawah masih kosong.

**Tujuan:** menganalisis data operasi mesin publik untuk menemukan kondisi dan jenis kegagalan yang paling sering menyebabkan mesin rusak, lalu merumuskan aturan ambang sederhana yang terukur ketepatannya, agar jadwal inspeksi dan penggantian alat bisa ditentukan sebelum kerusakan terjadi.

| | |
|---|---|
| Kategori | Perawatan mesin (Manufaktur) |
| Tingkat | Menengah |
| Data | Dataset publik AI4I 2020 Predictive Maintenance, UCI (sintetis) |
| Tools | DuckDB + SQL, Python (pandas), Streamlit + Plotly, Excel (cek silang); scikit-learn dan SciPy opsional |

## 1. Problem

**Pertanyaan utama:** Kondisi operasi dan jenis kegagalan apa yang paling sering menyebabkan mesin rusak, dan pada ambang berapa risikonya naik?

Rancangan memecahnya menjadi 14 pertanyaan (9 Utama, 4 Pendukung, 1 Tambahan) dalam 5 tema: kegagalan, kondisi, aturan ambang, penerapan, serta data dan validitas.

## 2. Data

- Sumber data: [here](https://archive.ics.uci.edu/dataset/601) (Versi: UCI 2020, Tanggal akses: 24 Oktober 2026)
- Ukuran (perkiraan, **belum diverifikasi**): ±10.000 baris, 14 kolom, sekitar 3% run berlabel gagal. Angka ini dicek saat data diunduh.
- Data sintetis: dibuat penyusun dataset untuk meniru kondisi mesin nyata. Semua angka dampak diberi label `simulated`.
- Lisensi: CC BY 4.0 (halaman UCI, dicek 28 Oktober 2026). Sitasi: AI4I 2020 Predictive Maintenance Dataset [Dataset]. (2020). UCI Machine Learning Repository. https://doi.org/10.24432/C5HS5C. Data sintetis, bukan dari mesin nyata.
- Data mentah tidak di-commit ke repository. Cara mengunduhnya akan ditulis di `data/README.md`.
- Rencana tabel: `raw_ai4i`, `features`, `failure_mode_long`, `rule_eval`.

## 3. Analysis

Belum dikerjakan. Setiap aturan ambang dinilai dengan precision, recall, dan proporsi peringatan, lalu dibandingkan dengan baseline yang tidak pernah memberi peringatan.

Hipotesis yang akan diuji (belum terbukti):
1. Failure rate naik tajam setelah tool wear melewati sekitar 200 menit.
2. Tipe produk L lebih sering gagal dibanding tipe M dan H.
3. Selisih suhu proses dan udara yang kecil, ditambah putaran rendah, terkait dengan kegagalan panas.
4. Power yang terlalu rendah atau terlalu tinggi terkait dengan kegagalan daya.
5. Kombinasi torque tinggi dan tool wear tinggi mendahului overstrain, dengan batas yang berbeda per tipe produk.

## 4. Recommendation

Belum dikerjakan. Output yang direncanakan: usulan jadwal inspeksi dan penggantian alat berdasarkan ambang tool wear dan torque, beserta trade-off-nya.

## 5. Impact

Belum dikerjakan. Rumus yang akan dipakai (semua hasil diberi label `estimated` dan `simulated`):

```
Downtime terhindari = (failure rate lama − failure rate baru) × jumlah run × biaya per kejadian
```

Asumsi biaya per kejadian ditulis eksplisit, bukan angka nyata.

## Batasan yang sudah diketahui

- Data sintetis, polanya bisa lebih rapi dari kondisi nyata.
- Kegagalan sangat jarang, sehingga akurasi tinggi tidak berarti aturan berguna.
- Satu run bisa punya lebih dari satu jenis kegagalan, dan kegagalan acak (RNF) tidak bisa diprediksi.
- Pola belum tentu penyebab; ambang perlu diuji di lapangan.

## Struktur repository

```
index.html   Halaman rancangan project (bisa dibuka di browser atau lewat GitHub Pages)
README.md    Dokumen ini
```

Folder `docs/`, `data/`, `scripts/`, `sql/`, `notebooks/`, `dashboard/`, dan `outputs/` ditambahkan saat pengerjaan dimulai.
