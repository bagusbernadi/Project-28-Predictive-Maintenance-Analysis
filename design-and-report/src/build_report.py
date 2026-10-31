"""Membuat design-and-report/index.html (Report Project versi 2) dari page_v1.html dan CSV hasil.

- Pane Design diambil apa adanya dari page_v1.html (dicek identik).
- Semua angka di Report berasal dari project/results/*.csv lewat helper I/D/P/cs (report_lib.py) dan diaudit di akhir.
Jalankan dari folder mana saja:  python design-and-report/src/build_report.py
"""
import re
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "project" / "code"))
sys.path.insert(0, str(HERE))
from common import ALERT_LIMIT, DB_PATH, DOWNTIME_H, INSPECT_H, PREVENT, RES_ANALYSIS, RES_PREP, RES_PRESENT, result  # noqa: E402
from report_lib import (BLUE, D, GREY, HI, I, NO, NUM, OK, P, PART, REG, SOFT, audit, bars, cs, esc, gbars, legend,  # noqa: E402
                        lines, pareto_svg, pill, qa, table)

R = lambda n: pd.read_csv(result(n))
PRIO = {1: "Utama", 2: "Utama", 3: "Utama", 4: "Utama", 5: "Pendukung", 6: "Pendukung", 7: "Pendukung", 8: "Utama", 9: "Utama",
        10: "Pendukung", 11: "Utama", 12: "Utama", 13: "Utama", 14: "Tambahan"}
QT = {1: "Berapa failure rate keseluruhan, dan apakah berbeda untuk tipe produk L, M, dan H?",
      2: "Jenis kegagalan mana yang paling sering, dan berapa porsi masing-masing?",
      3: "Pada tool wear berapa menit failure rate mulai naik tajam?",
      4: "Bagaimana torque dan kecepatan putar berhubungan dengan kegagalan?",
      5: "Apakah selisih suhu proses dan udara yang kecil terkait dengan kegagalan panas?",
      6: "Apakah power yang terlalu rendah atau terlalu tinggi terkait dengan kegagalan daya?",
      7: "Kombinasi torque dan tool wear seperti apa yang mendahului overstrain?",
      8: "Aturan ambang sederhana apa yang menangkap kegagalan terbanyak dengan peringatan palsu paling sedikit?",
      9: "Kenapa akurasi menyesatkan untuk data ini, dibanding aturan \"tidak pernah memberi peringatan\"?",
      10: "Apakah aturan terbaik tetap bekerja untuk tipe L, M, dan H secara terpisah?",
      11: "Berapa kegagalan yang bisa dicegah, dan berapa alat yang diganti terlalu cepat, jika aturan dipakai?",
      12: "Berapa estimasi downtime yang bisa dihindari?",
      13: "Apakah ada nilai kosong, duplikat, atau label yang tidak konsisten, misalnya mesin gagal tanpa jenis kegagalan?",
      14: "Seberapa mirip ambang yang ditemukan dengan aturan yang dijelaskan di dokumentasi dataset?"}
WARN = set()


def Q(n, ans, warn=False):
    if warn:
        WARN.add(n)
    return qa(f"Q{n}", QT[n], PRIO[n], ans, "Terjawab dengan catatan" if warn else "Terjawab", warn)


mk = lambda *a: "".join(a)
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
TGL = lambda s: cs(f"{int(str(s)[8:10])} {BULAN[int(str(s)[5:7]) - 1]} {str(s)[:4]}")


def PV(p):
    """p-value: di bawah 0,001 ditulis '< 0,001', selain itu tiga desimal."""
    return "&lt; " + D(0.001, 3) if float(p) < 0.001 else D(p, 3)


def lab(s):
    """Label bucket dari CSV (sudah berformat Indonesia): buang awalan 'a: ', daftarkan angkanya untuk audit."""
    t = re.sub(r"^[a-f]: ", "", str(s))
    for tok in NUM.findall(t):
        REG.add(tok.lstrip("+-").rstrip(".,"))
    return esc(t)


VP = lambda v: {"Terbukti": OK, "Sebagian": PART, "Tidak terbukti": NO}[v](v)


def pick(df, **kw):
    m = pd.Series(True, index=df.index)
    for k, v in kw.items():
        m &= np.isclose(df[k], v) if isinstance(v, float) else (df[k] == v)
    assert m.sum() == 1, (kw, int(m.sum()))
    return df[m].iloc[0]


# ---------------------------------------------------------------- data
dq = R("data_quality").set_index("ukuran").nilai
dlog, tabrows = R("download_log").iloc[0], R("table_rows").set_index("tabel").baris
ctest, cons, lissue = R("constraint_tests"), R("consistency_checks"), R("label_issues")
rt, fm = R("rate_by_type").set_index("type"), R("failure_modes").set_index("failure_mode")
wb, h1 = R("wear_bucket"), R("h1_wear_scan").set_index("ambang_menit")
trq, td, pw, ob = R("torque_rpm"), R("temp_diff_hdf"), R("power_pwf"), R("osf_by_type")
hy = R("hypotheses").set_index("id")
h2t, h2s, h3, h4, h5 = R("h2_type_tests").set_index("pasangan"), R("h2_stratified").set_index("kelompok"), R("h3_heat_tests"), R("h4_power_tests"), R("h5_type_thresholds").set_index("type")
ev, rsel, fr = R("rule_eval"), R("rule_selection"), R("final_rule").iloc[0]
frt, tree, tro, imp, dcmp = R("final_rule_by_type"), R("tree_compare"), R("tradeoff"), R("impact"), R("doc_comparison")
xs, xr, xe = R("crosscheck_sql_pandas"), R("crosscheck_rules"), R("crosscheck_excel")
con = duckdb.connect(str(DB_PATH), read_only=True)
sample = con.execute("SELECT * FROM ((SELECT udi, type, rpm, torque_nm, tool_wear_min, machine_failure FROM raw_ai4i ORDER BY udi LIMIT 3) "
                     "UNION ALL (SELECT udi, type, rpm, torque_nm, tool_wear_min, machine_failure FROM raw_ai4i WHERE machine_failure = 1 ORDER BY udi LIMIT 2))").fetchall()
con.close()

N, NF = int(dq["baris"]), int(dq["machine_failure = 1"])
NMODE = ["HDF", "OSF", "PWF", "TWF", "RNF"]
b_all = pick(ev, rule_name="baseline (tidak pernah memberi peringatan)", period="all")
b_test = pick(ev, rule_name="baseline (tidak pernah memberi peringatan)", period="test")
w200 = pick(tro, rule_name="tool wear >= T", threshold="200 menit")
w100 = pick(tro, rule_name="tool wear >= T", threshold="100 menit")
fall = pick(tro, rule_name="aturan terpilih (gabungan)", period="all")
rs_ = lambda lim, name: pick(rsel, batas_alert_share=lim, rule_name=name, period="test")
u10, u05, u20 = (rs_(x, "gabungan (OR)") for x in (0.1, 0.05, 0.2))
pt10 = rs_(0.1, "tool wear x torque >= P (per tipe)")
assert u10.threshold == u20.threshold == fr.threshold and fr.batas_alert_share == ALERT_LIMIT
tr3 = pick(tree, model="pohon keputusan kedalaman 3", period="test")
tr3b = pick(tree, model="pohon keputusan kedalaman 3, bobot seimbang", period="test")
ip = lambda h, pr, sk="titik": pick(imp, downtime_per_kegagalan_h=h, porsi_tercegah=pr, skenario=sk)
i48, i48lo, i48hi = ip(4, 0.8), ip(4, 0.8, "batas bawah (Wilson 95%)"), ip(4, 0.8, "batas atas (Wilson 95%)")
i22 = ip(2, 0.5)
fz = lambda t, p: pick(frt, type=t, period=p)
npr = {k: sum(1 for v in PRIO.values() if v == k) for k in ("Utama", "Pendukung", "Tambahan")}
best_wear = int(h1.log_likelihood.idxmax())

assert (N, NF, len(PRIO)) == (10000, 339, 14) and npr == {"Utama": 9, "Pendukung": 4, "Tambahan": 1}
assert (xs.status == "PASS").all() and (xr.status == "PASS").all() and (xe.status == "PASS").all()
assert (ctest.outcome == "ditolak").all() and (cons.violations == 0).all()
assert best_wear == 200 and tuple(hy.verdict) == ("Terbukti", "Terbukti", "Terbukti", "Terbukti", "Sebagian")
assert (fr.tp_all, fr.fp_all, fr.fn_all, fr.tn_all) == (fall.failures_caught, fall.false_alerts, fall.failures_missed, N - fall.alerts - fall.failures_missed)
assert len(lissue) == dq["machine_failure = 1 tanpa jenis kegagalan"] + dq["jenis kegagalan = 1 tetapi machine_failure = 0"]

# ---------------------------------------------------------------- 1. data
kp = lambda c, v, l, d: f'<div class="card kpi" style="--h:var(--{c}H)"><span class="v">{v}</span><span class="l">{l}</span><span class="d">{d}</span></div>'
rp1 = mk(
    '<div class="callout a"><h4>Data project ini adalah simulasi</h4><p>Dataset AI4I 2020 dibuat sintetis oleh penyusunnya untuk meniru mesin milling; bukan data dari lini produksi nyata. '
    'Karena itu angka dampak diberi label <i>estimated</i> dan <i>simulated</i>.</p></div>',
    '<div class="kpis">',
    kp("navy", I(N), "run mesin", f"Satu baris satu run, {I(dq['kolom'])} kolom, tipe L {I(dq['run L'])}, M {I(dq['run M'])}, H {I(dq['run H'])}."),
    kp("amber", I(NF), "run gagal", f"Failure rate {P(rt.failures_rate['Semua'], 2)}; kegagalan sangat jarang, sehingga akurasi bisa menyesatkan."),
    kp("teal", I(tabrows["failure_mode_long"]), "kejadian jenis kegagalan", f"TWF, HDF, PWF, OSF, RNF; satu run bisa punya lebih dari satu jenis ({I(dq['run dengan lebih dari satu jenis kegagalan'])} run)."),
    kp("plum", I(len(lissue)), "baris label tidak konsisten", f"{I(dq['machine_failure = 1 tanpa jenis kegagalan'])} gagal tanpa jenis kegagalan dan {I(dq['jenis kegagalan = 1 tetapi machine_failure = 0'])} jenis kegagalan (semua RNF) tanpa label gagal."),
    kp("rose", I(len(ev)), "baris evaluasi aturan", "Setiap aturan dan ambang dinilai pada data latih, uji, dan seluruh data."),
    kp("sky", I(len(xs) + len(xr) + len(xe)), "cek silang PASS", f"{I(len(xs))} SQL vs pandas, {I(len(xr))} aturan SQL vs Python, {I(len(xe))} SQL/Python vs Excel."),
    '</div><h3>1.1 Data mentah (AI4I 2020)</h3>')
rp1 += '<div class="card"><h4>Cuplikan raw_ai4i (tiga baris pertama dan dua run gagal pertama)</h4>' + table(
    ["udi", "type", "rpm", "torque_nm", "tool_wear_min", "machine_failure"], [[I(r[0]), r[1], I(r[2]), D(r[3], 1), I(r[4]), I(r[5])] for r in sample]) + \
    '<p>Kolom suhu dan label jenis kegagalan tidak ditampilkan agar tabel ringkas.</p></div>'
