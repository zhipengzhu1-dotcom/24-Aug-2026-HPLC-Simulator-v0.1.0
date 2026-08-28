"""The Cockpit (SPEC §7): entry to fit to prediction, live — ticket #19.

Run it with::

    uv run --extra app streamlit run streamlit_app.py

It sits at the repo root on purpose. Streamlit puts the *script's own folder* on
``sys.path`` — not the working directory — so an entry point inside ``app/`` cannot
import ``app.pipeline`` at all. Keeping it here is what makes the documented command
work with no ``PYTHONPATH`` and no ``sys.path`` surgery.

Only widgets and layout live here. Every number on screen is computed by
:func:`app.pipeline.run_cockpit` and shaped by :mod:`app.tables`, so the whole path
can be exercised without a browser (``tests/test_app.py``) and ticket #20's
diagnostics have a logic layer to attach to.

Layout follows the instrument software this tool sits beside (DryLab and its
relatives), at the driver's direction: a narrow left rail carrying the condition and
its summary, a tabbed main view with the resolution map first, the chromatogram pinned
underneath, and a status bar at the foot. SPEC §7 still describes the earlier prototype
layout, so it needs amending — the diff is with the driver.

Panels are filled out of render order. Streamlit containers are reserved first and
written into later, which is how the left rail can summarise a fit that the peak table
on the right has not yet been rendered to produce.

Scope: the guided empty state and the sticky chromatogram are ticket #21's, and five
of SPEC §6's six diagnostics are ticket #20's. Diagnostic 5's banner is here because
SPEC §6 assigns its wording to this ticket and this is what first puts widths and Rs
on screen.
"""

from __future__ import annotations

import streamlit as st

from app import chromatogram, panels, tables
from app.panels import Row
from app.pipeline import (
    Cockpit,
    CockpitInputs,
    MethodEntry,
    PeakRow,
    dwell_from_volume,
    run_cockpit,
)
from hplcsim.model import (
    Gradient,
    Method,
    Run,
    log10_k0_from_ln_k0,
    percent_b_from_phi,
    s_base10_from_s_e,
)
from hplcsim.width import default_plate_count

# The driver's Acquity H-Class / CORTECS 2.1×100 method (validation/method.csv). SPEC §1
# scopes v0.1 to a single user locally, so the number inputs open on that user's real
# instrument rather than on a textbook column; the peak table still opens empty.
_COLUMN_LENGTH_MM = 100.0
_COLUMN_ID_MM = 2.1
_PARTICLE_UM = 1.6
_FLOW = 0.4
_TEMPERATURE_C = 45.0
_T0 = 0.6
_PERCENT_B_START = 5.0
_PERCENT_B_END = 95.0
_HOLD = 0.5
_TG_RUN1 = 15.0
_TG_RUN2 = 45.0
_TG_CANDIDATE = 25.0
_PLATE_COUNT = 12_000.0

_MAX_CANDIDATE_TG = 180.0
_MAX_CANDIDATE_HOLD = 20.0

_MEASURED = "Measured marker"
_BY_VOLUME = "Volume (mL)"

_DWELL_REQUIRED = (
    "**Enter the dwell before anything can be predicted.** It belongs to the instrument, "
    "not to the method, and there is no sensible default to guess: a dwell that is wrong "
    "by a minute moves every predicted retention time by a minute, in the same direction, "
    "and the fit cannot see the error. The sidebar takes it as a volume or as a time."
)

# validation/PROTOCOL.md §1, which is how this repo's own dwell should have been obtained
# — method.csv records it as "from instrument spec sheet, NOT measured".
_DWELL_GUIDANCE = """\
Replace the column with a zero-dead-volume union, then:

1. A = water; B = water + ~0.1% acetone. Detector ~265 nm.
2. Program a sharp linear gradient 0 → 100 %B at your normal flow.
3. **t_D** = the time from gradient start to the **midpoint** of the absorbance rise.
4. **V_D** = t_D × F.

A spec-sheet figure is a starting point, not a measurement — dwell volume belongs to the
instrument as plumbed, and it is worth about 1% of systematic bias when it is wrong.
"""

