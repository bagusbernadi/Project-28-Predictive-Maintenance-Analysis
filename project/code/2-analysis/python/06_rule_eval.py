"""Langkah 8 dan 10 (bagian dokumentasi): uji aturan ambang (precision, recall, proporsi peringatan), pilih dari data latih, nilai di data uji (Q8-Q10, Q14)."""
import itertools
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "1-data-preparation" / "python"))
from importlib import import_module  # noqa: E402

from common import ALERT_LIMIT, ALERT_LIMITS, DB_PATH, DOC, RES_ANALYSIS, SEED, TEST_SIZE  # noqa: E402

d, _, _ = import_module("01_load_audit").load_raw()
d["dt"] = d.process_temp_k - d.air_temp_k
d["power"] = d.torque_nm * d.rpm * 2 * np.pi / 60
d["wxt"] = d.tool_wear_min * d.torque_nm
d["wear"], d["tq"] = d.tool_wear_min, d.torque_nm
y = d.machine_failure.values
tr_i, te_i = train_test_split(np.arange(len(d)), test_size=TEST_SIZE, random_state=SEED, stratify=y)
PER = {"train": np.sort(tr_i), "test": np.sort(te_i), "all": np.arange(len(d))}
GRID_TYPE = np.arange(6000, 16001, 500)


def conf(m, ix):
    mm, yy = m[ix], y[ix]
    tp, fp = int((mm & (yy == 1)).sum()), int((mm & (yy == 0)).sum())
    fn, tn = int((~mm & (yy == 1)).sum()), int((~mm & (yy == 0)).sum())
    n = tp + fp + fn + tn
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, precision=tp / (tp + fp) if tp + fp else np.nan, recall=tp / (tp + fn) if tp + fn else np.nan,
                alert_share=(tp + fp) / n, accuracy=(tp + tn) / n, f1=2 * tp / (2 * tp + fp + fn) if tp else 0.0)


# ---- keluarga aturan: nama -> daftar (label ambang, mask)
cand = {}
cand["tool wear >= T"] = [(f"{T} menit", (d.wear >= T).values) for T in range(100, 250, 10)]
cand["torque >= T"] = [(f"{T} Nm", (d.tq >= T).values) for T in range(35, 75, 5)]
cand["tool wear >= Tw dan torque >= Tq"] = [(f"{tw} menit, {tq} Nm", ((d.wear >= tw) & (d.tq >= tq)).values) for tw in (150, 175, 200, 210, 220) for tq in (35, 40, 45, 50, 55, 60)]
cand["tool wear x torque >= P"] = [(f"{P} minNm", (d.wxt >= P).values) for P in range(8000, 14001, 1000)]
cand["power di luar [Pl, Ph]"] = [(f"{lo} W, {hi} W", ((d.power < lo) | (d.power > hi)).values) for lo in (3000, 3500, 4000, 4500) for hi in (8500, 9000, 9500)]
cand["selisih suhu < D dan rpm < R"] = [(f"{D} K, {R} rpm", ((d.dt < D) & (d.rpm < R)).values) for D in (8.0, 8.6, 9.0, 9.5) for R in (1300, 1380, 1450, 1500)]
# tool wear x torque dengan ambang per tipe: ambang tiap tipe = F1 terbaik di data latih
typ_thr = {}
for t in ("L", "M", "H"):
    ix = PER["train"][(d.type.values[PER["train"]] == t)]
    sc = [(conf((d.wxt >= P).values & (d.type == t).values, ix)["f1"], -P) for P in GRID_TYPE]
    typ_thr[t] = -max(sc)[1]
pt = np.array([typ_thr[t] for t in d.type])
cand["tool wear x torque >= P (per tipe)"] = [("L={L}, M={M}, H={H} minNm".format(**typ_thr), (d.wxt.values >= pt))]


def pick(family, limit, ix=PER["train"]):
    rows = [(lab, m, conf(m, ix)) for lab, m in cand[family]]
    ok = [r for r in rows if r[2]["alert_share"] <= limit] or [min(rows, key=lambda r: r[2]["alert_share"])]
    return max(ok, key=lambda r: (r[2]["recall"], r[2]["precision"] if not np.isnan(r[2]["precision"]) else 0))