rp1 += '<div class="card"><h4>Tabel 1.1. Kualitas data</h4>' + table(
    ["Pemeriksaan", "Hasil", "Keputusan"],
    [["Baris dan kolom", f"{I(dq['baris'])} baris, {I(dq['kolom'])} kolom", "Dipakai semua"],
     ["Sel kosong, <code>udi</code> atau <code>product_id</code> ganda, baris ganda", f"{I(dq['sel kosong'])}, {I(dq['udi duplikat'])}, {I(dq['product_id duplikat'])}, {I(dq['baris duplikat (semua kolom selain id)'])}", "Tidak perlu penanganan"],
     ["Rentang nilai", f"suhu proses selalu di atas suhu udara ({I(dq['suhu proses <= suhu udara'])} pelanggaran); rpm {I(dq['rpm minimum'])} sampai {I(dq['rpm maksimum'])}; torque {D(dq['torque minimum (Nm)'], 1)} sampai {D(dq['torque maksimum (Nm)'], 1)} Nm; tool wear {I(dq['tool wear minimum (menit)'])} sampai {I(dq['tool wear maksimum (menit)'])} menit", "Wajar, dipakai"],
     ["Gagal (<code>machine_failure</code> = 1) tanpa jenis kegagalan", I(dq["machine_failure = 1 tanpa jenis kegagalan"]), "Dipertahankan; ikut failure rate dan aturan, tidak ikut porsi jenis"],
     ["Jenis kegagalan = 1 tetapi tidak gagal", f"{I(dq['jenis kegagalan = 1 tetapi machine_failure = 0'])} (semuanya RNF)", "Dipertahankan; <code>machine_failure</code> tidak diubah"],
     ["Run dengan lebih dari satu jenis kegagalan", I(dq["run dengan lebih dari satu jenis kegagalan"]), "Dipertahankan; porsi dihitung dari kejadian jenis"]]) + \
    f'<p>Sumber: AI4I 2020 versi {cs(dlog.versi)}, tanggal akses {TGL(dlog.tanggal_akses)}; berkas diunggah ke repositori dataset pemilik pada {TGL(dlog.diunggah_ke_datacenter)} dan diverifikasi dengan SHA-256 (<code>download_log.csv</code>). Data mentah tidak di-commit. Keputusan lengkap ada di <code>project/docs/cleaning_decisions.md</code>; Q13 menjawabnya di bagian 2.8.</p></div>'
rp1 += '<h3>1.2 Tabel di database (<code>pdm.duckdb</code>)</h3><div class="card"><h4>Tabel 1.2a. Isi database</h4>' + table(
    ["Tabel", "Baris", "Isi"],
    [["raw_ai4i", I(tabrows["raw_ai4i"]), "Satu run mesin seperti di file asli, dengan constraint kolom."],
     ["features", I(tabrows["features"]), "Satu run dengan fitur turunan: selisih suhu, power, tool wear x torque, bucket tool wear, torque, dan rpm."],
     ["failure_mode_long", I(tabrows["failure_mode_long"]), "Satu jenis kegagalan yang terjadi pada satu run."],
     ["rule_eval", I(len(ev)), "Satu aturan dengan satu ambang pada satu periode (diisi skrip evaluasi aturan)."]]) + \
    '<h4>Tabel 1.2b. Uji aturan pengecekan (constraint)</h4>' + table(
    ["Baris salah yang dicoba dimasukkan", "Hasil"], [[r.test, OK("Ditolak") if r.outcome == "ditolak" else NO("Diterima")] for r in ctest.itertuples()]) + \
    f'<p>Kesepuluh jenis data salah ditolak oleh database. {I(len(cons))} pemeriksaan konsistensi menghasilkan 0 pelanggaran.</p></div>'
FILES = {"consistency_checks": ("Pemeriksaan konsistensi database", "Q13"), "constraint_tests": ("Uji penolakan data salah (constraint)", "Q13"),
         "data_quality": ("Ringkasan kualitas data", "Q13"), "download_log": ("Log sumber data (versi, tanggal akses, SHA-256)", "dokumentasi"),
         "label_issues": ("Baris dengan label kegagalan tidak konsisten", "Q13"), "table_rows": ("Baris per tabel database", "dokumentasi"),
         "crosscheck_excel": ("Cek silang SQL dan Python vs Excel", "validasi"), "crosscheck_rules": ("Aturan: SQL vs Python", "validasi"),
         "crosscheck_sql_pandas": ("Query SQL vs pandas", "validasi"), "doc_comparison": ("Temuan vs dokumentasi UCI", "Q14"),
         "failure_modes": ("Jenis kegagalan dan porsinya (Pareto)", "Q2"), "final_rule": ("Aturan terpilih: latih, uji, semua data", "Q8, Q9"),
         "final_rule_by_type": ("Aturan terpilih per tipe produk", "Q10"), "h1_wear_scan": ("Pemindaian ambang tool wear", "Q3"),
         "h2_stratified": ("Tipe L vs M dan H per kelompok tool wear", "Q1"), "h2_type_tests": ("Uji perbedaan antar tipe", "Q1"),
         "h3_heat_tests": ("Uji HDF: selisih suhu dan rpm rendah", "Q5"), "h4_power_tests": ("Uji PWF: ekor power", "Q6"),
         "h5_type_thresholds": ("Ambang tool wear x torque terbaik per tipe", "Q7"), "hypotheses": ("Verdict kelima hipotesis", "Q1, Q3, Q5, Q6, Q7"),
         "impact": ("Skenario downtime terhindari (estimated)", "Q12"), "osf_by_type": ("OSF per tipe, kelompok tool wear dan torque", "Q7"),
         "power_pwf": ("PWF per bucket power", "Q6"), "rate_by_type": ("Failure rate per tipe dengan interval Wilson", "Q1"),
         "rule_eval": ("Semua aturan dan ambang pada latih, uji, semua data", "Q8, Q9"), "rule_selection": ("Aturan terpilih pada batas peringatan 5%, 10%, 20%", "Q8"),
         "temp_diff_hdf": ("HDF per bucket selisih suhu", "Q5"), "torque_rpm": ("Failure rate per bucket torque x rpm", "Q4"),
         "tradeoff": ("Kegagalan tertangkap vs peringatan palsu", "Q11"), "tree_compare": ("Pohon keputusan sebagai pembanding", "Q8"),
         "wear_bucket": ("Failure rate per bucket tool wear", "Q3")}
resfiles = sorted(p for d in (RES_PREP, RES_ANALYSIS) for p in d.glob("*.csv"))
miss = [p.stem for p in resfiles if p.stem not in FILES]
assert not miss, f"CSV hasil belum didokumentasikan di FILES: {miss}"
assert not [k for k in FILES if k not in {p.stem for p in resfiles}]
ndash = len(list(RES_PRESENT.glob("dash_*.csv")))
rp1 += '<div class="card"><h4>Tabel 1.2c. Data hasil analisis (<code>project/results/</code>)</h4>' + table(
    ["File", "Isi", "Baris", "Menjawab"], [[f"<code>{p.stem}.csv</code>", FILES[p.stem][0], I(len(pd.read_csv(p))), FILES[p.stem][1]] for p in resfiles]) + \
    f'<p>{I(len(resfiles))} file CSV, ditambah {I(ndash)} CSV data dashboard di <code>results/3-presentation/</code>.</p></div>'
rp1 += '<h3>1.3 Angka kunci (KPI)</h3><div class="card"><h4>Tabel 1.3. Lima KPI (definisi di <code>project/docs/definitions.md</code>)</h4>' + table(
    ["KPI", "Rumus ringkas", "Hasil", "Jumlah data"],
    [["Failure rate", "run gagal ÷ semua run", f"{P(rt.failures_rate['Semua'], 2)} (interval 95%: {P(rt.failures_lo['Semua'], 2)} sampai {P(rt.failures_hi['Semua'], 2)})", f"{I(NF)} dari {I(N)} run"],
     ["Recall aturan terpilih", "kegagalan yang diberi peringatan ÷ semua kegagalan", f"{P(fr.recall_test, 1)} pada data uji ({P(fr.recall_all, 1)} semua data)", f"{I(fr.tp_test)} dari {I(fr.tp_test + fr.fn_test)} kegagalan uji"],
     ["Precision aturan terpilih", "peringatan yang benar ÷ semua peringatan", f"{P(fr.precision_test, 1)} pada data uji", f"{I(fr.tp_test)} dari {I(fr.tp_test + fr.fp_test)} peringatan uji"],
     ["Proporsi peringatan", "run yang diberi peringatan ÷ semua run", f"{P(fr.alert_share_test, 1)} pada data uji (batas pemilihan {P(ALERT_LIMIT, 0)})", f"{I(fr.tp_test + fr.fp_test)} dari {I(fr.tp_test + fr.fp_test + fr.fn_test + fr.tn_test)} run uji"],
     ["Downtime terhindari bersih (estimated)", "(kegagalan tertangkap × porsi tercegah × jam downtime) − jam inspeksi", f"{D(i48.downtime_terhindari_bersih_h, 0)} jam per {I(10000)} run",
      f"asumsi 4 jam, {P(0.8, 0)} tercegah, {D(INSPECT_H, 1)} jam per inspeksi"]]) + \
    f'<p>Aturan terpilih dipilih pada data latih (batas peringatan {P(ALERT_LIMIT, 0)}); angka uji tidak dipakai untuk memilih ulang.</p></div>'

# ---------------------------------------------------------------- 2. business questions
hyp_rows = [
    ["H1", hy.loc["H1", "hipotesis"], VP(hy.loc["H1", "verdict"]),
     f"Failure rate {P(h1.loc[200].rate_ge, 1)} pada tool wear ≥ 200 menit vs {P(h1.loc[200].rate_lt, 1)} di bawahnya (rasio {D(h1.loc[200].rasio, 2)}x, p {PV(h1.loc[200].p_fisher)}); ambang dengan likelihood terbaik: {I(best_wear)} menit"],
    ["H2", hy.loc["H2", "hipotesis"], VP(hy.loc["H2", "verdict"]),
     f"L {P(rt.failures_rate['L'], 2)} vs M {P(rt.failures_rate['M'], 2)} (p Bonferroni {D(h2t.loc['L vs M'].p_bonferroni, 3)}) dan vs H {P(rt.failures_rate['H'], 2)} (p {D(h2t.loc['L vs H'].p_bonferroni, 3)}); di dalam kelompok tool wear &lt; 200 beda L vs M+H belum signifikan (p {D(h2s.loc['tool wear < 200'].p_fisher, 3)})"],
    ["H3", hy.loc["H3", "hipotesis"], VP(hy.loc["H3", "verdict"]),
     f"Kelompok selisih suhu ≤ {D(h3.iloc[0].batas_selisih_suhu_k, 1)} K dan rpm ≤ {I(h3.iloc[0].batas_rpm)}: HDF {P(h3.iloc[0].rate_kelompok, 1)} vs {P(h3.iloc[0].rate_lainnya, 0)} di luar kelompok, menangkap {P(h3.iloc[0].recall_hdf, 0)} HDF (p {PV(h3.iloc[0].p_fisher)})"],
    ["H4", hy.loc["H4", "hipotesis"], VP(hy.loc["H4", "verdict"]),
     f"PWF {P(hy.loc['H4', 'statistik_rasio'], 0)} di kedua ekor power (2,5% bawah dan atas) vs 0% di bagian tengah (p {PV(hy.loc['H4', 'p_value'])})"],
    ["H5", hy.loc["H5", "hipotesis"], VP(hy.loc["H5", "verdict"]),
     f"Torque dan tool wear sama-sama ≥ P75 jelas mendahului OSF (p {PV(hy.loc['H5', 'p_value'])}); ambang terbaik L {I(h5.loc['L'].ambang_terbaik_minNm)}, M {I(h5.loc['M'].ambang_terbaik_minNm)}, H {I(h5.loc['H'].ambang_terbaik_minNm)} minNm, tetapi M sama dengan H dan H hanya {I(h5.loc['H'].osf)} kejadian OSF"]]