# SPEC §6 diagnostic 5. Scoped to peaks whose N is the column estimate, per the amended
# wording of that section; the numbers are research docs `gradient-elution-math.md` §6
# and `plate-count-from-widths.md` §0.2. Wording is this ticket's.
_DIAGNOSTIC_5 = (
    "**Widths and resolution below rest on a column estimate of N for {names}.** Those "
    "peaks carry no measured W½, so their plate count is column geometry — not this "
    "instrument's efficiency. Against the validation dataset that estimate draws peaks "
    "at 0.69–0.92× their measured width and reads resolution 18–39% high, where an N "
    "fitted from a peak's own scouting widths lands at 0.99–1.16× and −4 to −10%. Enter "
    "a W½ for a peak in either scouting run to have its N fitted. The **critical pair is "
    "identified correctly either way**; it is the absolute Rs that is optimistic."
)


def main() -> None:
    st.set_page_config(page_title="hplcsim — Cockpit", layout="wide")
    st.markdown(panels.STYLE, unsafe_allow_html=True)
    constants = _sidebar()

    # SPEC §4 makes the dwell required with no silent default: it belongs to the
    # instrument, a guessed one biases every prediction the same way, and this is the
    # one constant the spec singles out. So nothing is predicted until it is entered.
    if constants is None:
        st.title("hplcsim")
        st.warning(_DWELL_REQUIRED, icon="⚠️")
        return

    rail, main_view = st.columns([1.15, 3.0], gap="medium")

    with rail:
        run1, run2 = _scouting_runs(constants)
        candidate = _candidate_controls(constants)
        summary_slot = st.container()

    with main_view:
        map_tab, peaks_tab, fit_tab, resolution_tab = st.tabs(
            ["Resolution map", "Table of peaks", "Fit parameters", "Resolution"]
        )
        with peaks_tab:
            rows = _peak_table()
        chromatogram_slot = st.container()

    cockpit = run_cockpit(
        CockpitInputs(
            method=constants.method,
            run1=run1,
            run2=run2,
            candidate=candidate,
            rows=tuple(rows),
            plate_count=constants.plate_count,
        )
    )

    with summary_slot:
        _summary_panels(cockpit)
    with peaks_tab:
        _entry_notes(cockpit)
    with map_tab:
        _resolution_map(candidate)
    with fit_tab:
        _fit_tab(cockpit)
    with resolution_tab:
        _resolution_tab(cockpit)
    with chromatogram_slot:
        _chromatogram(cockpit, candidate)

    _status_bar(cockpit, candidate)


# --- sidebar: the method constants of SPEC §4 -----------------------------------------


def _sidebar() -> MethodEntry | None:
    """The method constants, or ``None`` while the required dwell is still unset."""
    with st.sidebar:
        st.header("Method constants")
        st.caption("Shared by both scouting runs and by the candidate.")

        length = st.number_input("Column length (mm)", 1.0, 1000.0, _COLUMN_LENGTH_MM)
        column_id = st.number_input("Column i.d. (mm)", 0.05, 50.0, _COLUMN_ID_MM)
        particle = st.number_input("Particle size (µm)", 0.5, 50.0, _PARTICLE_UM)
        flow = st.number_input("Flow F (mL/min)", 0.001, 20.0, _FLOW, step=0.05, format="%.3f")
        temperature = st.number_input("Temperature (°C)", -20.0, 200.0, _TEMPERATURE_C)
        st.caption("Temperature is metadata in v0.1 — the model is fixed-temperature.")

        st.subheader("Dead time")
        t0_source = st.radio("t0 source", [_MEASURED, "Geometry estimate"], horizontal=True)
        t0 = st.number_input("t0 (min)", 0.001, 100.0, _T0, step=0.05, format="%.4f")
        if t0_source != _MEASURED:
            st.caption(
                "Enter the t0 you estimated from the column geometry — the app does not "
                "compute one. Predictions from an estimated t0 are stamped "
                "lower-confidence (SPEC §6 diagnostic 6)."
            )

        st.subheader("Dwell")
        t_dwell = _dwell(flow)
        if t_dwell is None:
            return None

        st.subheader("Gradient")
        percent_b_start = st.number_input("%B start", 0.0, 100.0, _PERCENT_B_START)
        percent_b_end = st.number_input("%B end", 0.0, 100.0, _PERCENT_B_END)
        hold = st.number_input("Initial hold (min)", 0.0, 60.0, _HOLD, step=0.1)

        method = Method(
            t0=t0,
            t_dwell=t_dwell,
            flow=flow,
            column_length_mm=length,
            column_id_mm=column_id,
            particle_um=particle,
            temperature_c=temperature,
            t0_is_measured=t0_source == _MEASURED,
        )

        st.subheader("Plate count N")
        plate_count = _plate_count_knob(method)

    return MethodEntry(
        method=method,
        percent_b_start=percent_b_start,
        percent_b_end=percent_b_end,
        hold=hold,
        plate_count=plate_count,
    )