UNION_FAMS = ("tool wear x torque >= P (per tipe)", "selisih suhu < D dan rpm < R", "torque >= T", "power di luar [Pl, Ph]", "tool wear >= T")


def build_union(limit):
    """Gabungan bertahap: aturan terbaik tiap keluarga (data latih), urut precision; ditambahkan selama total proporsi peringatan data latih <= batas."""
    picks = sorted(((f, pick(f, limit)) for f in UNION_FAMS), key=lambda t: -t[1][2]["precision"])
    m, parts = np.zeros(len(d), bool), {}
    for f, (lab, mm, _) in picks:
        if conf(m | mm, PER["train"])["alert_share"] <= limit:
            m |= mm
            parts[f] = (lab, mm, None)
    return parts, m


SHORT = {"tool wear x torque >= P (per tipe)": "wear x torque", "selisih suhu < D dan rpm < R": "suhu-rpm", "torque >= T": "torque", "power di luar [Pl, Ph]": "power", "tool wear >= T": "wear"}
parts, mu = build_union(ALERT_LIMIT)
cand["gabungan (OR)"] = [(" | ".join(f"{SHORT[k]}: {v[0]}" for k, v in parts.items()), mu)]
FAM = list(cand)
records = []
for fam in FAM:
    for lab, m in cand[fam]:
        for per, ix in PER.items():
            records.append({"rule_name": fam, "threshold": lab, "period": per, **conf(m, ix)})
base_m = np.zeros(len(d), bool)
for per, ix in PER.items():
    records.append({"rule_name": "baseline (tidak pernah memberi peringatan)", "threshold": "-", "period": per, **conf(base_m, ix)})
ev = pd.DataFrame(records)
num = ["precision", "recall", "alert_share", "accuracy", "f1"]
ev[num] = ev[num].round(8)
ev.to_csv(RES_ANALYSIS / "rule_eval.csv", index=False)

# ---- aturan terbaik per keluarga (dipilih di data latih dengan batas proporsi peringatan) dan sensitivitas batas
sel = []
for limit in ALERT_LIMITS:
    # gabungan: coba penyusunan pada semua batas <= batas ini, ambil recall latih tertinggi yang proporsi peringatannya <= batas
    unions = [build_union(l2) for l2 in ALERT_LIMITS if l2 <= limit]
    unions = [u for u in unions if conf(u[1], PER["train"])["alert_share"] <= limit]
    p_u, m_u = max(unions, key=lambda u: conf(u[1], PER["train"])["recall"])
    fam_cand = {f: pick(f, limit) for f in FAM if f != "gabungan (OR)"}
    fam_cand["gabungan (OR)"] = (" | ".join(f"{SHORT[k]}: {v[0]}" for k, v in p_u.items()), m_u, conf(m_u, PER["train"]))
    for fam, (lab, m, c_tr) in fam_cand.items():
        for per, ix in PER.items():
            sel.append({"batas_alert_share": limit, "rule_name": fam, "threshold": lab, "period": per, **conf(m, ix)})
sl = pd.DataFrame(sel)
sl[num] = sl[num].round(8)
sl.to_csv(RES_ANALYSIS / "rule_selection.csv", index=False)
main = sl[(sl.batas_alert_share == ALERT_LIMIT) & (sl.period == "train")]
best = main[main.alert_share <= ALERT_LIMIT].sort_values(["recall", "precision"], ascending=False).iloc[0]
# sinkronkan label gabungan di rule_eval dan seleksi untuk batas utama
best_name, best_lab = best.rule_name, best.threshold
# mask aturan terpilih
if best_name == "gabungan (OR)":
    best_m = max((build_union(l2) for l2 in ALERT_LIMITS if l2 <= ALERT_LIMIT and conf(build_union(l2)[1], PER["train"])["alert_share"] <= ALERT_LIMIT), key=lambda u: conf(u[1], PER["train"])["recall"])[1]
else:
    best_m = next(m for lab, m in cand[best_name] if lab == best_lab)
