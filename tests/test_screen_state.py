"""The screen's memory has exactly one door, and the door is checked (ticket #93).

Two things nothing in this suite could see before. The first is the *seam*: with the
accessor in :mod:`app.screen_state`, every other file naming ``session_state`` is a way
round it, and that is a grep. The second is the *ordering rule* — restore before any
widget is drawn — which was a comment in ``main()`` enforced by nothing, and which #57
and #79 both shipped past because ``AppTest`` has no frontend to notice a widget that
ignored the state written after it.
"""

from __future__ import annotations

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
    unclaimed = [
        f"{number}: {line.strip()}"
        for number, line in enumerate(
            (ROOT / "streamlit_app.py").read_text(encoding="utf-8").splitlines(), 1
        )
        if "key=Keys." in line and "claim(" not in line
    ]

    assert not unclaimed, (
        f"widget keys that bypass screen_state.claim: {unclaimed}. Wrap the key — "
        "`key=screen_state.claim(Keys.X)` — so restore()'s ordering guard can see the "
        "widget take it."
    )
