"""THROWAWAY — three resolution-map panes for ticket #31, switchable with ?variant=.

Three structurally different answers to "what should this pane look and feel like":

* **A — One instrument**: everything on a single dense chart; the readout is a caption.
* **B — Answer first**: the two recommendations are cards at the top; the map is the
  evidence beneath them, split into an Rs strip and a run-time strip.
* **C — Trade-off**: Rs over run time as one two-panel figure with a feasible band
  spanning both; the recommendations leave the tab entirely and live in the left rail.

All three read the same `Sweep`, so any disagreement between them is a design
disagreement, not a data one. No tests, no error handling — this is a prototype.
"""

from __future__ import annotations

from html import escape
from typing import Any

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from app import panels
from prototype.sweep import Point, Sweep

INK = "#1f4e79"
GREY = "#c3ccd6"
CRITICAL = "#c0392b"
GOAL = "#1f9d55"
CEIL = "#7048b6"
SHADE = "rgba(120,140,165,0.13)"
DANGER = "rgba(192,57,43,0.11)"
FEASIBLE = "rgba(31,157,85,0.10)"

NAMES = {"A": "One instrument", "B": "Answer first", "C": "Trade-off"}


# --- shared scaffolding (deliberately thin — variants may throw any of it out) --------


def _zones(fig: Any, sweep: Sweep, *, row: int | None = None) -> None:
    """#30's edges: bracket lines, extrapolation shading, co-elution bands."""
    kw = {} if row is None else {"row": row, "col": 1}
    low, high = sweep.bounds
    for x0, x1 in ((low, sweep.bracket[0]), (sweep.bracket[1], high)):
        if x1 > x0:
            fig.add_vrect(x0=x0, x1=x1, fillcolor=SHADE, line_width=0, layer="below", **kw)
    for flip in sweep.flips:
        fig.add_vrect(
            x0=max(flip.zone[0], low),
            x1=min(flip.zone[1], high),
            fillcolor=DANGER,
            line_width=0,
            layer="below",
            **kw,
        )
    for edge, label in zip(sweep.bracket, ("run 1", "run 2"), strict=True):
        fig.add_vline(
            x=edge,
            line={"color": "#8fa0b4", "width": 1, "dash": "dot"},
            annotation_text=label,
            annotation_font_size=10,
            annotation_position="top",
            **kw,
        )


def _envelope(sweep: Sweep) -> tuple[list[float], list[float]]:
    return sweep.grid, [point.critical_rs for point in sweep.points]


def _sentence(point: Point, *, lead: str) -> str:
    earlier, later = point.critical_names
    return (
        f"{lead} **tG {point.t_gradient:g} min** — critical pair "
        f"**{escape(earlier)} / {escape(later)}** at **Rs {point.critical_rs:.2f}**, "
        f"run time **{point.run_time:.2f} min**."
    )


def _apply(point: Point, key: str) -> None:
    if st.button("Apply as candidate", key=key, width="stretch"):
        st.session_state["proto_apply_tg"] = point.t_gradient
        st.rerun()


def _click_to_candidate(event: Any) -> None:
    points = (event or {}).get("selection", {}).get("points", [])
    if points:
        st.session_state["proto_apply_tg"] = round(float(points[0]["x"]) * 2.0) / 2.0
        st.rerun()


# --- A: one instrument ----------------------------------------------------------------