assert (np.isclose(hy.loc["H4", "statistik_rasio"], 0.19))
hyp_tbl = '<div class="card"><h4>Hipotesis pada Design Project (bunyi sama dengan rancangan)</h4>' + table(["No", "Hipotesis", "Hasil", "Bukti"], hyp_rows) + \
    '<p>Penafsiran istilah yang tidak didefinisikan rancangan (\"kecil\", \"terlalu\", \"tinggi\") ada di <code>project/docs/definitions.md</code> dan diuji sensitivitasnya (Tabel 2.4c, 2.4d); lihat juga 7.6.</p></div>'

TYPES = ["L", "M", "H"]
sec21 = mk(
    '<h3 id="sec21">2.1 Failure rate dan jenis kegagalan <span class="qlist">Q1, Q2</span></h3><div class="card">',
    Q(1, f"Failure rate keseluruhan {P(rt.failures_rate['Semua'], 2)} ({I(NF)} dari {I(N)} run). Tipe L {P(rt.failures_rate['L'], 2)}, M {P(rt.failures_rate['M'], 2)}, H {P(rt.failures_rate['H'], 2)}: L paling tinggi dan perbedaannya nyata (L vs M p Bonferroni {D(h2t.loc['L vs M'].p_bonferroni, 3)}, L vs H p {D(h2t.loc['L vs H'].p_bonferroni, 3)}; M vs H tidak berbeda, p {D(h2t.loc['M vs H'].p_bonferroni, 2)}). "
         f"Selisihnya sebagian berasal dari tool wear: pada tool wear ≥ 200 menit L {P(h2s.loc['tool wear >= 200'].rate_L, 1)} vs M dan H {P(h2s.loc['tool wear >= 200'].rate_MH, 1)}."),
    Q(2, f"HDF paling sering ({I(fm.loc['HDF']['flags'])} kejadian, {P(fm.loc['HDF'].share_of_flags, 1)} dari semua kejadian jenis), lalu OSF ({I(fm.loc['OSF']['flags'])}), PWF ({I(fm.loc['PWF']['flags'])}), TWF ({I(fm.loc['TWF']['flags'])}), dan RNF ({I(fm.loc['RNF']['flags'])}). Tiga jenis pertama sudah {P(fm.loc['PWF'].cum_share, 1)} dari kejadian. "
         f"RNF hanya {I(fm.loc['RNF'].flags_with_failure)} dari {I(fm.loc['RNF']['flags'])} kejadian yang berlabel gagal, jadi bukan penyebab kegagalan yang berarti."),
    '<h4>Grafik 2.1a. Failure rate per tipe produk (batang = titik; tooltip memuat interval Wilson 95%)</h4>',
    bars([(t, rt.failures_rate[t], BLUE if t == "L" else GREY, f"Tipe {t}: {P(rt.failures_rate[t], 2)}, interval {P(rt.failures_lo[t], 2)} sampai {P(rt.failures_hi[t], 2)}, {I(rt.failures[t])} dari {I(rt.n[t])} run") for t in TYPES],
         lambda v: P(v, 1), "Failure rate per tipe", rot=0, small=True),
    '<h4>Grafik 2.1b. Pareto jenis kegagalan (porsi dari semua kejadian jenis; garis = kumulatif, garis putus-putus = 80%)</h4>',
    pareto_svg(NMODE, [fm.loc[m].share_of_flags for m in NMODE], [fm.loc[m].cum_share for m in NMODE], [fm.loc[m].cum_share - fm.loc[m].share_of_flags < 0.8 for m in NMODE],
               [f"{m}: {I(fm.loc[m]['flags'])} kejadian, {P(fm.loc[m].share_of_flags, 1)}, kumulatif {P(fm.loc[m].cum_share, 1)}" for m in NMODE], "Pareto jenis kegagalan"),
    '<h4>Tabel 2.1c. Uji perbedaan antar tipe (Fisher exact, koreksi Bonferroni)</h4>',
    table(["Pasangan", "Failure rate pertama", "Failure rate kedua", "Rasio", "p Fisher", "p Bonferroni"],
          [[p, P(r.rate_pertama, 2), P(r.rate_kedua, 2), D(r.rasio, 2) + "x", PV(r.p_fisher), PV(r.p_bonferroni)] for p, r in h2t.iterrows() if p != "chi-kuadrat 3 tipe"]),
    '<h4>Tabel 2.1d. Tipe L vs M dan H menurut kelompok tool wear</h4>',
    table(["Kelompok", "Run L", "Failure rate L", "Run M dan H", "Failure rate M dan H", "p Fisher"],
          [[k, I(r.n_L), P(r.rate_L, 2), I(r.n_MH), P(r.rate_MH, 2), PV(r.p_fisher)] for k, r in h2s.iterrows()]),
    '<h4>Tabel 2.1e. Jenis kegagalan</h4>',
    table(["Jenis", "Kejadian", "Dengan label gagal", "Tanpa label gagal", "Porsi dari kejadian", "Kumulatif"],
          [[m, I(fm.loc[m]['flags']), I(fm.loc[m].flags_with_failure), I(fm.loc[m].flags_without_failure), P(fm.loc[m].share_of_flags, 1), P(fm.loc[m].cum_share, 1)] for m in NMODE]),
    f'<p>Satu run bisa punya lebih dari satu jenis ({I(dq["run dengan lebih dari satu jenis kegagalan"])} run) dan {I(dq["machine_failure = 1 tanpa jenis kegagalan"])} run gagal tidak punya jenis, sehingga porsi dihitung dari kejadian jenis, bukan dari run gagal.</p></div>')

sec22 = mk(
    '<h3 id="sec22">2.2 Tool wear <span class="qlist">Q3</span></h3><div class="card">',
    Q(3, f"Failure rate datar di sekitar {P(wb.failures_rate[:7].min(), 1)} sampai {P(wb.failures_rate[:7].max(), 1)} sampai tool wear {I(175)} menit, naik sedikit ke {P(wb.failures_rate[7], 1)} pada {I(175)} sampai {I(199)} menit, lalu melonjak ke {P(wb.failures_rate[8], 1)} pada {I(200)} sampai {I(224)} menit dan {P(wb.failures_rate[9], 1)} pada {I(225)} sampai {I(249)} menit. "
         f"Tool wear ≥ 200 menit: {P(h1.loc[200].rate_ge, 1)} vs {P(h1.loc[200].rate_lt, 1)} di bawahnya (rasio {D(h1.loc[200].rasio, 2)}x); ambang 200 menit juga yang likelihood-nya tertinggi di antara ambang {I(h1.index.min())} sampai {I(h1.index.max())}. "
         f"Bucket 250+ hanya {I(wb.n.iloc[-1])} run, jadi tidak dibaca. \"Naik tajam\" dalam rancangan tidak didefinisikan; saya menafsirkannya sebagai rasio minimal 3x dengan p &lt; {D(0.001, 3)} (hipotesis 1 Terbukti).", warn=True),
    '<h4>Grafik 2.2a. Failure rate per bucket tool wear (menit)</h4>',
    bars([(r.wear_bucket, r.failures_rate, HI if r.wear_bucket in ("200-224", "225-249") else BLUE, f"{r.wear_bucket} menit: {P(r.failures_rate, 1)}, interval {P(r.failures_lo, 1)} sampai {P(r.failures_hi, 1)}, {I(r.failures)} dari {I(r.n)} run") for r in wb.itertuples()],
         lambda v: P(v, 0), "Failure rate per bucket tool wear", rot=35),
    '<h4>Tabel 2.2b. Pemindaian ambang tool wear (Fisher exact)</h4>',
    table(["Ambang (menit)", "Run ≥ ambang", "Failure rate ≥", "Failure rate &lt;", "Rasio", "p Fisher"],
          [[I(a), I(h1.loc[a].n_ge), P(h1.loc[a].rate_ge, 1), P(h1.loc[a].rate_lt, 1), D(h1.loc[a].rasio, 2) + "x", PV(h1.loc[a].p_fisher)] for a in (150, 175, 190, 200, 210, 220, 240)]),
    f'<p>Hasil semua ambang ({I(len(h1))} ambang) ada di <code>h1_wear_scan.csv</code>. Di tool wear ≥ 200 menit sebagian besar kegagalan adalah TWF dan OSF (Tabel 2.2c).</p>',
    '<h4>Tabel 2.2c. Jenis kegagalan per bucket tool wear (kejadian)</h4>',
    table(["Bucket (menit)", "Run", "Run gagal", "TWF", "OSF"], [[r.wear_bucket, I(r.n), I(r.failures), I(r.twf), I(r.osf)] for r in wb.iloc[6:].itertuples()]), '</div>')

TB = ["<30", "30-39", "40-49", "50-59", "60+"]
RB = ["<1400", "1400-1499", "1500-1599", "1600-1799", "1800+"]
hm = trq.set_index(["torque_bucket", "rpm_bucket"])


def cell(t, r):
    if (t, r) not in hm.index:
        return "-"
    x = hm.loc[(t, r)]
    return f"{P(x.failures_rate, 1)} ({I(x.n)}){'' if x.reliable else ' †'}"


hot = trq[trq.reliable].sort_values("failures_rate", ascending=False).iloc[0]
sec23 = mk(
    '<h3 id="sec23">2.3 Torque dan kecepatan putar <span class="qlist">Q4</span></h3><div class="card">',
    Q(4, f"Risiko naik ketika torque tinggi dan rpm rendah. Sel dengan data cukup (≥ 30 run) yang paling berisiko: torque {lab(hot.torque_bucket)} Nm dengan rpm {lab(hot.rpm_bucket)}: {P(hot.failures_rate, 1)} ({I(hot.failures)} dari {I(hot.n)} run). "
         f"Pada torque {I(50)} sampai {I(59)} Nm dan rpm &lt; 1400 failure rate {P(hm.loc[('50-59', '<1400')].failures_rate, 1)}; pada torque &lt; 30 Nm dengan rpm 1800+ {P(hm.loc[('<30', '1800+')].failures_rate, 1)}, jadi rpm sangat tinggi dengan torque rendah juga berisiko (PWF). "
         f"Pada rentang tengah (torque {I(30)} sampai {I(49)} Nm, rpm {I(1400)} sampai {I(1799)}) failure rate di bawah {P(0.01, 0)}. Sel dengan kurang dari {I(30)} run ditandai † dan tidak dibaca (mis. torque 60+ dengan rpm 1400-1499: {I(hm.loc[('60+', '1400-1499')].n)} run).", warn=True),
    '<h4>Tabel 2.3a. Failure rate per bucket torque (Nm) × rpm, dengan jumlah run di kurung (heatmap dalam bentuk tabel)</h4>',
    table(["Torque \\ rpm"] + [lab(r) for r in RB], [[lab(t)] + [cell(t, r) for r in RB] for t in TB]),
    f'<p>† = kurang dari {I(30)} run; interval kepercayaan sangat lebar. Dashboard memuat versi warna (<code>dash_heatmap.csv</code>).</p></div>')

