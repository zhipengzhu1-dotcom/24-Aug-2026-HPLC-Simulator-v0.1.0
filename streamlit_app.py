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
relatives), at the driver's direction: a narrow left rail carrying the condition — the
scouting programme and the candidate programme as two No. / Time / %B tables (v0.2,
#45, #73) — and its summary, a tabbed main view with the resolution map first, the
chromatogram pinned underneath, and a status bar at the foot.

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
from app.diagnostics import (
    Diagnostic,
    Diagnostics,
    critical_pair_is_indicative,
    diagnose,
)
from app.panels import Row
from app.pipeline import (
    Cockpit,
    CockpitInputs,
    MethodEntry,
    PeakRow,
    ProgrammeRead,
    ScoutingEntry,
    dwell_from_volume,
    points_from_programme,
    programme_from_points,
    programme_summary,
    run_cockpit,
    t0_autofill,
)
from app.session_io import (
    Restore,
    inputs_from_session,
    session_filename,
    session_from_inputs,
)
from app.worksheet import Step, needs_guidance, worksheet_steps
from hplcsim.dead_time import DeadTimeEstimate, estimate_t0
from hplcsim.model import (
    Gradient,
    Method,
    Programme,
    log10_k0_from_ln_k0,
    s_base10_from_s_e,
)
from hplcsim.retention import gradient_end_time
from hplcsim.session import Session, SessionFileError, load_session, save_session
from hplcsim.width import default_plate_count

# The driver's Acquity H-Class / CORTECS 2.1×100 method (validation/method.csv). SPEC §1
# scopes v0.1 to a single user locally, so the number inputs open on that user's real
# instrument rather than on a textbook column; the peak table still opens empty.
_COLUMN_LENGTH_MM = 100.0
_COLUMN_ID_MM = 2.1
_PARTICLE_UM = 1.6
_FLOW = 0.4
_TEMPERATURE_C = 45.0
# The driver's re-read of the solvent-front time (2026-08-31, method.csv), which
# supersedes the 0.6 first entered. The engine fixtures are a separate question (#24).
_T0 = 0.525
# The scouting programme the rail opens on: 5 → 95 %B after a 0.5 min hold, run at
# tG 15 and 45 min — validation/method.csv's pair. The candidate opens as one ramp over
# the same range at tG 25 min (v0.1's default) and follows the scouting table until it
# is typed into.
_DEFAULT_SCOUTING = ScoutingEntry(
    percent_b_start=5.0, percent_b_end=95.0, hold=0.5, t_gradient1=15.0, t_gradient2=45.0
)
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
_PLATE_COUNT_RANGE = (100.0, 1_000_000.0)
# The two programme tables have no slider to clamp to (SPEC §7, v0.2): a 500-minute
# candidate is a real method and a table cell holds it. Only %B is bounded, 0–100, by
# the cells themselves.
_PERCENT_B_RANGE = (0.0, 100.0)
# A cell's step is also the precision it accepts: hundredths of a minute, tenths of %B.
_TIME_STEP = 0.01
_PERCENT_STEP = 0.1
# The programme tables' column widths, in pixels. The scouting table's four add up to
# the rail's table width at 1440 × 900 (303 px, measured in the browser); the
# candidate's two share the same width less the dynamic-row selector Streamlit puts in
# front of them.
_ROW_NUMBER_PX = 36
_TIME_PX = 84
_PERCENT_PX = 64
_CANDIDATE_TIME_PX = 120
_CANDIDATE_PERCENT_PX = 90

_MEASURED = "Measured marker"
_ESTIMATED = "Geometry estimate"
_FULLY_POROUS = "Fully porous"
_CORE_SHELL = "Core–shell (solid core)"
_BY_VOLUME = "Volume (mL)"
_BY_TIME = "Time (min)"

_UNTITLED = "Untitled session"

# SPEC §6 diagnostic 6's short form. One wording, wherever an output surface carries it,
# and the same two regimes as the long form: the predictions barely move, the fitted
# parameters do (`dead-time-from-geometry.md` §6).
_STAMP_SHORT = (
    "⚠️ Estimated t0 — retention here barely moves with it; the fitted S, k0 and N carry "
    "about a quarter of its error and must not be transferred to another flow or column "
    "(SPEC §6)."
)


# SPEC §6's *indicative, not decision-grade* stamp, short (#44 decision 8, #74). One
# wording wherever an output surface carries it, and deliberately narrower than the t0
# stamp's: this one downgrades Rs and the critical pair only, and says so, because SPEC
# §6 keeps the retention times shown as numbers at exactly the same condition.
_INDICATIVE_SHORT = (
    "🚫 Rs and the critical pair are indicative, not decision-grade — the LSS line was "
    "never pinned where these peaks are being predicted (SPEC §6). Retention times stay "
    "numbers; see the candidate warnings in the rail."
)

# What the status bar says for the same stamp. The bar is one line of small text and
# every field on it is a fragment, so the sentence above would not fit and would not
# read as a field if it did.
_INDICATIVE_STATUS = "Rs indicative — not decision-grade"

# The same downgrade reached by the other road (SPEC §6): no method-level guard fired,
# but a peak in the critical pair carries a low-k0 or wash-eluted badge, which downgrades
# the pairs that peak is in and only those. Its own reason, because the stamp's sentence
# — "the LSS line was never pinned where these peaks are being predicted" — is about the
# candidate, and this is about one peak.
_INDICATIVE_BY_BADGE = (
    "🚫 The critical pair is indicative, not decision-grade — one of its peaks carries a "
    "badge (see Flags, and the selected-peak panel for what it says). Every other pair "
    "on the resolution tab still stands; the Rs grade column says which (SPEC §6)."
)


class Keys:
    """Every widget's ``session_state`` key, in one place (ticket #21).

    Loading a session file means writing the restored values into the widgets before
    they are drawn, so each one needs a name that the loader and the widget agree on.
    Spelling those names as constants is what keeps the two ends from drifting: a typo
    in a string literal here does not raise, it silently leaves that one field on its
    default while every other field loads, which is the worst possible shape for the bug.

    The two programme tables (#73) are keyed by a stem and a nonce: the frame a table
    shows is held under the stem, and the nonce is bumped whenever that frame is
    *replaced* — a session loaded, a cell put back — so the editor is rebuilt from it
    rather than layering its last edits over the new frame (the peak table's rule).
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
    ARCHITECTURE = "particle_architecture"
    T0_SOURCE = "t0_source"
    T0 = "t0"
    T0_MARKER = "t0_marker"
    # The last value the geometry estimate wrote into the t0 field. Not a widget: it is
    # how a typed overwrite is told apart from the autofill it replaced.
    T0_AUTOFILL = "t0_autofill"
    DWELL_AS = "dwell_entered_as"
    DWELL_TIME = "dwell_time"
    DWELL_VOLUME = "dwell_volume"
    USE_N_ESTIMATE = "use_plate_count_estimate"
    PLATE_COUNT = "plate_count"
    # The rail's two programme tables (SPEC §7, v0.2, #73). Each holds the frame its
    # editor was built from; the candidate also remembers whether it has been typed
    # into, since until then it follows the scouting table.
    SCOUTING_FRAME = "scouting_frame"
    SCOUTING_NONCE = "scouting_nonce"
    CANDIDATE_FRAME = "candidate_frame"
    CANDIDATE_NONCE = "candidate_nonce"
    CANDIDATE_TOUCHED = "candidate_touched"

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
    _load_control()
    save_slot = st.sidebar.container()

    constants, t0_notices = _sidebar()

    # SPEC §4 makes the dwell required with no silent default: it belongs to the
    # instrument, a guessed one biases every prediction the same way, and this is the
    # one constant the spec singles out. So nothing is predicted until it is entered.
    if constants is None:
        st.title("hplcsim")
        st.warning(_DWELL_REQUIRED, icon="⚠️")
        # Loading still works from here: a file carries its own dwell, which is the
        # fastest way out of this screen and the reason the uploader is drawn above it.
        return

    # The rail carries a four-column table's worth of entry (#62); its share of the row
    # is a layout number, so it lives with the rest of them in `app.panels`.
    rail, main_view = st.columns(list(panels.RAIL_COLUMNS), gap="medium")

    with rail:
        scouting = _scouting_table()
        run1, run2 = scouting.entry.runs()
        read = _candidate_table(scouting.entry)
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

    # With no ramp on the candidate table there is nothing to predict; the seed stands
    # in so the inputs are whole, and `blocked` is what stops it being predicted.
    inputs = CockpitInputs.with_programme(
        method=constants.method,
        run1=run1,
        run2=run2,
        programme=read.programme or _seed_programme(scouting.entry),
        rows=tuple(rows),
        plate_count=constants.plate_count,
    )
    cockpit = run_cockpit(inputs, blocked=read.blocked)

    diagnostics = diagnose(inputs, cockpit)

    with save_slot:
        _save_control(inputs)
    with t0_notices:
        # SPEC §4's checks on the typed t0 — beside the field they are about, in the
        # sidebar, filled here because they are diagnostics like every other notice.
        _notices(diagnostics.method)
    with worksheet_slot:
        # SPEC §7's guided empty state, above the tabs rather than instead of them.
        # Step 2 asks for the peak table and SPEC §4's scouting-spacing warning is
        # painted on the fit tab before any peak is typed, so both have to stay
        # reachable — the guidance leads the main view rather than replacing it.
        if needs_guidance(cockpit):
            _worksheet(worksheet_steps(inputs, cockpit))
    with candidate_slot:
        # SPEC §6 and §7: the candidate-control inline warnings sit directly beneath the
        # candidate table, not in a tab the user may not have open. This slot carries
        # whatever `diagnostics.candidate` holds — diagnostic 1 today, and #72's
        # re-expression on s* with diagnostic 7 beside it once that lands.
        _notices(diagnostics.candidate)
    with summary_slot:
        _summary_panels(cockpit, diagnostics)
    with peaks_tab:
        _entry_notes(cockpit, diagnostics)
    with map_tab:
        _resolution_map(inputs.candidate)
    with fit_tab:
        _fit_tab(cockpit, diagnostics)
    with resolution_tab:
        _resolution_tab(cockpit, diagnostics)
    with chromatogram_slot:
        view = _chromatogram(cockpit, inputs, read, diagnostics)
    if view is not None:
        # The axis range is its own pinned strip (#62), between the chromatogram block
        # and the status bar — outside the block, because the block scrolls and boxes
        # inside it can only be reached by scrolling the very plot they act on. It is
        # appended to the main column here, after the block, rather than reserved with
        # the other slots: with no trace on screen there is nothing for it to act on,
        # and an empty bordered row is worse than no row.
        with main_view, st.container(key="hs-axis"):
            _axis_controls(view)

    _status_bar(cockpit, inputs, read, diagnostics)


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

    Every number box goes through :class:`~app.session_io.Restore`, against the same
    ``_*_RANGE`` the widget itself is built from. A file may legitimately hold a value
    no box on this screen can display — a 5 m column is a real column and the box stops
    at 1000 mm — and writing it in raw makes Streamlit raise on the rerun, replacing the
    page with a traceback rather than saying anything useful. The two programme tables
    are not boxes: they take the file's rows as they are.
    """
    method = session.method
    restore = Restore()
    # The file's shape crossing the screen's — the two peak tables as one — happens in
    # `inputs_from_session` and nowhere else.
    inputs = inputs_from_session(session)
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
            Keys.T0_MARKER: method.t0_marker or "",
            # The file stores the dwell as a time (SPEC §8), so the time is what comes
            # back. Dividing a volume out of it would be inventing the V_D that was
            # typed, at whatever the flow happens to be now — the conversion is an
            # entry boundary and is not meant to run backwards.
            Keys.DWELL_AS: _BY_TIME,
            Keys.DWELL_TIME: restore.within("dwell", method.t_dwell, *_DWELL_TIME_RANGE),
            Keys.USE_N_ESTIMATE: session.plate_count is None,
            # The two programme tables take the file's programmes as they are (SPEC §7,
            # §8): a table cell has no slider's end to squeeze to. The file already
            # refuses a %B outside 0–100. Each frame is *replaced*, so its nonce moves
            # too — the editor is rebuilt from the file rather than showing the file's
            # rows with the previous session's edits still layered over them.
            Keys.SCOUTING_FRAME: tables.scouting_frame(ScoutingEntry.from_runs(*session.runs)),
            Keys.SCOUTING_NONCE: st.session_state.get(Keys.SCOUTING_NONCE, 0) + 1,
            Keys.CANDIDATE_FRAME: tables.candidate_frame(points_from_programme(session.candidate)),
            Keys.CANDIDATE_NONCE: st.session_state.get(Keys.CANDIDATE_NONCE, 0) + 1,
            # A loaded candidate is the file's, whatever the scouting table says.
            Keys.CANDIDATE_TOUCHED: True,
            Keys.PEAK_FRAME: tables.peak_frame_from_rows(inputs.rows),
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
    # An undeclared architecture is an *absent* choice, and the selectbox shows that as
    # its placeholder only when its key holds nothing at all.
    st.session_state.pop(Keys.ARCHITECTURE, None)
    if method.particle_is_solid_core is not None:
        st.session_state[Keys.ARCHITECTURE] = (
            _CORE_SHELL if method.particle_is_solid_core else _FULLY_POROUS
        )
    # A restored estimate is treated as the autofill in place. With an architecture in
    # the file that means it is *recomputed* from the file's geometry on the same run —
    # the estimate is derived from inputs, so it recomputes on load exactly as the fit
    # does (SPEC §8), and a file written before a porosity constant changed comes back
    # at the current constant. Without an architecture there is nothing to recompute
    # from and the file's number stands, stamped as the estimate it was saved as.
    st.session_state.pop(Keys.T0_AUTOFILL, None)
    if not method.t0_is_measured:
        st.session_state[Keys.T0_AUTOFILL] = st.session_state[Keys.T0]
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


def _sidebar() -> tuple[MethodEntry | None, object]:
    """The method constants, or ``None`` while the required dwell is still unset.

    The second value is the container reserved beneath the t0 field for SPEC §4's
    dead-time notices, which ``main`` fills from the diagnostics once they exist.
    """
    with st.sidebar:
        st.header("Method constants")
        st.caption("Instrument and column — shared by both scouting runs and the candidate.")

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
        architecture = st.selectbox(
            "Packing architecture",
            [_FULLY_POROUS, _CORE_SHELL],
            index=None,
            placeholder="Choose — never inferred from the column name",
            key=Keys.ARCHITECTURE,
        )
        solid_core = None if architecture is None else architecture == _CORE_SHELL
        t0_source = st.radio(
            "t0 source",
            [_MEASURED, _ESTIMATED],
            horizontal=True,
            key=Keys.T0_SOURCE,
            on_change=_t0_source_chosen,
        )
        estimate = None
        if t0_source == _ESTIMATED:
            estimate = _autofill_t0(length, column_id, particle, flow, solid_core)
        t0 = st.number_input(
            "t0 (min)",
            *_T0_RANGE,
            _T0,
            step=0.05,
            format="%.4f",
            key=Keys.T0,
            on_change=_t0_typed,
        )
        marker: str | None = None
        if t0_source == _MEASURED:
            marker = st.text_input(
                "t0 marker",
                key=Keys.T0_MARKER,
                placeholder="uracil, apex — or: solvent front, first disturbance",
                help=(
                    "What was injected to measure t0, and which point of its trace was "
                    "read. A dead time without its marker has no provenance."
                ),
            )
        # SPEC §4's checks on the typed t0 are painted here, beside the field, from the
        # diagnostics `main` computes once everything is entered. Reserved now.
        t0_notices = st.container()
        if t0_source == _ESTIMATED:
            _estimate_caption(estimate)

        st.subheader("Dwell")
        t_dwell = _dwell(flow)
        if t_dwell is None:
            return None, t0_notices

        # The gradient is not here any more (SPEC §7, v0.2): its %B range and hold are
        # rows of the scouting table in the rail, beside the candidate they are read with.
        method = Method(
            t0=t0,
            t_dwell=t_dwell,
            flow=flow,
            column_length_mm=length,
            column_id_mm=column_id,
            particle_um=particle,
            temperature_c=temperature,
            t0_is_measured=t0_source == _MEASURED,
            particle_is_solid_core=solid_core,
            t0_marker=(marker or "").strip() or None,
        )

        st.subheader("Plate count N")
        plate_count = _plate_count_knob(method)

    return MethodEntry(method=method, plate_count=plate_count), t0_notices


def _autofill_t0(
    length: float, column_id: float, particle: float, flow: float, solid_core: bool | None
) -> DeadTimeEstimate | None:
    """Write the geometry estimate into the t0 field, when there is one to write.

    Runs before the field is drawn, which is the only moment a keyed widget's value can
    be set from this side. :func:`app.pipeline.t0_autofill` decides whether to; this
    only knows which keys hold what. No architecture, no estimate — the field keeps
    what it holds, and the caption says why (the estimator refuses to guess, #34).
    """
    if solid_core is None:
        return None
    geometry = Method(
        t0=_T0,
        t_dwell=0.0,
        flow=flow,
        column_length_mm=length,
        column_id_mm=column_id,
        particle_um=particle,
        particle_is_solid_core=solid_core,
    )
    estimate = estimate_t0(geometry)
    filled = t0_autofill(
        st.session_state.get(Keys.T0), st.session_state.get(Keys.T0_AUTOFILL), estimate.t0
    )
    if filled is not None:
        st.session_state[Keys.T0] = filled
        st.session_state[Keys.T0_AUTOFILL] = filled
    return estimate


def _t0_source_chosen() -> None:
    """Choosing the estimate starts a fresh autofill; choosing the marker keeps the field."""
    if st.session_state.get(Keys.T0_SOURCE) == _ESTIMATED:
        st.session_state.pop(Keys.T0_AUTOFILL, None)


def _t0_typed() -> None:
    """A value typed over the autofill is a measured one — the source follows the field.

    Runs as the widget's callback, before the rerun, which is the one place a widget
    that has already been drawn (the source radio) may have its state written.
    """
    if st.session_state.get(Keys.T0_SOURCE) != _ESTIMATED:
        return
    if st.session_state.get(Keys.T0) != st.session_state.get(Keys.T0_AUTOFILL):
        st.session_state[Keys.T0_SOURCE] = _MEASURED


def _estimate_caption(estimate: DeadTimeEstimate | None) -> None:
    """The band as a caption, and only a caption (#34, decision 3)."""
    if estimate is None:
        st.warning(
            "**Choose the packing architecture to get an estimate.** Total porosity "
            "differs by 16% between fully porous and core–shell packings, and the app "
            "will not guess which this column is. Until then the field keeps the value "
            "you typed, stamped as an estimate.",
            icon="⚠️",
        )
        return
    lo, hi = estimate.t0_band
    st.caption(
        f"t0 = ε_total · V_col / F = {estimate.porosity.value:.2f} × "
        f"{estimate.column_volume_ml:.3f} mL / F = **{estimate.t0:.3f} min** "
        f"({estimate.porosity.label}; band {lo:.3f}–{hi:.3f} min). Geometry leaves the "
        "plumbing out, so a marker would read a little above this. Type a measured value "
        "to replace it — the source follows the field."
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
    three_decimals = st.column_config.NumberColumn(format="%.3f", width="small")
    # A restored table arrives as a frame in state; an unloaded one is the blank frame,
    # exactly as before. The nonce in the key is what makes a *second* load land: the
    # editor's edits belong to its key, and reusing the key would leave them on top of
    # the new data. It is only ever bumped by `_restore`.
    edited = st.data_editor(
        st.session_state.get(Keys.PEAK_FRAME, tables.blank_peak_frame()),
        key=f"peak_table_{st.session_state.get(Keys.PEAK_TABLE_NONCE, 0)}",
        num_rows="dynamic",
        width="stretch",
        # Compact rows (#62): the peak table shares the screen with the pinned
        # chromatogram and the axis strip, and Streamlit's default row spends a third of
        # their budget on four peaks. The column names are the frame's own and are not
        # touched — `app.tables` reads the frame back by them.
        row_height=panels.TABLE_ROW_HEIGHT_PX,
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


def _scouting_table() -> tables.ScoutingRead:
    """The scouting programme as one No. / t₁ / t₂ / %B table (SPEC §7, v0.2, #45).

    One programme at two speeds: row 1 the start, row 2 the end of the initial hold,
    row 3 the end of each run's ramp, with a time column per run. It is read-mostly —
    row 1's times are the start of the run, row 2's second time and %B follow its
    first and row 1's — and a cell that follows another is *put back* when typed over:
    the frame the read says the table should show replaces the one it was built from,
    and the editor is rebuilt from it, rather than showing a value the run does not use.
    """
    st.markdown("### Scouting — as run")
    if Keys.SCOUTING_FRAME not in st.session_state:
        st.session_state[Keys.SCOUTING_FRAME] = tables.scouting_frame(_DEFAULT_SCOUTING)
    base = st.session_state[Keys.SCOUTING_FRAME]
    edited = st.data_editor(
        base,
        key=f"scouting_table_{st.session_state.get(Keys.SCOUTING_NONCE, 0)}",
        num_rows="fixed",
        hide_index=True,
        width="stretch",
        row_height=panels.TABLE_ROW_HEIGHT_PX,
        # Four columns in a rail 1.45 : 3.0 wide (#62): the widths are fixed in pixels
        # so the %B column is not the one that gets clipped, and they add up to the
        # table's width at 1440 × 900 with the row-number column narrowest.
        column_config={
            tables.NO: st.column_config.NumberColumn(width=_ROW_NUMBER_PX, disabled=True),
            tables.T1: _time_column(_TIME_PX),
            tables.T2: _time_column(_TIME_PX),
            tables.PERCENT_B: _percent_column(_PERCENT_PX),
        },
    )
    read = tables.scouting_read_from_frame(edited)
    if not tables.frames_agree(read.frame, edited):
        _replace_frame(Keys.SCOUTING_FRAME, Keys.SCOUTING_NONCE, read.frame)
        st.rerun()
    entry = read.entry
    st.caption(
        f"tG {entry.t_gradient1:g} / {entry.t_gradient2:g} min · hold {entry.hold:g} min · "
        f"{entry.percent_b_start:g} → {entry.percent_b_end:g} %B — row 2 follows row 1's %B."
    )
    for note in read.notes:
        st.warning(note, icon="⚠️")
    return read


def _candidate_table(scouting: ScoutingEntry) -> ProgrammeRead:
    """The candidate programme as a t / %B table with dynamic rows (SPEC §7, v0.2, #45).

    A segment is a row, a further segment a further row, and the count is open (#58).
    No tG slider: the cell steps with the keyboard. Until it is typed into, the table
    follows the scouting one — one ramp over the scouting range at tG 25 min, v0.1's
    opening candidate — and from the first edit on it is the reader's, until Reset.

    The frame the editor was built from is held in state and left alone while the
    reader types; the editor holds the edits and the read takes the edited rows. Only a
    put-back (row 1's time is the start of the run) replaces the frame.
    """
    st.markdown("### Candidate — predicted")
    seed = tables.candidate_frame(points_from_programme(_seed_programme(scouting)))
    touched = st.session_state.get(Keys.CANDIDATE_TOUCHED, False)
    base = st.session_state.get(Keys.CANDIDATE_FRAME)
    if base is None or (not touched and not tables.frames_agree(base, seed)):
        _replace_frame(Keys.CANDIDATE_FRAME, Keys.CANDIDATE_NONCE, seed)
        base = seed
    edited = st.data_editor(
        base,
        key=f"candidate_table_{st.session_state.get(Keys.CANDIDATE_NONCE, 0)}",
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        row_height=panels.TABLE_ROW_HEIGHT_PX,
        column_config={
            tables.T_CANDIDATE: _time_column(_CANDIDATE_TIME_PX),
            tables.PERCENT_B: _percent_column(_CANDIDATE_PERCENT_PX),
        },
    )
    if not tables.frames_agree(edited, base):
        # The reader has typed: from here on the table is theirs, not the scouting's.
        st.session_state[Keys.CANDIDATE_TOUCHED] = True
    read = programme_from_points(tables.candidate_points_from_frame(edited))
    shown = tables.candidate_frame(read.points)
    if not tables.frames_agree(shown, edited):
        st.session_state[Keys.CANDIDATE_TOUCHED] = True
        _replace_frame(Keys.CANDIDATE_FRAME, Keys.CANDIDATE_NONCE, shown)
        st.rerun()
    caption, reset = st.columns([3.2, 1.0], vertical_alignment="center")
    with caption:
        if read.programme is not None:
            st.caption(programme_summary(read.programme))
    with reset:
        st.button(
            "Reset",
            on_click=_reset_candidate,
            width="stretch",
            help="Back to one ramp over the scouting range at tG 25 min.",
        )
    for note in read.notes:
        st.warning(note, icon="⚠️")
    return read


def _time_column(width: int) -> object:
    # A column's `step` is the precision a cell accepts as well as its keyboard step
    # (Streamlit's own rule), so it matches the format: a method about to be written
    # down is 24.35 min, not the nearest tenth.
    return st.column_config.NumberColumn(
        min_value=0.0, step=_TIME_STEP, format="%.2f", required=True, width=width
    )


def _percent_column(width: int) -> object:
    return st.column_config.NumberColumn(
        min_value=_PERCENT_B_RANGE[0],
        max_value=_PERCENT_B_RANGE[1],
        step=_PERCENT_STEP,
        format="%g",
        required=True,
        width=width,
    )


def _seed_programme(scouting: ScoutingEntry) -> Programme:
    """One ramp over the scouting range at tG 25 min — v0.1's opening candidate."""
    return Programme.from_gradient(scouting.gradient(_TG_CANDIDATE))


def _replace_frame(frame_key: str, nonce_key: str, frame: object) -> None:
    """Replace a table's frame and move its nonce, so the editor is rebuilt from it."""
    st.session_state[frame_key] = frame
    st.session_state[nonce_key] = st.session_state.get(nonce_key, 0) + 1


def _reset_candidate() -> None:
    """Back to following the scouting table. A callback, so it lands before the redraw."""
    st.session_state[Keys.CANDIDATE_TOUCHED] = False
    st.session_state.pop(Keys.CANDIDATE_FRAME, None)
    st.session_state[Keys.CANDIDATE_NONCE] = st.session_state.get(Keys.CANDIDATE_NONCE, 0) + 1


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
    indicative = critical_pair_is_indicative(cockpit, diagnostics)
    st.markdown(
        panels.panel("Method summary", _summary_rows(cockpit, indicative)),
        unsafe_allow_html=True,
    )
    _peak_detail(cockpit, diagnostics)
    # SPEC §6 diagnostic 6 stamps *all* outputs, and the rail's two panels carry tR, k,
    # W½, N and Rs. The stamp is a caption beneath them rather than a row inside them,
    # because SPEC §7 enumerates what those panels hold.
    _stamp_caption(diagnostics)
    _indicative_caption(diagnostics, indicative)


def _summary_rows(cockpit: Cockpit, indicative: bool) -> list[Row]:
    resolution = cockpit.resolution
    if resolution is None or not resolution.peaks:
        return []

    rows = [Row("Peaks fitted", str(len(resolution.peaks)))]
    if cockpit.entry.untracked_count:
        rows.append(Row("Untracked", str(cockpit.entry.untracked_count), colour="#c77700"))

    critical = resolution.critical_pair
    if critical is not None:
        # SPEC §6's stamp names *Min. Rs and the critical pair*, and only those: the run
        # time and the minimum k on the same panel are retention, which the same
        # paragraph keeps shown as numbers. So the mark goes on the two labels it is
        # about rather than over the whole panel, and the caption beneath says why.
        mark = " (indicative)" if indicative else ""
        rows += [
            Row(f"Min. Rs{mark}", f"{critical.rs:.2f}", panels.resolution_colour(critical.rs)),
            Row(f"Critical pair{mark}", f"{critical.earlier.name} / {critical.later.name}"),
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
        row_height=panels.TABLE_ROW_HEIGHT_PX,
        column_config={
            "log10 k0": st.column_config.NumberColumn(format="%.2f"),
            "S": st.column_config.NumberColumn(format="%.2f"),
            "N": st.column_config.NumberColumn(format="%.0f"),
            tables.N_RATIO: st.column_config.NumberColumn(format="%.3f"),
        },
    )
    st.caption("log10 k0 is quoted at the scouting φ0; S is the base-10 slope (SPEC §3).")
    _window_readout(diagnostics)


def _window_readout(diagnostics: Diagnostics) -> None:
    """SPEC §6's per-peak composition-window readout — its own table on the fit tab.

    The per-peak fact behind diagnostic 1, whose tier is method-level: the rail says in
    one number how far outside the scouting bracket the candidate's steepness sits, and
    this says, peak by peak, which compositions the fit was actually shown and where the
    candidate is putting that peak against them. The same
    :class:`~app.diagnostics.CompositionWindow` objects are the chromatogram's whiskers,
    so the table and the plot cannot disagree.
    """
    if not diagnostics.windows:
        return
    st.markdown("**Calibrated composition windows**")
    st.dataframe(
        tables.composition_window_frame(diagnostics.windows),
        width="stretch",
        hide_index=True,
        row_height=panels.TABLE_ROW_HEIGHT_PX,
        column_config={
            tables.WINDOW_LOW: st.column_config.NumberColumn(format="%.1f"),
            tables.WINDOW_HIGH: st.column_config.NumberColumn(format="%.1f"),
            tables.WINDOW_WIDTH: st.column_config.NumberColumn(format="%.1f"),
            tables.WINDOW_CANDIDATE: st.column_config.NumberColumn(format="%.1f"),
            # Not "small": the cell reads "0.18 widths below", and at Streamlit's small
            # width the browser clipped it to "0.18 widths belo" at 1440 × 900.
            tables.WINDOW_POSITION: st.column_config.TextColumn(width="medium"),
        },
    )
    st.caption(
        "The **calibrated composition window** is the two elution compositions the two "
        "scouting runs actually showed this peak, and its width is ln β / S_e. "
        "**Elutes at** is where the candidate brings the peak off. A peak outside its "
        "own window is being extrapolated, by the distance under Position (SPEC §6, "
        "diagnostic 1). The same numbers are the chromatogram's whiskers."
    )


def _resolution_tab(cockpit: Cockpit, diagnostics: Diagnostics) -> None:
    if cockpit.resolution is None:
        st.caption("Nothing fitted yet — enter a tR in both runs for at least one peak.")
        return
    # SPEC §6: diagnostic 5 is a "result banner", diagnostic 6 an "output stamp".
    _notices(diagnostics.banners)
    _stamp_caption(diagnostics)
    # SPEC §6's *indicative, not decision-grade* stamp, in full. The resolution tab is
    # the surface the stamp is about — every Rs it downgrades is on it — so this is
    # where the whole sentence is painted, and the rail and the status bar carry the
    # short form, exactly as diagnostic 6 is handled on the fit tab.
    if diagnostics.indicative is not None:
        _notices((diagnostics.indicative,))
    st.dataframe(
        tables.prediction_frame(cockpit, diagnostics.badges),
        width="stretch",
        hide_index=True,
        row_height=panels.TABLE_ROW_HEIGHT_PX,
        column_config={
            "tR (min)": st.column_config.NumberColumn(format="%.3f"),
            "W½ (min)": st.column_config.NumberColumn(format="%.4f"),
            "k at elution": st.column_config.NumberColumn(format="%.2f"),
            tables.FLAGS: st.column_config.TextColumn(width="small"),
        },
    )
    st.dataframe(
        tables.resolution_frame(cockpit, diagnostics),
        width="stretch",
        hide_index=True,
        row_height=panels.TABLE_ROW_HEIGHT_PX,
        column_config={
            "ΔtR (min)": st.column_config.NumberColumn(format="%.3f"),
            "Rs": st.column_config.NumberColumn(format="%.2f"),
            tables.GRADE: st.column_config.TextColumn(width="small"),
        },
    )


def _status_bar(
    cockpit: Cockpit, inputs: CockpitInputs, read: ProgrammeRead, diagnostics: Diagnostics
) -> None:
    fields = [_candidate_line(inputs, read)]
    critical = cockpit.resolution.critical_pair if cockpit.resolution else None
    if critical is not None:
        fields.append(f"Rs {critical.rs:.2f}")
    fields.append(_programme_kind(inputs))
    # SPEC §6 diagnostic 6 stamps *all* outputs, so it reaches the one strip of the
    # screen that is on show whichever tab is open.
    if any(stamp.code == "estimated_t0" for stamp in diagnostics.stamps):
        fields.append("t0 estimated — fitted S, k0, N not transferable")
    # SPEC §6's other output stamp, on the same always-visible strip and for the same
    # reason: an Rs read off any tab is read with the bar in view. The Rs on the bar is
    # the critical pair's, so it is the critical pair that is asked — a badged peak in
    # that pair downgrades this number with no method-level guard firing at all.
    if critical_pair_is_indicative(cockpit, diagnostics):
        fields.append(_INDICATIVE_STATUS)
    # A keyed container, so this row has the same shape as the other two pinned rows and
    # one CSS rule can reach all three wrappers (#79). Addressing the markdown chain
    # instead took four `:has()` selectors and broke the moment Streamlit renested it.
    with st.container(key="hs-status"):
        st.markdown(panels.status_bar(fields), unsafe_allow_html=True)


def _candidate_line(inputs: CockpitInputs, read: ProgrammeRead) -> str:
    """The candidate in one line, or the fact that there is none to predict yet."""
    if read.programme is None:
        return "candidate — no ramp yet"
    return programme_summary(inputs.target)


def _programme_kind(inputs: CockpitInputs) -> str:
    programme = inputs.programme
    if programme is None or len(programme.segments) == 1:
        return "RP gradient — linear, single segment"
    return f"RP gradient — {len(programme.segments)} segments, piecewise linear"


def _chromatogram(
    cockpit: Cockpit, inputs: CockpitInputs, read: ProgrammeRead, diagnostics: Diagnostics
) -> chromatogram.AxisView | None:
    """The pinned trace of SPEC §7. Everything around the plot earns its pixels.

    This block is sticky, so its height is screen the reader cannot scroll away. The
    condition, the area caveat and diagnostic 6's stamp all still have to appear — they
    are on one caption line beside the title rather than three stacked rows beneath it.

    Returns the axis view the trace was drawn on, so that the caller can draw the axis
    strip with it in the strip's own pinned row (#62); ``None`` when there is no trace.
    """
    st.markdown(f"**Predicted chromatogram** — {_candidate_line(inputs, read)}")
    if cockpit.resolution is None or not cockpit.resolution.peaks:
        st.caption("The chromatogram appears once at least one peak is fitted.")
        return None
    asked = _axis_request()
    trace = chromatogram.chromatogram(
        cockpit.resolution.peaks,
        cockpit.shares,
        gradient_end=gradient_end_time(inputs.method, inputs.target),
        # An x axis asked to end past the run needs trace to draw out there, not just a
        # wider window onto a baseline that stops halfway across the plot.
        extend_to=asked.x_end,
    )
    view = chromatogram.axis_view(trace, asked)
    # SPEC §7's programme overlay, always on. Built against the trace's own extent so
    # both programmes span the plot rather than stopping where the last segment does,
    # and from `diagnostics.windows`, which is what the fit tab's readout is built from
    # too — one set of numbers, two surfaces.
    overlay = chromatogram.programme_overlay(
        inputs.method,
        inputs.target,
        (inputs.run1, inputs.run2),
        diagnostics.windows,
        cockpit.predicted_by_name,
        extend_to=float(trace.time[-1]),
    )
    st.plotly_chart(chromatogram.figure(trace, view=view, overlay=overlay), width="stretch")
    notes = [
        "Candidate solid, scouting pair dashed, on the right-hand %B axis; each peak "
        "is marked at its elution composition, whiskered by its calibrated window.",
        "Peak areas scaled by the measured area shares."
        if trace.scaled_by_area
        else "Not every peak carries an area — all peaks drawn to the same height.",
    ]
    if diagnostics.stamps:
        notes.append(_STAMP_SHORT)
    st.caption("  ·  ".join(notes))
    # The "this window hides a peak" notes belong to the axis boxes, but they are painted
    # here, in the scrolling block above them, rather than in the strip: the strip is a
    # fixed-height pinned row and a warning painted inside it would be clipped by the
    # very rule that lets the block pin exactly on top of it.
    for note in view.notes:
        st.warning(note, icon="⚠️")
    return view


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
    """Both ends of both axes, always on show, in the strip's own pinned row (#62).

    No expander. Where each axis starts and ends is the first thing a reader checks
    before believing a trace, and behind a collapsed expander it was neither on show nor
    — the strip being inside the scrolling chromatogram block — reachable without
    scrolling the plot away. The strip is a row of its own instead, and the plot is drawn
    at `CHROMATOGRAM_HEIGHT` to pay for it out of the same pinned budget.

    Until the reader touches a box, the boxes are re-seeded from the run every rerun, so
    a longer candidate grows the window with it. Once touched, the entries stay put —
    a pinned window is what the reader asked for — until Reset.
    """
    touched = st.session_state.get(Keys.AXIS_TOUCHED, False)
    y_step = view.run_y[1] / 20.0 or 0.05
    boxes = (
        ("x start (min)", Keys.X_AXIS_START, view.run_x[0], 0.1, "%.2f"),
        ("x end (min)", Keys.X_AXIS_END, view.run_x[1], 0.1, "%.2f"),
        ("y start", Keys.Y_AXIS_START, view.run_y[0], y_step, "%.4f"),
        ("y end", Keys.Y_AXIS_END, view.run_y[1], y_step, "%.4f"),
    )
    # Issue #57's frozen window. Re-seeding used to *pop* these keys and pass the run's
    # value as the widget's default — but a keyed widget's default is only ever the value
    # for a key the browser does not already hold, and the browser holds it across the
    # rerun. So the window stayed the length of an earlier candidate, and a longer one
    # then drew its late peaks outside the axis. Writing the run's value into the key is
    # what pushes it to the browser; with the key always written, the widget takes its
    # value from state and is not given a default at all.
    for _label, key, value, _step, _fmt in boxes:
        if not touched or key not in st.session_state:
            st.session_state[key] = float(value)
    cols = st.columns([0.9, 1.0, 1.0, 1.0, 1.0, 0.7], vertical_alignment="bottom")
    with cols[0]:
        st.markdown(
            panels.axis_strip_title(view.run_x[1], view.run_y[1] / chromatogram.Y_HEADROOM),
            unsafe_allow_html=True,
        )
    for col, (label, key, _value, step, fmt) in zip(cols[1:], boxes, strict=False):
        with col:
            st.number_input(
                label,
                min_value=0.0 if key in (Keys.X_AXIS_START, Keys.X_AXIS_END) else None,
                step=step,
                format=fmt,
                key=key,
                on_change=_mark_axis_touched,
            )
    with cols[5]:
        st.button("Reset", on_click=_reset_axis_range, width="stretch")


def _mark_axis_touched() -> None:
    """From here on the boxes are the reader's, not the run's."""
    st.session_state[Keys.AXIS_TOUCHED] = True


def _reset_axis_range() -> None:
    """Back to the whole run. A callback, so it lands before the widgets are redrawn.

    Clearing the touched flag is the whole of it: `_axis_controls` re-seeds every key
    from the run whenever the flag is down. The keys are deliberately *not* popped —
    popping them is the mechanism behind #57, since a key the browser still holds is
    not re-pushed by a widget default, and leaving that call here would keep the bug one
    refactor away from coming back on the Reset path.
    """
    st.session_state[Keys.AXIS_TOUCHED] = False


def _stamp_caption(diagnostics: Diagnostics) -> None:
    """SPEC §6 diagnostic 6's short form, on an output surface that is not the fit tab.

    A stamp is meant to be short. The fit tab carries the whole explanation once; every
    other surface carries a line saying the outputs on it inherit an estimate, so that
    no output is read without it and no output is buried under it.
    """
    if diagnostics.stamps:
        st.caption(_STAMP_SHORT)


def _indicative_caption(diagnostics: Diagnostics, indicative: bool) -> None:
    """SPEC §6's *indicative, not decision-grade* stamp, short, beside a stamped output.

    Same shape as :func:`_stamp_caption` and for the same reason: the resolution tab
    carries the whole sentence once, and every other surface showing an Rs carries a
    line short enough to be read with the number rather than instead of it.

    ``indicative`` is about the *critical pair*, which is the Rs this panel leads with,
    so the caption follows the two rows it explains rather than the method-level stamp.
    The wording then says which road the downgrade came by.
    """
    if not indicative:
        return
    st.caption(_INDICATIVE_SHORT if diagnostics.indicative is not None else _INDICATIVE_BY_BADGE)


main()
