# Log kualitas data dan keputusan (Q13)

Sumber: `project/results/1-data-preparation/data_quality.csv` dan `label_issues.csv`.

| Temuan | Jumlah | Keputusan |
|---|---|---|
| Sel kosong, `udi` dan `product_id` duplikat, baris duplikat | 0 | Tidak perlu penanganan |
| Rentang nilai (suhu, rpm, torque, tool wear) | semua wajar; suhu proses selalu di atas suhu udara | Dipakai semua |
| `machine_failure = 1` tetapi tidak ada jenis kegagalan | 9 | Dipertahankan; label gagal dipakai untuk failure rate dan aturan; tidak masuk porsi jenis kegagalan |
| Jenis kegagalan = 1 tetapi `machine_failure = 0` | 18 (semuanya RNF) | Dipertahankan; `machine_failure` tidak diubah; kejadian RNF ini tidak dihitung pada porsi jenis kegagalan |
| Run dengan lebih dari satu jenis kegagalan | 24 | Dipertahankan; porsi jenis dihitung dari kejadian jenis, bukan dari run |
| Jumlah RNF di data vs dokumentasi UCI (19 vs 5) dan TWF (46 vs 120 kasus) | - | Dicatat sebagai perbedaan dengan dokumentasi (Q14); data tidak diubah |

Semua keputusan mempertahankan data asli; tidak ada baris yang dibuang.