td0 = td.iloc[:2]
sec24 = mk(
    '<h3 id="sec24">2.4 Selisih suhu dan power <span class="qlist">Q5, Q6</span></h3><div class="card">',
    Q(5, f"Ya, dengan rpm rendah. Seluruh {I(td.hdf.sum())} HDF jatuh pada selisih suhu &lt; {D(8.6, 1)} K dan rpm &lt; {I(1380)}; di bucket selisih suhu lain HDF 0. Pada selisih suhu &lt; {D(8.0, 1)} K HDF {P(td.hdf_rate[0], 1)} dan pada {D(8.0, 1)} sampai {D(8.5, 1)} K {P(td.hdf_rate[1], 1)}. "
         f"Definisi \"kecil\" dan \"rendah\" saya tafsirkan sebagai kuartil terbawah (selisih ≤ {D(h3.iloc[0].batas_selisih_suhu_k, 1)} K, rpm ≤ {I(h3.iloc[0].batas_rpm)}): HDF {P(h3.iloc[0].rate_kelompok, 1)} vs 0% di luarnya, menangkap {P(h3.iloc[0].recall_hdf, 0)} HDF; hasil sama pada sepertiga dan separuh terbawah (Tabel 2.4c). Hipotesis 3 Terbukti.", warn=True),
    Q(6, f"Ya. Power di bawah {I(3500)} W: {I(pw.pwf[0])} dari {I(pw.n[0])} run PWF ({P(pw.pwf_rate[0], 0)}); di atas {I(9000)} W: {I(pw.pwf[5])} dari {I(pw.n[5])} run ({P(pw.pwf_rate[5], 0)}); di rentang tengah PWF 0. "
         f"\"Terlalu rendah atau tinggi\" saya tafsirkan sebagai ekor {P(0.025, 1)} di tiap sisi (&lt; {I(h4[h4.ekor == '2.5%'].batas_bawah_w.iloc[0])} W atau &gt; {I(h4[h4.ekor == '2.5%'].batas_atas_w.iloc[0])} W): PWF {P(hy.loc['H4', 'statistik_rasio'], 0)} vs 0% di tengah; sensitivitas 1% dan 5% sama arahnya (Tabel 2.4d). Hipotesis 4 Terbukti.", warn=True),
    '<h4>Grafik 2.4a. Rate HDF per bucket selisih suhu (K)</h4>',
    bars([(lab(r.diff_bucket), r.hdf_rate, HI if i < 2 else BLUE, f"{lab(r.diff_bucket)} K: HDF {I(r.hdf)} dari {I(r.n)} run ({P(r.hdf_rate, 1)}), interval {P(r.hdf_lo, 1)} sampai {P(r.hdf_hi, 1)}") for i, r in enumerate(td.itertuples())],
         lambda v: P(v, 0), "Rate HDF per selisih suhu", rot=0, small=True),
    '<h4>Grafik 2.4b. Rate PWF per bucket power (W)</h4>',
    bars([(lab(r.power_bucket), r.pwf_rate, HI if i in (0, 5) else BLUE, f"{lab(r.power_bucket)}: PWF {I(r.pwf)} dari {I(r.n)} run ({P(r.pwf_rate, 1)})") for i, r in enumerate(pw.itertuples())],
         lambda v: P(v, 0), "Rate PWF per power", rot=20, small=True),
    '<h4>Tabel 2.4c. Sensitivitas definisi \"kecil dan rendah\" (H3)</h4>',
    table(["Definisi", "Selisih suhu ≤ (K)", "rpm ≤", "Run di kelompok", "HDF di kelompok", "Rate HDF kelompok", "Rate di luar", "Recall HDF"],
          [[r.definisi_kecil_rendah, D(r.batas_selisih_suhu_k, 1), I(r.batas_rpm), I(r.n_kelompok), I(r.hdf_kelompok), P(r.rate_kelompok, 1), P(r.rate_lainnya, 0), P(r.recall_hdf, 0)] for r in h3.itertuples()]),
    '<h4>Tabel 2.4d. Sensitivitas definisi \"terlalu rendah atau tinggi\" (H4)</h4>',
    table(["Ekor", "Kelompok", "Batas bawah (W)", "Batas atas (W)", "Run", "PWF", "Rate kelompok", "Rate lainnya", "p Fisher"],
          [[cs(r.ekor), r.kelompok, I(r.batas_bawah_w), I(r.batas_atas_w), I(r.n_kelompok), I(r.pwf_kelompok), P(r.rate_kelompok, 1), P(r.rate_lainnya, 2), PV(r.p_fisher)] for r in h4.itertuples()]), '</div>')

osf_n = {t: int(h5.loc[t].osf) for t in TYPES}
sec25 = mk(
    '<h3 id="sec25">2.5 Torque dan tool wear untuk overstrain <span class="qlist">Q7</span></h3><div class="card">',
    Q(7, f"Overstrain muncul ketika hasil kali tool wear × torque melewati batas yang berbeda per tipe. Ambang terbaik (F1 tertinggi): L {I(h5.loc['L'].ambang_terbaik_minNm)}, M {I(h5.loc['M'].ambang_terbaik_minNm)}, H {I(h5.loc['H'].ambang_terbaik_minNm)} minNm. Torque dan tool wear sama-sama ≥ P75 meningkatkan OSF jelas (p {PV(hy.loc['H5', 'p_value'])}). "
         f"Namun jumlah kejadian OSF kecil di tipe M ({I(osf_n['M'])}) dan H ({I(osf_n['H'])}): interval bootstrap tipe H {I(h5.loc['H'].ambang_boot_p2_5)} sampai {I(h5.loc['H'].ambang_boot_p97_5)} minNm dan {I(h5.loc['H'].boot_tanpa_osf)} dari {I(300)} sampel bootstrap tidak memuat OSF sama sekali. Hipotesis 5 hanya Sebagian: batas L dan H terpisah, tetapi M dan H tidak dapat dibedakan.", warn=True),
    '<h4>Tabel 2.5a. Ambang tool wear × torque terbaik per tipe (bootstrap 95%)</h4>',
    table(["Tipe", "Run", "Kejadian OSF", "Ambang terbaik (minNm)", "F1", "Bootstrap P2,5", "Bootstrap P97,5", "Sampel tanpa OSF"],
          [[t, I(h5.loc[t].n), I(h5.loc[t].osf), I(h5.loc[t].ambang_terbaik_minNm), D(h5.loc[t].f1, 2), I(h5.loc[t].ambang_boot_p2_5), I(h5.loc[t].ambang_boot_p97_5), I(h5.loc[t].boot_tanpa_osf)] for t in TYPES]),
    '<p>Bila beberapa ambang sama baik, dipakai yang terendah. Rincian OSF per tipe, kelompok tool wear, dan kelompok torque ada di <code>osf_by_type.csv</code>.</p></div>')

RN = {"tool wear >= T": "tool wear ≥ T", "torque >= T": "torque ≥ T", "tool wear >= Tw dan torque >= Tq": "tool wear ≥ Tw dan torque ≥ Tq", "tool wear x torque >= P": "tool wear × torque ≥ P",
      "power di luar [Pl, Ph]": "power di luar [Pl, Ph]", "selisih suhu < D dan rpm < R": "selisih suhu &lt; D dan rpm &lt; R", "tool wear x torque >= P (per tipe)": "tool wear × torque ≥ P (ambang per tipe)", "gabungan (OR)": "gabungan (OR)"}
r10 = rsel[np.isclose(rsel.batas_alert_share, 0.1) & (rsel.period == "test")]
sec26 = mk(
    '<h3 id="sec26">2.6 Aturan ambang dan akurasi <span class="qlist">Q8, Q9, Q10</span></h3><div class="card">',
    Q(8, f"Aturan gabungan (OR) dari tiga ambang: tool wear × torque ≥ ambang per tipe (L {I(11000)}, M {I(10500)}, H {I(11000)} minNm), selisih suhu &lt; {D(9.5, 1)} K dan rpm &lt; {I(1380)}, atau torque ≥ {I(55)} Nm. Dipilih di data latih sebagai aturan dengan recall tertinggi yang proporsi peringatannya ≤ {P(ALERT_LIMIT, 0)}. "
         f"Pada data uji: recall {P(u10.recall, 1)}, precision {P(u10.precision, 1)}, proporsi peringatan {P(u10.alert_share, 1)}. Batas {P(ALERT_LIMIT, 0)} adalah asumsi saya (kapasitas inspeksi tidak ada di rancangan); pada batas 5% gabungan terbaik (tool wear × torque per tipe + torque ≥ {I(60)} Nm) memberi recall {P(u05.recall, 1)} dan precision {P(u05.precision, 1)}, pada 20% hasilnya sama dengan 10%. "
         f"Catatan: di data uji aturan tool wear × torque per tipe saja punya F1 lebih tinggi (precision {P(pt10.precision, 1)}, recall {P(pt10.recall, 1)}, peringatan {P(pt10.alert_share, 1)}), tetapi aturan dipilih dari data latih dan tidak dipilih ulang dari data uji. Proporsi peringatan uji {P(u10.alert_share, 1)} sedikit di atas batas {P(ALERT_LIMIT, 0)}.", warn=True),
    Q(9, f"Aturan \"tidak pernah memberi peringatan\" punya akurasi {P(b_test.accuracy, 1)} pada data uji (semua data {P(b_all.accuracy, 1)}) tetapi recall 0%, karena hanya {P(rt.failures_rate['Semua'], 2)} run yang gagal. Aturan terpilih akurasinya lebih rendah ({P(u10.accuracy, 1)}) namun menangkap {P(u10.recall, 1)} kegagalan. "
         f"Pohon keputusan kedalaman 3 memberi akurasi {P(tr3.accuracy, 1)} dengan recall {P(tr3.recall, 1)} dan hanya {P(tr3.alert_share, 1)} peringatan; versi berbobot seimbang recall {P(tr3b.recall, 1)} dengan precision {P(tr3b.precision, 1)} dan {P(tr3b.alert_share, 0)} peringatan. Akurasi tidak bisa membedakan aturan yang berguna dari yang tidak; precision, recall, dan proporsi peringatan harus dilihat bersama."),
    Q(10, f"Cukup stabil tetapi tidak sama. Pada semua data recall tipe L {P(fz('L', 'all').recall, 1)}, M {P(fz('M', 'all').recall, 1)}, H {P(fz('H', 'all').recall, 1)}; precision L {P(fz('L', 'all').precision, 1)}, M {P(fz('M', 'all').precision, 1)}, H {P(fz('H', 'all').precision, 1)}. "
          f"Pada data uji tipe H hanya {I(fz('H', 'test').failures)} run gagal, jadi satu kegagalan mengubah recall {P(1 / fz('H', 'test').failures, 0)}; tipe M dan H tidak dievaluasi terpisah saat memilih aturan.", warn=True),
    '<h4>Grafik 2.6a. Akurasi vs recall pada data uji</h4>',
    gbars(["Tidak pernah beri peringatan", "Aturan terpilih (gabungan)", "Pohon keputusan kedalaman 3"], [("Akurasi", GREY, [b_test.accuracy, u10.accuracy, tr3.accuracy]), ("Recall", BLUE, [b_test.recall, u10.recall, tr3.recall])],
          lambda v: P(v, 0), "Akurasi vs recall pada data uji", rot=0),
    legend([(GREY, "Akurasi"), (BLUE, "Recall")]),
    f'<h4>Tabel 2.6b. Aturan terbaik tiap keluarga pada batas peringatan {P(ALERT_LIMIT, 0)} (dipilih di data latih, nilai data uji)</h4>',
    table(["Aturan", "Ambang", "Precision", "Recall", "Proporsi peringatan", "Akurasi", "F1"],
          [[RN[r.rule_name], cs(r.threshold).replace("minNm", "minNm"), P(r.precision, 1), P(r.recall, 1), P(r.alert_share, 1), P(r.accuracy, 1), D(r.f1, 2)] for r in r10.itertuples()]
          + [["baseline (tidak pernah memberi peringatan)", "-", "-", P(b_test.recall, 0), P(b_test.alert_share, 0), P(b_test.accuracy, 1), D(b_test.f1, 2)]]),
    '<h4>Tabel 2.6c. Aturan terpilih pada tiga batas peringatan (data uji)</h4>',
    table(["Batas peringatan", "Ambang", "Precision", "Recall", "Proporsi peringatan"],
          [[P(lim, 0), cs(x.threshold), P(x.precision, 1), P(x.recall, 1), P(x.alert_share, 1)] for lim, x in ((0.05, u05), (0.1, u10), (0.2, u20))]),
    '<h4>Tabel 2.6d. Aturan terpilih per tipe produk</h4>',
    table(["Tipe", "Periode", "Run", "Gagal", "Precision", "Recall", "Proporsi peringatan"],
          [[r.type, {"test": "uji", "all": "semua data"}[r.period], I(r.n), I(r.failures), P(r.precision, 1), P(r.recall, 1), P(r.alert_share, 1)] for r in frt.itertuples()]),
    '<h4>Tabel 2.6e. Pohon keputusan sebagai pembanding</h4>',
    table(["Model", "Periode", "Precision", "Recall", "Proporsi peringatan", "Akurasi"],
          [[r.model, {"train": "latih", "test": "uji", "all": "semua data"}[r.period], P(r.precision, 1), P(r.recall, 1), P(r.alert_share, 1), P(r.accuracy, 1)] for r in tree.itertuples()]),
    '<p>Pembagian data 70% latih dan 30% uji acak berstrata menurut label gagal (seed tetap), karena <code>UDI</code> bukan urutan waktu. Ambang dipilih hanya dari data latih.</p></div>')

