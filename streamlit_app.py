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
underneath, and a status bar at the foot.

Panels are filled out of render order. Streamlit containers are reserved first and
written into later, which is how the left rail can summarise a fit that the peak table
on the right has not yet been rendered to produce, and how the sidebar's save button can
offer a file built from a table further down the page.

Nothing here decides anything. SPEC §6's six diagnostics and SPEC §5's entry checks are
computed in :mod:`app.diagnostics`, SPEC §7's guided empty state in :mod:`app.worksheet`,
and SPEC §8's file in :mod:`app.session_io` and :mod:`hplcsim.session`; this file places
them, at the positions SPEC §6's own presentation sentence gives them.

What it does own, and cannot delegate, is **widget identity** (ticket #21). Restoring a
session means writing values into ``st.session_state`` under the keys the widgets answer
to, before those widgets are created — so the keys live in :class:`Keys`, the session
controls are drawn before everything they can overwrite, and a widget whose default is
fed by another widget needs its seed written too.
"""

from __future__ import annotations

from collections.abc import Sequence

import streamlit as st

from app import chromatogram, panels, tables, worksheet
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
from app.session_io import (
    Restore,
    peak_rows_from_session,
    session_filename,
    session_from_inputs,
)
from app.worksheet import Step, needs_guidance, worksheet_steps
from hplcsim.model import (
    Gradient,
    Method,
    Run,
    log10_k0_from_ln_k0,
    percent_b_from_phi,
    s_base10_from_s_e,
)
from hplcsim.retention import gradient_end_time
from hplcsim.session import Session, SessionFileError, load_session, save_session
from hplcsim.width import default_plate_count
from prototype import entry as proto  # PROTOTYPE #45 — leaves with the branch

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

# Every bounded widget's range, named once. The widget call spreads it and `_restore`
# clamps to it, so a file carrying a value past the end of a slider cannot reach the
# widget — Streamlit raises on that, and the whole page becomes a traceback (found by
# `/code-review` on this ticket). The two ends have to be the same numbers or the clamp
# is not a clamp, which is the only reason these are constants.
_LENGTH_RANGE = (1.0, 1000.0)
_COLUMN_ID_RANGE = (0.05, 50.0)
_PARTICLE_RANGE = (0.5, 50.0)
_FLOW_RANGE = (0.001, 20.0)
_TEMPERATURE_RANGE = (-20.0, 200.0)
_T0_RANGE = (0.001, 100.0)
_DWELL_TIME_RANGE = (0.0, 100.0)
_HOLD_RANGE = (0.0, 60.0)
_PLATE_COUNT_RANGE = (100.0, 1_000_000.0)
_PERCENT_B_RANGE = (0.0, 100.0)
_TG_RUN_RANGE = (0.1, 600.0)
_CANDIDATE_TG_RANGE = (1.0, _MAX_CANDIDATE_TG)
_CANDIDATE_HOLD_RANGE = (0.0, _MAX_CANDIDATE_HOLD)

_MEASURED = "Measured marker"
_ESTIMATED = "Geometry estimate"
_BY_VOLUME = "Volume (mL)"
_BY_TIME = "Time (min)"

_UNTITLED = "Untitled session"

# SPEC §6 diagnostic 6's short form. One wording, wherever an output surface carries it.
_STAMP_SHORT = "⚠️ Estimated t0 — every value here is lower-confidence (SPEC §6)."


class Keys:
    """Every widget's ``session_state`` key, in one place (ticket #21).

    Loading a session file means writing the restored values into the widgets before
    they are drawn, so each one needs a name that the loader and the widget agree on.
    Spelling those names as constants is what keeps the two ends from drifting: a typo
    in a string literal here does not raise, it silently leaves that one field on its
    default while every other field loads, which is the worst possible shape for the bug.

    :func:`_slider_with_box` derives three keys of its own from each name below, so a
    two-widget control's key is a stem rather than a widget id.
    """

    SESSION_NAME = "session_name"
    UPLOAD = "session_upload"
    LOADED_FILE = "loaded_file_id"
    LOAD_ERROR = "load_error"
    LOAD_NOTE = "load_note"
    PEAK_FRAME = "peak_frame"
    PEAK_TABLE_NONCE = "peak_table_nonce"

    LENGTH = "column_length_mm"
    COLUMN_ID = "column_id_mm"
    PARTICLE = "particle_um"
    FLOW = "flow"
    TEMPERATURE = "temperature_c"
    T0_SOURCE = "t0_source"
    T0 = "t0"
    DWELL_AS = "dwell_entered_as"
    DWELL_TIME = "dwell_time"
    DWELL_VOLUME = "dwell_volume"
    PERCENT_B_START = "percent_b_start"
    PERCENT_B_END = "percent_b_end"
    HOLD = "hold"
    USE_N_ESTIMATE = "use_plate_count_estimate"
    PLATE_COUNT = "plate_count"
    TG_RUN1 = "tg_run1"
    TG_RUN2 = "tg_run2"
    CANDIDATE_TG = "candidate_tg"
    CANDIDATE_HOLD = "candidate_hold"

    # Where the chromatogram's axes begin and end. These are a view onto the prediction,
    # not an input to it: SPEC §8 keeps the session file to inputs, so they live in
    # `session_state` and nowhere near `CockpitInputs`.
    X_AXIS_START = "x_axis_start"
    X_AXIS_END = "x_axis_end"
    Y_AXIS_START = "y_axis_start"
    Y_AXIS_END = "y_axis_end"
    AXIS_KEYS = (X_AXIS_START, X_AXIS_END, Y_AXIS_START, Y_AXIS_END)
    # Whether the reader has touched any of the four. Until they have, the boxes follow
    # the run — a keyed widget keeps its first value across reruns otherwise, and the
    # window would silently stay the length of the *previous* candidate's run.
    AXIS_TOUCHED = "axis_touched"


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

    # The session controls come first in the sidebar and, more to the point, before
    # every other widget is drawn: restoring a file writes the widgets' state, and
    # state written after a widget has been created for this run is state that widget
    # never sees. Save is the exception — it needs the peak table, which has not been
    # rendered yet — so it reserves a slot here and is filled in at the foot of `main`.
    # PROTOTYPE #45: the demo restore writes widget state, so it lands before any
    # widget it overwrites is created — the same rule the #31 prototype followed.
    _wanted = proto.wanted_demo()
    if _wanted is not None:
        _restore(_wanted)
        proto.mark_loaded()
    _pending = proto.pending_candidate()
    if _pending is not None:
        _preset_slider_with_box(Keys.CANDIDATE_TG, seed=_TG_CANDIDATE, value=_pending)

    _load_control()
    proto.switcher()  # PROTOTYPE #45
    save_slot = st.sidebar.container()

    constants = _sidebar()

    # SPEC §4 makes the dwell required with no silent default: it belongs to the
    # instrument, a guessed one biases every prediction the same way, and this is the
    # one constant the spec singles out. So nothing is predicted until it is entered.
    if constants is None:
        st.title("hplcsim")
        st.warning(_DWELL_REQUIRED, icon="⚠️")
        # Loading still works from here: a file carries its own dwell, which is the
        # fastest way out of this screen and the reason the uploader is drawn above it.
        return

    rail, main_view = st.columns([1.15, 3.0], gap="medium")

    with rail:
        run1, run2 = _scouting_runs(constants)
        # PROTOTYPE #45: the variant under test owns the candidate block.
        candidate = (
            proto.candidate_controls(constants, _proto_plumbing(constants), (run1, run2))
            if proto.active()
            else _candidate_controls(constants)
        )
        candidate_slot = st.container()
        summary_slot = st.container()

    with main_view:
        worksheet_slot = st.container()
        map_tab, peaks_tab, fit_tab, resolution_tab = st.tabs(
            ["Resolution map", "Table of peaks", "Fit parameters", "Resolution"]
        )
        with peaks_tab:
            rows = _peak_table()
        # SPEC §7: the chromatogram is pinned beneath the tabs and stays visible while
        # the entry and results above it scroll. `panels.STYLE` does the pinning, by
        # this container's key; nothing else in the app is addressed by CSS this way.
        chromatogram_slot = st.container(key="hs-chromatogram")

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
    diagnostics = proto.amend(diagnostics, inputs, cockpit)  # PROTOTYPE #45

    with save_slot:
        _save_control(inputs)
    with worksheet_slot:
        # SPEC §7's guided empty state, above the tabs rather than instead of them.
        # Step 2 asks for the peak table and SPEC §4's scouting-spacing warning is
        # painted on the fit tab before any peak is typed, so both have to stay
        # reachable — the guidance leads the main view rather than replacing it.
        if needs_guidance(cockpit):
            _worksheet(worksheet_steps(inputs, cockpit))
    with candidate_slot:
        # SPEC §6: diagnostic 1 is a "candidate-control inline warning" — it belongs
        # against the slider that caused it, not in a tab the user may not have open.
        # PROTOTYPE #45: variant C paints these as panel rows, A and B as boxes.
        proto.candidate_notices(diagnostics, _notices, constants=constants, candidate=candidate)
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
        _chromatogram(cockpit, inputs, diagnostics)

    _status_bar(cockpit, candidate, diagnostics)


# --- sidebar: the session file of SPEC §8 ---------------------------------------------


def _load_control() -> None:
    """The uploader, and the one-shot restore it triggers (SPEC §8).

    Drawn before every other widget, because restoring writes their state and a widget
    already created this run would ignore it. Streamlit hands the same uploaded file
    back on every rerun, so the restore is keyed on the file's id: without that, each
    rerun would overwrite whatever the user had changed since loading, and the app
    would refuse to be edited.
    """
    with st.sidebar:
        st.header("Session")
        # The uploader goes first, and the session name below it, because the name is
        # itself something a file restores — a widget instantiated before the restore
        # runs has already claimed its key, and writing to it then is an exception
        # rather than a value that quietly fails to land.
        uploaded = st.file_uploader("Load a session", type=["json"], key=Keys.UPLOAD)

        if uploaded is not None and st.session_state.get(Keys.LOADED_FILE) != uploaded.file_id:
            st.session_state[Keys.LOADED_FILE] = uploaded.file_id
            try:
                session = load_session(uploaded.getvalue())
            except SessionFileError as error:
                # A corrupt or unknown-schema file is a hard error (SPEC §8) — but it
                # is the *file* that is refused, not the session on screen, which is
                # left exactly as it was for the user to go on working in.
                st.session_state[Keys.LOAD_ERROR] = str(error)
                # Both notices describe the *last file handled*, so a refusal clears the
                # previous file's out-of-range warning. Left standing it would sit under
                # this error, naming a number from a session no longer on screen.
                st.session_state[Keys.LOAD_NOTE] = None
            else:
                st.session_state[Keys.LOAD_ERROR] = None
                _restore(session)
                st.rerun()

        error = st.session_state.get(Keys.LOAD_ERROR)
        if error:
            st.error(error, icon="🚫")
        note = st.session_state.get(Keys.LOAD_NOTE)
        if note:
            # The file was read; some of it just does not fit on screen. That is a
            # warning, not a refusal (CLAUDE.md's warnings-over-blocks).
            st.warning(note, icon="⚠️")

        st.text_input("Session name", key=Keys.SESSION_NAME, placeholder=_UNTITLED)


def _restore(session: Session) -> None:
    """Write a loaded session into the widgets, under the keys they answer to.

    This is the half of the round trip :mod:`app.session_io` deliberately does not do:
    the translation between the file's shape and the screen's is logic and lives there,
    while *which widget holds which value* is a fact about this file and only this one.

    Every number goes through :class:`~app.session_io.Restore`, against the same
    ``_*_RANGE`` the widget itself is built from. A file may legitimately hold a value
    no widget on this screen can display — a 500-minute candidate tG is a real method
    and the slider stops at 180 — and writing it in raw makes Streamlit raise on the
    rerun, replacing the page with a traceback rather than saying anything useful.
    """
    method, shared = session.method, session.runs[0].gradient
    restore = Restore()
    st.session_state.update(
        {
            Keys.SESSION_NAME: session.session_name,
            Keys.LENGTH: restore.within(
                "column length", method.column_length_mm or _COLUMN_LENGTH_MM, *_LENGTH_RANGE
            ),
            Keys.COLUMN_ID: restore.within(
                "column i.d.", method.column_id_mm or _COLUMN_ID_MM, *_COLUMN_ID_RANGE
            ),
            Keys.PARTICLE: restore.within(
                "particle size", method.particle_um or _PARTICLE_UM, *_PARTICLE_RANGE
            ),
            Keys.FLOW: restore.within("flow", method.flow, *_FLOW_RANGE),
            Keys.TEMPERATURE: restore.within(
                "temperature",
                _TEMPERATURE_C if method.temperature_c is None else method.temperature_c,
                *_TEMPERATURE_RANGE,
            ),
            Keys.T0_SOURCE: _MEASURED if method.t0_is_measured else _ESTIMATED,
            Keys.T0: restore.within("t0", method.t0, *_T0_RANGE),
            # The file stores the dwell as a time (SPEC §8), so the time is what comes
            # back. Dividing a volume out of it would be inventing the V_D that was
            # typed, at whatever the flow happens to be now — the conversion is an
            # entry boundary and is not meant to run backwards.
            Keys.DWELL_AS: _BY_TIME,
            Keys.DWELL_TIME: restore.within("dwell", method.t_dwell, *_DWELL_TIME_RANGE),
            # %B goes through `restore` like everything else. The file already refuses
            # anything outside 0–100 (`_check_percent`), so it should never bind — but
            # being the one documented exception is how a later reader ends up
            # re-deriving whether that exception is still safe.
            Keys.PERCENT_B_START: restore.within(
                "%B start", percent_b_from_phi(shared.phi0), *_PERCENT_B_RANGE
            ),
            Keys.PERCENT_B_END: restore.within(
                "%B end", percent_b_from_phi(shared.phif), *_PERCENT_B_RANGE
            ),
            Keys.HOLD: restore.within("initial hold", shared.t_init, *_HOLD_RANGE),
            Keys.USE_N_ESTIMATE: session.plate_count is None,
            Keys.TG_RUN1: restore.within(
                "run 1 tG", session.runs[0].gradient.t_gradient, *_TG_RUN_RANGE
            ),
            Keys.TG_RUN2: restore.within(
                "run 2 tG", session.runs[1].gradient.t_gradient, *_TG_RUN_RANGE
            ),
            Keys.PEAK_FRAME: tables.peak_frame_from_rows(peak_rows_from_session(session)),
            # A fresh identity for the data editor. Its state belongs to its key, so
            # reusing the key would show the loaded frame's columns with the previous
            # session's edits still layered over them.
            Keys.PEAK_TABLE_NONCE: st.session_state.get(Keys.PEAK_TABLE_NONCE, 0) + 1,
        }
    )
    if session.plate_count is not None:
        st.session_state[Keys.PLATE_COUNT] = restore.within(
            "plate count N", float(session.plate_count), *_PLATE_COUNT_RANGE
        )
    _preset_slider_with_box(
        Keys.CANDIDATE_TG,
        seed=_TG_CANDIDATE,
        value=restore.within("candidate tG", session.candidate.t_gradient, *_CANDIDATE_TG_RANGE),
    )
    _preset_slider_with_box(
        # The candidate hold's default is fed by the method hold, so the seed has to be
        # the *restored* method hold — seeded with anything else, the reseed in
        # `_slider_with_box` sees a changed default and overwrites the value just loaded.
        Keys.CANDIDATE_HOLD,
        seed=min(st.session_state[Keys.HOLD], _MAX_CANDIDATE_HOLD),
        value=restore.within(
            "candidate initial hold", session.candidate.t_init, *_CANDIDATE_HOLD_RANGE
        ),
    )
    st.session_state[Keys.LOAD_NOTE] = restore.note


def _save_control(inputs: CockpitInputs) -> None:
    """The download button of SPEC §8, or the reason there is not one.

    ``save_session`` and ``load_session`` validate identically on purpose (#18), so a
    save that would write an unopenable file raises instead. That is the right rule for
    the file and the wrong thing to show a chromatographer as a stack trace, so the
    refusal is caught and worded here — the gate is in the UI, and the file stays strict.
    """
    name = st.session_state.get(Keys.SESSION_NAME, "")
    try:
        text = save_session(session_from_inputs(inputs, session_name=name))
    except SessionFileError as error:
        st.warning(f"Not saveable yet — {error}", icon="⚠️")
        return
    st.download_button(
        "Save session",
        data=text,
        file_name=session_filename(name),
        mime="application/json",
        width="stretch",
    )
    st.caption("Inputs only — the fit recomputes when the file is reopened.")


# --- sidebar: the method constants of SPEC §4 -----------------------------------------


def _sidebar() -> MethodEntry | None:
    """The method constants, or ``None`` while the required dwell is still unset."""
    with st.sidebar:
        st.header("Method constants")
        st.caption("Shared by both scouting runs and by the candidate.")

        length = st.number_input(
            "Column length (mm)", *_LENGTH_RANGE, _COLUMN_LENGTH_MM, key=Keys.LENGTH
        )
        column_id = st.number_input(
            "Column i.d. (mm)", *_COLUMN_ID_RANGE, _COLUMN_ID_MM, key=Keys.COLUMN_ID
        )
        particle = st.number_input(
            "Particle size (µm)", *_PARTICLE_RANGE, _PARTICLE_UM, key=Keys.PARTICLE
        )
        flow = st.number_input(
            "Flow F (mL/min)", *_FLOW_RANGE, _FLOW, step=0.05, format="%.3f", key=Keys.FLOW
        )
        temperature = st.number_input(
            "Temperature (°C)", *_TEMPERATURE_RANGE, _TEMPERATURE_C, key=Keys.TEMPERATURE
        )
        st.caption("Temperature is metadata in v0.1 — the model is fixed-temperature.")

        st.subheader("Dead time")
        t0_source = st.radio(
            "t0 source", [_MEASURED, _ESTIMATED], horizontal=True, key=Keys.T0_SOURCE
        )
        t0 = st.number_input("t0 (min)", *_T0_RANGE, _T0, step=0.05, format="%.4f", key=Keys.T0)
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
        percent_b_start = st.number_input(
            "%B start", *_PERCENT_B_RANGE, _PERCENT_B_START, key=Keys.PERCENT_B_START
        )
        percent_b_end = st.number_input(
            "%B end", *_PERCENT_B_RANGE, _PERCENT_B_END, key=Keys.PERCENT_B_END
        )
        hold = st.number_input("Initial hold (min)", *_HOLD_RANGE, _HOLD, step=0.1, key=Keys.HOLD)

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
    entered_as = st.radio(
        "Dwell entered as", [_BY_VOLUME, _BY_TIME], horizontal=True, key=Keys.DWELL_AS
    )
    if entered_as != _BY_VOLUME:
        return st.number_input(
            "Dwell time t_D (min)",
            *_DWELL_TIME_RANGE,
            value=None,
            format="%.4f",
            key=Keys.DWELL_TIME,
        )

    volume = st.number_input(
        "Dwell volume V_D (mL)", 0.0, 100.0, value=None, format="%.4f", key=Keys.DWELL_VOLUME
    )
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
    label = f"Use the column estimate (N ≈ {estimate:,.0f})"
    if st.checkbox(label, value=True, key=Keys.USE_N_ESTIMATE):
        st.caption("N = L/(2·dp) — geometry, not this instrument's real efficiency.")
        return None
    return st.number_input(
        "Plate count N", *_PLATE_COUNT_RANGE, _PLATE_COUNT, step=500.0, key=Keys.PLATE_COUNT
    )


# --- entry ----------------------------------------------------------------------------


def _peak_table() -> list[PeakRow]:
    st.subheader("Peak table")
    st.caption(
        "One row per compound, both runs side by side — you pair the peaks as you type. "
        "Name, areas and W½ are optional; a W½ has its peak's plate count fitted from it."
    )
    three_decimals = st.column_config.NumberColumn(format="%.3f")
    # A restored table arrives as a frame in state; an unloaded one is the blank frame,
    # exactly as before. The nonce in the key is what makes a *second* load land: the
    # editor's edits belong to its key, and reusing the key would leave them on top of
    # the new data. It is only ever bumped by `_restore`.
    edited = st.data_editor(
        st.session_state.get(Keys.PEAK_FRAME, tables.blank_peak_frame()),
        key=f"peak_table_{st.session_state.get(Keys.PEAK_TABLE_NONCE, 0)}",
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
    t_gradient1 = left.number_input(
        "Run 1 tG", *_TG_RUN_RANGE, _TG_RUN1, step=0.5, key=Keys.TG_RUN1
    )
    t_gradient2 = right.number_input(
        "Run 2 tG", *_TG_RUN_RANGE, _TG_RUN2, step=0.5, key=Keys.TG_RUN2
    )
    return (
        Run(constants.gradient(t_gradient1), name=f"tG{t_gradient1:g}"),
        Run(constants.gradient(t_gradient2), name=f"tG{t_gradient2:g}"),
    )


def _candidate_controls(constants: MethodEntry) -> Gradient:
    st.markdown("### Candidate")
    t_gradient = _slider_with_box(
        "tG (min)",
        *_CANDIDATE_TG_RANGE,
        _TG_CANDIDATE,
        slider_step=0.5,
        box_step=0.1,
        box_label="Candidate tG (min)",
        key=Keys.CANDIDATE_TG,
    )
    hold = _slider_with_box(
        "Initial hold (min)",
        *_CANDIDATE_HOLD_RANGE,
        min(constants.hold, _MAX_CANDIDATE_HOLD),
        slider_step=0.05,
        box_step=0.01,
        box_label="Candidate initial hold (min)",
        key=Keys.CANDIDATE_HOLD,
    )
    return constants.gradient(t_gradient, hold=hold)


def _proto_plumbing(constants: MethodEntry) -> proto.Plumbing:
    """PROTOTYPE #45: lend the variants this file's two-widget control and its keys."""
    return proto.Plumbing(
        slider_with_box=_slider_with_box,
        preset=_preset_slider_with_box,
        tg_key=Keys.CANDIDATE_TG,
        hold_key=Keys.CANDIDATE_HOLD,
        tg_range=_CANDIDATE_TG_RANGE,
        hold_range=_CANDIDATE_HOLD_RANGE,
        default_tg=_TG_CANDIDATE,
        default_hold=min(constants.hold, _MAX_CANDIDATE_HOLD),
    )


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


def _preset_slider_with_box(key: str, *, seed: float, value: float) -> None:
    """Put a restored value into a two-widget control, reseed and all.

    Setting the two widgets alone is not enough: :func:`_slider_with_box` reseeds
    whenever the caller's default has moved since it last looked, and on the rerun
    after a load the default *has* moved — the method hold came out of the file too.
    Writing the seed here is what tells it the move has already been accounted for.
    """
    st.session_state[f"{key}_seed"] = seed
    st.session_state[f"{key}_slider"] = value
    st.session_state[f"{key}_box"] = value


# --- the guided empty state of SPEC §7 ------------------------------------------------


def _worksheet(steps: Sequence[Step]) -> None:
    """The numbered 1→4 worksheet, painted where the results will later be.

    Placement, and nothing else: which steps are done and what each one says are
    :mod:`app.worksheet`'s, on the rule ticket #20 set for the diagnostics.
    """
    st.markdown(
        panels.worksheet(worksheet.TITLE, worksheet.LEAD, steps),
        unsafe_allow_html=True,
    )


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
    if (stamp := proto.stamp_caption()) is not None:  # PROTOTYPE #45
        st.caption(f"⚠️ {stamp}")


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
    rows += proto.summary_rows()  # PROTOTYPE #45
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
        proto.fit_frame(tables.fit_frame(cockpit)),  # PROTOTYPE #45
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
    if (windows := proto.window_frame()) is not None:  # PROTOTYPE #45
        st.markdown("**Calibrated composition windows at this candidate**")
        st.dataframe(windows, width="stretch", hide_index=True)
    if (note := proto.fit_caption()) is not None:  # PROTOTYPE #45
        st.caption(note)


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
    fields.extend(proto.status_fields())  # PROTOTYPE #45
    # SPEC §6 diagnostic 6 stamps *all* outputs, so it reaches the one strip of the
    # screen that is on show whichever tab is open.
    if any(stamp.code == "estimated_t0" for stamp in diagnostics.stamps):
        fields.append("t0 estimated — predictions lower-confidence")
    st.markdown(panels.status_bar(fields), unsafe_allow_html=True)


def _chromatogram(cockpit: Cockpit, inputs: CockpitInputs, diagnostics: Diagnostics) -> None:
    """The pinned trace of SPEC §7. Everything around the plot earns its pixels.

    This block is sticky, so its height is screen the reader cannot scroll away. The
    condition, the area caveat and diagnostic 6's stamp all still have to appear — they
    are on one caption line beside the title rather than three stacked rows beneath it.
    """
    candidate = inputs.candidate
    st.markdown(
        f"**Predicted chromatogram** — tG {candidate.t_gradient:g} min, "
        f"hold {candidate.t_init:g} min"
    )
    if cockpit.resolution is None or not cockpit.resolution.peaks:
        st.caption("The chromatogram appears once at least one peak is fitted.")
        return
    asked = _axis_request()
    trace = chromatogram.chromatogram(
        cockpit.resolution.peaks,
        cockpit.shares,
        gradient_end=gradient_end_time(inputs.method, candidate),
        # An x axis asked to end past the run needs trace to draw out there, not just a
        # wider window onto a baseline that stops halfway across the plot.
        extend_to=asked.x_end,
    )
    view = chromatogram.axis_view(trace, asked)
    fig = chromatogram.figure(trace, view=view)
    proto.overlay(fig, inputs, cockpit, view)  # PROTOTYPE #45 — variant B only
    st.plotly_chart(fig, width="stretch")
    notes = [
        "Peak areas scaled by the measured area shares."
        if trace.scaled_by_area
        else "Not every peak carries an area — all peaks drawn to the same height."
    ]
    if diagnostics.stamps:
        notes.append(_STAMP_SHORT)
    st.caption("  ·  ".join(notes))
    _axis_controls(view)


def _axis_request() -> chromatogram.AxisRequest:
    """What the reader asked of the axes — nothing, until they have touched a box."""
    if not st.session_state.get(Keys.AXIS_TOUCHED, False):
        return chromatogram.AxisRequest()
    return chromatogram.AxisRequest(
        x_start=st.session_state.get(Keys.X_AXIS_START),
        x_end=st.session_state.get(Keys.X_AXIS_END),
        y_start=st.session_state.get(Keys.Y_AXIS_START),
        y_end=st.session_state.get(Keys.Y_AXIS_END),
    )


def _axis_controls(view: chromatogram.AxisView) -> None:
    """Both ends of both axes, as four boxes beneath the trace.

    Behind an expander rather than always on show. This block is pinned, so every row
    added here is screen the reader cannot scroll away from — the same budget that
    `CHROMATOGRAM_HEIGHT` is spending. Collapsed it costs one line; the reader who wants
    to crop the baseline off opens it once and it stays open.

    Until the reader touches a box, the boxes are re-seeded from the run every rerun, so
    a longer candidate grows the window with it. Once touched, the entries stay put —
    a pinned window is what the reader asked for — until Reset.
    """
    touched = st.session_state.get(Keys.AXIS_TOUCHED, False)
    if not touched:
        for key in Keys.AXIS_KEYS:
            st.session_state.pop(key, None)
    y_step = view.run_y[1] / 20.0 or 0.05
    boxes = (
        ("x start (min)", Keys.X_AXIS_START, view.run_x[0], 0.1, "%.2f"),
        ("x end (min)", Keys.X_AXIS_END, view.run_x[1], 0.1, "%.2f"),
        ("y start", Keys.Y_AXIS_START, view.run_y[0], y_step, "%.4f"),
        ("y end", Keys.Y_AXIS_END, view.run_y[1], y_step, "%.4f"),
    )
    with st.expander("Axis range", expanded=False):
        cols = st.columns([1.0, 1.0, 1.0, 1.0, 0.7], vertical_alignment="bottom")
        for col, (label, key, value, step, fmt) in zip(cols, boxes, strict=False):
            with col:
                st.number_input(
                    label,
                    min_value=0.0 if key in (Keys.X_AXIS_START, Keys.X_AXIS_END) else None,
                    value=value,
                    step=step,
                    format=fmt,
                    key=key,
                    on_change=_mark_axis_touched,
                )
        with cols[4]:
            st.button("Reset", on_click=_reset_axis_range, width="stretch")
        st.caption(
            f"The run ends at {view.run_x[1]:.2f} min and the tallest peak reaches "
            f"{view.run_y[1] / chromatogram.Y_HEADROOM:.4g}. An x end past the run draws "
            "the baseline out to it."
        )
    for note in view.notes:
        st.warning(note, icon="⚠️")


def _mark_axis_touched() -> None:
    """From here on the boxes are the reader's, not the run's."""
    st.session_state[Keys.AXIS_TOUCHED] = True


def _reset_axis_range() -> None:
    """Back to the whole run. A callback, so it lands before the widgets are redrawn."""
    st.session_state[Keys.AXIS_TOUCHED] = False
    for key in Keys.AXIS_KEYS:
        st.session_state.pop(key, None)


def _stamp_caption(diagnostics: Diagnostics) -> None:
    """SPEC §6 diagnostic 6's short form, on an output surface that is not the fit tab.

    A stamp is meant to be short. The fit tab carries the whole explanation once; every
    other surface carries a line saying the outputs on it inherit an estimate, so that
    no output is read without it and no output is buried under it.
    """
    if diagnostics.stamps:
        st.caption(_STAMP_SHORT)


main()
