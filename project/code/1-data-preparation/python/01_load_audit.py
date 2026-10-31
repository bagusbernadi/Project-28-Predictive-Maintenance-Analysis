"""Langkah 1 dan 3: verifikasi file sumber (SHA-256), baca CSV dari zip, audit kualitas data (Q13), tulis hasil."""
import hashlib
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import COLS, CSV_NAME, MODES, RAW_ZIP, RES_PREP, SHA_CSV, SHA_ZIP  # noqa: E402


def load_raw():
    """Baca ai4i2020.csv dari zip; verifikasi SHA-256 zip dan csv terhadap catatan DataCenter."""
    zb = RAW_ZIP.read_bytes()
    assert hashlib.sha256(zb).hexdigest() == SHA_ZIP, "SHA-256 zip tidak cocok dengan catatan DataCenter"
    cb = zipfile.ZipFile(io.BytesIO(zb)).read(CSV_NAME)
    assert hashlib.sha256(cb).hexdigest() == SHA_CSV, "SHA-256 csv tidak cocok"
    df = pd.read_csv(io.BytesIO(cb))
    assert len(df.columns) == 14
    df.columns = COLS
    return df, len(zb), len(cb)


if __name__ == "__main__":
    df, nz, nc = load_raw()
    nm = df[MODES].sum(axis=1)
    f = df.machine_failure == 1
    rows = [
        ("baris", len(df)), ("kolom", df.shape[1]), ("sel kosong", int(df.isna().sum().sum())), ("udi duplikat", int(df.udi.duplicated().sum())),
        ("product_id duplikat", int(df.product_id.duplicated().sum())), ("baris duplikat (semua kolom selain id)", int(df.drop(columns=["udi", "product_id"]).duplicated().sum())),
        ("run L", int((df.type == "L").sum())), ("run M", int((df.type == "M").sum())), ("run H", int((df.type == "H").sum())),
        ("machine_failure = 1", int(f.sum())), ("machine_failure = 1 tanpa jenis kegagalan", int((f & (nm == 0)).sum())),
        ("jenis kegagalan = 1 tetapi machine_failure = 0", int((~f & (nm > 0)).sum())), ("  di antaranya RNF", int((~f & (df.rnf == 1)).sum())),
        ("run dengan lebih dari satu jenis kegagalan", int((nm > 1).sum())),
        ("suhu udara minimum (K)", df.air_temp_k.min()), ("suhu udara maksimum (K)", df.air_temp_k.max()),
        ("suhu proses minimum (K)", df.process_temp_k.min()), ("suhu proses maksimum (K)", df.process_temp_k.max()),
        ("rpm minimum", int(df.rpm.min())), ("rpm maksimum", int(df.rpm.max())), ("torque minimum (Nm)", df.torque_nm.min()), ("torque maksimum (Nm)", df.torque_nm.max()),
        ("tool wear minimum (menit)", int(df.tool_wear_min.min())), ("tool wear maksimum (menit)", int(df.tool_wear_min.max())),
        ("suhu proses <= suhu udara", int((df.process_temp_k <= df.air_temp_k).sum())),
        ("ukuran zip (byte)", nz), ("ukuran csv (byte)", nc),
    ]
    for m in MODES:
        rows.append((f"{m.upper()} = 1", int(df[m].sum())))
    pd.DataFrame(rows, columns=["ukuran", "nilai"]).to_csv(RES_PREP / "data_quality.csv", index=False)
    # baris bermasalah (label)
    bad = df[(f & (nm == 0)) | (~f & (nm > 0))][["udi", "type", "machine_failure"] + MODES].copy()
    bad["masalah"] = ["gagal tanpa jenis kegagalan" if r.machine_failure == 1 else "jenis kegagalan tanpa label gagal" for r in bad.itertuples()]
    bad.to_csv(RES_PREP / "label_issues.csv", index=False)
    pd.DataFrame([{"versi": "1 (UCI 2020)", "tanggal_akses": "2026-10-24", "diunggah_ke_datacenter": "2026-10-28", "sha256_zip": SHA_ZIP, "sha256_csv": SHA_CSV,
                   "ukuran_zip_byte": nz, "ukuran_csv_byte": nc}]).to_csv(RES_PREP / "download_log.csv", index=False)
    print("audit selesai:", len(rows), "ukuran;", len(bad), "baris label bermasalah")
