"""THROWAWAY entry point for ticket #45 — the switcher and every hook into the Cockpit.

Sub-shape A of the prototype skill: the variants render *inside* the real Cockpit — the
real sidebar, the real fit, the real chromatogram beneath. `?variant=A|B|C` picks the
rail; `?data=lab|v2|own` picks what is loaded.

Every hook here is called from a hunk in `streamlit_app.py` commented `PROTOTYPE #45`.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pandas as pd
import streamlit as st

from app import tables
from app.diagnostics import Diagnostics
from app.panels import Row
from app.pipeline import Cockpit, CockpitInputs
from hplcsim.model import Run
from hplcsim.resolution import AdjacentPair, PredictedPeak, ResolutionTable, _resolution
from prototype import demo_data, diag, programme as prog, variants
from prototype.programme import Programme
from prototype.variants import NAMES, RailContext

ORDER = ["A", "B", "C", "D"]
DATASETS = {
    "lab": "validation/ runs 1+2 (three peaks)",
    "v2": "Validation_2 runs 1+2 (four peaks, near-critical pair)",
    "own": "Whatever is typed in",
}

# The badge label for the one new per-peak code, so the table of peaks can name it.
tables._BADGE_LABEL["low_k0"] = "low k0 at φ0"  # type: ignore[index]


class _Ctx:
    """Per-run stash: what the hooks downstream of the rail need to know."""

    programme: Programme | None = None
    rail: RailContext | None = None
    comp: diag.Composition | None = None
    cockpit: Cockpit | None = None


CTX = _Ctx()


# --- query params and the switcher ------------------------------------------------------


def current_variant() -> str:
    v = st.query_params.get("variant", "A").upper()[:1]
    return v if v in ORDER else "A"


def _default_dataset() -> str:
    # The screen tests type their own peaks in; a demo autoload would pre-empt them.
    import os

    return "own" if "PYTEST_CURRENT_TEST" in os.environ else "lab"


def current_dataset() -> str:
    d = st.query_params.get("data", _default_dataset())
    return d if d in DATASETS else _default_dataset()


def wanted_demo() -> str | None:
    key = current_dataset()
    if key == "own" or st.session_state.get("p45_loaded") == key:
        return None
    return key


def mark_loaded() -> None:
    st.session_state["p45_loaded"] = current_dataset()


def demo_session(key: str) -> Any:
    return demo_data.v2() if key == "v2" else demo_data.lab()


def scouting_in_rail() -> bool:
    """Variants B and D move the scouting %B / hold out of the sidebar into the rail."""
    return current_variant() in ("B", "D")


def switcher() -> None:
    st.session_state.setdefault("p45_variant", current_variant())
    st.session_state.setdefault("p45_data", current_dataset())

    def _sync() -> None:
        st.query_params["variant"] = st.session_state["p45_variant"]
        st.query_params["data"] = st.session_state["p45_data"]

    with st.sidebar:
        st.divider()
        st.markdown("**PROTOTYPE #45** — how the candidate's φ range enters the Cockpit")
        st.radio(
            "Variant", ORDER, key="p45_variant", on_change=_sync,
            format_func=lambda k: f"{k} — {NAMES[k]}",
        )
        st.selectbox(
            "Data", list(DATASETS), key="p45_data", on_change=_sync, format_func=DATASETS.get
        )
        st.caption("Throwaway. Nothing here is in SPEC; the decision carries forward, not the code.")


# --- the rail -----------------------------------------------------------------------------


def scouting_runs(ctx: RailContext, fallback: Any) -> tuple[Run, Run]:
    CTX.rail = ctx
    if current_variant() in ("B", "D"):
        runs = variants.scouting_b(ctx)
    else:
        runs = fallback(ctx.constants)
    ctx.run1, ctx.run2 = runs
    return runs


def candidate_controls(ctx: RailContext) -> Programme:
    v = current_variant()
    programme = {"A": variants.rail_a, "B": variants.rail_b, "C": variants.rail_c, "D": variants.rail_b}[v](ctx)
    CTX.programme = programme
    CTX.rail = ctx
    return programme


def rail_extras(cockpit: Cockpit) -> None:
    """Below the candidate's inline warnings, above the summary panels."""
    if current_variant() == "A" and CTX.programme is not None and CTX.rail is not None:
        variants.extras_a(CTX.programme, CTX.rail, cockpit, CTX.comp)


# --- prediction and diagnostics -------------------------------------------------------------