def _dwell(flow: float) -> float | None:
    """t_D directly, or V_D ÷ F — ``None`` until one of the two is entered.

    The only constant that opens empty. SPEC §4: "Dwell | required, no silent default;
    entered as t_D (min) or V_D (mL, ÷F); in-app measurement guidance."
    """
    entered_as = st.radio("Dwell entered as", [_BY_VOLUME, "Time (min)"], horizontal=True)
    if entered_as != _BY_VOLUME:
        return st.number_input("Dwell time t_D (min)", 0.0, 100.0, value=None, format="%.4f")

    volume = st.number_input("Dwell volume V_D (mL)", 0.0, 100.0, value=None, format="%.4f")
    with st.expander("How to measure V_D"):
        st.markdown(_DWELL_GUIDANCE)
    if volume is None:
        return None
    t_dwell = dwell_from_volume(volume, flow)
    st.caption(f"t_D = V_D / F = {t_dwell:.4f} min")
    return t_dwell


def _plate_count_knob(method: Method) -> float | None:
    """The global N, or ``None`` to fall through to the column estimate (SPEC §4).

    Measured-first either way: a peak carrying its own W½ has N fitted from it and never
    reaches this knob (SPEC §3, ticket #23).
    """
    estimate = default_plate_count(method)
    if st.checkbox(f"Use the column estimate (N ≈ {estimate:,.0f})", value=True):
        st.caption("N = L/(2·dp) — geometry, not this instrument's real efficiency.")
        return None
    return st.number_input("Plate count N", 100.0, 1_000_000.0, _PLATE_COUNT, step=500.0)


# --- entry ----------------------------------------------------------------------------


def _peak_table() -> list[PeakRow]:
    st.subheader("Peak table")
    st.caption(
        "One row per compound, both runs side by side — you pair the peaks as you type. "
        "Name, areas and W½ are optional; a W½ has its peak's plate count fitted from it."
    )
    three_decimals = st.column_config.NumberColumn(format="%.3f")
    edited = st.data_editor(
        tables.blank_peak_frame(),
        key="peak_table",
        num_rows="dynamic",
        width="stretch",
        column_config={
            tables.COMPOUND: st.column_config.TextColumn(width="medium"),
            tables.TR_RUN1: three_decimals,
            tables.TR_RUN2: three_decimals,
            tables.W_HALF_RUN1: three_decimals,
            tables.W_HALF_RUN2: three_decimals,
        },
    )
    return tables.peak_rows_from_frame(edited)


def _entry_notes(cockpit: Cockpit) -> None:
    """The count SPEC §5 asks for, beside the rows it counts."""
    untracked = cockpit.entry.untracked
    if untracked:
        names = ", ".join(row.name for row in untracked)
        st.info(
            f"**{len(untracked)} untracked — not fitted** ({names}). A row needs a tR in "
            "both runs before it can be fitted, predicted or resolved."
        )
    if cockpit.blocked is not None:
        st.error(cockpit.blocked)


# --- the left rail: the condition, and what it comes to -------------------------------


