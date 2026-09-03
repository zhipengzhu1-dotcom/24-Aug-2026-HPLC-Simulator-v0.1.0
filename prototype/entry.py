"""THROWAWAY entry point for ticket #45 — the switcher and the plumbing into the Cockpit.

Sub-shape A of the prototype skill: the variants render *inside* the real Cockpit's left
rail, with the real sidebar, tabs, chromatogram and fit around them. A candidate block
that only looks right in an empty route is not evidence.

`?variant=A|B|C` picks the rail (absent = the v0.1 rail, untouched, so every test that
drives the entry point stays green); `?data=lab|v2|own` picks what is loaded;
`?b0=&b1=&tg=` seed the candidate on a demo load.

Everything the four #44 surfaces need is computed once per rerun by
:func:`amend` and stashed in ``session_state`` — the hooks that paint it later in the
render order (summary rows, fit columns, overlay, status cells) read it from there.
That is a prototype shortcut, not a shape to keep.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from app import tables
from app.diagnostics import Diagnostic, Diagnostics
from app.panels import Row
from app.pipeline import Cockpit, CockpitInputs, MethodEntry
from hplcsim.model import Gradient, Run, percent_b_from_phi
from hplcsim.session import Session, load_session
from prototype import composition as comp
from prototype import variants
from prototype.variants import NAMES, NONCE, Plumbing  # noqa: F401 — re-exported

ROOT = Path(__file__).resolve().parent.parent
ORDER = ["off", "A", "B", "C"]
DATASETS = {
    "own": "Whatever is typed in",
    "lab": "validation/ — three peaks, Rs 30–116",
    "v2": "Validation_2 — four peaks in 0.5 min, Rs 1.75",
}
_PATHS = {
    "lab": ROOT / "validation" / "sticky-check.json",
    "v2": ROOT / "validation" / "Validation_2" / "sticky-check.json",
}
_ANALYSIS = "proto_analysis"

# The badge label map lives in app/tables.py and is keyed by Diagnostic.code; the new
# code would otherwise print raw in the Flags column. A throwaway reach-in, not a shape.
tables._BADGE_LABEL["low_k0"] = "low k0 at start"  # type: ignore[index]
_LOADED = "proto_loaded"


# --- query params ---------------------------------------------------------------------


def variant() -> str | None:
    value = str(st.query_params.get("variant", "")).upper()[:1]
    return value if value in ("A", "B", "C") else None


def active() -> bool:
    return variant() is not None


def dataset() -> str:
    value = str(st.query_params.get("data", "own"))
    return value if value in DATASETS else "own"


def wanted_demo() -> Session | None:
    key = dataset()
    if key == "own" or st.session_state.get(_LOADED) == key:
        return None
    return load_session(_PATHS[key].read_bytes())


def mark_loaded() -> None:
    st.session_state[_LOADED] = dataset()
    st.session_state[NONCE] = variants.nonce() + 1
    for name, key in (("b0", variants.B0_KEY), ("b1", variants.B1_KEY)):
        value = st.query_params.get(name)
        if value is not None:
            st.session_state[f"{key}_apply"] = float(value)
    tg = st.query_params.get("tg")
    if tg is not None:
        st.session_state["proto_apply_tg"] = float(tg)


def pending_candidate() -> float | None:
    return st.session_state.pop("proto_apply_tg", None)


# --- the switcher ---------------------------------------------------------------------


def switcher() -> None:
    current = variant() or "off"

    def _pick_variant() -> None:
        chosen = st.session_state["proto_variant_radio"]
        if chosen == "off":
            st.query_params.pop("variant", None)
        else:
            st.query_params["variant"] = chosen
        st.session_state[NONCE] = variants.nonce() + 1

    def _pick_data() -> None:
        st.query_params["data"] = st.session_state["proto_data_radio"]

    with st.sidebar:
        st.markdown("---")
        st.markdown("**PROTOTYPE #45** — candidate φ range")
        st.radio(
            "Variant",
            ORDER,
            index=ORDER.index(current),
            horizontal=True,
            key="proto_variant_radio",
            on_change=_pick_variant,
            captions=[""] + [NAMES[v] for v in ORDER[1:]],
        )
        st.radio(
            "Data",
            list(DATASETS),
            index=list(DATASETS).index(dataset()),
            key="proto_data_radio",
            on_change=_pick_data,
            format_func=lambda k: DATASETS[k],
        )
        if current != "off":
            st.caption(f"{current} — {NAMES[current]}")


# --- the rail -------------------------------------------------------------------------


def candidate_controls(constants: MethodEntry, plumb: Plumbing, runs: Sequence[Run]) -> Gradient:
    return variants.CONTROLS[variant() or "A"](constants, plumb, runs)


# --- the four #44 surfaces --------------------------------------------------------------


def amend(diagnostics: Diagnostics, inputs: CockpitInputs, cockpit: Cockpit) -> Diagnostics:
    """Replace diagnostic 1's tG bracket with the s* one, add 7 and the low-k0 badge."""
    if not active():
        st.session_state.pop(_ANALYSIS, None)
        return diagnostics
    analysis = comp.analyse(inputs, cockpit)
    st.session_state[_ANALYSIS] = analysis
    if analysis is None:
        return diagnostics
    badges = {
        name: (*found, *(() if name not in analysis.low_k0 else (analysis.low_k0[name],)))
        for name, found in diagnostics.badges.items()
    }
    return replace(diagnostics, candidate=analysis.candidate_diagnostics, badges=badges)