wt = tro[(tro.rule_name == "tool wear >= T")]
sec27 = mk(
    '<h3 id="sec27">2.7 Trade-off dan dampak <span class="qlist">Q11, Q12</span></h3><div class="card">',
    Q(11, f"Aturan terpilih (semua data) menangkap {I(fall.failures_caught)} dari {I(NF)} kegagalan dengan {I(fall.false_alerts)} peringatan palsu: {D(fall.false_alerts_per_caught, 2)} peringatan palsu per kegagalan tertangkap. Sebagai pembanding, tool wear ≥ 200 menit menangkap {I(w200.failures_caught)} dengan {I(w200.false_alerts)} peringatan palsu ({D(w200.false_alerts_per_caught, 2)} per kegagalan), dan ≥ 100 menit menangkap {I(w100.failures_caught)} tetapi {I(w100.false_alerts)} peringatan palsu. "
          "Satu peringatan palsu saya anggap satu alat yang diganti atau diinspeksi terlalu cepat; biaya per alat tidak ada di rancangan dan tidak diasumsikan.", warn=True),
    Q(12, f"Per {I(10000)} run dengan asumsi downtime 4 jam per kegagalan, {P(0.8, 0)} kegagalan berperingatan tercegah, dan {D(INSPECT_H, 1)} jam per inspeksi: downtime terhindari kotor {D(i48.downtime_terhindari_kotor_h, 0)} jam, jam inspeksi {D(i48.jam_inspeksi_h, 0)} jam, bersih {D(i48.downtime_terhindari_bersih_h, 0)} jam (rentang interval Wilson untuk recall: {D(i48lo.downtime_terhindari_bersih_h, 0)} sampai {D(i48hi.downtime_terhindari_bersih_h, 0)} jam). "
          f"Aturan baru hanya menguntungkan jika downtime per kegagalan lebih dari sekitar {D(i48.downtime_impas_h, 2)} jam (titik impas pada porsi tercegah {P(0.8, 0)}); pada downtime 2 jam dengan {P(0.5, 0)} tercegah hasil bersih {D(i22.downtime_terhindari_bersih_h, 0)} jam. Semua angka estimated dan simulated; downtime, porsi tercegah, dan waktu inspeksi adalah asumsi saya.", warn=True),
    '<h4>Grafik 2.7a. Peringatan palsu per kegagalan tertangkap menurut ambang tool wear (semua data)</h4>',
    lines([re.sub(r" menit", "", t) for t in wt.threshold], [("Peringatan palsu per kegagalan tertangkap", BLUE, 2.5, list(wt.false_alerts_per_caught))], lambda v: D(v, 0), "Peringatan palsu per kegagalan", zero=True),
    '<h4>Tabel 2.7b. Trade-off aturan tool wear ≥ T dan torque ≥ T (semua data)</h4>',
    table(["Aturan", "Ambang", "Kegagalan tertangkap", "Kegagalan terlewat", "Peringatan palsu", "Peringatan palsu per kegagalan tertangkap"],
          [[RN[r.rule_name] if r.rule_name in RN else r.rule_name, cs(r.threshold), I(r.failures_caught), I(r.failures_missed), I(r.false_alerts), D(r.false_alerts_per_caught, 2)]
           for r in tro[(tro.rule_name == "tool wear >= T") & tro.threshold.isin([f"{x} menit" for x in (100, 150, 200, 220)]) | (tro.rule_name == "torque >= T") & tro.threshold.isin(["40 Nm", "50 Nm", "60 Nm"]) | (tro.rule_name == "aturan terpilih (gabungan)") & (tro.period == "all")].itertuples()]),
    f'<h4>Tabel 2.7c. Downtime terhindari per {I(10000)} run (estimated; jam)</h4>',
    table(["Downtime per kegagalan (jam)", "Porsi tercegah", "Kotor", "Jam inspeksi", "Bersih", "Impas: downtime minimal (jam)"],
          [[I(r.downtime_per_kegagalan_h), P(r.porsi_tercegah, 0), D(r.downtime_terhindari_kotor_h, 0), D(r.jam_inspeksi_h, 0), D(r.downtime_terhindari_bersih_h, 0), D(r.downtime_impas_h, 2)] for r in imp[imp.skenario == "titik"].itertuples()]),
    f'<p>Skenario memakai matriks konfusi data uji yang diskalakan ke {I(10000)} run. Rumus: downtime terhindari = (failure rate lama − failure rate baru) × jumlah run × jam downtime; jam inspeksi = peringatan × {D(INSPECT_H, 1)} jam.</p></div>')

dm = dcmp.set_index("komponen")
nsm = dcmp.kecocokan.value_counts()
sec28 = mk(
    '<h3 id="sec28">2.8 Kualitas data dan dokumentasi <span class="qlist">Q13, Q14</span></h3><div class="card">',
    Q(13, f"Tidak ada sel kosong, <code>udi</code> atau <code>product_id</code> ganda, maupun baris ganda; semua rentang nilai wajar. Label tidak konsisten ada {I(len(lissue))} baris: {I(dq['machine_failure = 1 tanpa jenis kegagalan'])} run gagal tanpa jenis kegagalan dan {I(dq['jenis kegagalan = 1 tetapi machine_failure = 0'])} run berjenis RNF tanpa label gagal. "
          f"Keputusan: semuanya dipertahankan dan <code>machine_failure</code> tidak diubah; porsi jenis dihitung dari kejadian jenis. {I(dq['run dengan lebih dari satu jenis kegagalan'])} run punya lebih dari satu jenis. Rinciannya ada di Tabel 1.1 dan <code>label_issues.csv</code>."),
    Q(14, f"Dari {I(len(dcmp))} komponen, {I(nsm.get('Sesuai', 0))} sesuai, {I(nsm.get('Sebagian', 0))} sebagian, dan {I(nsm.get('Berbeda', 0))} berbeda. Ambang HDF (selisih suhu &lt; {D(8.6, 1)} K, rpm &lt; {I(1380)}), PWF ({I(3500)} sampai {I(9000)} W), dan OSF tipe L dan M ({I(11000)} dan {I(12000)} minNm) cocok dengan dokumentasi UCI. "
          f"OSF tipe H berbeda karena hanya {I(h5.loc['H'].osf)} kejadian ({I(12000)} di data vs {I(13000)} di dokumentasi). Jumlah kasus juga berbeda: TWF {I(46)} baris di data vs {I(120)} kasus di dokumentasi, RNF {I(19)} baris vs {I(5)} kasus. Dokumentasi dibaca pada 31 Oktober 2026.", warn=True),
    '<h4>Tabel 2.8a. Temuan vs dokumentasi UCI</h4>',
    table(["Komponen", "Dokumentasi UCI", "Hasil dari data", "Kecocokan"],
          [[r.komponen, cs(r.dokumentasi_uci), cs(r.hasil_data), OK(r.kecocokan) if r.kecocokan == "Sesuai" else (PART(r.kecocokan) if r.kecocokan == "Sebagian" else NO(r.kecocokan))] for r in dcmp.itertuples()]),
    '<h4>Tabel 2.8b. Baris dengan label tidak konsisten (cuplikan lima baris pertama)</h4>',
    table(["udi", "Tipe", "Gagal", "Jenis kegagalan", "Masalah"], [[I(r.udi), r.type, I(r.machine_failure), ", ".join(m.upper() for m in ("twf", "hdf", "pwf", "osf", "rnf") if getattr(r, m) == 1), r.masalah] for r in lissue.head(5).itertuples()]),
    f'<p>Dari {I(len(lissue))} baris, {I(len(lissue) - 5)} lainnya ada di <code>label_issues.csv</code>. Q13 juga dijawab di Tabel 1.1.</p></div>')

SEC = {1: "21", 2: "21", 3: "22", 4: "23", 5: "24", 6: "24", 7: "25", 8: "26", 9: "26", 10: "26", 11: "27", 12: "27", 13: "28", 14: "28"}
rp2_body = mk(sec21, sec22, sec23, sec24, sec25, sec26, sec27, sec28)
qn_uniq = sorted(set(int(x) for x in re.findall(r'<span class="qn">Q(\d+)</span>', rp2_body)))
assert qn_uniq == list(range(1, 15)), qn_uniq
nw = len(WARN)
wtxt = ", ".join(f"Q{n}" for n in sorted(WARN))
chips = '<div class="qchips">' + "".join(f'<a class="qc{" w" if n in WARN else ""}" href="#sec{SEC[n]}" title="{esc(QT[n])}">Q{n}</a>' for n in range(1, 15)) + "</div>"
rp2 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> semua {len(QT)} pertanyaan terjawab ({npr["Utama"]} Utama, {npr["Pendukung"]} Pendukung, {npr["Tambahan"]} Tambahan). '
         f'{nw} jawaban dengan catatan (kuning): {wtxt}. Klik nomor pertanyaan untuk melompat ke pembahasannya. Pertanyaan utama project dijawab di bagian 7.</p>',
         chips, '<p class="report-note">Q hijau = terjawab, Q kuning = terjawab dengan catatan. Pembahasan dikelompokkan per grafik atau tabel bukti (2.1 sampai 2.8); Q13 juga muncul di Tabel 1.1.</p></div>', hyp_tbl, rp2_body)

