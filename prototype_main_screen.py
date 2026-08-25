# PROTOTYPE — throwaway UI mock for wayfinder ticket #7 ("Prototype: main screen mock").
# Three structurally different layouts for the v0.1 main screen, switchable via
# ?variant=A|B|C or the floating bar at the bottom.
#
#   A · Cockpit         — sidebar constants, prediction as the hero, entry beside results
#   B · Bench worksheet — numbered top-to-bottom lab workflow, entry first
#   C · Split studio    — chromatogram pinned on top, everything else in tabs
#
# MOCK DATA + UNVALIDATED MATH. The engine here is a cartoon of the LSS closed form
# (natural-log convention, no edge-case branches, fixed G=0.85) purely so the sliders
# move peaks believably. Editing the peak table does NOT re-fit in this mock.
#
# Run: uv run --with streamlit,numpy,pandas,plotly streamlit run prototype_main_screen.py

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="hplcsim — prototype", layout="wide")

# ---------------------------------------------------------------- mock engine
def tr_pred(k0, Se, t0, tau, tG, dphi):
    be = t0 * dphi * Se / tG
    x = max(be * (k0 - tau / t0) + 1.0, 1e-6)
    return tau + t0 + (t0 / be) * np.log(x), be

def sigma_pred(be, t0, N):
    ke = 1.0 / max(be, 1e-6)
    return (t0 / np.sqrt(N)) * (1.0 + ke) * 0.85  # G fixed at 0.85 — MOCK

# name, k0 (at phi0), Se, area% run1, area% run2  (None tR = untracked demo)
COMPOUNDS = [
    ("Acetanilide",        60.0,  8.0, 12.0, 12.5),
    ("Methylparaben",     140.0,  9.5, 18.0, 17.2),
    ("Ketoprofen",        420.0, 13.0, 26.0, 25.1),
    ("Naproxen",          520.0, 11.0, 21.0, 34.0),   # area disagreement demo
    ("Ibuprofen imp. B",  900.0, 16.5,  8.0,  7.6),
    ("Valerophenone",     700.0, 10.5, 15.0, 14.9),
]
UNTRACKED = ("Unknown imp. 0.83", 4.0, None)  # tR run2 missing

# ------------------------------------------------------------- shared widgets
def method_constants():
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("Column length (mm)", value=150.0, key="len")
        st.number_input("Column i.d. (mm)", value=4.6, key="id")
        st.number_input("Particle size (µm)", value=5.0, key="dp")
        st.number_input("Flow F (mL/min)", value=1.0, key="flow")
        st.number_input("Temperature (°C) — metadata", value=30.0, key="temp")
    with c2:
        st.radio("t0 source", ["Measured marker", "Estimate (flagged)"], key="t0src", horizontal=True)
        st.number_input("t0 (min)", value=1.60, key="t0")
        st.number_input("Dwell volume VD (mL)", value=1.10, key="vd")
        st.number_input("Initial hold t_init (min)", value=0.25, key="hold0")
        st.slider("%B start → end", 0, 100, (5, 95), key="phis")
    st.slider("Plate count N (global knob)", 2000, 30000, 12000, step=1000, key="N")

def consts():
    phi0, phif = st.session_state.get("phis", (5, 95))
    t0 = st.session_state.get("t0", 1.60)
    f = st.session_state.get("flow", 1.0)
    tau = st.session_state.get("vd", 1.10) / f + st.session_state.get("hold0", 0.25)
    return t0, tau, (phif - phi0) / 100.0, st.session_state.get("N", 12000)

def scouting_inputs():
    c1, c2, c3 = st.columns([1, 1, 2])
    tg1 = c1.number_input("Run 1 tG (min)", value=15.0, key="tg1")
    tg2 = c2.number_input("Run 2 tG (min)", value=45.0, key="tg2")
    beta = tg2 / max(tg1, 1e-6)
    if beta < 1.2:
        c3.error(f"β = {beta:.2f} — runs nearly identical; fit unreliable")
    elif beta < 2.5:
        c3.warning(f"β = {beta:.2f} — recommend ~3 (run 2 ≈ 3×tG of run 1)")
    else:
        c3.success(f"β = {beta:.2f} — good spacing")
    return tg1, tg2

