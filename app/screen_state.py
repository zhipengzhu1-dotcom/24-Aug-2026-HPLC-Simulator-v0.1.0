"""The screen's own memory: every ``session_state`` touch in one module (ticket #93).

Streamlit's ``st.session_state`` is ambient global state. It was reached from about
fifteen functions in the entry point, which is the one file mypy does not check, and the
rule that keeps it correct — *restore before any widget is drawn* — was written in a
comment and enforced by nothing. #57 and #79 both shipped green: ``AppTest`` has no
frontend, so a widget that ignored the state written after it is invisible to pytest.

So the state is behind a door here instead. Three things live on the other side of it:

* :class:`Keys` — every name a widget answers to, including the three data-editor keys
  that used to be built as raw f-strings at their call sites and so escaped the registry
  the class docstring claims to be.
* the accessor — :func:`get`, :func:`put`, :func:`pop`, :func:`has` and the nonce pair.
  ``tests/test_screen_state.py`` asserts by grep that nothing else in ``app/``,
  ``scripts/`` or ``streamlit_app.py`` names ``session_state`` at all.
* :func:`restore` — SPEC §8's load, moved here whole, and the guard that makes its
  ordering rule a value rather than a habit.

This is the one module in ``app/`` that imports Streamlit, and it imports nothing of it
but the state proxy: no widget is created here, no layout is placed here. The entry point
keeps the widgets; what it no longer keeps is the state they are written into.

The numbers a widget and :func:`restore` must agree on live here too, and only those:
the eight ``*_RANGE`` clamps, the option labels a restored file picks by value, and the
four geometry fallbacks. A file may legitimately hold a value no box on the screen can
display, and ``Restore`` squeezes it to the range the box is built from; if the two ends
were named in two files they would be two numbers, and the clamp would stop being a
clamp. A number this module never reads is a widget default and stays with the widget —
which is why ``PLATE_COUNT_RANGE`` is here and the plate count's own default is not.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from app import tables
from app.entry import ScoutingEntry, points_from_programme
from app.session_io import Restore, inputs_from_session
from hplcsim.session import Session

# The four fields of the driver's Acquity H-Class / CORTECS 2.1×100 method
# (validation/method.csv) that a session file is allowed to leave out, and so the four
# `restore` needs a fallback for. The rest of that method — the flow and the t0 — are
# widget defaults with no restore behind them and stay in the entry point.
COLUMN_LENGTH_MM = 100.0
COLUMN_ID_MM = 2.1
PARTICLE_UM = 1.6
TEMPERATURE_C = 45.0

# Every bounded widget's range, named once. The widget call spreads it and `restore`
# clamps to it, so a file carrying a value past the end of a slider cannot reach the
# widget — Streamlit raises on that, and the whole page becomes a traceback (found by
# `/code-review` on ticket #21). The two ends have to be the same numbers or the clamp
# is not a clamp, which is the only reason these are constants.
LENGTH_RANGE = (1.0, 1000.0)
COLUMN_ID_RANGE = (0.05, 50.0)
PARTICLE_RANGE = (0.5, 50.0)
FLOW_RANGE = (0.001, 20.0)
TEMPERATURE_RANGE = (-20.0, 200.0)
T0_RANGE = (0.001, 100.0)
DWELL_TIME_RANGE = (0.0, 100.0)
PLATE_COUNT_RANGE = (100.0, 1_000_000.0)

# What the radios and selectboxes offer. A restored session picks one of them by value,
# so the wording is shared with the widget rather than repeated beside it.
MEASURED = "Measured marker"
ESTIMATED = "Geometry estimate"
FULLY_POROUS = "Fully porous"
CORE_SHELL = "Core–shell (solid core)"
BY_VOLUME = "Volume (mL)"
BY_TIME = "Time (min)"


class ScreenStateError(RuntimeError):
    """The screen was driven in an order that silently loses state.

    Not a user-facing refusal and not an exception to CLAUDE.md's warnings-over-blocks:
    nothing a chromatographer can type reaches it. It is raised only by a *code* ordering
    that Streamlit would otherwise swallow — see :func:`restore`.
    """


class Keys:
    """Every widget's ``session_state`` key, in one place (ticket #21, moved by #93).

    Loading a session file means writing the restored values into the widgets before
    they are drawn, so each one needs a name that the loader and the widget agree on.
    Spelling those names as constants is what keeps the two ends from drifting: a typo
    in a string literal here does not raise, it silently leaves that one field on its
    default while every other field loads, which is the worst possible shape for the bug.

    The two programme tables (#73) are keyed by a stem and a nonce: the frame a table
    shows is held under the stem, and the nonce is bumped whenever that frame is
    *replaced* — a session loaded, a cell put back — so the editor is rebuilt from it
    rather than layering its last edits over the new frame (the peak table's rule). The
    three data editors' full keys are built by the three methods at the foot of this
    class; built at the call site as f-strings, as they were until #93, they were exactly
    the string literals this registry exists to abolish.
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
    # Whether the reader has touched any of the four. Until they have, the boxes follow
    # the run — a keyed widget keeps its first value across reruns otherwise, and the
    # window would silently stay the length of the *previous* candidate's run.
    AXIS_TOUCHED = "axis_touched"

    @staticmethod
    def peak_table(nonce: int) -> str:
        """The peak editor's key for this nonce (:data:`PEAK_TABLE_NONCE`)."""
        return f"peak_table_{nonce}"

    @staticmethod
    def scouting_table(nonce: int) -> str:
        """The scouting editor's key for this nonce (:data:`SCOUTING_NONCE`)."""
        return f"scouting_table_{nonce}"

    @staticmethod
    def candidate_table(nonce: int) -> str:
        """The candidate editor's key for this nonce (:data:`CANDIDATE_NONCE`)."""
        return f"candidate_table_{nonce}"


# The keys read so far this run, held in `session_state` itself rather than in a module
# global: one Python process serves every browser session hitting the server, so a global
# would be shared between two chromatographers with two different screens open.
_READS = "_screen_state_reads"


def begin_run() -> None:
    """Start a fresh script run: nothing has been read yet.

    The first line of ``main()``. Widget callbacks fire at the head of the *next* rerun,
    before the script body, and the reads they make belong to the run that is over — this
    is what drops them, and why the read set is never captured anywhere.
    """
    st.session_state[_READS] = set()


def _reads() -> set[str]:
    """The read set for this run, created on demand so a touch is never unrecorded."""
    reads = st.session_state.get(_READS)
    if not isinstance(reads, set):
        reads = set()
        st.session_state[_READS] = reads
    return reads


def get(key: str, default: object = None) -> object:
    """Read a key, recording the read for :func:`restore`'s guard."""
    _reads().add(key)
    return st.session_state.get(key, default)


def claim(key: str) -> str:
    """Register a widget's key as taken this run, and hand it straight back to it.

    Every ``key=`` a widget is given goes through here. Creating a widget is Streamlit
    reading and then owning that key — after it, ``session_state`` writes to the key are
    refused by Streamlit itself, with a traceback where the page was — but it happens
    inside Streamlit's own widget API, which this module never sees. Without this the
    guard in :func:`restore` would cover only the keys some code path happens to read
    through the accessor, and would be inert for the eleven that no code reads at all.
    """
    _reads().add(key)
    return key


def has(key: str) -> bool:
    """Whether a key is set. A read: the answer is state the caller then acts on."""
    _reads().add(key)
    return key in st.session_state


def put(key: str, value: object) -> None:
    """Write a key. Not a read — writing is what :func:`restore` is guarding."""
    st.session_state[key] = value


def pop(key: str, default: object = None) -> object:
    """Remove a key and return what it held."""
    _reads().add(key)
    return st.session_state.pop(key, default)


def nonce(key: str) -> int:
    """A table's nonce, 0 until it has been bumped."""
    value = get(key, 0)
    return value if isinstance(value, int) else 0


def bump_nonce(key: str) -> None:
    """Move a table's nonce on, so its editor is rebuilt from the frame beside it."""
    put(key, nonce(key) + 1)


def taken_over(touched_key: str) -> bool:
    """Whether the reader has taken a control over from the source it follows."""
    return bool(get(touched_key, False))


def take_over(touched_key: str) -> None:
    """From here on the control is the reader's, not its source's."""
    put(touched_key, True)


def release(touched_key: str) -> None:
    """Reset: the control follows its source again.

    Only the flag. What else a Reset needs is the control's own business — a frame's
    identity has to move with it, and the axis keys must deliberately *not* be popped
    (#57: a key the browser still holds is not re-pushed by a widget default).
    """
    put(touched_key, False)


def follow(
    key: str,
    source: object,
    *,
    touched_key: str,
    same: Callable[[Any, Any], bool] | None = None,
    nonce_key: str | None = None,
) -> object:
    """Seed ``key`` from ``source`` unless the reader has taken the control over.

    One rule for both controls that follow something (SPEC §7): the candidate table
    follows the scouting seed, the axis boxes follow the run's computed range. Seed when
    the key is missing, or when the control is still following and what is on screen
    differs from the source — ``missing or (following and differs)``. Returns what is in
    state afterwards, so the caller need not read it back.

    ``same`` compares two values when ``==`` will not do it (two frames differ in dtype
    without reading differently — :func:`app.tables.frames_agree`). ``nonce_key`` moves a
    table's nonce whenever the frame is replaced, so the editor is rebuilt from it rather
    than showing the new frame with the old edits layered over.

    It reads ``key`` before it writes it, so any control it seeds is inside
    :func:`restore`'s ordering guard — which bites on the candidate frame, a key a loaded
    file does write. It does not bite on the axis boxes: SPEC §8 keeps the session file to
    inputs, the axis view is not one, and ``restore`` writes nothing there to conflict with.
    That is also why a restored session takes the candidate table over and leaves the boxes
    following — the file has a candidate programme in it and no window.
    """
    if not has(key):
        return _seed(key, source, nonce_key)
    current = get(key)
    if taken_over(touched_key):
        return current
    agrees = same(current, source) if same is not None else current == source
    return current if agrees else _seed(key, source, nonce_key)


def _seed(key: str, source: object, nonce_key: str | None) -> object:
    put(key, source)
    if nonce_key is not None:
        bump_nonce(nonce_key)
    return source


def restore(session: Session) -> None:
    """Write a loaded session into the widgets, under the keys they answer to (SPEC §8).

    This is the half of the round trip :mod:`app.session_io` deliberately does not do:
    the translation between the file's shape and the screen's is logic and lives there,
    while *which widget holds which value* is a fact about the screen and lives here.

    Every number box goes through :class:`~app.session_io.Restore`, against the same
    ``*_RANGE`` the widget itself is built from. A file may legitimately hold a value no
    box on this screen can display — a 5 m column is a real column and the box stops at
    1000 mm — and writing it in raw makes Streamlit raise on the rerun, replacing the
    page with a traceback rather than saying anything useful. The two programme tables
    are not boxes: they take the file's rows as they are.

    **The guard.** Restoring writes widget state, and state written after a widget has
    been created for this run is state that widget never sees — silently, with the file's
    values on screen in some fields and the old session's in others. Nothing checked
    that until now. A widget drawn ahead of the uploader takes its key first, through
    :func:`claim`, and any code reading one takes it through :func:`get`; either way, a
    key already taken this run that this call is about to write means the ordering has
    broken. That raises :class:`ScreenStateError` naming the keys, rather than loading
    two thirds of a file behind Streamlit's own traceback. No user input can reach it —
    only an edit to ``main()``.
    """
    # Snapshot first: everything below is itself a read, and a call must not trip over
    # its own footprints.
    already_read = frozenset(_reads())

    method = session.method
    clamp = Restore()
    # The file's shape crossing the screen's — the two peak tables as one — happens in
    # `inputs_from_session` and nowhere else.
    inputs = inputs_from_session(session)
    values: dict[str, object] = {
        Keys.SESSION_NAME: session.session_name,
        Keys.LENGTH: clamp.within(
            "column length", method.column_length_mm or COLUMN_LENGTH_MM, *LENGTH_RANGE
        ),
        Keys.COLUMN_ID: clamp.within(
            "column i.d.", method.column_id_mm or COLUMN_ID_MM, *COLUMN_ID_RANGE
        ),
        Keys.PARTICLE: clamp.within(
            "particle size", method.particle_um or PARTICLE_UM, *PARTICLE_RANGE
        ),
        Keys.FLOW: clamp.within("flow", method.flow, *FLOW_RANGE),
        Keys.TEMPERATURE: clamp.within(
            "temperature",
            TEMPERATURE_C if method.temperature_c is None else method.temperature_c,
            *TEMPERATURE_RANGE,
        ),
        Keys.T0_SOURCE: MEASURED if method.t0_is_measured else ESTIMATED,
        Keys.T0: clamp.within("t0", method.t0, *T0_RANGE),
        Keys.T0_MARKER: method.t0_marker or "",
        # The file stores the dwell as a time (SPEC §8), so the time is what comes
        # back. Dividing a volume out of it would be inventing the V_D that was
        # typed, at whatever the flow happens to be now — the conversion is an
        # entry boundary and is not meant to run backwards.
        Keys.DWELL_AS: BY_TIME,
        Keys.DWELL_TIME: clamp.within("dwell", method.t_dwell, *DWELL_TIME_RANGE),
        Keys.USE_N_ESTIMATE: session.plate_count is None,
        # The two programme tables take the file's programmes as they are (SPEC §7,
        # §8): a table cell has no slider's end to squeeze to. The file already
        # refuses a %B outside 0–100. Each frame is *replaced*, so its nonce moves
        # too — the editor is rebuilt from the file rather than showing the file's
        # rows with the previous session's edits still layered over them.
        Keys.SCOUTING_FRAME: tables.scouting_frame(ScoutingEntry.from_runs(*session.runs)),
        Keys.SCOUTING_NONCE: nonce(Keys.SCOUTING_NONCE) + 1,
        Keys.CANDIDATE_FRAME: tables.candidate_frame(points_from_programme(session.candidate)),
        Keys.CANDIDATE_NONCE: nonce(Keys.CANDIDATE_NONCE) + 1,
        # A loaded candidate is the file's, whatever the scouting table says.
        Keys.CANDIDATE_TOUCHED: True,
        Keys.PEAK_FRAME: tables.peak_frame_from_rows(inputs.rows),
        # A fresh identity for the data editor. Its state belongs to its key, so
        # reusing the key would show the loaded frame's columns with the previous
        # session's edits still layered over them.
        Keys.PEAK_TABLE_NONCE: nonce(Keys.PEAK_TABLE_NONCE) + 1,
    }
    if session.plate_count is not None:
        values[Keys.PLATE_COUNT] = clamp.within(
            "plate count N", float(session.plate_count), *PLATE_COUNT_RANGE
        )
    if method.particle_is_solid_core is not None:
        values[Keys.ARCHITECTURE] = CORE_SHELL if method.particle_is_solid_core else FULLY_POROUS
    # A restored estimate is treated as the autofill in place. With an architecture in
    # the file that means it is *recomputed* from the file's geometry on the same run —
    # the estimate is derived from inputs, so it recomputes on load exactly as the fit
    # does (SPEC §8), and a file written before a porosity constant changed comes back
    # at the current constant. Without an architecture there is nothing to recompute
    # from and the file's number stands, stamped as the estimate it was saved as.
    if not method.t0_is_measured:
        values[Keys.T0_AUTOFILL] = values[Keys.T0]
    # Every warning `Restore` gathered above, so this is the last value computed.
    values[Keys.LOAD_NOTE] = clamp.note
    # Cleared rather than written, and cleared either way: an undeclared architecture is
    # an *absent* choice, and the selectbox shows that as its placeholder only when its
    # key holds nothing at all. Same for an autofill the file does not re-establish.
    cleared = (Keys.ARCHITECTURE, Keys.T0_AUTOFILL)

    # Derived from the writes themselves rather than listed beside them, so a field added
    # to the load cannot be added without the guard covering it.
    _refuse_if_already_read(already_read, set(values) | set(cleared))

    for key in cleared:
        pop(key)
    st.session_state.update(values)


def _refuse_if_already_read(already_read: frozenset[str], about_to_write: set[str]) -> None:
    """Raise if the run has already read a key this restore is about to write."""
    offenders = sorted(already_read & about_to_write)
    if offenders:
        raise ScreenStateError(
            "restore() ran after the screen had already read "
            f"{', '.join(offenders)} — a widget drawn before the session controls "
            "would never see the values a loaded file writes into it. The session "
            "controls come first in main(), before every other widget."
        )