# ---------------------------------------------------------------- 3-5. dataset, tools, alur
CODE_REL = "project/code/"
allcode = list((REPO / CODE_REL).rglob("*.py"))
npy, loc = len(allcode), sum(len(p.read_text(encoding="utf-8").splitlines()) for p in allcode)
nsql = len(list((REPO / CODE_REL).rglob("*.sql")))
hv = hy.verdict.value_counts()
rp3 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> dataset sesuai rancangan (AI4I 2020 dari UCI, {I(N)} baris, {I(dq["kolom"])} kolom, failure rate {P(rt.failures_rate["Semua"], 2)}; lisensi CC BY 4.0). Dari lima hipotesis, {I(hv.get("Terbukti", 0))} terbukti dan {I(hv.get("Sebagian", 0))} sebagian (H5). '
         'Hipotesis diuji persis seperti tertulis di rancangan; penafsiran istilah yang tidak didefinisikan tercatat di <code>definitions.md</code>.</p></div>',
         table(["Aspek", "Rancangan", "Realisasi", "Verdict"], [
             ["Sumber", "UCI, AI4I 2020 Predictive Maintenance, versi UCI 2020, akses 24 Oktober 2026", f"Berkas dari UCI versi {cs(dlog.versi)}, akses {TGL(dlog.tanggal_akses)}; salinan arsip di repositori dataset pemilik ({TGL(dlog.diunggah_ke_datacenter)}), SHA-256 diverifikasi tiap dijalankan (<code>download_log.csv</code>)", OK("Sesuai")],
             ["Ukuran", "Sekitar 10.000 baris, 14 kolom, sekitar 3% gagal (perkiraan)", f"{I(N)} baris, {I(dq['kolom'])} kolom, {I(NF)} gagal ({P(rt.failures_rate['Semua'], 2)})", OK("Sesuai")],
             ["Lisensi dan sitasi", "Dicek di halaman dataset sebelum dipakai", "CC BY 4.0, dicek pemilik repo pada 28 Oktober 2026; sitasi di <code>project/data/README.md</code> dan README", OK("Sesuai")],
             ["Tabel", "raw_ai4i, features, failure_mode_long, rule_eval", f"Keempatnya ada ({I(len(ctest))} uji constraint ditolak, {I(len(cons))} pemeriksaan konsistensi); <code>rule_eval</code> dibuat kosong oleh skema lalu diisi skrip evaluasi aturan", PART("Sesuai + penyesuaian")],
             ] + [[f"Hipotesis {i[1]}: {hy.loc[i, 'hipotesis'].rstrip('.')}", "Belum terbukti", row[3], VP(hy.loc[i, "verdict"])] for i, row in zip(hy.index, hyp_rows)] + [
             ["Catatan data", "Sintetis; label kegagalan bisa tumpang tindih", f"{I(len(lissue))} baris label tidak konsisten dan {I(dq['run dengan lebih dari satu jenis kegagalan'])} run bermodus ganda dipertahankan dan dicatat (Q13)", OK("Sesuai")]]))
rp4 = mk('<div class="card"><p><b>Jawaban singkat:</b> semua tools rancangan dipakai. Excel dihitung ulang oleh LibreOffice, Streamlit dibuat dan diuji lokal tetapi belum di-deploy; statsmodels dan matplotlib ditambahkan.</p></div>',
         table(["Tool", "Rancangan", "Realisasi", "Verdict"], [
             ["Python (pandas)", "Memuat CSV, audit kualitas, fitur turunan", f"{I(npy)} skrip dan modul Python, {I(loc)} baris; seluruh hasil dibuat ulang dari skrip", OK("Sesuai")],
             ["DuckDB + SQL", "Menyimpan 4 tabel, failure rate, TP/FP/FN/TN", f"<code>pdm.duckdb</code> dengan constraint; {I(nsql)} file SQL (skema, fitur, query bernama); hasil dicek silang dengan pandas ({I(len(xs))} pemeriksaan)", OK("Sesuai")],
             ["Streamlit + Plotly", "Dashboard 3 halaman, dipublikasikan lewat link", "<code>streamlit/app.py</code> 3 halaman (Ringkasan Kegagalan, Kondisi Operasi, Simulasi Aturan); diuji dengan <code>AppTest</code>; belum di-deploy", PART("Sebagian")],
             ["Jupyter Notebook", "Mencatat langkah analisis", "<code>analysis.ipynb</code> dibuat otomatis dari CSV hasil dan dieksekusi tanpa error", OK("Sesuai")],
             ["scikit-learn (opsional)", "Pohon keputusan dangkal sebagai pembanding", f"Pohon kedalaman 3 (biasa dan berbobot seimbang), dilatih pada data latih saja (Tabel 2.6e)", OK("Sesuai")],
             ["Excel", "Cek silang failure rate dan tabel TP/FP/FN/TN", f"<code>crosscheck.xlsx</code> berisi rumus, dihitung ulang oleh LibreOffice (bukan Excel); {I(len(xe))} pemeriksaan PASS. Berkas memuat data sehingga tidak di-commit", PART("Sesuai + penyesuaian")],
             ["GitHub", "Kode, query, notebook, README; data tidak di-commit", "Struktur dan README siap; berada di branch <code>project-28-build</code>, belum digabung ke <code>main</code>; data tidak di-commit", PART("Sebagian")],
             ["Markdown", "README dengan sumber, versi, tanggal akses, temuan, batasan", "README dibuat otomatis dari CSV hasil", OK("Sesuai")],
             ["SciPy (opsional)", "Interval kepercayaan dan uji perbedaan antar tipe", "Fisher exact dan chi-kuadrat (SciPy); interval Wilson 95% (statsmodels)", OK("Sesuai")],
             ["matplotlib", "Tidak ada di rancangan", "One-sheet aturan inspeksi (PDF dan PNG)", PART("Tambahan")]]))
steps = [("1", "Mengunduh data dan mencatat sumbernya", "<code>project/data/README.md</code>, <code>01_load_audit.py</code>", PART("Sesuai + tambahan"), "Ditambah log unduhan dengan SHA-256; berkas diambil dari salinan arsip pemilik repo."),
         ("2", "Menetapkan metrik dan kamus data", "<code>project/docs/definitions.md</code>, <code>data_dictionary.md</code>", PART("Sesuai + penyesuaian"), "Penafsiran istilah hipotesis, batas peringatan, dan asumsi dampak adalah asumsi saya."),
         ("3", "Mengaudit kualitas data", "<code>01_load_audit.py</code>, <code>cleaning_decisions.md</code>", OK("Sesuai"), "Q13; 27 baris label tidak konsisten dicatat tanpa mengubah data."),
         ("4", "Memuat data dan membuat fitur turunan", "<code>02_build_db.py</code>, <code>01_schema.sql</code>, <code>02_features.sql</code>", PART("Sesuai + tambahan"), "Ditambah 10 uji penolakan dan 5 pemeriksaan konsistensi."),
         ("5", "Membuat kelompok kondisi", "<code>02_features.sql</code>", OK("Sesuai"), "Bucket tool wear, torque, dan rpm."),
         ("6", "Menghitung failure rate", "<code>03_queries.sql</code>, <code>03_run_queries.py</code>", OK("Sesuai"), "Interval Wilson 95%."),
         ("7", "Menganalisis kondisi operasi", "<code>03_queries.sql</code>, <code>05_stats_tests.py</code>", PART("Sesuai + tambahan"), "Ditambah uji statistik untuk kelima hipotesis."),
         ("8", "Menguji aturan ambang", "<code>06_rule_eval.py</code>", PART("Sesuai + penyesuaian"), "Pembagian latih dan uji acak berstrata (UDI bukan urutan waktu); sensitivitas batas peringatan 5%, 10%, 20%."),
         ("9", "Menghitung trade-off dan dampak", "<code>07_tradeoff_impact.py</code>", OK("Sesuai"), "Skenario berlabel estimated dan simulated."),
         ("10", "Cek silang dan bandingkan dokumentasi", "<code>04_crosscheck.py</code>, <code>08_excel_crosscheck.py</code>, <code>06_rule_eval.py</code>", PART("Sesuai + penyesuaian"), "Excel dihitung ulang oleh LibreOffice."),
         ("11", "Membuat dashboard", "<code>09_build_dashboard_data.py</code>, <code>10_build_onesheet.py</code>, <code>streamlit/app.py</code>", PART("Sebagian"), "Belum di-deploy ke Streamlit Community Cloud."),
         ("12", "Menulis README, rekomendasi, dan finalisasi", "<code>11_build_notebook.py</code>, <code>12_build_readme.py</code>, halaman ini", PART("Sebagian"), "Siap; digabung ke main setelah ditinjau.")]
S = CODE_REL
renames = [("data/README.md", "project/data/README.md"), ("docs/data_dictionary.md", "project/docs/data_dictionary.md"), ("docs/data_quality_log.md", "project/docs/cleaning_decisions.md"),
           ("data/raw/ai4i2020.csv", "project/data/raw/ (tidak di-commit)"), ("scripts/build_db.py", S + "1-data-preparation/python/02_build_db.py"),
           ("pdm.duckdb", "project/pdm.duckdb (tidak di-commit)"), ("sql/", S + "1-data-preparation/sql/01_schema.sql, " + S + "1-data-preparation/sql/02_features.sql, " + S + "2-analysis/sql/03_queries.sql"),
           ("notebooks/analysis.ipynb", "project/results/3-presentation/analysis.ipynb"), ("outputs/rule_eval.csv", "project/results/2-analysis/rule_eval.csv"),
           ("outputs/crosscheck.xlsx", "project/results/2-analysis/crosscheck.xlsx (tidak di-commit)"), ("dashboard/app.py", S + "3-presentation/streamlit/app.py"),
           ("outputs/onesheet.pdf / .png", "project/results/3-presentation/onesheet.pdf, project/results/3-presentation/onesheet.png"), ("requirements.txt", "project/requirements.txt"),
           ("(tidak ada)", ", ".join(S + p for p in ("common.py", "1-data-preparation/python/01_load_audit.py", "2-analysis/python/03_run_queries.py", "2-analysis/python/04_crosscheck.py", "2-analysis/python/05_stats_tests.py",
                                                      "2-analysis/python/06_rule_eval.py", "2-analysis/python/07_tradeoff_impact.py", "2-analysis/python/08_excel_crosscheck.py",
                                                      "3-presentation/python/09_build_dashboard_data.py", "3-presentation/python/10_build_onesheet.py", "3-presentation/python/11_build_notebook.py",
                                                      "3-presentation/python/12_build_readme.py")) + ", project/docs/definitions.md")]
allscripts = {p.name for p in allcode if p.name != "app.py"}
mapped = {Path(x).name for _, b in renames for x in b.split(", ")}
assert allscripts <= mapped, allscripts - mapped
for a, b in renames:
    for part in b.split(", "):
        part = part.split(" (")[0]
        if "tidak di-commit" in b or part.endswith("/"):
            continue
        assert (REPO / part).exists(), part
rp5 = mk('<div class="card"><p><b>Jawaban singkat:</b> 12 langkah dijalankan sesuai urutan. Nama dan lokasi file berubah mengikuti struktur repo standar, beberapa langkah ditambah (uji statistik, cek silang, pembanding pohon keputusan), dan dua langkah (11 dan 12) belum sepenuhnya selesai.</p></div>',
         table(["Langkah", "Rancangan", "Realisasi", "Verdict", "Catatan"], [[a, b, c, d, e] for a, b, c, d, e in steps]),
         '<div class="card"><h4>Penyesuaian dan improvisasi yang tidak ada di rancangan</h4><ul class="tight">',
         '<li>Pembagian latih dan uji acak berstrata 70/30 menggantikan pembagian menurut waktu, karena <code>UDI</code> bukan urutan waktu; ambang dipilih hanya dari data latih.</li>',
         f'<li>Batas peringatan {P(ALERT_LIMIT, 0)} (kapasitas inspeksi) tidak ada di rancangan; sensitivitas 5% dan 20% di Tabel 2.6c.</li>',
         '<li>Istilah \"kecil/rendah\" (H3), \"terlalu rendah/tinggi\" (H4), \"tinggi\" (H5), dan \"naik tajam\" (H1) tidak didefinisikan rancangan; penafsirannya ada di <code>definitions.md</code> dan diuji sensitivitasnya (Tabel 2.4c, 2.4d).</li>',
         f'<li>Asumsi dampak: downtime {", ".join(I(h) for h in DOWNTIME_H)} jam per kegagalan, porsi tercegah {", ".join(P(x, 0) for x in PREVENT)}, {D(INSPECT_H, 1)} jam per inspeksi; semuanya estimated dan simulated.</li>',
         f'<li>Excel dihitung ulang oleh LibreOffice, bukan Excel; berkas <code>crosscheck.xlsx</code> tidak di-commit karena memuat data.</li>',
         f'<li>Ditambah di luar rancangan: pohon keputusan pembanding, interval Wilson, uji kebocoran lewat pemisahan latih/uji, {I(len(xs) + len(xr) + len(xe))} cek silang, dan one-sheet.</li>',
         '<li>Notebook, README, dan angka halaman ini dibuat otomatis dari hasil, dan angka halaman ini diaudit terhadap file hasil.</li></ul></div>',
         '<div class="card"><h4>Perubahan nama dan lokasi file terhadap rancangan</h4>',
         table(["Rancangan", "Realisasi"], [[f"<code>{a}</code>" if a != "(tidak ada)" else "(tidak ada di rancangan)", ", ".join(f"<code>{x}</code>" if "(" not in x else x for x in b.split(", "))] for a, b in renames]) + '</div>')