def peak_table(tg1, tg2):
    t0, tau, dphi, _ = consts()
    rows = []
    for name, k0, se, a1, a2 in COMPOUNDS:
        tr1, _ = tr_pred(k0, se, t0, tau, tg1, dphi)
        tr2, _ = tr_pred(k0, se, t0, tau, tg2, dphi)
        rows.append({"Compound": name, "tR run 1": round(tr1, 2), "tR run 2": round(tr2, 2),
                     "Area% R1": a1, "Area% R2": a2, "W½ (min)": None})
    rows.append({"Compound": UNTRACKED[0], "tR run 1": UNTRACKED[1], "tR run 2": None,
                 "Area% R1": 3.0, "Area% R2": None, "W½ (min)": None})
    st.data_editor(pd.DataFrame(rows), num_rows="dynamic", width="stretch", key=f"pt{tg1}{tg2}")
    st.caption("One row per compound — you pair the runs as you type. Editing does not re-fit in this MOCK.")

def tracking_warnings():
    st.warning("Area check: **Naproxen** area share 21% → 34% between runs — verify tracking.")
    st.info("Crossing: **Naproxen / Valerophenone** swap order between run 1 and run 2 — legitimate, please confirm.")
    st.caption("1 peak untracked (missing tR run 2) — excluded from fit and prediction.")

def fit_table():
    rows = [{"Compound": n, "log10 k0": round(np.log10(k0), 2), "S": round(se / 2.303, 2),
             "Status": "fitted"} for n, k0, se, _, _ in COMPOUNDS]
    rows.append({"Compound": UNTRACKED[0], "log10 k0": None, "S": None, "Status": "untracked — not fitted"})
    st.dataframe(pd.DataFrame(rows), width="stretch", height=280)

def candidate_controls():
    c1, c2 = st.columns(2)
    tgc = c1.slider("Candidate gradient tG (min)", 5.0, 90.0, 30.0, 0.5, key="tgc")
    holdc = c2.slider("Candidate initial hold (min)", 0.0, 5.0, 0.25, 0.25, key="holdc")
    return tgc, holdc

def predicted(tgc, holdc):
    t0, tau0, dphi, N = consts()
    tau = tau0 - st.session_state.get("hold0", 0.25) + holdc
    out = []
    for name, k0, se, a1, _ in COMPOUNDS:
        tr, be = tr_pred(k0, se, t0, tau, tgc, dphi)
        out.append((name, tr, sigma_pred(be, t0, N), a1))
    return sorted(out, key=lambda r: r[1])

def chromatogram(pred, height=340):
    tmax = max(r[1] for r in pred) + 3
    t = np.linspace(0, tmax, 2500)
    y = np.zeros_like(t)
    fig = go.Figure()
    for name, tr, sg, area in pred:
        pk = area / (sg * np.sqrt(2 * np.pi)) * np.exp(-0.5 * ((t - tr) / sg) ** 2)
        y += pk
        fig.add_annotation(x=tr, y=float(pk.max()) * 1.04, text=name, textangle=-55,
                           showarrow=False, font=dict(size=9))
    fig.add_trace(go.Scatter(x=t, y=y, mode="lines", line=dict(width=1.5)))
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), showlegend=False,
                      xaxis_title="time (min)", yaxis_title="response (mock)")
    st.plotly_chart(fig, width="stretch")

def resolution_table(pred):
    rows = []
    for (n1, t1, s1, _), (n2, t2, s2, _) in zip(pred, pred[1:]):
        rs = (t2 - t1) / (2 * (s1 + s2))
        rows.append({"Pair": f"{n1} / {n2}", "ΔtR (min)": round(t2 - t1, 2), "Rs": round(rs, 2),
                     "": "🔴" if rs < 1.5 else ("🟡" if rs < 2.0 else "🟢")})
    df = pd.DataFrame(rows)
    crit = min(rows, key=lambda r: r["Rs"])
    st.metric("Critical pair", crit["Pair"], f"Rs {crit['Rs']}")
    st.dataframe(df, width="stretch", height=250)

