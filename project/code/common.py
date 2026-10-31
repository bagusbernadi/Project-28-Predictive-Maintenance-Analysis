"""Path, konstanta, dan asumsi Project 28 (satu tempat, dipakai semua skrip)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]            # folder project/
REPO = ROOT.parent
CODE = ROOT / "code"
RAW_DIR = ROOT / "data" / "raw"
RAW_ZIP = RAW_DIR / "ai4i+2020+predictive+maintenance+dataset.zip"
CSV_NAME = "ai4i2020.csv"
SHA_ZIP = "f601f14294bcf190f9d720676b7f0aea46a26cde9ab8ebc7b4f8174d9d26b252"   # dicatat di repo DataCenter
SHA_CSV = "dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e"
DB_PATH = ROOT / "pdm.duckdb"
SQL_PREP = CODE / "1-data-preparation" / "sql"
SQL_ANALYSIS = CODE / "2-analysis" / "sql"
RES_PREP = ROOT / "results" / "1-data-preparation"
RES_ANALYSIS = ROOT / "results" / "2-analysis"
RES_PRESENT = ROOT / "results" / "3-presentation"
DOCS_DIR = ROOT / "docs"
for _d in (RES_PREP, RES_ANALYSIS, RES_PRESENT):
    _d.mkdir(parents=True, exist_ok=True)

COLS = ["udi", "product_id", "type", "air_temp_k", "process_temp_k", "rpm", "torque_nm", "tool_wear_min",
        "machine_failure", "twf", "hdf", "pwf", "osf", "rnf"]
MODES = ["twf", "hdf", "pwf", "osf", "rnf"]

# ---- parameter analisis (asumsi saya; didokumentasikan di docs/definitions.md)
SEED = 28102026            # satu seed untuk pembagian latih/uji dan bootstrap
TEST_SIZE = 0.30           # pembagian acak berstrata menurut machine_failure (UDI bukan urutan waktu)
N_BOOT = 300
ALERT_LIMIT = 0.10         # batas proporsi peringatan (kapasitas inspeksi) untuk memilih aturan; sensitivitas 5% dan 20%
ALERT_LIMITS = (0.05, 0.10, 0.20)
MIN_CELL = 30              # sel heatmap dengan run kurang dari ini ditandai tidak andal
H1_RATIO = 3.0             # "naik tajam" = failure rate setelah ambang minimal 3x sebelum ambang
QUANTILE_TAIL = 0.025      # "terlalu rendah/tinggi" (H4) = ekor 2,5% di tiap sisi; sensitivitas 1% dan 5%
# ---- asumsi dampak (estimated dan simulated; bukan angka nyata)
DOWNTIME_H = (2, 4, 8)     # jam downtime per kegagalan
PREVENT = (0.5, 0.8, 1.0)  # porsi kegagalan berperingatan yang benar-benar tercegah
INSPECT_H = 0.5            # jam per inspeksi akibat peringatan palsu
N_RUNS_SCENARIO = 10000    # jumlah run per skenario (sama dengan dataset)

# ---- ambang pada dokumentasi UCI (dibaca 31 Okt 2026), dipakai hanya untuk Q14
DOC = {"twf_lo": 200, "twf_hi": 240, "hdf_dt": 8.6, "hdf_rpm": 1380, "pwf_lo": 3500, "pwf_hi": 9000,
       "osf": {"L": 11000, "M": 12000, "H": 13000}, "rnf_cases": 5, "twf_cases": 120}


def result(name):
    """Cari CSV hasil di folder hasil mana pun."""
    for d in (RES_PREP, RES_ANALYSIS, RES_PRESENT):
        p = d / f"{name}.csv"
        if p.exists():
            return p
    raise FileNotFoundError(name)