# ---------------------------------------------------------------- 6. output
chk = lambda rel: (REPO / rel).exists()
outs = [("Dashboard interaktif", "Utama", PART("Sebagian"), "<code>streamlit/app.py</code> (3 halaman) diuji lokal dengan AppTest; link publik belum ada"),
        ("One-sheet aturan inspeksi", "Utama", OK("Tercapai"), "<code>onesheet.pdf</code> dan <code>onesheet.png</code>: kondisi berisiko, aturan, dan trade-off"),
        ("Database & query SQL", "Utama", OK("Tercapai"), f"<code>pdm.duckdb</code> (dibuat ulang, tidak di-commit) dan {I(nsql)} file SQL"),
        ("Notebook analisis", "Utama", OK("Tercapai"), "<code>analysis.ipynb</code> dieksekusi tanpa error, mencakup Q1 sampai Q14"),
        ("Tabel evaluasi aturan", "Utama", OK("Tercapai"), f"<code>rule_eval.csv</code> ({I(len(ev))} baris) dan <code>final_rule_by_type.csv</code> (per tipe produk)"),
        ("Laporan temuan & rekomendasi", "Utama", OK("Tercapai"), "<code>README.md</code> dan halaman ini"),
        ("Repositori GitHub", "Utama", PART("Sebagian"), "Struktur dan cara menjalankan ulang siap; berada di branch <code>project-28-build</code>, belum digabung ke <code>main</code>"),
        ("Slide presentasi", "Opsional", NO("Tidak dibuat"), "Opsional, tidak dibuat")]
nU = [o for o in outs if o[1] == "Utama"]
cnt = lambda s: sum(1 for o in nU if s in o[2])
docs = [("data/README.md", "Sumber data, versi, tanggal akses, lisensi, cara mengunduh", "project/data/README.md"), ("docs/data_dictionary.md", "Kamus data dan definisi metrik", "project/docs/data_dictionary.md"),
        ("data/raw/ai4i2020.csv", "Data asli (tidak di-commit)", "project/data/raw"), ("docs/data_quality_log.md", "Audit kualitas data dan keputusannya", "project/docs/cleaning_decisions.md"),
        ("scripts/build_db.py", "Pemuat data dan pembuat fitur", "project/code/1-data-preparation/python/02_build_db.py"), ("pdm.duckdb", "File database (tidak di-commit)", "project/pdm.duckdb"),
        ("sql/", "Query failure rate, bucket, evaluasi aturan", "project/code/2-analysis/sql/03_queries.sql"), ("notebooks/analysis.ipynb", "Analisis Q1 sampai Q14", "project/results/3-presentation/analysis.ipynb"),
        ("outputs/rule_eval.csv", "Hasil uji semua aturan dan ambang", "project/results/2-analysis/rule_eval.csv"), ("outputs/crosscheck.xlsx", "Cek silang SQL vs Excel (tidak di-commit)", "project/results/2-analysis/crosscheck.xlsx"),
        ("dashboard/app.py", "Dashboard Streamlit", "project/code/3-presentation/streamlit/app.py"), ("requirements.txt", "Paket Python", "project/requirements.txt"),
        ("outputs/onesheet.pdf / .png", "One-sheet aturan inspeksi", "project/results/3-presentation/onesheet.pdf"), ("README.md", "Laporan temuan", "README.md"),
        ("index.html", "Pengalihan ke design-and-report/ (halaman rancangan dan laporan)", "index.html"), ("slides/presentation.pdf", "Slide presentasi (Opsional)", "slides/presentation.pdf")]
stat_doc = lambda rel: PART("Tidak di-commit") if ("duckdb" in rel or "raw" in rel or "xlsx" in rel) else (OK("Ada") if chk(rel) else NO("Belum ada"))
rp6 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> {I(cnt("Tercapai"))} dari {I(len(nU))} output Utama tercapai penuh dan {I(cnt("Sebagian"))} sebagian (dashboard belum punya link publik, repositori belum digabung ke main). Slide Opsional tidak dibuat.</p></div>',
         table(["Output", "Label", "Status", "Bukti"], [[f"<b>{a}</b>", b, c, d] for a, b, c, d in outs]),
         '<div class="card"><h4>Daftar dokumen pada rancangan vs repositori</h4>',
         table(["Dokumen (rancangan)", "Isi", "Lokasi sekarang", "Status"], [[f"<code>{a}</code>", b, f"<code>{c}</code>", stat_doc(c) if a != "slides/presentation.pdf" else NO("Belum ada")] for a, b, c in docs]),
         '<p>Data mentah, <code>pdm.duckdb</code>, dan <code>crosscheck.xlsx</code> tidak di-commit karena bisa dibuat ulang oleh skrip (atau memuat data).</p></div>')

# ---------------------------------------------------------------- 7. kesimpulan
crit = [("1. Kesembilan pertanyaan Utama terjawab dengan angka dari data", OK("Tercapai"), f"Q1, Q2, Q3, Q4, Q8, Q9, Q11, Q12, Q13 terjawab (bagian 2); {I(len([n for n in WARN if PRIO[n] == 'Utama']))} di antaranya dengan catatan"),
        ("2. Failure rate dan TP/FP/FN/TN dari SQL sama dengan hitungan ulang di Excel", OK("Tercapai"), f"{I(len(xe))} pemeriksaan PASS (Excel dihitung ulang oleh LibreOffice)"),
        ("3. Setiap aturan dinilai dengan precision, recall, proporsi peringatan, dan dibandingkan dengan baseline", OK("Tercapai"), f"{I(len(ev))} baris di <code>rule_eval.csv</code> (baseline akurasi {P(b_all.accuracy, 1)}, recall 0%)"),
        ("4. Kelima hipotesis diberi status jelas", OK("Tercapai"), f"{I(hv.get('Terbukti', 0))} Terbukti dan {I(hv.get('Sebagian', 0))} Sebagian (Tabel di bagian 2 dan 3)"),
        ("5. Sumber data, versi, tanggal akses, dan lisensi tercatat di README dan halaman ini", OK("Tercapai"), "README, <code>project/data/README.md</code>, dan bagian 3"),
        ("6. Orang awam membuka dashboard dan menyebut kondisi paling berisiko dalam &lt; 1 menit, dan checklist standar terpenuhi", PART("Belum diuji"), "Dashboard dibuat tetapi belum di-deploy dan belum diuji ke pembaca sebenarnya")]
ncr = sum(1 for c in crit if ">Tercapai<" in c[1])
fr_gain = i48.downtime_terhindari_bersih_h
rp7 = mk(
    '<div class="card"><h4>7.1 Hasil analisis: jawaban atas pertanyaan utama</h4>',
    '<p><i>Kondisi operasi dan jenis kegagalan apa yang paling sering menyebabkan mesin rusak, dan pada ambang berapa risikonya naik?</i></p><ul class="tight">',
    f'<li><b>Jenis kegagalan:</b> HDF ({I(fm.loc["HDF"]['flags'])}), OSF ({I(fm.loc["OSF"]['flags'])}), dan PWF ({I(fm.loc["PWF"]['flags'])}) menyumbang {P(fm.loc["PWF"].cum_share, 0)} kejadian; failure rate {P(rt.failures_rate["Semua"], 2)}, tertinggi pada tipe L ({P(rt.failures_rate["L"], 2)}).</li>',
    f'<li><b>Ambang risiko:</b> tool wear ≥ {I(200)} menit ({P(h1.loc[200].rate_ge, 1)} vs {P(h1.loc[200].rate_lt, 1)}); selisih suhu &lt; {D(8.6, 1)} K dengan rpm &lt; {I(1380)} untuk HDF; power di luar {I(3500)} sampai {I(9000)} W untuk PWF; tool wear × torque di atas ambang per tipe untuk OSF (L {I(11000)} minNm).</li>',
    f'<li><b>Aturan inspeksi:</b> gabungan tiga ambang menangkap {P(u10.recall, 1)} kegagalan pada data uji dengan precision {P(u10.precision, 1)} dan {P(u10.alert_share, 1)} run diberi peringatan. Akurasinya ({P(u10.accuracy, 1)}) lebih rendah daripada tidak berbuat apa-apa ({P(b_test.accuracy, 1)}), tetapi baseline tidak menangkap satu pun kegagalan.</li>',
    f'<li><b>Dampak (estimated, simulated):</b> sekitar {D(i48.downtime_terhindari_bersih_h, 0)} jam downtime bersih terhindari per {I(10000)} run pada asumsi 4 jam per kegagalan.</li></ul></div>',
    '<div class="card"><h4>7.2 Impact</h4><ul class="tight">',
    f'<li><b>Nilai praktis (estimated):</b> aturan yang bisa dijalankan tanpa model rumit mengubah jadwal ganti alat dari tebakan menjadi ambang terukur; jumlah peringatan palsu ({I(fall.false_alerts)} per {I(10000)} run) harus dibandingkan dengan biaya inspeksi sebenarnya.</li>',
    '<li><b>Nilai analitis:</b> aturan dinilai dengan precision, recall, dan proporsi peringatan pada data uji, bukan akurasi, dan dibandingkan dengan baseline serta pohon keputusan.</li>',
    '<li><b>Nilai portofolio:</b> pipeline lengkap dari data publik berversi: constraint database, query SQL, uji hipotesis, pemisahan latih dan uji, cek silang SQL/pandas/Excel, notebook, dan dashboard.</li>',
    '<li><b>Belum terukur:</b> biaya nyata downtime dan inspeksi, kinerja pada mesin nyata (data sintetis), dan penerimaan tim perawatan atas batas peringatan.</li></ul></div>')
rp7 += ('<div class="card"><h4>7.3 Success criteria</h4>' + table(["Kriteria (Design Project, bagian 8)", "Status", "Bukti"], [[a, b, c] for a, b, c in crit])
        + f'<p><b>Hasil:</b> {I(ncr)} dari {I(len(crit))} kriteria tercapai, {I(len(crit) - ncr)} belum diuji.</p></div>')