def variant_a(sweep: Sweep, candidate_tg: float, rs_target: float, _rail: Any) -> float:
    head, target_col = st.columns([3, 1])
    with head:
        st.caption(
            "Every adjacent pair across the sweep. The critical pair is the lower "
            "envelope, drawn dark. Click the chart to move the candidate."
        )
    with target_col:
        rs_target = st.number_input("Rs target", 0.5, 5.0, rs_target, 0.1, key="proto_a_target")

    fig = go.Figure()
    _zones(fig, sweep)
    for names in sweep.pair_names:
        curve = sweep.pair_curve(names)
        fig.add_trace(
            go.Scatter(
                x=[x for x, _ in curve],
                y=[y for _, y in curve],
                mode="lines",
                line={"color": GREY, "width": 1},
                name=" / ".join(sorted(names)),
                hoverinfo="name+y",
                showlegend=False,
            )
        )
    grid, envelope = _envelope(sweep)
    fig.add_trace(
        go.Scatter(
            x=grid,
            y=envelope,
            mode="lines",
            line={"color": CRITICAL, "width": 2.6},
            name="critical pair",
            customdata=[point.critical_names for point in sweep.points],
            hovertemplate="tG %{x:.1f} min<br>Rs %{y:.2f}<br>"
            "%{customdata[0]} / %{customdata[1]}<extra></extra>",
        )
    )
    fig.add_hline(
        y=rs_target,
        line={"color": GOAL, "width": 1, "dash": "dash"},
        annotation_text=f"Rs target {rs_target:g}",
        annotation_font_size=10,
        annotation_position="bottom right",
    )
    for flip in sweep.flips:
        fig.add_annotation(
            x=flip.t_gradient,
            y=0,
            ax=0,
            ay=-26,
            text=f"✕ {flip.earlier} ⇄ {flip.later}",
            font={"size": 10, "color": CRITICAL},
            arrowcolor=CRITICAL,
            arrowsize=0.7,
        )
    goal, ceiling = sweep.goal_seek(rs_target), sweep.ceiling
    for point, colour, label in ((goal, GOAL, "fastest ≥ target"), (ceiling, CEIL, "ceiling")):
        if point is None:
            continue
        fig.add_trace(
            go.Scatter(
                x=[point.t_gradient],
                y=[point.critical_rs],
                mode="markers+text",
                marker={"size": 13, "color": colour, "symbol": "star"},
                text=[f" {label}"],
                textposition="middle right",
                textfont={"size": 10, "color": colour},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    fig.add_vline(x=candidate_tg, line={"color": INK, "width": 2})
    fig.add_trace(
        go.Scatter(
            x=[candidate_tg],
            y=[sweep.at(candidate_tg).critical_rs],
            mode="markers",
            marker={"size": 12, "color": INK, "symbol": "diamond"},
            hovertemplate="candidate<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_layout(
        height=430,
        margin={"l": 10, "r": 10, "t": 24, "b": 10},
        showlegend=False,
        plot_bgcolor="#ffffff",
        xaxis={"title": "gradient time tG (min)", "range": list(sweep.bounds)},
        yaxis={"title": "resolution Rs", "rangemode": "tozero"},
    )
    _click_to_candidate(
        st.plotly_chart(fig, width="stretch", on_select="rerun", key="proto_a_chart")
    )

    st.markdown(
        (
            _sentence(goal, lead="**Fastest that meets the target:**")
            if goal
            else f"**No swept condition reaches Rs {rs_target:g}.** "
            f"The best this sweep can do is below."
        )
        + "  \n"
        + _sentence(ceiling, lead="**Best this sweep can do:**")
    )
    left, right, _ = st.columns([1, 1, 2])
    with left:
        if goal:
            _apply(goal, "proto_a_goal")
    with right:
        _apply(ceiling, "proto_a_ceil")
    return rs_target


# --- B: answer first ------------------------------------------------------------------


def variant_b(sweep: Sweep, candidate_tg: float, rs_target: float, _rail: Any) -> float:
    goal_col, ceil_col = st.columns(2)
    with goal_col, st.container(border=True):
        st.markdown("**Fastest method that separates**")
        rs_target = st.number_input(
            "Rs target for the critical pair", 0.5, 5.0, rs_target, 0.1, key="proto_b_target"
        )
        goal = sweep.goal_seek(rs_target)
        if goal is None:
            st.markdown(f"### — \nNo swept condition reaches Rs {rs_target:g}.")
        else:
            st.markdown(f"### tG {goal.t_gradient:g} min")
            st.markdown(_sentence(goal, lead="").strip().removeprefix("—").strip())
            _apply(goal, "proto_b_goal")
    with ceil_col, st.container(border=True):
        st.markdown("**Best this sweep can do**")
        ceiling = sweep.ceiling
        st.markdown(f"### tG {ceiling.t_gradient:g} min")
        st.markdown(_sentence(ceiling, lead="").strip().removeprefix("—").strip())
        st.caption("Run time is shown, not optimised — this answer is about resolution.")
        _apply(ceiling, "proto_b_ceil")

    show_pairs = st.toggle("Show every pair, not just the critical one", key="proto_b_pairs")

    fig = go.Figure()
    _zones(fig, sweep)
    if show_pairs:
        for names in sweep.pair_names:
            curve = sweep.pair_curve(names)
            fig.add_trace(
                go.Scatter(
                    x=[x for x, _ in curve],
                    y=[y for _, y in curve],
                    mode="lines",
                    line={"color": GREY, "width": 1},
                    name=" / ".join(sorted(names)),
                    hoverinfo="name+y",
                    showlegend=False,
                )
            )
    grid, envelope = _envelope(sweep)
    fig.add_trace(
        go.Scatter(
            x=grid,
            y=envelope,
            mode="lines",
            line={"color": CRITICAL, "width": 2.4},
            customdata=[point.critical_names for point in sweep.points],
            hovertemplate="tG %{x:.1f}<br>Rs %{y:.2f}<br>"
            "%{customdata[0]} / %{customdata[1]}<extra></extra>",
        )
    )
    fig.add_hline(y=rs_target, line={"color": GOAL, "width": 1, "dash": "dash"})
    fig.add_vline(x=candidate_tg, line={"color": INK, "width": 2})
    for point, colour in ((goal, GOAL), (ceiling, CEIL)):
        if point:
            fig.add_trace(
                go.Scatter(
                    x=[point.t_gradient],
                    y=[point.critical_rs],
                    mode="markers",
                    marker={"size": 12, "color": colour, "symbol": "star"},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
    fig.update_layout(
        height=250,
        margin={"l": 10, "r": 10, "t": 8, "b": 4},
        showlegend=False,
        plot_bgcolor="#ffffff",
        xaxis={"range": list(sweep.bounds), "showticklabels": False},
        yaxis={"title": "critical Rs", "rangemode": "tozero"},
    )
    _click_to_candidate(st.plotly_chart(fig, width="stretch", on_select="rerun", key="proto_b_rs"))

    strip = go.Figure()
    _zones(strip, sweep)
    strip.add_trace(
        go.Scatter(
            x=grid,
            y=[point.run_time for point in sweep.points],
            mode="lines",
            line={"color": "#5a6a7d", "width": 2},
            hovertemplate="tG %{x:.1f}<br>run time %{y:.2f} min<extra></extra>",
        )
    )
    strip.add_vline(x=candidate_tg, line={"color": INK, "width": 2})
    for point, colour in ((goal, GOAL), (ceiling, CEIL)):
        if point:
            strip.add_trace(
                go.Scatter(
                    x=[point.t_gradient],
                    y=[point.run_time],
                    mode="markers",
                    marker={"size": 11, "color": colour, "symbol": "star"},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
    strip.update_layout(
        height=130,
        margin={"l": 10, "r": 10, "t": 4, "b": 10},
        showlegend=False,
        plot_bgcolor="#ffffff",
        xaxis={"title": "gradient time tG (min)", "range": list(sweep.bounds)},
        yaxis={"title": "run time (min)", "rangemode": "tozero"},
    )
    _click_to_candidate(
        st.plotly_chart(strip, width="stretch", on_select="rerun", key="proto_b_rt")
    )
    st.caption(
        "Grey = outside the scouting bracket (extrapolation). "
        "Red = the critical pair is below the target there. Blue line = current candidate."
    )
    return rs_target


# --- C: trade-off, with the answer in the rail ----------------------------------------


def variant_c(sweep: Sweep, candidate_tg: float, rs_target: float, rail: Any) -> float:
    rs_target = st.number_input(
        "Rs target", 0.5, 5.0, rs_target, 0.1, key="proto_c_target", width=160
    )
    goal, ceiling = sweep.goal_seek(rs_target), sweep.ceiling
    grid, envelope = _envelope(sweep)

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.62, 0.38]
    )
    for row in (1, 2):
        _zones(fig, sweep, row=row)
    # The feasible band spans both panels: "anywhere green, at the run time below".
    for span in _feasible_spans(sweep, rs_target):
        for row in (1, 2):
            fig.add_vrect(
                x0=span[0],
                x1=span[1],
                fillcolor=FEASIBLE,
                line_width=0,
                layer="below",
                row=row,
                col=1,
            )
    # The envelope is coloured by *which* pair is critical, so an identity change reads.
    for segment, names in _critical_segments(sweep):
        fig.add_trace(
            go.Scatter(
                x=[x for x, _ in segment],
                y=[y for _, y in segment],
                mode="lines",
                line={"width": 2.6},
                name=" / ".join(names),
                hovertemplate="tG %{x:.1f}<br>Rs %{y:.2f}<extra>%{fullData.name}</extra>",
            ),
            row=1,
            col=1,
        )
    fig.add_hline(
        y=rs_target,
        line={"color": GOAL, "width": 1, "dash": "dash"},
        row=1,
        col=1,
        annotation_text=f"target {rs_target:g}",
        annotation_font_size=10,
    )
    fig.add_trace(
        go.Scatter(
            x=grid,
            y=[point.run_time for point in sweep.points],
            mode="lines",
            line={"color": "#5a6a7d", "width": 2},
            showlegend=False,
            hovertemplate="tG %{x:.1f}<br>run time %{y:.2f} min<extra></extra>",
        ),
        row=2,
        col=1,
    )
    for row in (1, 2):
        fig.add_vline(x=candidate_tg, line={"color": INK, "width": 2}, row=row, col=1)
    fig.update_layout(
        height=470,
        margin={"l": 10, "r": 10, "t": 26, "b": 10},
        hovermode="x unified",
        plot_bgcolor="#ffffff",
        legend={"orientation": "h", "y": 1.12, "font": {"size": 10}, "title": "critical pair"},
    )
    fig.update_yaxes(title_text="Rs", rangemode="tozero", row=1, col=1)
    fig.update_yaxes(title_text="run time (min)", rangemode="tozero", row=2, col=1)
    fig.update_xaxes(title_text="gradient time tG (min)", range=list(sweep.bounds), row=2, col=1)
    _click_to_candidate(
        st.plotly_chart(fig, width="stretch", on_select="rerun", key="proto_c_chart")
    )
    st.caption(
        "Green = every tG whose critical pair clears the target; read its cost off the "
        "lower panel. Click either panel to set the candidate."
    )

    with rail:
        rows = [
            panels.Row("Rs target", f"{rs_target:g}"),
            panels.Row(
                "Fastest ≥ target",
                f"tG {goal.t_gradient:g} · {goal.run_time:.2f} min" if goal else "none in sweep",
                panels.resolution_colour(goal.critical_rs) if goal else None,
            ),
            panels.Row(
                "  critical there",
                " / ".join(goal.critical_names) if goal else "—",
            ),
            panels.Row("Ceiling", f"tG {ceiling.t_gradient:g} · Rs {ceiling.critical_rs:.2f}"),
            panels.Row("  critical there", " / ".join(ceiling.critical_names)),
        ]
        st.markdown(panels.panel("Optimiser", rows), unsafe_allow_html=True)
        if goal:
            _apply(goal, "proto_c_goal")
        _apply(ceiling, "proto_c_ceil")
    return rs_target


def _feasible_spans(sweep: Sweep, rs_target: float) -> list[tuple[float, float]]:
    spans, start = [], None
    for point in sweep.points:
        if point.critical_rs >= rs_target and start is None:
            start = point.t_gradient
        elif point.critical_rs < rs_target and start is not None:
            spans.append((start, point.t_gradient))
            start = None
    if start is not None:
        spans.append((start, sweep.bounds[1]))
    return spans


def _critical_segments(sweep: Sweep) -> list[tuple[list[tuple[float, float]], tuple[str, str]]]:
    """The envelope cut wherever the critical pair's identity changes."""
    out: list[tuple[list[tuple[float, float]], tuple[str, str]]] = []
    current: list[tuple[float, float]] = []
    names: tuple[str, str] | None = None
    for point in sweep.points:
        here = tuple(sorted(point.critical_names))
        if names is not None and here != names:
            current.append((point.t_gradient, point.critical_rs))
            out.append((current, names))
            current = []
        names = here  # type: ignore[assignment]
        current.append((point.t_gradient, point.critical_rs))
    if current and names:
        out.append((current, names))
    return out


VARIANTS = {"A": variant_a, "B": variant_b, "C": variant_c}
