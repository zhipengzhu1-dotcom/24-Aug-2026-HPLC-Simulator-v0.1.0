"""The Cockpit (SPEC §7): entry to fit to prediction, live — ticket #19.

Run it with::

    uv run --extra app streamlit run app/streamlit_app.py

Only widgets and layout live here. Every number on screen is computed by
:func:`app.pipeline.run_cockpit` and shaped by :mod:`app.tables`, so the whole path
can be exercised without a browser (``tests/test_app.py``) and ticket #20's
diagnostics have a logic layer to attach to.

Layout is the winning prototype variant: sidebar constants, candidate controls and
the chromatogram at the top, entry on the left, results on the right. The
chromatogram is drawn into a container reserved *before* the peak table is rendered,
which is how it sits above the entry it depends on.

Scope: the guided empty state and the sticky chromatogram are ticket #21's, and five
of SPEC §6's six diagnostics are ticket #20's. Diagnostic 5's banner is here because
SPEC §6 assigns its wording to this ticket and this is what first puts widths and Rs
on screen.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from app import chromatogram, tables
from app.pipeline import Cockpit, CockpitInputs, PeakRow, run_cockpit
from hplcsim.model import Gradient, Method, Run, phi_from_percent_b
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
_DWELL_VOLUME_ML = 0.375
_DWELL_TIME_MIN = 0.9375
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


@dataclass(frozen=True)
class _Constants:
    """What the sidebar holds: the method, the shared gradient shape, and the N knob."""

    method: Method
    percent_b_start: float
    percent_b_end: float
    hold: float
    plate_count: float | None

    def gradient(self, t_gradient: float, hold: float | None = None) -> Gradient:
        """The shared gradient at one gradient time — the %B → φ boundary, in one place."""
        return Gradient(
            phi0=phi_from_percent_b(self.percent_b_start),
            phif=phi_from_percent_b(self.percent_b_end),
            t_gradient=t_gradient,
            t_init=self.hold if hold is None else hold,
        )


def main() -> None:
    st.set_page_config(page_title="hplcsim — Cockpit", layout="wide")
    constants = _sidebar()

    st.title("hplcsim — Cockpit")
    st.caption("Two scouting runs in, per-peak LSS parameters out, any linear gradient predicted.")

    run1, run2 = _scouting_runs(constants)
    candidate = _candidate_gradient(constants)
    hero = st.container()

    entry_column, results_column = st.columns(2, gap="large")
    with entry_column:
        rows = _peak_table()

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

    with entry_column:
        _entry_notes(cockpit)
    with results_column:
        _results(cockpit)
    with hero:
        _chromatogram(cockpit, candidate)


# --- sidebar: the method constants of SPEC §4 -----------------------------------------


def _sidebar() -> _Constants:
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
            st.caption("An estimated t0 stamps every prediction lower-confidence (SPEC §6).")

        st.subheader("Dwell")
        t_dwell = _dwell(flow)

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

    return _Constants(
        method=method,
        percent_b_start=percent_b_start,
        percent_b_end=percent_b_end,
        hold=hold,
        plate_count=plate_count,
    )


def _dwell(flow: float) -> float:
    """t_D directly, or V_D ÷ F — the entry-boundary conversion of SPEC §4."""
    entered_as = st.radio("Dwell entered as", [_BY_VOLUME, "Time (min)"], horizontal=True)
    if entered_as != _BY_VOLUME:
        return st.number_input("Dwell time t_D (min)", 0.0, 100.0, _DWELL_TIME_MIN, format="%.4f")
    volume = st.number_input("Dwell volume V_D (mL)", 0.0, 100.0, _DWELL_VOLUME_ML, format="%.4f")
    t_dwell = volume / flow
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


# --- runs, candidate, entry -----------------------------------------------------------


def _scouting_runs(constants: _Constants) -> tuple[Run, Run]:
    st.subheader("Scouting runs")
    left, right = st.columns(2)
    t_gradient1 = left.number_input("Run 1 tG (min)", 0.1, 600.0, _TG_RUN1, step=0.5)
    t_gradient2 = right.number_input("Run 2 tG (min)", 0.1, 600.0, _TG_RUN2, step=0.5)
    return (
        Run(constants.gradient(t_gradient1), name=f"tG{t_gradient1:g}"),
        Run(constants.gradient(t_gradient2), name=f"tG{t_gradient2:g}"),
    )


def _candidate_gradient(constants: _Constants) -> Gradient:
    st.subheader("Candidate gradient")
    left, right = st.columns(2)
    t_gradient = left.slider("Candidate tG (min)", 1.0, _MAX_CANDIDATE_TG, _TG_CANDIDATE, step=0.5)
    hold = right.slider(
        "Candidate initial hold (min)",
        0.0,
        _MAX_CANDIDATE_HOLD,
        min(constants.hold, _MAX_CANDIDATE_HOLD),
        step=0.05,
    )
    return constants.gradient(t_gradient, hold=hold)


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


# --- results --------------------------------------------------------------------------


def _results(cockpit: Cockpit) -> None:
    st.subheader("Predicted at the candidate gradient")
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

    st.subheader("Resolution")
    critical = cockpit.resolution.critical_pair
    if critical is None:
        st.caption("Resolution needs two fitted peaks.")
    else:
        st.metric(
            "Critical pair",
            f"{critical.earlier.name} / {critical.later.name}",
            f"Rs {critical.rs:.2f}",
            delta_color="off",
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

    st.subheader("Fitted parameters")
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
