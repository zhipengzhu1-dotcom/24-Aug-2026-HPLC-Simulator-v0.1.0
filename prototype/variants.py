"""THROWAWAY: three structurally different answers to "how does the candidate's φ range
enter the Cockpit?" (ticket #45). Each returns a :class:`Programme`; the pane mounts it.

A — **Range beside the sliders.** The sidebar keeps the scouting %B as method constants
    (relabelled "as run"); the rail's Candidate block gains a %B range slider under tG
    and hold, with a "match scouting" reset. Extra segments live in an expander table.
    The programme is drawn as a small φ-vs-time sparkline in the rail beneath the
    controls — candidate solid, scouting dashed.

B — **Programme table, paired.** ACD/DryLab shape (#56). The scouting programme leaves
    the sidebar and becomes a read-mostly No./Time/%B table at the top of the rail (two
    time columns: the same programme at two speeds); the candidate is a second table of
    the same shape directly beneath, dynamic rows, no sliders. Multi-segment is more
    rows. The programme is shown as the table and nothing else.

C — **Segments stacked, programme drawn on the chromatogram.** Start %B, hold, then one
    block per segment ("to %B over min"), with + / − buttons. The programme is overlaid on
    the pinned chromatogram on a right-hand %B axis — candidate solid, scouting dashed —
    with each peak's elution composition marked and its calibrated window as a whisker.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.pipeline import Cockpit, MethodEntry
from hplcsim.model import Gradient, Run
from prototype.diag import Composition
from prototype.programme import Programme, Segment

NAMES = {
    "A": "Range beside the sliders",
    "B": "Programme table, paired",
    "C": "Segments stacked, drawn on the chromatogram",
    "D": "The pick — B's paired tables with C's overlay",
}

_SCOUT = "#8d99a8"
_CAND = "#c77700"
_AMBER = "#c77700"


@dataclass
class RailContext:
    constants: MethodEntry
    run1: Run | None
    run2: Run | None
    slider_with_box: Callable[..., float]
    keys: Any
    tg_range: tuple[float, float]
    hold_range: tuple[float, float]
    tg_default: float
    max_hold: float


def _restored_tg(ctx: RailContext) -> float:
    """The candidate tG a session load put into the slider, if any."""
    return float(st.session_state.get(f"{ctx.keys.CANDIDATE_TG}_slider", ctx.tg_default))


def _tg_slider(ctx: RailContext, label: str = "tG (min)") -> float:
    return ctx.slider_with_box(
        label,
        *ctx.tg_range,
        ctx.tg_default,
        slider_step=0.5,
        box_step=0.1,
        box_label="Candidate tG (min)",
        key=ctx.keys.CANDIDATE_TG,
    )


def _hold_slider(ctx: RailContext) -> float:
    return ctx.slider_with_box(
        "Initial hold (min)",
        *ctx.hold_range,
        min(ctx.constants.hold, ctx.max_hold),
        slider_step=0.05,
        box_step=0.01,
        box_label="Candidate initial hold (min)",
        key=ctx.keys.CANDIDATE_HOLD,
    )


# =====================================================================================
# A — range beside the sliders
# =====================================================================================


def rail_a(ctx: RailContext) -> Programme:
    st.markdown("### Candidate — predicted")
    tg = _tg_slider(ctx)
    hold = _hold_slider(ctx)

    scout = (float(ctx.constants.percent_b_start), float(ctx.constants.percent_b_end))
    # Streamlit drops a widget's session state on any run that does not draw it, so
    # coming back from variant B or C finds the seed but not the slider's pair. Reseed
    # from the last pair this variant saw (a plain key, which survives), else scouting.
    if st.session_state.get("p45_a_seed") != scout:
        _a_reset(scout)
    elif not isinstance(st.session_state.get("p45_a_range"), (tuple, list)):
        _a_reset(scout, st.session_state.get("p45_a_last", scout))

    def _from_range() -> None:
        lo, hi = st.session_state["p45_a_range"]
        st.session_state["p45_a_lo"], st.session_state["p45_a_hi"] = float(lo), float(hi)

    def _from_boxes() -> None:
        lo, hi = st.session_state["p45_a_lo"], st.session_state["p45_a_hi"]
        if lo > hi:
            lo, hi = hi, lo
        st.session_state["p45_a_range"] = (float(lo), float(hi))

    st.slider("%B range", 0.0, 100.0, step=1.0, key="p45_a_range", on_change=_from_range)
    c1, c2 = st.columns(2)
    c1.number_input(
        "start %B", 0.0, 100.0, step=0.5, format="%.1f", key="p45_a_lo",
        on_change=_from_boxes, label_visibility="collapsed",
    )
    c2.number_input(
        "end %B", 0.0, 100.0, step=0.5, format="%.1f", key="p45_a_hi",
        on_change=_from_boxes, label_visibility="collapsed",
    )
    lo, hi = st.session_state["p45_a_range"]
    st.session_state["p45_a_last"] = (float(lo), float(hi))
    cap, btn = st.columns([2.2, 1.0], vertical_alignment="center")
    cap.caption(f"Scouting ran **{scout[0]:g} → {scout[1]:g} %B** (sidebar).")
    btn.button("↺", key="p45_a_reset", on_click=_a_reset, args=(scout,), width="stretch", help="Match the scouting range again")

    segments = [Segment(tg, hi / 100.0)]
    with st.expander("More segments (v0.2)", expanded=False):
        st.caption("Segment 1 is the sliders above. Each row appends a segment after it.")
        seed = pd.DataFrame({"Duration (min)": pd.Series(dtype=float), "End %B": pd.Series(dtype=float)})
        df = st.data_editor(
            seed, num_rows="dynamic", key="p45_a_segs", hide_index=True, width="stretch",
            column_config={
                "Duration (min)": st.column_config.NumberColumn(min_value=0.1, step=0.5, format="%.1f"),
                "End %B": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=1.0, format="%.0f"),
            },
        )
        for _, row in df.iterrows():
            d, e = row.get("Duration (min)"), row.get("End %B")
            if d is None or e is None or pd.isna(d) or pd.isna(e) or float(d) <= 0:
                continue
            segments.append(Segment(float(d), float(e) / 100.0))
    return Programme(lo / 100.0, hold, tuple(segments))


def _a_reset(scout: tuple[float, float], pair: tuple[float, float] | None = None) -> None:
    pair = tuple(pair) if pair is not None else scout
    st.session_state["p45_a_seed"] = scout
    st.session_state["p45_a_range"] = pair
    st.session_state["p45_a_lo"], st.session_state["p45_a_hi"] = pair
    st.session_state["p45_a_last"] = pair


def extras_a(
    programme: Programme, ctx: RailContext, cockpit: Cockpit, comp: Composition | None
) -> None:
    """The φ-vs-time sparkline under the controls: pump programme, candidate vs scouting."""
    fig = go.Figure()
    for run, name in ((ctx.run1, "run 1"), (ctx.run2, "run 2")):
        if run is None:
            continue
        pts = Programme.from_gradient(run.gradient).breakpoints()
        fig.add_trace(go.Scatter(
            x=[t for t, _ in pts], y=[p * 100 for _, p in pts], mode="lines", name=f"scouting {name}",
            line={"color": _SCOUT, "width": 1.2, "dash": "dash"},
            hovertemplate=f"{name}: %{{x:.1f}} min, %{{y:.0f}} %B<extra></extra>",
        ))
    pts = programme.breakpoints()
    fig.add_trace(go.Scatter(
        x=[t for t, _ in pts], y=[p * 100 for _, p in pts], mode="lines+markers", name="candidate",
        line={"color": _CAND, "width": 2.2}, marker={"size": 5},
        hovertemplate="candidate: %{x:.1f} min, %{y:.0f} %B<extra></extra>",
    ))
    method = ctx.constants.method
    if comp is not None and comp.rows:
        by_name = cockpit.predicted_by_name
        xs, ys, names = [], [], []
        for row in comp.rows:
            pk = by_name.get(row.name)
            if pk is None:
                continue
            xs.append(pk.retention.t_r - method.t0 - method.t_dwell)
            ys.append(row.phi_e_pct)
            names.append(row.name)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+text", text=names, textposition="top left",
            textfont={"size": 8}, marker={"size": 7, "color": "#24445f"}, name="elutes",
            hovertemplate="<b>%{text}</b> leaves at %{y:.1f} %B<extra></extra>",
        ))
    fig.update_layout(
        height=175, margin={"l": 34, "r": 6, "t": 6, "b": 28}, showlegend=False,
        xaxis={"title": {"text": "pump time (min)", "font": {"size": 9}}, "tickfont": {"size": 8}},
        yaxis={"title": {"text": "%B", "font": {"size": 9}}, "range": [0, 100], "tickfont": {"size": 8}},
        plot_bgcolor="#f8fbff", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("Solid: candidate, predicted. Dashed: scouting runs, as run. Dots: where each peak leaves the column.")


# =====================================================================================
# B — programme table, paired
# =====================================================================================

_B_SCOUT_COLS = ["No.", "Time run 1 (min)", "Time run 2 (min)", "%B"]


def scouting_b(ctx: RailContext) -> tuple[Run, Run]:
    """The scouting programme as a No./Time/%B table with two time columns."""
    st.markdown("### Scouting programme — as run")
    K = ctx.keys
    c = ctx.constants
    tg1 = float(st.session_state.get(K.TG_RUN1, 15.0))
    tg2 = float(st.session_state.get(K.TG_RUN2, 45.0))
    base = (float(c.percent_b_start), float(c.percent_b_end), float(c.hold), tg1, tg2)
    phi0, phif, hold, tg1, tg2 = base
    rows = [
        [1, 0.0, 0.0, phi0],
        [2, hold, hold, phi0],
        [3, hold + tg1, hold + tg2, phif],
    ]
    key = f"p45_b_scout_{hash(base) & 0xFFFF}"
    st.session_state["p45_b_scout_base"] = base

    def _apply() -> None:
        b = st.session_state["p45_b_scout_base"]
        phi0, phif, hold, tg1, tg2 = b
        table = {
            0: {"Time run 1 (min)": 0.0, "Time run 2 (min)": 0.0, "%B": phi0},
            1: {"Time run 1 (min)": hold, "Time run 2 (min)": hold, "%B": phi0},
            2: {"Time run 1 (min)": hold + tg1, "Time run 2 (min)": hold + tg2, "%B": phif},
        }
        for r, changes in st.session_state[key].get("edited_rows", {}).items():
            table[int(r)].update(changes)
        new_phi0 = float(table[0]["%B"])
        new_hold = max(0.0, float(table[1]["Time run 1 (min)"]))
        new_tg1 = max(0.1, float(table[2]["Time run 1 (min)"]) - new_hold)
        new_tg2 = max(0.1, float(table[2]["Time run 2 (min)"]) - new_hold)
        st.session_state[K.PERCENT_B_START] = new_phi0
        st.session_state[K.PERCENT_B_END] = float(table[2]["%B"])
        st.session_state[K.HOLD] = new_hold
        st.session_state[K.TG_RUN1] = new_tg1
        st.session_state[K.TG_RUN2] = new_tg2

    st.data_editor(
        pd.DataFrame(rows, columns=_B_SCOUT_COLS), key=key, hide_index=True, width="stretch",
        disabled=["No."], on_change=_apply,
        column_config={
            "No.": st.column_config.NumberColumn(width="small"),
            "Time run 1 (min)": st.column_config.NumberColumn("t, run 1", format="%.1f", step=0.5),
            "Time run 2 (min)": st.column_config.NumberColumn("t, run 2", format="%.1f", step=0.5),
            "%B": st.column_config.NumberColumn(format="%.0f", step=1.0, min_value=0.0, max_value=100.0),
        },
    )
    st.caption(f"One programme at two speeds: tG {tg1:g} and {tg2:g} min, hold {hold:g} min. Row 2 follows row 1's %B.")
    return (
        Run(c.gradient(tg1), name=f"tG{tg1:g}"),
        Run(c.gradient(tg2), name=f"tG{tg2:g}"),
    )


def rail_b(ctx: RailContext) -> Programme:
    st.markdown("### Candidate programme — predicted")
    c = ctx.constants
    scout = (float(c.percent_b_start), float(c.percent_b_end), float(c.hold))
    # `?b0=&b1=&tg=` seed the candidate on load (the other branch's convention), so a
    # trap case can be linked to; the seeds ride in the seed tuple and so re-key the table.
    q = st.query_params
    seeds = (q.get("b0"), q.get("b1"), q.get("tg"))
    if st.session_state.get("p45_b_seed") != (scout, seeds):
        st.session_state["p45_b_seed"] = (scout, seeds)
        st.session_state["p45_b_nonce"] = st.session_state.get("p45_b_nonce", 0) + 1
    phi0, phif, hold = scout
    tg = _restored_tg(ctx)
    if seeds[0] is not None: phi0 = float(seeds[0])
    if seeds[1] is not None: phif = float(seeds[1])
    if seeds[2] is not None: tg = float(seeds[2])
    # No "No." column here: the dynamic editor spends a gutter on its row handle, and the
    # rail has room for two numeric columns beside it. Rows read in time order.
    base = pd.DataFrame([[0.0, phi0], [hold, phi0], [hold + tg, phif]], columns=["Time (min)", "%B"])
    df = st.data_editor(
        base, num_rows="dynamic", key=f"p45_b_cand_{st.session_state['p45_b_nonce']}",
        width="stretch", hide_index=True,
        column_config={
            "Time (min)": st.column_config.NumberColumn("t (min)", format="%.1f", step=0.5, min_value=0.0, width="small"),
            "%B": st.column_config.NumberColumn(format="%.0f", step=1.0, min_value=0.0, max_value=100.0, width="small"),
        },
    )
    programme, note = _parse_table(df, fallback_tg=tg)
    line = f"tG {programme.t_ramp:g} min · hold {programme.t_init:g} min · {len(programme.segments)} segment{'s' if len(programme.segments) != 1 else ''}"
    cap, btn = st.columns([2.2, 1.0], vertical_alignment="center")
    cap.caption(line + (f" · {note}" if note else ""))
    btn.button("↺", key="p45_b_reset", on_click=_b_bump, width="stretch", help="Copy the scouting programme again")
    return programme


def _b_bump() -> None:
    st.session_state["p45_b_nonce"] = st.session_state.get("p45_b_nonce", 0) + 1


def _parse_table(df: pd.DataFrame, *, fallback_tg: float) -> tuple[Programme, str]:
    pts: list[tuple[float, float]] = []
    for _, row in df.iterrows():
        t, b = row.get("Time (min)"), row.get("%B")
        if t is None or b is None or pd.isna(t) or pd.isna(b):
            continue
        pts.append((float(t), float(b) / 100.0))
    pts.sort()
    if not pts:
        return Programme(0.05, 0.0, (Segment(fallback_tg, 0.05),)), "empty table — flat 5 %B"
    note = ""
    if pts[0][0] != 0.0:
        pts.insert(0, (0.0, pts[0][1]))
        note = "row 1 assumed at t = 0"
    phi0 = pts[0][1]
    i = 1
    t_init = 0.0
    while i < len(pts) and pts[i][1] == phi0:
        t_init = pts[i][0]
        i += 1
    segments: list[Segment] = []
    t_prev = t_init
    for t, phi in pts[i:]:
        if t > t_prev:
            segments.append(Segment(t - t_prev, phi))
            t_prev = t
    if not segments:
        return Programme(phi0, t_init, (Segment(fallback_tg, phi0),)), "no ramp — isocratic"
    return Programme(phi0, t_init, tuple(segments)), note


# =====================================================================================
# C — segments stacked, drawn on the chromatogram
# =====================================================================================


def rail_c(ctx: RailContext) -> Programme:
    st.markdown("### Candidate — predicted")
    c = ctx.constants
    scout = (float(c.percent_b_start), float(c.percent_b_end))
    if st.session_state.get("p45_c_seed") != scout:
        st.session_state["p45_c_seed"] = scout
        st.session_state["p45_c_vals"] = {"phi0": scout[0], "to1": scout[1]}
        st.session_state["p45_c_extra"] = []
        for k in [k for k in st.session_state if k.startswith("p45_c_to") or k.startswith("p45_c_over")]:
            st.session_state.pop(k, None)
    # Widget keys are dropped on any run that does not draw them (variant B or A on
    # show); `p45_c_vals` is plain state and survives, so refill from it.
    vals: dict[str, float] = st.session_state["p45_c_vals"]
    st.session_state.setdefault("p45_c_phi0", vals["phi0"])
    st.session_state.setdefault("p45_c_to1", vals["to1"])
    for n in st.session_state["p45_c_extra"]:
        st.session_state.setdefault(f"p45_c_to{n}", vals.get(f"to{n}", scout[1]))
        st.session_state.setdefault(f"p45_c_over{n}", vals.get(f"over{n}", 2.0))

    hold = _hold_slider(ctx)
    s1, s2 = st.columns([1.0, 1.0])
    phi0 = s1.number_input("Start %B", 0.0, 100.0, step=0.5, format="%.1f", key="p45_c_phi0")
    vals["phi0"] = float(phi0)
    s2.markdown(
        f"<div style='font-size:.72rem;color:#4a5768;padding-top:1.9rem'>scouting: "
        f"<b>{scout[0]:g} → {scout[1]:g} %B</b><br>dashed on the chromatogram</div>",
        unsafe_allow_html=True,
    )

    st.markdown("**Segment 1**")
    tg = _tg_slider(ctx, "over (min)")
    to1 = st.number_input("to %B", 0.0, 100.0, step=0.5, format="%.1f", key="p45_c_to1")
    vals["to1"] = float(to1)
    segments = [Segment(tg, to1 / 100.0)]

    extra: list[int] = st.session_state["p45_c_extra"]
    for n in extra:
        st.markdown(f"**Segment {n}**")
        c1, c2 = st.columns(2)
        to = c1.number_input("to %B", 0.0, 100.0, step=0.5, format="%.1f", key=f"p45_c_to{n}")
        over = c2.number_input("over (min)", 0.1, 600.0, step=0.5, format="%.1f", key=f"p45_c_over{n}")
        vals[f"to{n}"], vals[f"over{n}"] = float(to), float(over)
        segments.append(Segment(float(over), float(to) / 100.0))

    b1, b2 = st.columns(2)
    b1.button("＋ segment", key="p45_c_add", on_click=_c_add, args=(scout,), width="stretch")
    b2.button("− last", key="p45_c_drop", on_click=_c_drop, disabled=not extra, width="stretch")
    return Programme(phi0 / 100.0, hold, tuple(segments))


def _c_add(scout: tuple[float, float]) -> None:
    extra: list[int] = st.session_state["p45_c_extra"]
    n = (extra[-1] if extra else 1) + 1
    last_to = st.session_state.get(f"p45_c_to{extra[-1]}" if extra else "p45_c_to1", scout[1])
    # A new segment opens as a 2-minute hold at the last composition — the wash a
    # chromatographer usually adds first; edit "to %B" to make it a ramp.
    st.session_state[f"p45_c_to{n}"] = float(last_to)
    st.session_state[f"p45_c_over{n}"] = 2.0
    st.session_state["p45_c_vals"][f"to{n}"] = float(last_to)
    st.session_state["p45_c_vals"][f"over{n}"] = 2.0
    extra.append(n)


def _c_drop() -> None:
    extra: list[int] = st.session_state["p45_c_extra"]
    if extra:
        n = extra.pop()
        for k in (f"p45_c_to{n}", f"p45_c_over{n}"):
            st.session_state.pop(k, None)
        for k in (f"to{n}", f"over{n}"):
            st.session_state["p45_c_vals"].pop(k, None)


def decorate_c(
    fig: Any, programme: Programme, ctx: RailContext, cockpit: Cockpit, comp: Composition | None
) -> Any:
    """Overlay the programme at the detector on the chromatogram's right-hand axis."""
    method = ctx.constants.method
    lag = method.t_dwell + method.t0
    x_range = fig.layout.xaxis.range
    x_end = float(x_range[1]) if x_range else programme.t_end + lag + 2.0

    def detector(p: Programme) -> tuple[list[float], list[float]]:
        pts = p.breakpoints()
        xs = [0.0] + [t + lag for t, _ in pts] + [max(x_end, pts[-1][0] + lag)]
        ys = [p.phi0 * 100] + [phi * 100 for _, phi in pts] + [pts[-1][1] * 100]
        return xs, ys

    for run, name in ((ctx.run1, "run 1"), (ctx.run2, "run 2")):
        if run is None:
            continue
        xs, ys = detector(Programme.from_gradient(run.gradient))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, yaxis="y2", mode="lines", name=f"scouting {name} (as run)",
            line={"color": _SCOUT, "width": 1.1, "dash": "dash"},
            hovertemplate=f"scouting {name}: %{{y:.0f}} %B at %{{x:.2f}} min<extra></extra>",
        ))
    xs, ys = detector(programme)
    fig.add_trace(go.Scatter(
        x=xs, y=ys, yaxis="y2", mode="lines", name="candidate (predicted)",
        line={"color": _CAND, "width": 2.0},
        hovertemplate="candidate: %{y:.0f} %B at %{x:.2f} min<extra></extra>",
    ))
    if comp is not None and comp.rows:
        by_name = cockpit.predicted_by_name
        px, py, up, down, txt = [], [], [], [], []
        for row in comp.rows:
            pk = by_name.get(row.name)
            if pk is None:
                continue
            px.append(pk.retention.t_r)
            py.append(row.phi_e_pct)
            up.append(max(0.0, row.hi_pct - row.phi_e_pct))
            down.append(max(0.0, row.phi_e_pct - row.lo_pct))
            txt.append(f"{row.name}: leaves at {row.phi_e_pct:.1f} %B; window {row.lo_pct:.1f}–{row.hi_pct:.1f}")
        fig.add_trace(go.Scatter(
            x=px, y=py, yaxis="y2", mode="markers", name="peak leaves at / calibrated window",
            marker={"size": 7, "color": "#24445f", "symbol": "diamond"},
            error_y={"type": "data", "symmetric": False, "array": up, "arrayminus": down,
                     "color": "#24445f", "thickness": 1.2, "width": 5},
            text=txt, hovertemplate="%{text}<extra></extra>",
        ))
    fig.update_layout(
        yaxis2={"title": {"text": "%B at detector", "font": {"size": 9}}, "overlaying": "y",
                "side": "right", "range": [0, 100], "showgrid": False, "tickfont": {"size": 8}},
        legend={"orientation": "h", "y": 1.0, "x": 1.0, "xanchor": "right", "yanchor": "bottom",
                "font": {"size": 8}},
        margin={"r": 48},
    )
    return fig


# --- shared helpers -----------------------------------------------------------------


def isfinite(x: float) -> bool:
    return not (math.isnan(x) or math.isinf(x))


def scouting_gradient(run1: Run | None) -> Gradient | None:
    return None if run1 is None else run1.gradient
