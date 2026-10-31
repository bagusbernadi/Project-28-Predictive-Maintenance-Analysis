"""Dashboard Streamlit 3 halaman. Membaca hanya CSV kecil di results/3-presentation (tanpa data mentah).
Jalankan dari folder project/:  streamlit run code/3-presentation/streamlit/app.py"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path(__file__).resolve().parents[3] / "results" / "3-presentation"
P = lambda x: f"{x * 100:.1f}%".replace(".", ",")
st.set_page_config(page_title="Project 28: Predictive Maintenance", layout="wide")
rd = lambda n: pd.read_csv(DATA / f"dash_{n}.csv")
page = st.sidebar.radio("Halaman", ["Ringkasan Kegagalan", "Kondisi Operasi", "Simulasi Aturan Ambang"])
st.sidebar.caption("Data: AI4I 2020 (UCI 601), sintetis. Angka dampak berlabel estimated dan simulated.")
sm = rd("summary").iloc[0]
if page == "Ringkasan Kegagalan":
    st.title("Ringkasan Kegagalan")
    c = st.columns(3)
    c[0].metric("Run mesin", f"{int(sm.runs):,}".replace(",", "."))
    c[1].metric("Failure rate", P(sm.failure_rate))
    c[2].metric("Akurasi aturan 'tidak pernah peringatan'", P(sm.baseline_accuracy), help="Tinggi, tetapi recall-nya 0%.")
    rt = rd("rate_type")
    rt["failures_rate_pct"] = rt.failures_rate * 100
    st.plotly_chart(px.bar(rt, x="type", y="failures_rate_pct", title="Failure rate per tipe produk (%)", labels={"failures_rate_pct": "Failure rate (%)", "type": "Tipe"}), width="stretch")
    md = rd("modes")
    md["porsi_pct"] = md.share_of_flags * 100
    st.plotly_chart(px.bar(md, x="failure_mode", y="porsi_pct", title="Porsi jenis kegagalan (Pareto, % dari kejadian jenis)", labels={"porsi_pct": "%", "failure_mode": "Jenis"}), width="stretch")
elif page == "Kondisi Operasi":
    st.title("Kondisi Operasi")
    w = rd("wear")
    w["rate_pct"] = w.failures_rate * 100
    st.plotly_chart(px.bar(w, x="wear_bucket", y="rate_pct", title="Failure rate per bucket tool wear (menit)", labels={"rate_pct": "Failure rate (%)", "wear_bucket": "Tool wear"}), width="stretch")
    h = rd("heatmap")
    h["rate_pct"] = h.failures_rate.where(h.reliable) * 100
    pv = h.pivot(index="torque_bucket", columns="rpm_bucket", values="rate_pct")
    st.plotly_chart(px.imshow(pv, text_auto=".1f", aspect="auto", title="Failure rate torque x rpm (%; sel dengan kurang dari 30 run dikosongkan)", labels=dict(color="%")), width="stretch")
else:
    st.title("Simulasi Aturan Ambang")
    g = rd("rule_grid")
    fam = st.selectbox("Aturan", sorted(g.rule_name.unique()), index=1 if "tool wear >= T" in set(g.rule_name) else 0)
    gf = g[g.rule_name == fam].sort_values("ambang")
    t = st.select_slider("Ambang", options=list(gf.ambang), value=int(gf.ambang.iloc[len(gf) // 2]))
    r = gf[gf.ambang == t].iloc[0]
    c = st.columns(4)
    c[0].metric("Precision", P(r.precision) if pd.notna(r.precision) else "-")
    c[1].metric("Recall", P(r.recall))
    c[2].metric("Proporsi peringatan", P(r.alert_share))
    c[3].metric("Akurasi", P(r.accuracy), delta=f"{(r.accuracy - sm.baseline_accuracy) * 100:.1f} poin vs baseline".replace(".", ","))
    st.caption(f"Baseline tidak pernah memberi peringatan: akurasi {P(sm.baseline_accuracy)}, recall 0%. Aturan terpilih project: {sm.final_rule} (data uji: precision {P(sm.final_precision_test)}, recall {P(sm.final_recall_test)}, peringatan {P(sm.final_alert_test)}).")