rp7 += mk('<div class="card"><h4>7.4 Rekomendasi</h4><ul class="tight">',
          f'<li>Jadikan inspeksi untuk tool wear ≥ {I(200)} menit sebagai aturan awal yang paling sederhana, dan tambahkan ambang tool wear × torque per tipe untuk overstrain.</li>',
          f'<li>Pakai aturan gabungan hanya jika kapasitas inspeksi sekitar {P(ALERT_LIMIT, 0)} run per periode; jika kapasitasnya {P(0.05, 0)}, pakai versi {P(u05.recall, 0)} recall dengan precision {P(u05.precision, 0)} (Tabel 2.6c).</li>',
          f'<li>Hitung biaya nyata downtime dan inspeksi dulu: pada downtime di bawah sekitar {D(i48.downtime_impas_h, 1)} jam per kegagalan aturan ini merugi (Tabel 2.7c).</li>',
          '<li>Laporkan precision, recall, dan proporsi peringatan, bukan akurasi.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.5 Saran perbaikan</h4><ul class="tight">',
          '<li>Uji ulang aturan pada data mesin nyata; data sintetis tidak membuktikan perilaku lapangan.</li>',
          '<li>Sepakati batas peringatan, biaya downtime, dan waktu inspeksi dengan tim perawatan agar analisis dampak memakai angka nyata.</li>',
          '<li>Deploy dashboard ke Streamlit Community Cloud dan uji ke satu pembaca awam untuk mengisi kriteria 6.</li>',
          '<li>Evaluasi aturan per tipe produk secara terpisah bila kejadian tipe M dan H lebih banyak.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.6 Batasan</h4><ul class="tight">',
          '<li>Data pada project ini adalah simulasi (sintetis dari penyusun dataset); pola lebih rapi daripada kondisi nyata dan semua angka dampak berlabel estimated dan simulated.</li>',
          f'<li>Penafsiran istilah hipotesis (kuartil terbawah, ekor {P(0.025, 1)}, P75, rasio minimal 3x), batas peringatan {P(ALERT_LIMIT, 0)}, dan asumsi dampak (downtime {", ".join(I(h) for h in DOWNTIME_H)} jam, porsi tercegah {", ".join(P(x, 0) for x in PREVENT)}, {D(INSPECT_H, 1)} jam per inspeksi) adalah asumsi saya, diuji sensitivitasnya.</li>',
          f'<li>Kejadian sedikit: OSF tipe H {I(osf_n["H"])} dan tipe M {I(osf_n["M"])}, run gagal tipe H di data uji {I(fz("H", "test").failures)}, dan bucket tool wear 250+ hanya {I(wb.n.iloc[-1])} run; hipotesis 5 hanya Sebagian.</li>',
          f'<li>Proporsi peringatan data uji {P(u10.alert_share, 1)} sedikit di atas batas {P(ALERT_LIMIT, 0)}; aturan tool wear × torque per tipe memberi F1 uji lebih tinggi tetapi tidak dipilih ulang dari data uji.</li>',
          f'<li>{I(dq["jenis kegagalan = 1 tetapi machine_failure = 0"])} baris RNF tanpa label gagal dan jumlah TWF ({I(46)} vs {I(120)}) serta RNF ({I(19)} vs {I(5)}) berbeda dari dokumentasi UCI; data tidak diubah.</li>',
          '<li>Pola dalam data belum tentu penyebab; ambang perlu diuji di lapangan. Uji statistik antar aturan tidak dikoreksi untuk banyak perbandingan.</li>',
          '<li>Excel dihitung ulang oleh LibreOffice, dan <code>crosscheck.xlsx</code> tidak di-commit. Dashboard belum di-deploy, kriteria 6 belum diuji ke pembaca awam, dan slide presentasi (Opsional) tidak dibuat.</li>',
          '<li>Lisensi CC BY 4.0 sudah dicek pemilik repo (28 Oktober 2026); atribusi dicantumkan di README.</li></ul></div>')

evq = [("1", "rp1", "Data yang didapat", OK("Didapat"), f"{I(N)} run mesin, {I(NF)} gagal, {I(tabrows['failure_mode_long'])} kejadian jenis kegagalan, {I(len(ev))} baris evaluasi aturan"),
       ("2", "rp2", "Business question terjawab?", OK(f"{len(QT)} dari {len(QT)}"), f"Semua terjawab ({npr['Utama']} Utama, {npr['Pendukung']} Pendukung, {npr['Tambahan']} Tambahan); {nw} dengan catatan ({wtxt})"),
       ("3", "rp3", "Dataset sesuai?", PART("Sesuai + temuan"), f"Dataset sesuai; {I(hv.get('Terbukti', 0))} hipotesis terbukti, {I(hv.get('Sebagian', 0))} sebagian"),
       ("4", "rp4", "Tools sesuai?", PART("Sesuai + tambahan"), "Semua tools dipakai; Excel dihitung LibreOffice, Streamlit belum di-deploy"),
       ("5", "rp5", "Alur sesuai?", PART("Sesuai + penyesuaian"), f"{len(steps)} langkah dijalankan; pembagian latih/uji dan uji statistik ditambahkan"),
       ("6", "rp6", "Output tercapai?", PART(f"{cnt('Tercapai')} penuh, {cnt('Sebagian')} sebagian"), f"{cnt('Tercapai')} dari {len(nU)} output Utama penuh"),
       ("7", "rp7", "Kesimpulan", OK("Tersedia"), f"Hasil analisis, Impact, {len(crit)} kriteria sukses ({ncr} tercapai), rekomendasi, saran perbaikan, batasan")]
evq_html = '<div class="scroll"><table class="evq"><tr><th>No</th><th>Pertanyaan evaluasi</th><th>Verdict</th><th>Ringkasan</th></tr>' + "".join(
    f'<tr><td><span class="en">{n}</span></td><td><a href="#{h}">{t}</a></td><td>{v}</td><td>{s}</td></tr>' for n, h, t, v, s in evq) + "</table></div>"
H = lambda i, t, sm, body: f'\n<h2 id="rp{i}">{i}. {t}<small>{sm}</small></h2>\n{body}\n'
report = mk(
    '<div class="pane" id="report" data-tab="report" hidden>\n',
    '<div class="callout g"><h4>Report Project versi 2: evaluasi hasil terhadap Design Project</h4><p>Halaman ini disusun sebagai 7 jawaban atas pertanyaan evaluasi. Tabel dan grafik dibuat otomatis dari hasil query SQL (DuckDB) dan evaluasi aturan pada data AI4I 2020. '
    f'Hasil SQL dicek silang dengan pandas, Python, dan Excel ({I(len(xs) + len(xr) + len(xe))} pemeriksaan). Angka pada teks diaudit terhadap file di <code>project/results/</code>: @@AUDIT@@ angka diperiksa tanpa selisih. '
    '<b>Data pada project ini adalah simulasi</b> (sintetis), jadi kesimpulan menggambarkan data, bukan lini produksi nyata. Rancangan lengkap ada di tab <a href="#design">Design Project</a>.</p></div>\n',
    evq_html,
    H(1, "Data yang berhasil didapatkan", "Isi data mentah, tabel di database, dan data hasil analisis", rp1),
    H(2, "Apakah business question terjawab?", f"{len(QT)} pertanyaan pada Design Project, dijawab dengan data", rp2),
    H(3, "Apakah dataset sesuai dengan Design Project?", "Perbandingan rancangan dengan realisasi", rp3),
    H(4, "Apakah tools yang digunakan sesuai?", "Perbandingan rancangan dengan eksekusi", rp4),
    H(5, "Apakah alur pengerjaan sesuai dengan Design Project?", f"{len(steps)} langkah rancangan vs yang dijalankan", rp5),
    H(6, "Apakah project output tercapai?", "Output pada Design Project, bagian 7", rp6),
    H(7, "Kesimpulan", "Hasil analisis, Impact, success criteria, rekomendasi, saran perbaikan, dan batasan", rp7),
    '</div>\n')

# ---------------------------------------------------------------- audit angka
STATIC = {str(i) for i in range(0, 21)} | {f"{i:02d}" for i in range(0, 13)} | {"24", "25", "28", "31", "30", "50", "100", "2026", "2020", "2,5", "0,001", "75", "80", "95", "70", "14", "27", "12", "22"}
STATIC |= {f"{a}.{b}" for a in range(1, 10) for b in range(0, 10)}
n_tok, bad = audit(report, STATIC)
manual = [("seluruh CSV hasil terdokumentasi", not miss), ("cross-check SQL/pandas, aturan, Excel semua PASS", (xs.status == "PASS").all() and (xr.status == "PASS").all() and (xe.status == "PASS").all()),
          ("semua uji constraint ditolak", (ctest.outcome == "ditolak").all()), ("semua pemeriksaan konsistensi 0 pelanggaran", (cons.violations == 0).all()),
          ("jumlah pertanyaan = 14 (9 Utama, 4 Pendukung, 1 Tambahan)", len(QT) == 14 and npr == {"Utama": 9, "Pendukung": 4, "Tambahan": 1}),
          ("catatan hanya Q3-Q8, Q10-Q12, Q14", WARN == {3, 4, 5, 6, 7, 8, 10, 11, 12, 14}), ("langkah rancangan = 12", len(steps) == 12), ("jumlah pertanyaan unik pada bagian 2 = 14", qn_uniq == list(range(1, 15))),
          ("aturan terpilih: TP+FP+FN+TN = jumlah run", fr.tp_all + fr.fp_all + fr.fn_all + fr.tn_all == N), ("TP+FN semua data = jumlah kegagalan", fr.tp_all + fr.fn_all == NF),
          ("latih + uji = semua data", fr.tp_train + fr.tp_test == fr.tp_all and fr.fp_train + fr.fp_test == fr.fp_all),
          ("jumlah run per tipe = total", rt.n["L"] + rt.n["M"] + rt.n["H"] == N), ("kegagalan per tipe = total", rt.failures["L"] + rt.failures["M"] + rt.failures["H"] == NF),
          ("kumulatif jenis kegagalan berakhir 100%", np.isclose(fm.cum_share.iloc[-1], 1.0)), ("downtime bersih = kotor - inspeksi", np.isclose(i48.downtime_terhindari_bersih_h, i48.downtime_terhindari_kotor_h - i48.jam_inspeksi_h)),
          ("baseline recall 0 dan akurasi = 1 - failure rate", b_all.recall == 0 and np.isclose(b_all.accuracy, 1 - NF / N)), ("keempat tabel database ada", set(tabrows.index) == {"raw_ai4i", "features", "failure_mode_long", "rule_eval"}),
          ("bucket tool wear menutup semua run", wb.n.sum() == N)]
assert all(v for _, v in manual), [k for k, v in manual if not v]
if bad:
    print("TOKEN TIDAK TERDAFTAR:", bad)
    sys.exit(1)
report = report.replace("@@AUDIT@@", I(n_tok) + f" (ditambah {I(len(manual))} klaim manual)")

# ---------------------------------------------------------------- rakit halaman
v1 = (HERE / "page_v1.html").read_text(encoding="utf-8")
a = v1.index('<div class="pane" id="report"')
b = v1.index("</main>")
design_pane = v1[v1.index('<div class="pane" id="design"'):a]
nav_old = re.search(r'<nav aria-label="Project navigation">.*?</nav>', v1, re.S).group(0)
btn = lambda t: re.search(rf'<button type="button" class="tab[^"]*" data-t="{t}".*?</button>', nav_old, re.S).group(0)
design_links = re.search(r'<div class="links" data-tab="design">.*?</div>', nav_old, re.S).group(0)
report_links = ('<div class="links" data-tab="report" hidden>' + "".join(f'<a href="#rp{i}">{t}</a>' for i, t in
               enumerate(["Data", "Business Questions", "Dataset", "Tools", "Alur Kerja", "Project Output", "Kesimpulan"], 1)) + "</div>")
nav_new = f'<nav aria-label="Project navigation">{btn("design")}{btn("report")}{design_links}{report_links}</nav>'
css = (HERE / "report.css").read_text(encoding="utf-8")
html = v1[:a] + report + v1[b:]
html = html.replace(nav_old, nav_new)
i = html.rindex("</style>")
html = html[:i] + css + html[i:]
out = REPO / "design-and-report" / "index.html"
out.write_text(html, encoding="utf-8")
assert design_pane == html[html.index('<div class="pane" id="design"'):html.index('<div class="pane" id="report"')], "pane Design berubah"
print(f"index.html {len(html) / 1024:.0f} KB; {n_tok} angka diaudit; {len(manual)} klaim manual; pane Design identik")