def banner():
    st.warning("**PROTOTYPE** — mock data, unvalidated cartoon math. Layout evaluation only.", icon="⚠️")

# ------------------------------------------------------------------ variants
def variant_a():  # Cockpit
    with st.sidebar:
        st.header("Method constants")
        method_constants()
    st.title("hplcsim — Cockpit")
    banner()
    tg1, tg2 = scouting_inputs()
    tgc, holdc = candidate_controls()
    pred = predicted(tgc, holdc)
    chromatogram(pred, height=380)
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Peak table (scouting runs)")
        peak_table(tg1, tg2)
        tracking_warnings()
    with right:
        st.subheader("Resolution")
        resolution_table(pred)
        with st.expander("Fitted parameters"):
            fit_table()

def variant_b():  # Bench worksheet
    st.title("hplcsim — Bench worksheet")
    banner()
    st.header("1 · Method & instrument")
    with st.expander("Method constants (shared by both scouting runs)", expanded=True):
        method_constants()
    st.header("2 · Scouting runs & peaks")
    tg1, tg2 = scouting_inputs()
    peak_table(tg1, tg2)
    tracking_warnings()
    st.header("3 · Fit results")
    fit_table()
    st.header("4 · Predict a candidate gradient")
    tgc, holdc = candidate_controls()
    pred = predicted(tgc, holdc)
    chromatogram(pred)
    resolution_table(pred)

def variant_c():  # Split studio
    st.title("hplcsim — Split studio")
    banner()
    top_l, top_r = st.columns([4, 1])
    with top_r:
        tgc = st.slider("tG (min)", 5.0, 90.0, 30.0, 0.5, key="tgc")
        holdc = st.slider("hold (min)", 0.0, 5.0, 0.25, 0.25, key="holdc")
    pred = predicted(tgc, holdc)
    with top_l:
        chromatogram(pred, height=300)
    t_method, t_runs, t_fit, t_res = st.tabs(["Method", "Runs & peaks", "Fit", "Resolution & warnings"])
    with t_method:
        method_constants()
    with t_runs:
        tg1, tg2 = scouting_inputs()
        peak_table(tg1, tg2)
    with t_fit:
        fit_table()
    with t_res:
        resolution_table(pred)
        tracking_warnings()

# ------------------------------------------------------------------ switcher
VARIANTS = {"A": ("Cockpit", variant_a), "B": ("Bench worksheet", variant_b), "C": ("Split studio", variant_c)}
cur = st.query_params.get("variant", "A")
cur = cur if cur in VARIANTS else "A"
keys = list(VARIANTS)
prev_k = keys[(keys.index(cur) - 1) % len(keys)]
next_k = keys[(keys.index(cur) + 1) % len(keys)]

VARIANTS[cur][1]()

st.markdown(
    f"""
    <div style="position:fixed;bottom:18px;left:50%;transform:translateX(-50%);
                background:#1e293b;color:#fff;padding:8px 18px;border-radius:999px;
                box-shadow:0 4px 14px rgba(0,0,0,.4);z-index:9999;font-size:14px;">
      <a href="?variant={prev_k}" target="_self" style="color:#93c5fd;text-decoration:none;">◀</a>
      &nbsp;&nbsp;<b>{cur} — {VARIANTS[cur][0]}</b>&nbsp;&nbsp;
      <a href="?variant={next_k}" target="_self" style="color:#93c5fd;text-decoration:none;">▶</a>
      &nbsp;&nbsp;<span style="opacity:.6">|</span>&nbsp;&nbsp;
      {"&nbsp;".join(f'<a href="?variant={k}" target="_self" style="color:{"#fff" if k == cur else "#93c5fd"};text-decoration:none;">{k}</a>' for k in keys)}
    </div>
    """,
    unsafe_allow_html=True,
)