def _scouting_runs(constants: MethodEntry) -> tuple[Run, Run]:
    st.markdown("### Scouting runs")
    left, right = st.columns(2)
    t_gradient1 = left.number_input("Run 1 tG", 0.1, 600.0, _TG_RUN1, step=0.5)
    t_gradient2 = right.number_input("Run 2 tG", 0.1, 600.0, _TG_RUN2, step=0.5)
    return (
        Run(constants.gradient(t_gradient1), name=f"tG{t_gradient1:g}"),
        Run(constants.gradient(t_gradient2), name=f"tG{t_gradient2:g}"),
    )


def _candidate_controls(constants: MethodEntry) -> Gradient:
    st.markdown("### Candidate")
    t_gradient = st.slider("tG (min)", 1.0, _MAX_CANDIDATE_TG, _TG_CANDIDATE, step=0.5)
    hold = st.slider(
        "Initial hold (min)",
        0.0,
        _MAX_CANDIDATE_HOLD,
        min(constants.hold, _MAX_CANDIDATE_HOLD),
        step=0.05,
    )
    return constants.gradient(t_gradient, hold=hold)


def _summary_panels(cockpit: Cockpit) -> None:
    """What the condition on screen comes to, and then one peak in detail."""
    if cockpit.blocked is not None:
        st.error(cockpit.blocked)
        return
    st.markdown(panels.panel("Method summary", _summary_rows(cockpit)), unsafe_allow_html=True)
    _peak_detail(cockpit)


def _summary_rows(cockpit: Cockpit) -> list[Row]:
    resolution = cockpit.resolution
    if resolution is None or not resolution.peaks:
        return []

    rows = [Row("Peaks fitted", str(len(resolution.peaks)))]
    if cockpit.entry.untracked_count:
        rows.append(Row("Untracked", str(cockpit.entry.untracked_count), colour="#c77700"))

    critical = resolution.critical_pair
    if critical is not None:
        rows += [
            Row("Min. Rs", f"{critical.rs:.2f}", panels.resolution_colour(critical.rs)),
            Row("Critical pair", f"{critical.earlier.name} / {critical.later.name}"),
        ]
    rows += [
        Row("Run time", f"{max(p.retention.t_r for p in resolution.peaks):.2f} min"),
        Row("Min. k", f"{min(p.retention.k_e for p in resolution.peaks):.2f}"),
    ]
    if cockpit.defaulted_width_names:
        rows.append(
            Row("N estimated for", f"{len(cockpit.defaulted_width_names)} peak(s)", "#c77700")
        )
    return rows


def _peak_detail(cockpit: Cockpit) -> None:
    """One peak at a time, the way instrument software shows a selected peak."""
    predicted = cockpit.predicted_by_name
    if not predicted:
        return
    name = st.selectbox("Peak", list(predicted), label_visibility="collapsed")
    peak = predicted[name]
    fit = next((f for p, f in cockpit.fitted if p.name == name), None)

    rows = [
        Row("Name", name),
        Row("tR", f"{peak.retention.t_r:.3f} min"),
        Row("k at elution", f"{peak.retention.k_e:.2f}"),
        Row("W½", f"{peak.width.w_half:.4f} min"),
        Row("N", f"{peak.width.plate_count:,.0f}"),
        Row("N from", tables.plate_count_label(peak.width.plate_count_source)),
    ]
    if fit is not None:
        rows += [
            Row("log10 k0", f"{log10_k0_from_ln_k0(fit.params.ln_k0):.2f}"),
            Row("S", f"{s_base10_from_s_e(fit.params.s_e):.2f}"),
        ]
    before, after = _neighbouring_resolution(cockpit, name)
    rows.append(Row("Rs before/after", f"{_rs_text(before)} / {_rs_text(after)}"))
    st.markdown(panels.panel("Selected peak", rows), unsafe_allow_html=True)


