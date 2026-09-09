"""The screen's memory has exactly one door, and the door is checked (ticket #93).

Two things nothing in this suite could see before. The first is the *seam*: with the
accessor in :mod:`app.screen_state`, every other file naming ``session_state`` is a way
round it, and that is a grep. The second is the *ordering rule* — restore before any
widget is drawn — which was a comment in ``main()`` enforced by nothing, and which #57
and #79 both shipped past because ``AppTest`` has no frontend to notice a widget that
ignored the state written after it.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import screen_state
from app.screen_state import Keys, ScreenStateError
from hplcsim.model import Gradient, Method, Peak, Programme, Run
from hplcsim.session import Session

ROOT = Path(__file__).resolve().parent.parent
# The one module allowed to name it. Everything else on this list goes through the door.
OWNER = ROOT / "app" / "screen_state.py"
SEARCHED = "session_state"


def _guarded_files() -> list[Path]:
    """Every file the seam covers: `app/`, `scripts/` and the entry point at the root."""
    candidates = [
        # `rglob`, not `glob`: CLAUDE.md's rule says *no other file in* `app/`, and the
        # first `app/<subpackage>/` would walk straight out of a non-recursive glob.
        *(ROOT / "app").rglob("*.py"),
        *(ROOT / "scripts").rglob("*.py"),
        ROOT / "streamlit_app.py",
    ]
    return sorted(path for path in candidates if path != OWNER)


def test_only_screen_state_touches_session_state() -> None:
    """The seam, asserted by grep — across app/, scripts/ and streamlit_app.py.

    Deliberately blind to whether the hit is code or prose. A docstring that tells the
    next reader this file writes ``session_state`` is wrong in the same way the call
    would be, and the two are equally cheap to fix; a grep that had to tell them apart
    would be a grep with a hole in it.
    """
    files = _guarded_files()
    assert len(files) > 5, f"the seam is scanning almost nothing: {files}"

    offenders = {
        path.relative_to(ROOT).as_posix(): [
            number
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if SEARCHED in line
        ]
        for path in files
    }
    offenders = {path: lines for path, lines in offenders.items() if lines}

    assert not offenders, (
        f"{SEARCHED} is named outside {OWNER.relative_to(ROOT).as_posix()}: {offenders}. "
        "Reach it through the accessor — screen_state.get/put/pop/has — so the ordering "
        "guard in screen_state.restore sees every read."
    )


# A session with nothing in common with the app's opening values, so a field that failed
# to land cannot pass by looking like one that did.
_GRADIENT = Gradient(phi0=0.10, phif=0.90, t_gradient=0.0, t_init=1.25)
_SESSION = Session(
    session_name="Reopened",
    method=Method(
        t0=1.42,
        t_dwell=0.55,
        flow=1.2,
        column_length_mm=150.0,
        column_id_mm=4.6,
        particle_um=3.5,
        temperature_c=30.0,
        particle_is_solid_core=True,
    ),
    runs=(
        Run(Gradient(phi0=0.10, phif=0.90, t_gradient=20.0, t_init=1.25), name="tG20"),
        Run(Gradient(phi0=0.10, phif=0.90, t_gradient=60.0, t_init=1.25), name="tG60"),
    ),
    peaks=(
        Peak(t_r_run1=9.855, t_r_run2=20.831, name="Acetanilide"),
        Peak(t_r_run1=11.592, t_r_run2=25.932, name="Ketoprofen"),
    ),
    candidate=Programme.from_gradient(Gradient(phi0=0.10, phif=0.90, t_gradient=37.5, t_init=2.5)),
)


def _screen(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """A screen with no browser behind it: `session_state` as a plain dict.

    `screen_state` reaches Streamlit for the state proxy and for nothing else — no
    widget, no layout — so the whole of it can be exercised against a dict.
    """
    state: dict[str, object] = {}
    monkeypatch.setattr(screen_state, "st", SimpleNamespace(session_state=state))
    screen_state.begin_run()
    return state


def test_restore_after_a_read_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ordering is a value now, not a habit."""
    _screen(monkeypatch)
    # What a widget drawn ahead of the session controls does: it reads its own key
    # first, and from then on it can never see what a loaded file writes there.
    screen_state.get(Keys.T0)

    with pytest.raises(ScreenStateError) as raised:
        screen_state.restore(_SESSION)

    assert Keys.T0 in str(raised.value)
    assert Keys.SESSION_NAME not in str(raised.value), "only the keys actually read"