fr = {"rule_name": best_name, "threshold": best_lab, "batas_alert_share": ALERT_LIMIT}
for per, ix in PER.items():
    for k, v in conf(best_m, ix).items():
        fr[f"{k}_{per}"] = v
pd.DataFrame([fr]).round(8).to_csv(RES_ANALYSIS / "final_rule.csv", index=False)
# per tipe (Q10)
pt_rows = []
for t in ("L", "M", "H"):
    for per in ("test", "all"):
        ix = PER[per][d.type.values[PER[per]] == t]
        pt_rows.append({"type": t, "period": per, "n": len(ix), "failures": int(y[ix].sum()), **conf(best_m, ix)})
pd.DataFrame(pt_rows).round(8).to_csv(RES_ANALYSIS / "final_rule_by_type.csv", index=False)
np.save(RES_ANALYSIS / ".final_mask.npy", best_m)  # sementara untuk skrip berikutnya (diabaikan git)

# ---- pohon keputusan dangkal sebagai pembanding (opsional pada rancangan)
X = pd.DataFrame({"rpm": d.rpm, "torque": d.tq, "wear": d.wear, "dt": d.dt, "power": d.power, "wxt": d.wxt, "tipe_L": (d.type == "L").astype(int), "tipe_M": (d.type == "M").astype(int)})
tree_rows = []
for nm, cw in (("pohon keputusan kedalaman 3", None), ("pohon keputusan kedalaman 3, bobot seimbang", "balanced")):
    clf = DecisionTreeClassifier(max_depth=3, random_state=SEED, class_weight=cw).fit(X.iloc[PER["train"]], y[PER["train"]])
    pm = clf.predict(X).astype(bool)
    for per, ix in PER.items():
        tree_rows.append({"model": nm, "period": per, **conf(pm, ix)})
tr = pd.DataFrame(tree_rows)
tr[num] = tr[num].round(8)
tr.to_csv(RES_ANALYSIS / "tree_compare.csv", index=False)

# ---- Q14: bandingkan dengan dokumentasi UCI (dibaca 31 Okt 2026)
h5 = pd.read_csv(RES_ANALYSIS / "h5_type_thresholds.csv").set_index("type")


def f1_of(mask, lab):
    tp = int((mask & (lab == 1)).sum()); fp = int((mask & (lab == 0)).sum()); fn = int((~mask & (lab == 1)).sum())
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


hdf = d.hdf.values
bh = max(((f1_of(((d.dt < D) & (d.rpm < R)).values, hdf), D, R) for D in np.round(np.arange(7.0, 11.01, 0.1), 1) for R in range(1200, 1701, 10)), key=lambda t: (t[0], -t[1], -t[2]))
pw = d.pwf.values
bp = max(((f1_of(((d.power < lo) | (d.power > hi)).values, pw), lo, hi) for lo in range(2500, 4501, 50) for hi in range(8000, 10501, 50)), key=lambda t: (t[0], -t[1], t[2]))
twf_w = d[d.twf == 1].wear
rows = [("TWF: rentang tool wear", f"{DOC['twf_lo']} sampai {DOC['twf_hi']} menit (dipilih acak)", f"{int(twf_w.min())} sampai {int(twf_w.max())} menit (median {int(twf_w.median())})", "Sesuai" if twf_w.min() >= DOC["twf_lo"] - 5 and twf_w.max() <= DOC["twf_hi"] + 15 else "Berbeda"),
        ("TWF: jumlah kasus", f"{DOC['twf_cases']} kasus (69 penggantian, 51 kegagalan)", f"{int(d.twf.sum())} baris dengan TWF = 1", "Berbeda"),
        ("HDF: selisih suhu dan rpm", f"selisih suhu < {DOC['hdf_dt']} K dan rpm < {DOC['hdf_rpm']}", f"terbaik di data: selisih suhu < {bh[1]} K dan rpm < {bh[2]} (F1 {bh[0]:.3f}); aturan dokumentasi F1 {f1_of(((d.dt < DOC['hdf_dt']) & (d.rpm < DOC['hdf_rpm'])).values, hdf):.3f}", "Sesuai"),
        ("PWF: rentang power", f"di bawah {DOC['pwf_lo']} W atau di atas {DOC['pwf_hi']} W", f"terbaik di data: di bawah {bp[1]} W atau di atas {bp[2]} W (F1 {bp[0]:.3f}); aturan dokumentasi F1 {f1_of(((d.power < DOC['pwf_lo']) | (d.power > DOC['pwf_hi'])).values, pw):.3f}", "Sesuai")]