def _neighbouring_resolution(cockpit: Cockpit, name: str) -> tuple[float | None, float | None]:
    """This peak's resolution from the peak before it and the peak after it."""
    if cockpit.resolution is None:
        return None, None
    before = next((p.rs for p in cockpit.resolution.pairs if p.later.name == name), None)
    after = next((p.rs for p in cockpit.resolution.pairs if p.earlier.name == name), None)
    return before, after


def _rs_text(rs: float | None) -> str:
    return "—" if rs is None else f"{rs:.2f}"


# --- the main view --------------------------------------------------------------------


def _resolution_map(candidate: Gradient) -> None:
    st.plotly_chart(
        chromatogram.resolution_map_placeholder(
            t_gradient_range=(1.0, _MAX_CANDIDATE_TG),
            hold_range=(0.0, _MAX_CANDIDATE_HOLD),
            candidate=(candidate.t_gradient, candidate.t_init),
        ),
        width="stretch",
    )


def _fit_tab(cockpit: Cockpit) -> None:
    if not cockpit.outcomes and not cockpit.entry.untracked:
        st.caption("Nothing fitted yet — enter a tR in both runs for at least one peak.")
        return
    st.dataframe(
        tables.fit_frame(cockpit),
        width="stretch",
        hide_index=True,
        column_config={
            "log10 k0": st.column_config.NumberColumn(format="%.2f"),
            "S": st.column_config.NumberColumn(format="%.2f"),
            "N": st.column_config.NumberColumn(format="%.0f"),
            tables.N_RATIO: st.column_config.NumberColumn(format="%.3f"),
        },
    )
    st.caption("log10 k0 is quoted at the scouting φ0; S is the base-10 slope (SPEC §3).")


def _resolution_tab(cockpit: Cockpit) -> None:
    if cockpit.resolution is None:
        st.caption("Nothing fitted yet — enter a tR in both runs for at least one peak.")
        return
    _diagnostic_5_banner(cockpit)
    st.dataframe(
        tables.prediction_frame(cockpit),
        width="stretch",
        hide_index=True,
        column_config={
            "tR (min)": st.column_config.NumberColumn(format="%.3f"),
            "W½ (min)": st.column_config.NumberColumn(format="%.4f"),
            "k at elution": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.dataframe(
        tables.resolution_frame(cockpit),
        width="stretch",
        hide_index=True,
        column_config={
            "ΔtR (min)": st.column_config.NumberColumn(format="%.3f"),
            "Rs": st.column_config.NumberColumn(format="%.2f"),
        },
    )


def _status_bar(cockpit: Cockpit, candidate: Gradient) -> None:
    fields = [
        f"tG {candidate.t_gradient:g} min; hold {candidate.t_init:g} min",
        f"%B {percent_b_from_phi(candidate.phi0):g} → {percent_b_from_phi(candidate.phif):g}",
    ]
    critical = cockpit.resolution.critical_pair if cockpit.resolution else None
    if critical is not None:
        fields.append(f"Rs {critical.rs:.2f}")
    fields.append("RP gradient — linear, single segment")
    st.markdown(panels.status_bar(fields), unsafe_allow_html=True)


def _diagnostic_5_banner(cockpit: Cockpit) -> None:
    """SPEC §6 diagnostic 5, scoped to peaks whose N is the column estimate."""
    defaulted = cockpit.defaulted_width_names
    if defaulted:
        st.warning(_DIAGNOSTIC_5.format(names=", ".join(defaulted)), icon="⚠️")


def _chromatogram(cockpit: Cockpit, candidate: Gradient) -> None:
    st.subheader(
        f"Predicted chromatogram — tG {candidate.t_gradient:g} min, hold {candidate.t_init:g} min"
    )
    if cockpit.resolution is None or not cockpit.resolution.peaks:
        st.caption("The chromatogram appears once at least one peak is fitted.")
        return
    trace = chromatogram.chromatogram(cockpit.resolution.peaks, cockpit.shares)
    st.plotly_chart(chromatogram.figure(trace), width="stretch")
    st.caption(
        "Peak areas scaled by the measured area shares."
        if trace.scaled_by_area
        else "Not every peak carries an area — all peaks drawn to the same height."
    )


main()
