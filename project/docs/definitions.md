# Definisi metrik, hipotesis, dan asumsi (Project 28)

## Metrik
- **Failure rate** = run dengan `machine_failure = 1` ÷ total run. Interval kepercayaan: Wilson 95%.
- **TP, FP, FN, TN** (per aturan): TP = peringatan pada run gagal; FP = peringatan pada run tidak gagal (alat diinspeksi atau diganti terlalu cepat); FN = run gagal tanpa peringatan; TN = tanpa peringatan dan tidak gagal.
- **Precision** = TP ÷ (TP + FP). **Recall** = TP ÷ (TP + FN). **Proporsi peringatan** = (TP + FP) ÷ total run. **Akurasi** = (TP + TN) ÷ total run. **F1** = 2TP ÷ (2TP + FP + FN).
- **Baseline** = aturan yang tidak pernah memberi peringatan (akurasi = 1 − failure rate, recall 0%).
- **Power (W)** = torque (Nm) × rpm × 2π ÷ 60. **Selisih suhu (K)** = process temperature − air temperature. **Wear x torque (min·Nm)** = tool wear × torque.
- **Porsi jenis kegagalan**: dihitung dari kejadian jenis pada run bergagal (`machine_failure = 1`); satu run bisa punya beberapa jenis, jadi porsi per run gagal bisa melebihi 100% bila dijumlah. Pareto memakai porsi dari jumlah kejadian jenis.

## Penafsiran hipotesis (asumsi saya, karena rancangan tidak mendefinisikan angkanya)
| Hipotesis | Penafsiran dan kriteria verdict |
|---|---|
| H1 naik tajam setelah sekitar 200 menit | Tool wear >= 200 vs < 200. "Tajam" = failure rate minimal 3x; Fisher p < 0,001; titik naik terbaik (likelihood) dalam 25 menit dari 200 → Terbukti. Rasio minimal 3x tetapi titik jauh → Sebagian. |
| H2 tipe L lebih sering gagal | L vs M dan L vs H, Fisher exact, koreksi Bonferroni (3 perbandingan). Kedua signifikan → Terbukti; satu → Sebagian. Cek perancu: L vs M+H di dalam kelompok tool wear. |
| H3 selisih suhu kecil dan putaran rendah → HDF | "Kecil" dan "rendah" = kuartil terbawah (<= P25) selisih suhu dan rpm; sensitivitas P33 dan P50. Terbukti bila rasio >= 3x (atau pembanding 0 kejadian), p < 0,001, dan kelompok memuat >= 50% HDF. |
| H4 power terlalu rendah atau tinggi → PWF | "Terlalu" = ekor 2,5% bawah dan atas; sensitivitas 1% dan 5%. Terbukti bila kedua ekor masing-masing p < 0,001 dan rate PWF di ekor lebih tinggi dari bagian tengah. |
| H5 torque tinggi + tool wear tinggi → OSF, batas beda per tipe | "Tinggi" = >= P75 keduanya (Fisher p < 0,001). Batas per tipe = ambang wear x torque dengan F1 terbaik (grid 250), interval bootstrap 95% (300 ulangan, seed tetap). Terbukti bila batas L < M < H dan interval L dan H terpisah; hanya efek kelompok → Sebagian. |

## Pemilihan aturan ambang (Q8) dan asumsi
- **Pembagian data:** 70% latih dan 30% uji, acak berstrata menurut `machine_failure` (seed tetap). `UDI` bukan urutan waktu, jadi walk-forward tidak berlaku.
- **Pemilihan:** di data latih, aturan dengan recall tertinggi yang proporsi peringatannya <= **10%** (asumsi kapasitas inspeksi; sensitivitas 5% dan 20%). Seri → precision lebih tinggi. Nilai ambang per tipe untuk wear x torque dipilih dari F1 terbaik di data latih; bila F1 sama, ambang terendah.
- **Gabungan (OR):** aturan terbaik tiap keluarga ditambahkan berurutan menurut precision selama proporsi peringatan data latih gabungan <= batas.
- **Interpretasi hasil uji:** data uji hanya 102 run gagal, jadi satu kegagalan mengubah recall sekitar 1 poin; tipe H hanya 8 run gagal di data uji.

## Asumsi dampak (estimated, simulated; bukan angka nyata)
- Downtime per kegagalan: 2, 4, atau 8 jam. Porsi kegagalan berperingatan yang tercegah: 50%, 80%, atau 100%. Waktu per inspeksi: 0,5 jam untuk setiap peringatan. Skenario 10.000 run, memakai konfusi data uji dikalikan 10.000 ÷ 3.000.
- **Downtime terhindari (kotor)** = (failure rate lama − failure rate baru) × jumlah run × downtime per kegagalan; **bersih** = kotor − (jumlah peringatan × 0,5 jam). Rentang memakai batas bawah dan atas Wilson 95% untuk recall data uji.