for t in ("L", "M", "H"):
    s = d.type == t
    rows.append((f"OSF tipe {t}: tool wear x torque", f"di atas {DOC['osf'][t]} minNm", f"terbaik di data: {int(h5.loc[t, 'ambang_terbaik_minNm'])} minNm ({int(h5.loc[t, 'osf'])} kasus OSF); aturan dokumentasi F1 {f1_of(((d.wxt > DOC['osf'][t]) & s).values & s.values, d.osf.values * s.values):.3f}",
                 "Sesuai" if h5.loc[t, "ambang_terbaik_minNm"] == DOC["osf"][t] else "Sebagian"))
rows.append(("RNF: jumlah kasus", f"{DOC['rnf_cases']} kasus (peluang 0,1% per proses)", f"{int(d.rnf.sum())} baris RNF = 1; hanya {int(((d.rnf == 1) & (d.machine_failure == 1)).sum())} di antaranya machine_failure = 1", "Berbeda"))
pd.DataFrame(rows, columns=["komponen", "dokumentasi_uci", "hasil_data", "kecocokan"]).to_csv(RES_ANALYSIS / "doc_comparison.csv", index=False)

# ---- muat ke tabel rule_eval di DuckDB dan cek silang SQL untuk aturan terpilih
con = duckdb.connect(str(DB_PATH))
con.execute("DELETE FROM rule_eval")
ins = ev[["rule_name", "threshold", "period", "tp", "fp", "fn", "tn", "precision", "recall", "alert_share"]]
con.register("ins", ins)
con.execute("INSERT INTO rule_eval SELECT * FROM ins")
chk = []
sqls = {"tool wear >= T": "tool_wear_min >= 200", "tool wear >= Tw dan torque >= Tq": "tool_wear_min >= 200 AND torque_nm >= 45"}
for nm, cond in sqls.items():
    r = con.execute(f"SELECT sum(CASE WHEN {cond} AND machine_failure=1 THEN 1 ELSE 0 END), sum(CASE WHEN {cond} AND machine_failure=0 THEN 1 ELSE 0 END), sum(CASE WHEN NOT({cond}) AND machine_failure=1 THEN 1 ELSE 0 END), sum(CASE WHEN NOT({cond}) AND machine_failure=0 THEN 1 ELSE 0 END) FROM raw_ai4i").fetchone()
    lab = "200 menit" if nm == "tool wear >= T" else "200 menit, 45 Nm"
    p = ev[(ev.rule_name == nm) & (ev.threshold == lab) & (ev.period == "all")].iloc[0]
    chk.append((nm + " (" + lab + ")", "SQL vs Python", "PASS" if tuple(int(x) for x in r) == (p.tp, p.fp, p.fn, p.tn) else "FAIL"))
w = con.execute("SELECT count(*) FROM rule_eval").fetchone()[0]
con.close()
pd.DataFrame(chk, columns=["aturan", "pembanding", "status"]).to_csv(RES_ANALYSIS / "crosscheck_rules.csv", index=False)
assert all(c[2] == "PASS" for c in chk) and w == len(ins)
print("aturan terpilih:", best_name, best_lab, "| latih recall", round(best.recall, 3), "alert", round(best.alert_share, 3))
print(sl[(sl.batas_alert_share == ALERT_LIMIT) & (sl.period.isin(["train", "test"]))][["rule_name", "threshold", "period", "precision", "recall", "alert_share", "accuracy"]].round(3).to_string(index=False))
print(tr[tr.period == "test"].round(3).to_string(index=False))
print(pd.read_csv(RES_ANALYSIS / "doc_comparison.csv").to_string(index=False))
