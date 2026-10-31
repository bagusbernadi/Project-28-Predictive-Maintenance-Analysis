# Kamus data (AI4I 2020, UCI 601)

| Kolom asli | Kolom di database | Arti | Satuan / nilai |
|---|---|---|---|
| UDI | udi | Nomor baris unik 1 sampai 10.000 (bukan urutan waktu) | integer |
| Product ID | product_id | Kode produk, huruf tipe + nomor | teks, unik |
| Type | type | Tipe kualitas produk | L, M, H |
| Air temperature [K] | air_temp_k | Suhu udara | kelvin |
| Process temperature [K] | process_temp_k | Suhu proses | kelvin |
| Rotational speed [rpm] | rpm | Kecepatan putar | putaran per menit |
| Torque [Nm] | torque_nm | Gaya putar | newton meter |
| Tool wear [min] | tool_wear_min | Lama alat potong dipakai | menit |
| Machine failure | machine_failure | Run gagal | 0 atau 1 |
| TWF, HDF, PWF, OSF, RNF | twf, hdf, pwf, osf, rnf | Jenis kegagalan: tool wear, heat dissipation, power, overstrain, random | 0 atau 1 |

Tabel turunan: `features` (selisih suhu `temp_diff_k`, `power_w`, `wear_x_torque`, bucket tool wear 25 menit, bucket torque, bucket rpm), `failure_mode_long` (satu baris per jenis kegagalan per run), `rule_eval` (hasil uji aturan: tp, fp, fn, tn, precision, recall, alert_share).
