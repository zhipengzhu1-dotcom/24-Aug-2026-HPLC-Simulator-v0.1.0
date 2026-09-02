"""THROWAWAY entry point for ticket #31's map pane — the switcher and its plumbing.

Sub-shape A of the prototype skill: the variants render *inside* the real Cockpit's
Resolution map tab, with the real rail, the real chromatogram and the real fit beneath
them. A variant that only looks good in an empty route is not evidence.

`?variant=A|B|C` picks the pane; `?data=eight|lab|own` picks what is loaded.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from hplcsim.model import Gradient
from prototype import demo_data
from prototype.sweep import Sweep, run_sweep
from prototype.variants import NAMES, VARIANTS

ORDER = ["A", "B", "C"]
DATASETS = {
    "eight": "Eight peaks (invented compounds, engine-computed)",
    "lab": "Lab runs 1+2 (validation/, three peaks)",
    "own": "Whatever is typed in",
}


def current_variant() -> str:
    return st.query_params.get("variant", "A").upper()[:1] or "A"


def current_dataset() -> str:
    return st.query_params.get("data", "eight")


def wanted_demo() -> str | None:
    """The demo session to force-load, or None if the screen's own entry stands."""
    key = current_dataset()
    if key == "own" or st.session_state.get("proto_loaded") == key:
        return None
    return key


def mark_loaded() -> None:
    st.session_state["proto_loaded"] = current_dataset()


def demo_session(key: str) -> Any:
    return demo_data.lab() if key == "lab" else demo_data.eight_peak()


def pending_candidate() -> float | None:
    """A tG a variant asked for — applied by the entry point, which owns the widget."""
    return st.session_state.pop("proto_apply_tg", None)


def render(
    *,
    cockpit: Any,
    method: Any,
    tg1: float,
    tg2: float,
    candidate: Gradient,
    plate_count: float | None,
    slider: tuple[float, float],
    rail: Any,
) -> None:
    banner()
    if not cockpit.fitted:
        st.info("Nothing fitted yet — the map needs at least two peaks fitted from both runs.")
        return

    # The target is read off the variant's own widget *before* the sweep, so the
    # co-elution zones the sweep computes match the number on screen this run
    # rather than lagging it by one.
    variant = current_variant()
    rs_target = float(st.session_state.get(f"proto_{variant.lower()}_target", 1.5))
    sweep = _sweep(cockpit, method, tg1, tg2, candidate, plate_count, rs_target, slider)
    VARIANTS[variant](sweep, candidate.t_gradient, rs_target, rail)
    _footnotes(sweep)


def _sweep(
    cockpit: Any,
    method: Any,
    tg1: float,
    tg2: float,
    candidate: Gradient,
    plate_count: float | None,
    rs_target: float,
    slider: tuple[float, float],
) -> Sweep:
    fitted = [(peak, fit.params, fit.plate_count) for peak, fit in cockpit.fitted]
    return run_sweep(
        fitted,
        method,
        tg1=tg1,
        tg2=tg2,
        candidate=candidate,
        hold=candidate.t_init,
        plate_count=plate_count,
        rs_target=rs_target,
        slider=slider,
    )


def _footnotes(sweep: Sweep) -> None:
    notes = []
    if sweep.clipped_low or sweep.clipped_high:
        notes.append("The sweep was clipped to the candidate slider's range.")
    for flip in sweep.flips:
        notes.append(
            f"Order flip at tG {flip.t_gradient:.2f} min: {flip.earlier} ⇄ {flip.later} "
            f"(below target from {flip.zone[0]:.1f} to {flip.zone[1]:.1f} min)."
        )
    if notes:
        st.caption("  \n".join(notes))


def banner() -> None:
    variant = current_variant()
    st.markdown(
        f"<div style='background:#2b2f36;color:#fff;padding:6px 10px;border-radius:6px;"
        f"font:600 12px/1.4 system-ui;margin-bottom:8px'>PROTOTYPE #31 · variant "
        f"{variant} — {NAMES.get(variant, '?')} · not shippable code</div>",
        unsafe_allow_html=True,
    )


def switcher() -> None:
    """The floating bar. Sidebar-footed rather than fixed: Streamlit has no z-layer."""
    with st.sidebar:
        st.divider()
        st.markdown("**PROTOTYPE #31 — resolution map**")
        back, label, forward = st.columns([1, 3, 1])
        index = ORDER.index(current_variant()) if current_variant() in ORDER else 0
        with back:
            if st.button("←", key="proto_prev", width="stretch"):
                _go(ORDER[(index - 1) % len(ORDER)])
        with label:
            st.markdown(
                f"<div style='text-align:center;font:600 13px/2 system-ui'>"
                f"{ORDER[index]} — {NAMES[ORDER[index]]}</div>",
                unsafe_allow_html=True,
            )
        with forward:
            if st.button("→", key="proto_next", width="stretch"):
                _go(ORDER[(index + 1) % len(ORDER)])
        choice = st.radio(
            "Demo data",
            list(DATASETS),
            key="proto_data_pick",
            index=list(DATASETS).index(current_dataset()) if current_dataset() in DATASETS else 0,
            format_func=lambda key: DATASETS[key],
        )
        if choice != current_dataset():
            st.query_params["data"] = choice
            st.rerun()
        st.caption("Shareable: ?variant=A|B|C&data=eight|lab|own")


def _go(variant: str) -> None:
    st.query_params["variant"] = variant
    st.rerun()