def _analysis() -> comp.Analysis | None:
    return st.session_state.get(_ANALYSIS) if active() else None


def candidate_notices(
    diagnostics: Diagnostics,
    paint: Callable[[Sequence[Diagnostic]], None],
    *,
    constants: MethodEntry,
    candidate: Gradient,
) -> None:
    if variant() == "C":
        variants.notices_c(
            diagnostics.candidate,
            _analysis(),
            constants=constants,
            candidate=candidate,
            paint=paint,
        )
        return
    paint(diagnostics.candidate)


def summary_rows() -> list[Row]:
    analysis = _analysis()
    if analysis is None:
        return []
    rows = []
    if analysis.window_widths > 0:
        rows.append(Row("s* outside", f"{analysis.window_widths:.2f} window-widths", "#c77700"))
    if analysis.stamp:
        rows.append(Row("Rs standing", "indicative — not decision-grade", "#c0392b"))
    return rows


def fit_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Unchanged — the readout is its own table beneath (the columns ran off the tab)."""
    return frame


def window_frame() -> pd.DataFrame | None:
    """One readout row per peak: window, width, where the candidate puts the peak."""
    analysis = _analysis()
    if analysis is None or not analysis.windows:
        return None
    pct = percent_b_from_phi
    return pd.DataFrame(
        [
            {
                "Compound": w.name,
                "Window (%B)": f"{pct(w.lo):.1f}–{pct(w.hi):.1f}",
                "Width (%B)": round(pct(w.width), 1),
                "At candidate (%B)": round(pct(w.at_candidate), 1),
                "Standing": w.standing,
            }
            for w in analysis.windows
        ]
    )


def fit_caption() -> str | None:
    analysis = _analysis()
    if analysis is None:
        return None
    outside = [w.name for w in analysis.windows if w.distance != 0.0]
    if not outside:
        return "Every peak elutes inside its calibrated composition window at this candidate."
    return (
        f"Outside their calibrated windows at this candidate: {', '.join(outside)}. "
        "The window is [φe,run2, φe,run1]; its width is ln β / S_e."
    )


def overlay(fig: Any, inputs: CockpitInputs, cockpit: Cockpit, view: Any) -> None:
    if variant() != "B" or cockpit.resolution is None:
        return
    variants.overlay_b(
        fig,
        method=inputs.method,
        runs=(inputs.run1, inputs.run2),
        candidate=inputs.candidate,
        analysis=_analysis(),
        apex_times={p.name: p.retention.t_r for p in cockpit.resolution.peaks},
        x_end=view.x_range[1],
    )


def status_fields() -> list[str]:
    analysis = _analysis()
    if analysis is None:
        return []
    fields = []
    if analysis.window_widths > 0:
        fields.append(f"s* {analysis.s_cand:.4f} — {analysis.window_widths:.2f} ww outside")
    else:
        fields.append(f"s* {analysis.s_cand:.4f} — in bracket")
    if analysis.departure is not None:
        fields.append(
            "Δφ0 " + analysis.departure.message.split("**")[1].split(",")[1].strip().rstrip(".")
        )
    if analysis.stamp:
        fields.append("Rs indicative — not decision-grade")
    return fields


def stamp_caption() -> str | None:
    analysis = _analysis()
    return None if analysis is None else analysis.stamp
