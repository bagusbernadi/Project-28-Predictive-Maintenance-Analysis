"""Langkah 7 (bagian hipotesis): uji lima hipotesis Design persis seperti ditulis; definisi 'kecil', 'rendah', 'tinggi' ada di docs/definitions.md."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "1-data-preparation" / "python"))
from importlib import import_module  # noqa: E402

from common import H1_RATIO, N_BOOT, QUANTILE_TAIL, RES_ANALYSIS, SEED  # noqa: E402

df, _, _ = import_module("01_load_audit").load_raw()
df["dt"] = df.process_temp_k - df.air_temp_k
df["power"] = df.torque_nm * df.rpm * 2 * np.pi / 60
df["wxt"] = df.tool_wear_min * df.torque_nm
y = df.machine_failure.values


def fx(a, b, c, d):
    """Fisher exact dua sisi untuk tabel [[a, b], [c, d]]."""
    return fisher_exact([[a, b], [c, d]])[1]


def two(mask, target):
    """Tabel kelompok (mask) vs sisanya untuk label target: (k1, n1, k0, n0)."""
    t = target.values if hasattr(target, "values") else target
    return int(t[mask].sum()), int(mask.sum()), int(t[~mask].sum()), int((~mask).sum())


H = []
# ---- H1: failure rate naik tajam setelah tool wear sekitar 200 menit
scan = []
for T in range(100, 245, 5):
    k1, n1, k0, n0 = two((df.tool_wear_min >= T).values, df.machine_failure)
    p1, p0, p = k1 / n1, k0 / n0, (k1 + k0) / (n1 + n0)
    ll = k1 * np.log(p1 / p) + (n1 - k1) * np.log((1 - p1) / (1 - p)) + k0 * np.log(p0 / p) + (n0 - k0) * np.log((1 - p0) / (1 - p)) if 0 < p1 < 1 and 0 < p0 < 1 else np.nan
    scan.append((T, n1, k1, p1, n0, k0, p0, p1 / p0 if p0 else np.nan, fx(k1, n1 - k1, k0, n0 - k0), ll))
sc = pd.DataFrame(scan, columns=["ambang_menit", "n_ge", "gagal_ge", "rate_ge", "n_lt", "gagal_lt", "rate_lt", "rasio", "p_fisher", "log_likelihood"])
sc[[c for c in sc.columns if c != "p_fisher"]] = sc[[c for c in sc.columns if c != "p_fisher"]].round(8)
sc.to_csv(RES_ANALYSIS / "h1_wear_scan.csv", index=False)
r200 = sc[sc.ambang_menit == 200].iloc[0]
tstar = int(sc.loc[sc.log_likelihood.idxmax(), "ambang_menit"])
v1 = "Terbukti" if (r200.rasio >= H1_RATIO and r200.p_fisher < 1e-3 and abs(tstar - 200) <= 25) else ("Sebagian" if r200.rasio >= H1_RATIO else "Tidak terbukti")
H.append(("H1", "Failure rate naik tajam setelah tool wear melewati sekitar 200 menit.", "Fisher exact: tool wear >= 200 vs < 200; pemindaian ambang 100-240 (rasio dan likelihood)",
          round(r200.rasio, 4), float(r200.p_fisher), v1, f"rate {r200.rate_ge:.4f} vs {r200.rate_lt:.4f}; ambang terbaik menurut likelihood = {tstar} menit"))
# ---- H2: tipe L lebih sering gagal dibanding M dan H
tab = pd.crosstab(df.type, df.machine_failure).reindex(["L", "M", "H"])
chi_p = chi2_contingency(tab.values)[1]
pair = []
for a, b in (("L", "M"), ("L", "H"), ("M", "H")):
    ka, na, kb, nb = int(tab.loc[a, 1]), int(tab.loc[a].sum()), int(tab.loc[b, 1]), int(tab.loc[b].sum())
    p = fx(ka, na - ka, kb, nb - kb)
    pair.append((f"{a} vs {b}", ka / na, kb / nb, (ka / na) / (kb / nb), p, min(1.0, p * 3)))
pr = pd.DataFrame(pair, columns=["pasangan", "rate_pertama", "rate_kedua", "rasio", "p_fisher", "p_bonferroni"])
pr[["rate_pertama", "rate_kedua", "rasio"]] = pr[["rate_pertama", "rate_kedua", "rasio"]].round(8)
pr.loc[len(pr)] = ["chi-kuadrat 3 tipe", np.nan, np.nan, np.nan, chi_p, chi_p]
pr.to_csv(RES_ANALYSIS / "h2_type_tests.csv", index=False)
lm, lh = pr.iloc[0], pr.iloc[1]
n_sig = int(lm.p_bonferroni < 0.05) + int(lh.p_bonferroni < 0.05)
H.append(("H2", "Tipe produk L lebih sering gagal dibanding tipe M dan H.", "Fisher exact L vs M dan L vs H, koreksi Bonferroni (3 perbandingan); chi-kuadrat 3 tipe",
          round(lm.rasio, 4), lm.p_bonferroni, "Terbukti" if n_sig == 2 else ("Sebagian" if n_sig == 1 else "Tidak terbukti"), f"L vs M p Bonferroni {lm.p_bonferroni:.4g}; L vs H {lh.p_bonferroni:.4g}"))
# cek perancu: L vs M+H di dalam kelompok tool wear
st = []
for g, m in (("tool wear < 200", df.tool_wear_min < 200), ("tool wear >= 200", df.tool_wear_min >= 200)):
    sub = df[m]
    isl = (sub.type == "L").values
    k1, n1, k0, n0 = two(isl, sub.machine_failure)
    st.append((g, n1, k1, k1 / n1, n0, k0, k0 / n0, fx(k1, n1 - k1, k0, n0 - k0)))
pd.DataFrame(st, columns=["kelompok", "n_L", "gagal_L", "rate_L", "n_MH", "gagal_MH", "rate_MH", "p_fisher"]).round(8).to_csv(RES_ANALYSIS / "h2_stratified.csv", index=False)
# ---- H3: selisih suhu kecil + putaran rendah -> HDF
q = lambda s, p: float(np.quantile(s, p))
rows3 = []
for lab, pq in (("kuartil terbawah (25%)", .25), ("sepertiga terbawah (33%)", 1 / 3), ("separuh terbawah (50%)", .5)):
    dq, rq = q(df.dt, pq), q(df.rpm, pq)
    m = ((df.dt <= dq) & (df.rpm <= rq)).values
    k1, n1, k0, n0 = two(m, df.hdf)
    rows3.append((lab, round(dq, 4), round(rq, 2), n1, k1, k1 / n1, k0 / n0, (k1 / n1) / (k0 / n0) if k0 else np.nan, k1 / df.hdf.sum(), fx(k1, n1 - k1, k0, n0 - k0)))
h3 = pd.DataFrame(rows3, columns=["definisi_kecil_rendah", "batas_selisih_suhu_k", "batas_rpm", "n_kelompok", "hdf_kelompok", "rate_kelompok", "rate_lainnya", "rasio", "recall_hdf", "p_fisher"])
h3[["rate_kelompok", "rate_lainnya", "rasio", "recall_hdf"]] = h3[["rate_kelompok", "rate_lainnya", "rasio", "recall_hdf"]].round(8)
h3.to_csv(RES_ANALYSIS / "h3_heat_tests.csv", index=False)
b3 = h3.iloc[0]
r3ok = (b3.rate_lainnya == 0 and b3.rate_kelompok > 0) or b3.rasio >= H1_RATIO      # rasio tak terhingga bila pembanding tidak punya HDF
H.append(("H3", "Selisih suhu proses dan udara yang kecil, ditambah putaran rendah, terkait dengan kegagalan panas.", "Fisher exact: kelompok (selisih suhu dan rpm di kuartil terbawah) vs sisanya, label HDF; sensitivitas 33% dan 50%",
          (round(b3.rasio, 4) if pd.notna(b3.rasio) else np.nan), b3.p_fisher, "Terbukti" if (r3ok and b3.p_fisher < 1e-3 and b3.recall_hdf >= .5) else ("Sebagian" if r3ok and b3.p_fisher < 1e-3 else "Tidak terbukti"),
          f"rate HDF {b3.rate_kelompok:.4f} vs {b3.rate_lainnya:.5f}; menangkap {b3.recall_hdf:.0%} HDF"))
# ---- H4: power terlalu rendah atau terlalu tinggi -> PWF
rows4 = []
for tail in (0.01, QUANTILE_TAIL, 0.05):
    lo, hi = q(df.power, tail), q(df.power, 1 - tail)
    for nm, m in (("rendah (ekor bawah)", (df.power <= lo).values), ("tinggi (ekor atas)", (df.power >= hi).values), ("keduanya", ((df.power <= lo) | (df.power >= hi)).values)):
        k1, n1, k0, n0 = two(m, df.pwf)
        rows4.append((f"{tail:.1%}", nm, round(lo, 1), round(hi, 1), n1, k1, k1 / n1, k0 / n0, fx(k1, n1 - k1, k0, n0 - k0)))
h4 = pd.DataFrame(rows4, columns=["ekor", "kelompok", "batas_bawah_w", "batas_atas_w", "n_kelompok", "pwf_kelompok", "rate_kelompok", "rate_lainnya", "p_fisher"])
h4[["rate_kelompok", "rate_lainnya"]] = h4[["rate_kelompok", "rate_lainnya"]].round(8)
h4.to_csv(RES_ANALYSIS / "h4_power_tests.csv", index=False)
m4 = h4[h4.ekor == f"{QUANTILE_TAIL:.1%}"].set_index("kelompok")
ok4 = (m4.loc["rendah (ekor bawah)", "p_fisher"] < 1e-3) and (m4.loc["tinggi (ekor atas)", "p_fisher"] < 1e-3) and (m4.loc["keduanya", "rate_kelompok"] > m4.loc["keduanya", "rate_lainnya"])
H.append(("H4", "Power yang terlalu rendah atau terlalu tinggi terkait dengan kegagalan daya.", "Fisher exact: ekor 2,5% bawah, ekor 2,5% atas, dan keduanya vs bagian tengah, label PWF; sensitivitas 1% dan 5%",
          round(m4.loc["keduanya", "rate_kelompok"], 4), m4.loc["keduanya", "p_fisher"], "Terbukti" if ok4 else "Tidak terbukti",
          f"rate PWF di kedua ekor {m4.loc['keduanya', 'rate_kelompok']:.4f} vs {m4.loc['keduanya', 'rate_lainnya']:.5f} di tengah"))
# ---- H5: torque tinggi + tool wear tinggi -> OSF, batas berbeda per tipe
tq75, tw75 = q(df.torque_nm, .75), q(df.tool_wear_min, .75)
m5 = ((df.torque_nm >= tq75) & (df.tool_wear_min >= tw75)).values
k1, n1, k0, n0 = two(m5, df.osf)
p5 = fx(k1, n1 - k1, k0, n0 - k0)
grid = np.arange(6000, 20001, 250)
rng = np.random.default_rng(SEED)


def best_thr(x, o):
    tp = (x[:, None] >= grid[None, :]) & (o[:, None] == 1)
    al = (x[:, None] >= grid[None, :])
    tpn, aln = tp.sum(0), al.sum(0)
    f1 = 2 * tpn / (aln + o.sum()) if o.sum() else np.zeros(len(grid))
    j = int(np.argmax(f1))
    return grid[j], f1[j]


rows5 = []
for t in ("L", "M", "H"):
    s = df[df.type == t]
    x, o = s.wxt.values, s.osf.values
    thr, f1 = best_thr(x, o)
    bs = []
    for _ in range(N_BOOT):
        ix = rng.integers(0, len(s), len(s))
        bs.append(best_thr(x[ix], o[ix])[0] if o[ix].sum() else np.nan)
    bs = np.array(bs, dtype=float)
    rows5.append((t, len(s), int(o.sum()), int(thr), round(f1, 4), float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5)), int(np.isnan(bs).sum())))
h5 = pd.DataFrame(rows5, columns=["type", "n", "osf", "ambang_terbaik_minNm", "f1", "ambang_boot_p2_5", "ambang_boot_p97_5", "boot_tanpa_osf"])
h5.to_csv(RES_ANALYSIS / "h5_type_thresholds.csv", index=False)
thr = h5.set_index("type")
ordered = thr.loc["L", "ambang_terbaik_minNm"] < thr.loc["M", "ambang_terbaik_minNm"] < thr.loc["H", "ambang_terbaik_minNm"]
sep_lh = thr.loc["L", "ambang_boot_p97_5"] < thr.loc["H", "ambang_boot_p2_5"]
v5 = "Terbukti" if (p5 < 1e-3 and ordered and sep_lh) else ("Sebagian" if p5 < 1e-3 else "Tidak terbukti")
H.append(("H5", "Kombinasi torque tinggi dan tool wear tinggi mendahului overstrain, dengan batas yang berbeda per tipe produk.",
          "Fisher exact: torque >= P75 dan tool wear >= P75 vs sisanya, label OSF; ambang tool wear x torque terbaik per tipe (bootstrap 95%)",
          round((k1 / n1) / (k0 / n0), 4) if k0 else np.nan, p5, v5, f"ambang L/M/H = {thr.loc['L','ambang_terbaik_minNm']}/{thr.loc['M','ambang_terbaik_minNm']}/{thr.loc['H','ambang_terbaik_minNm']}; interval L dan H {'terpisah' if sep_lh else 'tumpang tindih'}"))
pd.DataFrame(H, columns=["id", "hipotesis", "uji", "statistik_rasio", "p_value", "verdict", "bukti"]).to_csv(RES_ANALYSIS / "hypotheses.csv", index=False)
print(pd.DataFrame(H)[[0, 3, 4, 5, 6]].to_string(index=False))
print(h5.to_string(index=False)); print(h3.to_string(index=False)); print(pr.to_string(index=False))
