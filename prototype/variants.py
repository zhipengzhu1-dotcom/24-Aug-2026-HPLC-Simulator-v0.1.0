"""THROWAWAY: three structurally different answers to #45, rendered in the real rail.

A — **Programme table**: the candidate *is* a No. / Time / %B table (the instrument's
    own shape, and #56's); the scouting programme sits above it read-only in the same
    shape; what differs is named beneath. The sweep slider is gone — that is the cost.
B — **Knobs + profile overlay**: four slider+box controls (start %B, end %B, tG, hold);
    the programme is *drawn* on the chromatogram against a right-hand %B axis, scouting
    runs dashed grey, candidate solid, each peak's calibrated window as a bar at its
    apex. No table, and a segment list has nowhere to go.
C — **Departure rail**: "what was run" is a pinned dense panel; the candidate is entered
    as numbers and every departure from the scouting pair is a coloured panel row, not
    a prose box. The two candidate-control warnings become rows with a "Why" expander.
    A "+ segment" affordance is stubbed and refused.

Shared, because #44 decided them: the fit-tab readout columns, the low-k0 badge, the
Rs stamp and the status-bar cells — see :mod:`prototype.entry`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import panels
from app.diagnostics import Diagnostic
from app.panels import Row
from app.pipeline import MethodEntry
from hplcsim.model import Gradient, Run, percent_b_from_phi, phi_from_percent_b
from prototype import composition as comp

_GOOD, _FAIR, _POOR = "#1f9d55", "#c77700", "#c0392b"
_SEVERITY_COLOUR = {None: _GOOD, "info": _FAIR, "warning": _FAIR, "strong": _POOR}

B0_KEY, B1_KEY = "proto_b0", "proto_b1"
NONCE = "proto_nonce"


@dataclass(frozen=True)
class Plumbing:
    """What the entry point owns and lends: its two-widget control and its keys."""

    slider_with_box: Callable[..., float]
    preset: Callable[..., None]
    tg_key: str
    hold_key: str
    tg_range: tuple[float, float]
    hold_range: tuple[float, float]
    default_tg: float
    default_hold: float


@dataclass(frozen=True)
class Programme:
    b0: float
    b1: float
    tg: float
    hold: float

    def gradient(self) -> Gradient:
        return Gradient(
            phi0=phi_from_percent_b(self.b0),
            phif=phi_from_percent_b(self.b1),
            t_gradient=self.tg,
            t_init=self.hold,
        )


def nonce() -> int:
    return int(st.session_state.get(NONCE, 0))


# --- canonical candidate state, shared by every variant ---------------------------------


def canonical(constants: MethodEntry, plumb: Plumbing) -> Programme:
    """The candidate as the widgets hold it, seeded from the scouting programme."""
    for key, seed in ((B0_KEY, constants.percent_b_start), (B1_KEY, constants.percent_b_end)):
        pending = st.session_state.pop(f"{key}_apply", None)
        if pending is not None:
            plumb.preset(key, seed=seed, value=float(pending))
        elif f"{key}_slider" not in st.session_state:
            plumb.preset(key, seed=seed, value=seed)
    for key, seed in ((plumb.tg_key, plumb.default_tg), (plumb.hold_key, plumb.default_hold)):
        if f"{key}_slider" not in st.session_state:
            plumb.preset(key, seed=seed, value=seed)
    return Programme(
        b0=float(st.session_state[f"{B0_KEY}_slider"]),
        b1=float(st.session_state[f"{B1_KEY}_slider"]),
        tg=float(st.session_state[f"{plumb.tg_key}_slider"]),
        hold=float(st.session_state[f"{plumb.hold_key}_slider"]),
    )


def write_percent_b(constants: MethodEntry, plumb: Plumbing, p: Programme) -> None:
    plumb.preset(B0_KEY, seed=constants.percent_b_start, value=p.b0)
    plumb.preset(B1_KEY, seed=constants.percent_b_end, value=p.b1)


def write_canonical(constants: MethodEntry, plumb: Plumbing, p: Programme) -> None:
    """All four — only from a variant that draws no tG/hold slider of its own (A)."""
    write_percent_b(constants, plumb, p)
    plumb.preset(plumb.tg_key, seed=plumb.default_tg, value=p.tg)
    plumb.preset(plumb.hold_key, seed=plumb.default_hold, value=p.hold)


def reset_to_scouting(constants: MethodEntry, plumb: Plumbing) -> Callable[[], None]:
    def _go() -> None:
        plumb.preset(B0_KEY, seed=constants.percent_b_start, value=constants.percent_b_start)
        plumb.preset(B1_KEY, seed=constants.percent_b_end, value=constants.percent_b_end)
        st.session_state[NONCE] = nonce() + 1

    return _go


def _differences(constants: MethodEntry, p: Programme, runs: Sequence[Run]) -> list[str]:
    parts = []
    if p.b0 != constants.percent_b_start:
        parts.append(f"start {constants.percent_b_start:g} → {p.b0:g} %B")
    if p.b1 != constants.percent_b_end:
        parts.append(f"end {constants.percent_b_end:g} → {p.b1:g} %B")
    if p.hold != constants.hold:
        parts.append(f"hold {constants.hold:g} → {p.hold:g} min")
    tgs = [run.gradient.t_gradient for run in runs]
    if p.tg not in tgs:
        parts.append(f"tG {p.tg:g} min (runs: {' / '.join(f'{t:g}' for t in tgs)})")
    return parts


# --- variant A: the programme table -------------------------------------------------------


def controls_a(constants: MethodEntry, plumb: Plumbing, runs: Sequence[Run]) -> Gradient:
    st.markdown("### Candidate programme")
    p = canonical(constants, plumb)
    _as_run_table(constants, runs)
    frame = pd.DataFrame(
        {
            "No.": pd.Series([1, 2, 3, 4, 5], dtype="Int64"),
            "Time (min)": pd.Series([0.0, p.hold, p.hold + p.tg, None, None], dtype="Float64"),
            "%B": pd.Series([p.b0, p.b0, p.b1, None, None], dtype="Float64"),
        }
    )
    edited = st.data_editor(
        frame,
        key=f"proto_programme_{nonce()}",
        hide_index=True,
        num_rows="fixed",
        width="stretch",
        column_config={
            "No.": st.column_config.NumberColumn(disabled=True, width="small"),
            "Time (min)": st.column_config.NumberColumn(format="%.2f", min_value=0.0),
            "%B": st.column_config.NumberColumn(format="%.1f", min_value=0.0, max_value=100.0),
        },
    )
    parsed, notes = _parse_programme(edited, fallback=p, plumb=plumb)
    for note in notes:
        st.warning(note, icon="⚠️")
    write_canonical(constants, plumb, parsed)
    differs = _differences(constants, parsed, runs)
    st.caption(
        "Differs from the scouting programme: " + "; ".join(differs)
        if differs
        else "Same programme as the scouting runs — only tG is being predicted."
    )
    st.button("Copy the scouting programme", on_click=reset_to_scouting(constants, plumb))
    return parsed.gradient()


def _as_run_table(constants: MethodEntry, runs: Sequence[Run]) -> None:
    tgs = " | ".join(f"{run.gradient.t_gradient:g}" for run in runs)
    rows = [
        Row("1  0.00 min", f"{constants.percent_b_start:g} %B"),
        Row(f"2  {constants.hold:.2f} min", f"{constants.percent_b_start:g} %B"),
        Row(f"3  hold + tG ({tgs})", f"{constants.percent_b_end:g} %B"),
    ]
    st.markdown(panels.panel("As run — scouting programme", rows), unsafe_allow_html=True)


def _parse_programme(
    edited: pd.DataFrame, *, fallback: Programme, plumb: Plumbing
) -> tuple[Programme, list[str]]:
    points = sorted(
        (float(t), float(b))
        for t, b in zip(edited["Time (min)"], edited["%B"], strict=True)
        if not pd.isna(t) and not pd.isna(b)
    )
    if len(points) < 2:
        return fallback, ["The programme needs at least a start row and a ramp-end row."]
    b0 = points[0][1]
    first_change = next((i for i, (_, b) in enumerate(points) if b != b0), None)
    if first_change is None:
        return fallback, ["A flat programme has no ramp to predict — keeping the last one."]
    hold = points[first_change - 1][0]
    tg = points[first_change][0] - hold
    b1 = points[first_change][1]
    notes = []
    if len(points) > first_change + 1:
        extra = ", ".join(str(i + 1) for i in range(first_change + 1, len(points)))
        notes.append(
            f"**Rows {extra} describe a second segment.** The engine predicts one linear "
            "ramp (SPEC §4); they are ignored, not refused — the first ramp is what is shown."
        )
    lo, hi = plumb.tg_range
    if not lo <= tg <= hi:
        notes.append(f"tG {tg:g} min is outside {lo:g}–{hi:g}; clamped.")
        tg = min(max(tg, lo), hi)
    lo, hi = plumb.hold_range
    if not lo <= hold <= hi:
        notes.append(f"Hold {hold:g} min is outside {lo:g}–{hi:g}; clamped.")
        hold = min(max(hold, lo), hi)
    return Programme(b0=b0, b1=b1, tg=tg, hold=hold), notes


# --- variant B: four knobs, programme drawn on the chromatogram ---------------------------


def controls_b(constants: MethodEntry, plumb: Plumbing, runs: Sequence[Run]) -> Gradient:
    st.markdown("### Candidate")
    canonical(constants, plumb)
    b0 = plumb.slider_with_box(
        "Start %B",
        0.0,
        100.0,
        constants.percent_b_start,
        slider_step=1.0,
        box_step=0.1,
        box_label="Candidate start %B",
        key=B0_KEY,
    )
    b1 = plumb.slider_with_box(
        "End %B",
        0.0,
        100.0,
        constants.percent_b_end,
        slider_step=1.0,
        box_step=0.1,
        box_label="Candidate end %B",
        key=B1_KEY,
    )
    tg = plumb.slider_with_box(
        "tG (min)",
        *plumb.tg_range,
        plumb.default_tg,
        slider_step=0.5,
        box_step=0.1,
        box_label="Candidate tG (min)",
        key=plumb.tg_key,
    )
    hold = plumb.slider_with_box(
        "Initial hold (min)",
        *plumb.hold_range,
        plumb.default_hold,
        slider_step=0.05,
        box_step=0.01,
        box_label="Candidate initial hold (min)",
        key=plumb.hold_key,
    )
    st.button("Same %B as the scouting runs", on_click=reset_to_scouting(constants, plumb))
    st.caption(
        "The programme is drawn on the chromatogram against the right-hand %B axis: "
        "scouting runs dashed grey, candidate solid, each peak's calibrated window as a "
        "bar at its apex."
    )
    return Programme(b0, b1, tg, hold).gradient()


def overlay_b(
    fig: Any,
    *,
    method: Any,
    runs: Sequence[Run],
    candidate: Gradient,
    analysis: comp.Analysis | None,
    apex_times: dict[str, float],
    x_end: float,
) -> None:
    for run, dash in zip(runs, ("dot", "dash"), strict=False):
        pts = comp.programme_points(method, run.gradient, x_end)
        fig.add_trace(
            go.Scatter(
                x=[t for t, _ in pts],
                y=[b for _, b in pts],
                mode="lines",
                yaxis="y2",
                line={"color": "#8d99a8", "width": 1, "dash": dash},
                hovertemplate=(
                    f"as run — {run.name}<br>%{{x:.2f}} min · %{{y:.1f}} %B<extra></extra>"
                ),
            )
        )
    pts = comp.programme_points(method, candidate, x_end)
    fig.add_trace(
        go.Scatter(
            x=[t for t, _ in pts],
            y=[b for _, b in pts],
            mode="lines",
            yaxis="y2",
            line={"color": "#1f4e79", "width": 1.6},
            hovertemplate="candidate<br>%{x:.2f} min · %{y:.1f} %B<extra></extra>",
        )
    )
    if analysis is not None:
        for w in analysis.windows:
            t_r = apex_times.get(w.name)
            if t_r is None:
                continue
            colour = _GOOD if w.distance == 0.0 else _POOR
            fig.add_trace(
                go.Scatter(
                    x=[t_r, t_r],
                    y=[percent_b_from_phi(w.lo), percent_b_from_phi(w.hi)],
                    mode="lines",
                    yaxis="y2",
                    line={"color": colour, "width": 5},
                    opacity=0.5,
                    hovertemplate=(
                        f"{w.name} — calibrated window<br>"
                        f"{percent_b_from_phi(w.lo):.1f}–{percent_b_from_phi(w.hi):.1f} %B"
                        "<extra></extra>"
                    ),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[t_r],
                    y=[percent_b_from_phi(w.at_candidate)],
                    mode="markers",
                    yaxis="y2",
                    marker={
                        "symbol": "diamond",
                        "size": 8,
                        "color": colour,
                        "line": {"width": 1, "color": "#ffffff"},
                    },
                    hovertemplate=(
                        f"{w.name} elutes at %{{y:.1f}} %B — {w.standing}<extra></extra>"
                    ),
                )
            )
    fig.update_layout(
        yaxis2={
            "title": {"text": "%B at detector", "font": {"size": 10}},
            "overlaying": "y",
            "side": "right",
            "range": [0, 100],
            "showgrid": False,
            "tickfont": {"size": 9},
        },
        margin={"l": 10, "r": 56, "t": 44, "b": 10},
        showlegend=False,
    )


# --- variant C: the departure rail --------------------------------------------------------


def controls_c(constants: MethodEntry, plumb: Plumbing, runs: Sequence[Run]) -> Gradient:
    p = canonical(constants, plumb)
    method = constants.method
    bracket = comp.scouting_bracket(method, runs[0], runs[1])
    st.markdown(
        panels.panel(
            "As run — scouting pair",
            [
                Row("Programme", f"{constants.percent_b_start:g} → {constants.percent_b_end:g} %B"),
                Row("Hold", f"{constants.hold:g} min"),
                Row("tG", " / ".join(f"{r.gradient.t_gradient:g}" for r in runs) + " min"),
                Row("s* bracket", f"{bracket.lo:.4f} – {bracket.hi:.4f}"),
            ],
        ),
        unsafe_allow_html=True,
    )
    st.markdown("### Candidate — what changes")
    left, right = st.columns(2)
    b0 = float(
        left.number_input(
            "Start %B", 0.0, 100.0, p.b0, step=1.0, format="%.1f", key=f"proto_c_b0_{nonce()}"
        )
    )
    b1 = float(
        right.number_input(
            "End %B", 0.0, 100.0, p.b1, step=1.0, format="%.1f", key=f"proto_c_b1_{nonce()}"
        )
    )
    tg = plumb.slider_with_box(
        "tG (min)",
        *plumb.tg_range,
        plumb.default_tg,
        slider_step=0.5,
        box_step=0.1,
        box_label="Candidate tG (min)",
        key=plumb.tg_key,
    )
    hold = plumb.slider_with_box(
        "Initial hold (min)",
        *plumb.hold_range,
        plumb.default_hold,
        slider_step=0.05,
        box_step=0.01,
        box_label="Candidate initial hold (min)",
        key=plumb.hold_key,
    )
    parsed = Programme(b0, b1, tg, hold)
    write_percent_b(constants, plumb, parsed)
    st.caption(f"0 min {b0:g} %B → {hold:g} min {b0:g} %B → {hold + tg:g} min {b1:g} %B")
    if st.button("+ Add a segment", key="proto_c_segment"):
        st.session_state["proto_c_segment_asked"] = True
    if st.session_state.get("proto_c_segment_asked"):
        st.warning(
            "**A second segment is not predicted.** The engine models one linear ramp "
            "(SPEC §4); the row pair below is where it would go, and it is refused until "
            "the engine can read it.",
            icon="⚠️",
        )
        s1, s2 = st.columns(2)
        s1.number_input(
            "Seg. 2 end (min)", value=hold + tg + 5.0, disabled=True, key="proto_c_seg_t"
        )
        s2.number_input("Seg. 2 %B", value=b1, disabled=True, key="proto_c_seg_b")
    return parsed.gradient()


def notices_c(
    diagnostics_candidate: Sequence[Diagnostic],
    analysis: comp.Analysis | None,
    *,
    constants: MethodEntry,
    candidate: Gradient,
    paint: Callable[[Sequence[Diagnostic]], None],
) -> None:
    """The two candidate-control warnings as coloured panel rows, prose behind 'Why'."""
    if analysis is None:
        return
    b0c, b1c = percent_b_from_phi(candidate.phi0), percent_b_from_phi(candidate.phif)
    d0 = b0c - constants.percent_b_start
    d1 = b1c - constants.percent_b_end
    dep = analysis.departure
    start_text = f"{b0c:g} %B ({d0:+.1f})"
    if dep is not None and d0 > 0:
        start_text += f" · ×{comp.DOUBLING_FACTOR ** (d0 / comp.DOUBLING_PER_PERCENT_B):.1f} error"
    steep = analysis.steepness
    ww = analysis.window_widths
    rows = [
        Row("Start %B", start_text, _SEVERITY_COLOUR[None if dep is None else dep.severity]),
        Row("End %B", f"{b1c:g} %B ({d1:+.1f}) — via s* only"),
        Row(
            "Steepness s*",
            f"{analysis.s_cand:.4f} · " + ("inside bracket" if ww == 0 else f"{ww:.2f} ww out"),
            _SEVERITY_COLOUR[None if steep is None else steep.severity],
        ),
        Row(
            "Rs standing",
            "indicative" if analysis.stamp else "decision-grade",
            _POOR if analysis.stamp else _GOOD,
        ),
    ]
    st.markdown(panels.panel("Departure from the scouting runs", rows), unsafe_allow_html=True)
    if diagnostics_candidate:
        with st.expander("Why", expanded=False):
            paint(diagnostics_candidate)


CONTROLS = {"A": controls_a, "B": controls_b, "C": controls_c}
NAMES = {
    "A": "Programme table",
    "B": "Knobs + profile overlay",
    "C": "Departure rail",
}
