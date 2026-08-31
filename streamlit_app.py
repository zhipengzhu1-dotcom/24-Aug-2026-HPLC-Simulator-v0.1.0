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

Scope: the guided empty state and the sticky chromatogram are ticket #21's. SPEC §6's
six diagnostics and SPEC §5's entry checks are all computed in :mod:`app.diagnostics`
and only *placed* here, at the positions SPEC §6's own presentation sentence gives
them — including diagnostic 5's banner, whose wording ticket #19 wrote in this file and
ticket #20 moved out to sit beside the other five.
"""

from __future__ import annotations

from collections.abc import Sequence

import streamlit as st

from app import chromatogram, panels, tables
from app.diagnostics import Diagnostic, Diagnostics, diagnose
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

# How a diagnostic's severity is painted. SPEC §6 escalates rather than shouts once —
# an info flag is a fact about the condition, a warning is worth a second look, and a
# strong one is a reason not to run the method as it stands.
_PAINT = {
    "info": (st.info, "ℹ️"),
    "warning": (st.warning, "⚠️"),
    "strong": (st.error, "🚫"),
}


def _notices(diagnostics: Sequence[Diagnostic]) -> None:
    """Paint a group of diagnostics where the caller has put the cursor."""
    for diagnostic in diagnostics:
        paint, icon = _PAINT[diagnostic.severity]
        paint(diagnostic.message, icon=icon)


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
        candidate_slot = st.container()
        summary_slot = st.container()

    with main_view:
        map_tab, peaks_tab, fit_tab, resolution_tab = st.tabs(
            ["Resolution map", "Table of peaks", "Fit parameters", "Resolution"]
        )
        with peaks_tab:
            rows = _peak_table()
        chromatogram_slot = st.container()

    inputs = CockpitInputs(
        method=constants.method,
        run1=run1,
        run2=run2,
        candidate=candidate,
        rows=tuple(rows),
        plate_count=constants.plate_count,
    )
    cockpit = run_cockpit(inputs)

    diagnostics = diagnose(inputs, cockpit)

    with candidate_slot:
        # SPEC §6: diagnostic 1 is a "candidate-control inline warning" — it belongs
        # against the slider that caused it, not in a tab the user may not have open.
        _notices(diagnostics.candidate)
    with summary_slot:
        _summary_panels(cockpit, diagnostics)
    with peaks_tab:
        _entry_notes(cockpit, diagnostics)
    with map_tab:
        _resolution_map(candidate)
    with fit_tab:
        _fit_tab(cockpit, diagnostics)
    with resolution_tab:
        _resolution_tab(cockpit, diagnostics)
    with chromatogram_slot:
        _chromatogram(cockpit, candidate, diagnostics)

    _status_bar(cockpit, candidate, diagnostics)


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


def _entry_notes(cockpit: Cockpit, diagnostics: Diagnostics) -> None:
    """The count SPEC §5 asks for, and its two tracking checks, beside the rows they read."""
    untracked = cockpit.entry.untracked
    if untracked:
        names = ", ".join(row.name for row in untracked)
        st.info(
            f"**{len(untracked)} untracked — not fitted** ({names}). A row needs a tR in "
            "both runs before it can be fitted, predicted or resolved."
        )
    if cockpit.entry.renamed:
        pairs = ", ".join(f"{old} → {new}" for old, new in cockpit.entry.renamed)
        st.warning(
            f"**Duplicate peak names renamed** ({pairs}). Every peak is looked up by "
            "name, so two rows sharing one would drop a peak from the fit table and "
            "the selected-peak list."
        )
    # SPEC §5's two tracking checks — area-share disagreement and elution-order
    # crossing — sit under the table they are asking the user about. Both are questions
    # about the *pairing*, which is the thing being typed on this tab.
    _notices(diagnostics.entry)
    # The block message belongs to the rail, which is always on screen; painting it
    # here as well showed it twice whenever the peaks tab was the one open.


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
    t_gradient = _slider_with_box(
        "tG (min)",
        1.0,
        _MAX_CANDIDATE_TG,
        _TG_CANDIDATE,
        slider_step=0.5,
        box_step=0.1,
        box_label="Candidate tG (min)",
        key="candidate_tg",
    )
    hold = _slider_with_box(
        "Initial hold (min)",
        0.0,
        _MAX_CANDIDATE_HOLD,
        min(constants.hold, _MAX_CANDIDATE_HOLD),
        slider_step=0.05,
        box_step=0.01,
        box_label="Candidate initial hold (min)",
        key="candidate_hold",
    )
    return constants.gradient(t_gradient, hold=hold)


def _slider_with_box(
    label: str,
    min_value: float,
    max_value: float,
    default: float,
    *,
    slider_step: float,
    box_step: float,
    box_label: str,
    key: str,
) -> float:
    """One candidate control as two widgets: a slider to sweep, a box to land exactly.

    The slider is how the shape of the separation is explored — drag it and watch the
    critical pair move. It cannot express "24.35 min", though, and a method that is about
    to be written down is a specific number, not a nearby one. So the same value carries a
    box underneath, stepping ten times finer than the slider and accepting anything typed
    between the same two bounds.

    They are one value in two widgets, so each writes the other's state back on change.
    The slider tolerates a value off its own step grid — 24.35 on a 0.5 slider sits where
    it belongs and drags away from there — which is what lets the box stay the precise one
    without a second, disagreeing number appearing on screen.
    """
    slider_key, box_key, seed_key = f"{key}_slider", f"{key}_box", f"{key}_seed"

    # Re-seed when the caller's default moves — the method's initial hold feeds the
    # candidate's. Unkeyed widgets got this for free (a changed default is a changed
    # widget identity); keyed ones hold their value, so the reseed has to be explicit.
    if st.session_state.get(seed_key) != default:
        st.session_state[seed_key] = default
        st.session_state[slider_key] = default
        st.session_state[box_key] = default

    def _from_slider() -> None:
        st.session_state[box_key] = st.session_state[slider_key]

    def _from_box() -> None:
        st.session_state[slider_key] = st.session_state[box_key]

    st.slider(
        label,
        min_value,
        max_value,
        step=slider_step,
        key=slider_key,
        on_change=_from_slider,
    )
    # The box is labelled for the accessibility tree and for tests that address a
    # widget by the name a user reads; on screen the slider's label serves them both, so
    # `box_label` distinguishes this from the method-page hold input of the same name.
    st.number_input(
        box_label,
        min_value,
        max_value,
        step=box_step,
        format="%.2f",
        key=box_key,
        on_change=_from_box,
        label_visibility="collapsed",
    )
    return float(st.session_state[slider_key])


def _summary_panels(cockpit: Cockpit, diagnostics: Diagnostics) -> None:
    """What the condition on screen comes to, and then one peak in detail."""
    if cockpit.blocked is not None:
        st.error(cockpit.blocked)
        return
    st.markdown(panels.panel("Method summary", _summary_rows(cockpit)), unsafe_allow_html=True)
    _peak_detail(cockpit, diagnostics)
    # SPEC §6 diagnostic 6 stamps *all* outputs, and the rail's two panels carry tR, k,
    # W½, N and Rs. The stamp is a caption beneath them rather than a row inside them,
    # because SPEC §7 enumerates what those panels hold.
    _stamp_caption(diagnostics)


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


def _peak_detail(cockpit: Cockpit, diagnostics: Diagnostics) -> None:
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
    # SPEC §6's per-peak badges (diagnostics 2 and 4), in full, for the peak on show.
    # The table of peaks carries the same badges as one scannable word per row.
    _notices(diagnostics.badges.get(name, ()))


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


def _fit_tab(cockpit: Cockpit, diagnostics: Diagnostics) -> None:
    # SPEC §6: diagnostic 3 is a "fit-page notice", and diagnostic 6 stamps every output.
    # The fit tab carries the estimated-t0 stamp in full — it is the first place the
    # outputs appear — and every other surface carries the short form.
    #
    # Both are painted *before* the empty-table check on purpose. They are facts about
    # the experiment, not about its results: a chromatographer who has set two scouting
    # gradients 1.5× apart wants to know that before typing the peaks in, not after.
    _notices(diagnostics.fit)
    _notices(diagnostics.stamps)
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


def _resolution_tab(cockpit: Cockpit, diagnostics: Diagnostics) -> None:
    if cockpit.resolution is None:
        st.caption("Nothing fitted yet — enter a tR in both runs for at least one peak.")
        return
    # SPEC §6: diagnostic 5 is a "result banner", diagnostic 6 an "output stamp".
    _notices(diagnostics.banners)
    _stamp_caption(diagnostics)
    st.dataframe(
        tables.prediction_frame(cockpit, diagnostics.badges),
        width="stretch",
        hide_index=True,
        column_config={
            "tR (min)": st.column_config.NumberColumn(format="%.3f"),
            "W½ (min)": st.column_config.NumberColumn(format="%.4f"),
            "k at elution": st.column_config.NumberColumn(format="%.2f"),
            tables.FLAGS: st.column_config.TextColumn(width="small"),
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


def _status_bar(cockpit: Cockpit, candidate: Gradient, diagnostics: Diagnostics) -> None:
    fields = [
        f"tG {candidate.t_gradient:g} min; hold {candidate.t_init:g} min",
        f"%B {percent_b_from_phi(candidate.phi0):g} → {percent_b_from_phi(candidate.phif):g}",
    ]
    critical = cockpit.resolution.critical_pair if cockpit.resolution else None
    if critical is not None:
        fields.append(f"Rs {critical.rs:.2f}")
    fields.append("RP gradient — linear, single segment")
    # SPEC §6 diagnostic 6 stamps *all* outputs, so it reaches the one strip of the
    # screen that is on show whichever tab is open.
    if any(stamp.code == "estimated_t0" for stamp in diagnostics.stamps):
        fields.append("t0 estimated — predictions lower-confidence")
    st.markdown(panels.status_bar(fields), unsafe_allow_html=True)


def _chromatogram(cockpit: Cockpit, candidate: Gradient, diagnostics: Diagnostics) -> None:
    st.subheader(
        f"Predicted chromatogram — tG {candidate.t_gradient:g} min, hold {candidate.t_init:g} min"
    )
    if cockpit.resolution is None or not cockpit.resolution.peaks:
        st.caption("The chromatogram appears once at least one peak is fitted.")
        return
    trace = chromatogram.chromatogram(cockpit.resolution.peaks, cockpit.shares)
    st.plotly_chart(chromatogram.figure(trace), width="stretch")
    _stamp_caption(diagnostics)
    st.caption(
        "Peak areas scaled by the measured area shares."
        if trace.scaled_by_area
        else "Not every peak carries an area — all peaks drawn to the same height."
    )


def _stamp_caption(diagnostics: Diagnostics) -> None:
    """SPEC §6 diagnostic 6's short form, on an output surface that is not the fit tab.

    A stamp is meant to be short. The fit tab carries the whole explanation once; every
    other surface carries a line saying the outputs on it inherit an estimate, so that
    no output is read without it and no output is buried under it.
    """
    if diagnostics.stamps:
        st.caption("⚠️ Estimated t0 — every value here is lower-confidence (SPEC §6).")


main()