def test_restore_before_any_read_lands(monkeypatch: pytest.MonkeyPatch) -> None:
    """The guard is a guard, not a wall: the ordering `main()` uses still loads."""
    state = _screen(monkeypatch)

    screen_state.restore(_SESSION)

    assert state[Keys.SESSION_NAME] == "Reopened"
    assert state[Keys.T0] == pytest.approx(1.42)
    assert state[Keys.LENGTH] == pytest.approx(150.0)
    assert state[Keys.ARCHITECTURE] == screen_state.CORE_SHELL
    assert state[Keys.CANDIDATE_TOUCHED] is True


def test_a_run_forgets_the_reads_of_the_last_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """`begin_run` is why a widget callback's reads cannot block the next run's load.

    Callbacks fire at the head of the *next* rerun, before the script body — so a
    `_t0_typed` that read the t0 key would otherwise refuse every file loaded after it.
    """
    _screen(monkeypatch)
    screen_state.get(Keys.T0)

    screen_state.begin_run()

    screen_state.restore(_SESSION)  # no ScreenStateError


def test_a_widget_taking_its_key_arms_the_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """`claim` is the half of the guard the accessor cannot see for itself.

    Creating a widget is Streamlit taking the key and refusing every later write to it,
    and it happens inside Streamlit's own API. Without `claim` the guard would be inert
    for exactly the keys that matter most — the eleven no code path ever reads.
    """
    _screen(monkeypatch)
    # What `st.number_input("Column length (mm)", ..., key=Keys.LENGTH)` does.
    assert screen_state.claim(Keys.LENGTH) == Keys.LENGTH, "the widget still gets its key"

    with pytest.raises(ScreenStateError) as raised:
        screen_state.restore(_SESSION)

    assert Keys.LENGTH in str(raised.value)


def test_every_widget_key_in_the_entry_point_is_claimed() -> None:
    """A widget added without `claim` is a widget the guard cannot see — so grep for it.

    The same reason the seam above is a grep: this ticket exists because a rule written
    in a comment and enforced by nothing decayed twice (#57, #79). `key=Keys.X` is how
    every named widget key reaches Streamlit; the axis boxes pass a loop variable and
    are covered by the accessor read directly above them.
    """
    # `key=Keys.X` is a widget taking a key. `touched_key=Keys.X` and `nonce_key=Keys.X`
    # are arguments to `screen_state.follow` naming state no widget ever takes, and they
    # end in the same four characters — so the match is anchored on what precedes `key`.
    binds_a_widget_key = re.compile(r"(?<!\w)key=Keys\.")
    unclaimed = [
        f"{number}: {line.strip()}"
        for number, line in enumerate(
            (ROOT / "streamlit_app.py").read_text(encoding="utf-8").splitlines(), 1
        )
        if binds_a_widget_key.search(line) and "claim(" not in line
    ]

    assert not unclaimed, (
        f"widget keys that bypass screen_state.claim: {unclaimed}. Wrap the key — "
        "`key=screen_state.claim(Keys.X)` — so restore()'s ordering guard can see the "
        "widget take it."
    )


# --- the takeover rule: a control that follows a source until the reader takes it over ---
#
# One rule for the two controls that follow something (SPEC §7): the candidate table
# follows the scouting seed, the axis boxes follow the run's computed range. Before it was
# one rule it was two spellings — `not touched and differs` on the table, `not touched or
# missing` on the boxes — and nothing compared them. These pin the unified rule, including
# the one case where the two old spellings differed.


def test_follow_seeds_a_key_that_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nothing on screen yet: the source is what the control starts from."""
    state = _screen(monkeypatch)

    result = screen_state.follow(Keys.X_AXIS_END, 12.0, touched_key=Keys.AXIS_TOUCHED)

    assert result == pytest.approx(12.0)
    assert state[Keys.X_AXIS_END] == pytest.approx(12.0)


def test_follow_leaves_a_taken_over_control_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    """Once the reader has typed, the source stops writing — that is the whole rule."""
    state = _screen(monkeypatch)
    screen_state.put(Keys.X_AXIS_END, 3.0)
    screen_state.take_over(Keys.AXIS_TOUCHED)

    result = screen_state.follow(Keys.X_AXIS_END, 12.0, touched_key=Keys.AXIS_TOUCHED)

    assert result == pytest.approx(3.0), "the reader's value, not the run's"
    assert state[Keys.X_AXIS_END] == pytest.approx(3.0)


def test_follow_reseeds_a_following_control_when_the_source_moves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#57's frozen window, in one assertion: a longer run must widen an untouched box."""
    state = _screen(monkeypatch)
    screen_state.put(Keys.X_AXIS_END, 3.0)

    result = screen_state.follow(Keys.X_AXIS_END, 12.0, touched_key=Keys.AXIS_TOUCHED)

    assert result == pytest.approx(12.0)
    assert state[Keys.X_AXIS_END] == pytest.approx(12.0)