def repredict(cockpit: Cockpit, inputs: CockpitInputs) -> Cockpit:
    """Multi-segment: replace the engine's envelope prediction with the piecewise one."""
    CTX.cockpit = cockpit
    programme = CTX.programme
    if programme is None or programme.is_single or cockpit.resolution is None:
        return cockpit
    predicted = []
    for peak, fit in cockpit.fitted:
        e = prog.elute(fit.params, inputs.method, programme)
        w = prog.width(fit.params, inputs.method, programme,
                       fit.plate_count if fit.plate_count is not None else inputs.plate_count)
        predicted.append(PredictedPeak(name=peak.name, retention=e.retention, width=w))
    predicted.sort(key=lambda p: p.retention.t_r)
    pairs = tuple(
        AdjacentPair(earlier=a, later=b, rs=_resolution(a, b))
        for a, b in zip(predicted, predicted[1:], strict=False)
    )
    replaced = dataclasses.replace(cockpit, resolution=ResolutionTable(tuple(predicted), pairs))
    CTX.cockpit = replaced
    return replaced


def rediagnose(diagnostics: Diagnostics, cockpit: Cockpit, inputs: CockpitInputs) -> Diagnostics:
    """Swap diagnostic 1 for its s* form, add diagnostic 7 and the low-k0 badges."""
    programme = CTX.programme
    if programme is None or cockpit.blocked is not None:
        CTX.comp = None
        return diagnostics
    comp = diag.compose(cockpit, inputs.method, inputs.run1, inputs.run2, programme)
    CTX.comp = comp
    badges = dict(diagnostics.badges)
    for name, badge in comp.low_k0.items():
        badges[name] = (*badges.get(name, ()), badge)
    return dataclasses.replace(diagnostics, candidate=comp.candidate, badges=badges)


# --- output surfaces ------------------------------------------------------------------------


def title_text(fallback: str) -> str:
    return CTX.programme.describe() if CTX.programme is not None else fallback


def status_fields(fields: list[str], *, rs_text: str | None) -> list[str]:
    p = CTX.programme
    comp = CTX.comp
    if p is None:
        return fields
    out = [p.describe()]
    if rs_text is not None:
        out.append(rs_text + (" (indicative)" if comp is not None and comp.stamp else ""))
    n = len(p.segments)
    out.append(f"RP gradient — {n} linear segment{'s' if n != 1 else ''}"
               + ("" if n == 1 else " (prototype arithmetic)"))
    return out


def summary_rows(rows: list[Row]) -> list[Row]:
    comp = CTX.comp
    if comp is None:
        return rows
    out: list[Row] = []
    for row in rows:
        if row.label == "Min. Rs" and comp.stamp:
            out.append(Row(row.label, f"{row.value} · indicative", "#c77700"))
        else:
            out.append(row)
    if comp.stamp:
        out.append(Row("Rs standing", "indicative — not decision-grade", "#c77700"))
    elif comp.downgraded:
        out.append(Row("Rs standing", f"indicative for pairs with {', '.join(comp.downgraded)}", "#c77700"))
    return out


def stamp_caption() -> None:
    comp = CTX.comp
    if comp is not None and comp.stamp:
        st.caption("⚠️ " + comp.stamp)
    elif comp is not None and comp.downgraded:
        st.caption(
            "⚠️ Low k0 at the candidate start for "
            + ", ".join(comp.downgraded)
            + " — Rs on that peak's pairs is indicative only."
        )


def fit_tab_readout() -> None:
    comp = CTX.comp
    if comp is None or not comp.rows:
        return
    st.markdown("**Calibrated composition windows** — where each peak's retention line was pinned, and where this candidate puts it")
    rows = []
    for r in comp.rows:
        if r.regime == "post_gradient":
            standing = "elutes after the ramp, at φf"
        elif r.regime == "isocratic_hold":
            standing = "elutes during the hold"
        elif r.outside_pct == 0.0:
            standing = "inside"
        else:
            side = "above" if r.outside_pct > 0 else "below"
            standing = f"{abs(r.outside_pct):.1f} %B {side} ({r.outside_ww:.2f} window-widths)"
        seg = "" if r.segment is None else f"segment {r.segment + 1}"
        rows.append({
            "Compound": r.name,
            "Window (%B)": f"{r.lo_pct:.1f} – {r.hi_pct:.1f}",
            "Width (%B)": round(r.width_pct, 1),
            "Candidate φe (%B)": round(r.phi_e_pct, 1),
            "Standing": standing,
            "In": seg,
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption(
        "Window = the compositions this peak eluted at in the two scouting runs; width = ln β / S_e. "
        "The tier at the candidate controls is the overshoot in window-widths, the same for every peak "
        "because S_e cancels (#44). Numbers provisional until #55."
    )


def decorate_chromatogram(fig: Any, cockpit: Cockpit) -> Any:
    if current_variant() in ("C", "D") and CTX.programme is not None and CTX.rail is not None:
        return variants.decorate_c(fig, CTX.programme, CTX.rail, cockpit, CTX.comp)
    return fig