def test_follow_does_not_write_when_the_source_has_not_moved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The one case the two old spellings disagreed on — and it is a no-op either way.

    The axis boxes used to re-write the run's value into the key on every rerun while the
    control was following, whether or not it had changed; the candidate table only wrote
    when the frame differed. Unifying on the table's rule means the boxes now skip a write
    that put the same value back, so nothing a reader can observe changes.
    """
    state = _screen(monkeypatch)
    held: list[float] = [12.0]
    screen_state.put(Keys.X_AXIS_END, held)

    result = screen_state.follow(Keys.X_AXIS_END, [12.0], touched_key=Keys.AXIS_TOUCHED)

    assert result is held, "equal to the source, so the stored value is left where it is"
    assert state[Keys.X_AXIS_END] is held


def test_follow_moves_a_frames_nonce_only_when_it_replaces_the_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced frame needs a new editor identity; an unreplaced one must not get one."""
    state = _screen(monkeypatch)
    screen_state.put(Keys.CANDIDATE_FRAME, "old")
    screen_state.put(Keys.CANDIDATE_NONCE, 4)

    screen_state.follow(
        Keys.CANDIDATE_FRAME,
        "new",
        touched_key=Keys.CANDIDATE_TOUCHED,
        nonce_key=Keys.CANDIDATE_NONCE,
    )
    assert state[Keys.CANDIDATE_FRAME] == "new"
    assert state[Keys.CANDIDATE_NONCE] == 5, "the editor is rebuilt from the new frame"

    screen_state.follow(
        Keys.CANDIDATE_FRAME,
        "new",
        touched_key=Keys.CANDIDATE_TOUCHED,
        nonce_key=Keys.CANDIDATE_NONCE,
    )
    assert state[Keys.CANDIDATE_NONCE] == 5, "no replacement, so no new identity"


def test_follow_uses_the_comparison_it_is_given(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two frames differ in dtype without reading differently — `==` is the wrong test."""
    state = _screen(monkeypatch)
    screen_state.put(Keys.CANDIDATE_FRAME, "1.0")

    screen_state.follow(
        Keys.CANDIDATE_FRAME,
        "1",
        touched_key=Keys.CANDIDATE_TOUCHED,
        same=lambda left, right: float(left) == float(right),
    )

    assert state[Keys.CANDIDATE_FRAME] == "1.0", "the comparison said they agree"


def test_follow_arms_the_guard_for_the_key_it_seeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """`follow` reads before it writes, so what it seeds is inside `restore`'s guard.

    It bites on the candidate frame, which a loaded file writes. It does not bite on the
    axis boxes, and cannot: SPEC §8 keeps the file to inputs, the axis view is not one,
    and `restore` writes nothing there to conflict with — which is the same fact that
    makes a restored session take the table over and leave the boxes following.
    """
    _screen(monkeypatch)

    screen_state.follow(Keys.CANDIDATE_FRAME, "seed", touched_key=Keys.CANDIDATE_TOUCHED)

    with pytest.raises(ScreenStateError) as raised:
        screen_state.restore(_SESSION)
    assert Keys.CANDIDATE_FRAME in str(raised.value)


def test_restore_does_not_write_the_axis_boxes(monkeypatch: pytest.MonkeyPatch) -> None:
    """The asymmetry in `restore`, pinned as the persistence fact it follows from."""
    state = _screen(monkeypatch)

    screen_state.restore(_SESSION)

    assert state[Keys.CANDIDATE_TOUCHED] is True, "the file's candidate, not the seed's"
    assert Keys.AXIS_TOUCHED not in state, "no window in the file, so nothing to pin"
    assert Keys.X_AXIS_END not in state


def test_take_over_and_release_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset puts a control back to following its source."""
    _screen(monkeypatch)
    assert screen_state.taken_over(Keys.AXIS_TOUCHED) is False

    screen_state.take_over(Keys.AXIS_TOUCHED)
    assert screen_state.taken_over(Keys.AXIS_TOUCHED) is True

    screen_state.release(Keys.AXIS_TOUCHED)
    assert screen_state.taken_over(Keys.AXIS_TOUCHED) is False
