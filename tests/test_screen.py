"""The diagnostics of SPEC §6 actually reach the rendered page (ticket #20).

This file exists because of what ticket #19 learned the expensive way: **tests do not
see the screen.** Three defects shipped past 200 passing tests and were found by a
person looking at a browser — the app not starting at all, panels clipping their own
values, the status bar hidden behind the sidebar. `tests/test_diagnostics.py` proves the
thresholds are right; nothing in it proves a single one of them is ever painted.

So this runs the real entry point through Streamlit's own `AppTest`, drives the widgets
a user drives, and asserts the notices appear. It reaches the diagnostics that need no
peak table — `st.data_editor` cannot be driven from `AppTest` — which is diagnostic 1
and diagnostic 6. The rest are asserted in the logic layer and placed by code this file
does at least execute end to end.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from app.diagnostics import STRONG_EXTRAPOLATION
from hplcsim.model import Gradient, Method, Peak, Run
from hplcsim.session import (
    Session,
    UntrackedPeak,
    save_session,
)

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

ENTRY_POINT = Path(__file__).resolve().parent.parent / "streamlit_app.py"

# The sidebar's dwell field opens empty (SPEC §4), and nothing is predicted until it is
# filled — so every test here starts by filling it, exactly as a user must.
_DWELL_ML = 0.375

# A phrase from the dwell gate's own wording, to recognise that screen by.
_DWELL_REQUIRED_MARK = "Enter the dwell before anything can be predicted"

_RESTORED_GRADIENT = Gradient(phi0=0.10, phif=0.90, t_gradient=0.0, t_init=1.25)

# Deliberately not the app's opening values — every field differs from its default, so a
# field that failed to load cannot pass by looking like one that did. The peaks are the
# lab pair at these gradients, plus one half-paired row: the shape ticket #18 could not
# save, carried all the way to the screen's untracked count.
RESTORED = Session(
    session_name="Reopened",
    method=Method(
        t0=1.42,
        t_dwell=0.55,
        flow=1.2,
        column_length_mm=150.0,
        column_id_mm=4.6,
        particle_um=3.5,
        temperature_c=30.0,
    ),
    runs=(
        Run(replace(_RESTORED_GRADIENT, t_gradient=20.0), name="tG20"),
        Run(replace(_RESTORED_GRADIENT, t_gradient=60.0), name="tG60"),
    ),
    peaks=(
        Peak(t_r_run1=9.855, t_r_run2=20.831, name="Acetanilide"),
        Peak(t_r_run1=11.592, t_r_run2=25.932, name="Ketoprofen"),
    ),
    untracked=(UntrackedPeak(name="Impurity B", t_r_run1=13.204),),
    candidate=replace(_RESTORED_GRADIENT, t_gradient=37.5, t_init=2.5),
)


def _running_app() -> object:
    app = AppTest.from_file(str(ENTRY_POINT), default_timeout=120).run()
    assert not app.exception, app.exception
    _number(app, "Dwell volume V_D (mL)").set_value(_DWELL_ML).run()
    assert not app.exception, app.exception
    return app


def _number(app: object, label: str) -> object:
    """One number input, by the label a user reads — not by an index that shifts."""
    widgets = [w for w in app.number_input if w.label == label]  # type: ignore[attr-defined]
    assert len(widgets) == 1, f"{label!r} matched {len(widgets)} inputs"
    return widgets[0]


def _radio(app: object, label: str) -> object:
    widgets = [w for w in app.radio if w.label == label]  # type: ignore[attr-defined]
    assert len(widgets) == 1, f"{label!r} matched {len(widgets)} radios"
    return widgets[0]


def _text_input(app: object, label: str) -> object:
    widgets = [w for w in app.text_input if w.label == label]  # type: ignore[attr-defined]
    assert len(widgets) == 1, f"{label!r} matched {len(widgets)} text inputs"
    return widgets[0]


def _messages(app: object) -> dict[str, list[str]]:
    return {
        "info": [element.value for element in app.info],  # type: ignore[attr-defined]
        "warning": [element.value for element in app.warning],  # type: ignore[attr-defined]
        "error": [element.value for element in app.error],  # type: ignore[attr-defined]
    }


def _extrapolation(app: object, severity: str) -> list[str]:
    return [text for text in _messages(app)[severity] if "outside the" in text]


def test_a_candidate_inside_the_bracket_paints_no_extrapolation_notice() -> None:
    """The app opens at tG = 25 inside its 15–45 default bracket — a quiet screen."""
    app = _running_app()
    assert _extrapolation(app, "info") == []
    assert _extrapolation(app, "error") == []


def test_the_gentle_extrapolation_flag_reaches_the_page_as_an_info_notice() -> None:
    app = _running_app()
    app.slider[0].set_value(60.0).run()  # type: ignore[attr-defined]

    (notice,) = _extrapolation(app, "info")
    assert "1.33×" in notice
    assert _extrapolation(app, "error") == []


def test_the_strong_extrapolation_warning_reaches_the_page_as_an_error() -> None:
    """Past ~2× outside the bracket SPEC §6 escalates, and the page must escalate with it."""
    app = _running_app()
    app.slider[0].set_value(120.0).run()  # type: ignore[attr-defined]

    (notice,) = _extrapolation(app, "error")
    assert f"{120.0 / 45.0:.2f}×" in notice
    assert STRONG_EXTRAPOLATION < 120.0 / 45.0
    assert _extrapolation(app, "info") == []


def test_an_estimated_t0_stamps_the_status_bar_whatever_tab_is_open() -> None:
    """SPEC §6 diagnostic 6 stamps *all* outputs, so it reaches the always-visible strip."""
    app = _running_app()
    status = [m.value for m in app.markdown if "hs-status" in m.value]  # type: ignore[attr-defined]
    assert status and not any("t0 estimated" in bar for bar in status)

    _radio(app, "t0 source").set_value("Geometry estimate").run()
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    stamped = [m.value for m in app.markdown if "hs-status" in m.value]  # type: ignore[attr-defined]
    assert any("t0 estimated" in bar for bar in stamped)

    # SPEC §6.6 says *all* outputs, and the rail's panels are outputs too.
    captions = [c.value for c in app.caption]  # type: ignore[attr-defined]
    assert any("Estimated t0" in caption for caption in captions)


def test_a_narrow_scouting_pair_paints_the_spacing_notice_before_any_peak_is_typed() -> None:
    """SPEC §4's spacing warning is about the experiment, so it does not wait for results.

    Two scouting runs 20 and 15 min apart are β = 1.33 — under SPEC §4's 2.5 warning
    tier — and the page says so with the peak table still empty.
    """
    app = _running_app()
    assert not any("β" in text for text in _messages(app)["warning"])

    _number(app, "Run 2 tG").set_value(20.0).run()
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    (notice,) = [text for text in _messages(app)["warning"] if "Scouting runs" in text]
    assert "β = 1.33" in notice


# --- the candidate's two-widget controls ----------------------------------------------
#
# Each candidate control is a slider and a number box over one value, so the pair can
# disagree in a way no logic-layer test would see: the box writes the slider's state and
# the slider writes the box's, and either callback going missing leaves a screen showing
# two different tG values with the prediction quietly following the wrong one.


def _candidate_tg(app: object) -> object:
    return _number(app, "Candidate tG (min)")


def test_the_candidate_box_takes_a_value_finer_than_the_slider_can_reach() -> None:
    """The point of the box: 24.35 min on a slider that steps in halves."""
    app = _running_app()
    _candidate_tg(app).set_value(24.35).run()
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert app.slider[0].value == 24.35  # type: ignore[attr-defined]
    assert _candidate_tg(app).value == 24.35
    status = [m.value for m in app.markdown if "hs-status-cell" in m.value]  # type: ignore[attr-defined]
    assert any("tG 24.35 min" in bar for bar in status), "the typed tG never reached the prediction"


def test_dragging_the_slider_writes_the_box_back() -> None:
    app = _running_app()
    app.slider[0].set_value(60.0).run()  # type: ignore[attr-defined]
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert _candidate_tg(app).value == 60.0


def test_the_method_hold_still_reseeds_the_candidate_hold() -> None:
    """Keying the widgets must not cost the seeding the unkeyed ones had for free."""
    app = _running_app()
    _number(app, "Initial hold (min)").set_value(2.0).run()
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert app.slider[1].value == 2.0  # type: ignore[attr-defined]
    assert _number(app, "Candidate initial hold (min)").value == 2.0


# --- the session file, on screen (SPEC §8, ticket #21) --------------------------------
#
# This is the half of #21 the logic layer cannot reach. `tests/test_session_io.py` proves
# a screen becomes a file and a file becomes a screen; none of it proves the download
# button exists, that an uploaded file is ever read, or — the failure that actually bites
# — that a restored value lands in the widget it belongs to. A key misspelled between
# `K` and a widget call does not raise: it leaves that one field on its default while
# every other field loads, and only the rendered page shows it.


def _uploader(app: object) -> object:
    (widget,) = app.file_uploader  # type: ignore[attr-defined]
    return widget


def _download(app: object) -> object:
    widgets = [w for w in app.download_button if w.label == "Save session"]  # type: ignore[attr-defined]
    assert len(widgets) == 1, f"Save session matched {len(widgets)} buttons"
    return widgets[0]


def _download_url(app: object) -> str:
    """The download's media URL, which is a hash of the bytes it would hand over.

    The bytes themselves are out of reach: `AppTest` runs with no Streamlit runtime,
    so the media file manager that holds a download's content does not exist and the
    proto carries only this URL. What the URL is good for is *change* — two sessions
    that differ produce different content and so different URLs — which is enough to
    show the button is wired to the session on screen rather than to a stale one.
    The file's own content is asserted in `tests/test_session_io.py`.
    """
    return str(_download(app).proto.url)  # type: ignore[attr-defined]


def test_the_save_button_is_offered_once_the_session_can_be_written() -> None:
    app = _running_app()
    assert _download_url(app).endswith(".json")
    # The refusal path would have replaced the button with a warning (SPEC §8, #18).
    assert not any("Not saveable yet" in text for text in _messages(app)["warning"])


def test_the_download_follows_the_session_on_screen_rather_than_a_stale_one() -> None:
    """The save slot is filled after the peak table is read, out of render order."""
    app = _running_app()
    before = _download_url(app)

    _number(app, "Run 2 tG").set_value(30.0).run()
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert _download_url(app) != before


def test_naming_the_session_changes_the_file_that_would_be_written() -> None:
    """AC-1 asks for the name in the file *and* in the suggested filename. The
    filename is not in the proto, so it is `session_filename`'s test that pins it;
    this pins the other half — that the name typed here reaches the document."""
    app = _running_app()
    before = _download_url(app)

    _text_input(app, "Session name").set_value("Impurity screen").run()
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert _download_url(app) != before


def test_uploading_a_session_restores_every_widget_it_names() -> None:
    """The one that catches a key typo: each restored value in its own widget.

    Every field here is set to something the app does *not* open on, so a field that
    quietly kept its default fails rather than passing by coincidence.
    """
    app = _running_app()
    _uploader(app).upload("s.json", save_session(RESTORED).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert _number(app, "Column length (mm)").value == pytest.approx(150.0)
    assert _number(app, "Column i.d. (mm)").value == pytest.approx(4.6)
    assert _number(app, "Particle size (µm)").value == pytest.approx(3.5)
    assert _number(app, "Flow F (mL/min)").value == pytest.approx(1.2)
    assert _number(app, "Temperature (°C)").value == pytest.approx(30.0)
    assert _number(app, "t0 (min)").value == pytest.approx(1.42)
    assert _number(app, "%B start").value == pytest.approx(10.0)
    assert _number(app, "%B end").value == pytest.approx(90.0)
    assert _number(app, "Initial hold (min)").value == pytest.approx(1.25)
    assert _number(app, "Run 1 tG").value == pytest.approx(20.0)
    assert _number(app, "Run 2 tG").value == pytest.approx(60.0)
    assert _text_input(app, "Session name").value == "Reopened"


def test_uploading_a_session_restores_the_dwell_as_the_time_the_file_stores() -> None:
    """V_D ÷ F is an entry boundary and does not run backwards (SPEC §8) — so the
    radio moves to the time, rather than a volume being invented at the current flow."""
    app = _running_app()
    _uploader(app).upload("s.json", save_session(RESTORED).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    assert _radio(app, "Dwell entered as").value == "Time (min)"
    assert _number(app, "Dwell time t_D (min)").value == pytest.approx(RESTORED.method.t_dwell)


def test_uploading_a_session_restores_the_candidate_through_both_of_its_widgets() -> None:
    """The reseed in `_slider_with_box` fires on the restored method hold and would
    otherwise overwrite the candidate hold that came out of the same file."""
    app = _running_app()
    _uploader(app).upload("s.json", save_session(RESTORED).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    assert _candidate_tg(app).value == pytest.approx(37.5)
    assert app.slider[0].value == pytest.approx(37.5)  # type: ignore[attr-defined]
    assert _number(app, "Candidate initial hold (min)").value == pytest.approx(2.5)
    assert app.slider[1].value == pytest.approx(2.5)  # type: ignore[attr-defined]


def test_a_restored_estimated_t0_still_stamps_the_outputs() -> None:
    """A restored input has to reach the diagnostics, not just the widget it sits in."""
    estimated = replace(RESTORED, method=replace(RESTORED.method, t0_is_measured=False))
    app = _running_app()
    _uploader(app).upload("s.json", save_session(estimated).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    status = [m.value for m in app.markdown if "hs-status" in m.value]  # type: ignore[attr-defined]
    assert any("t0 estimated" in bar for bar in status)


def test_a_restored_session_saves_back_to_an_identical_file() -> None:
    """Round trip through the actual screen: load, then save, and get the file back.

    Compared by the content-hash URL, which is the only handle on a download's bytes
    from here — the app is made to save the same session twice, once from a fresh
    upload and once after a detour through a different tG, and the two must agree.
    """
    app = _running_app()
    _uploader(app).upload("s.json", save_session(RESTORED).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]
    restored = _download_url(app)

    _number(app, "Run 2 tG").set_value(30.0).run()
    assert _download_url(app) != restored
    _number(app, "Run 2 tG").set_value(60.0).run()

    assert _download_url(app) == restored


def test_a_corrupt_file_is_refused_by_name_and_leaves_the_screen_alone() -> None:
    """SPEC §8's hard rejection, worded to name the field — and nothing else disturbed."""
    app = _running_app()
    _uploader(app).upload("s.json", b'{"schema_version": 99, "app_version": "0.1.0"}')
    app.run()  # type: ignore[attr-defined]
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert any("schema_version 99" in text for text in _messages(app)["error"])
    assert _number(app, "t0 (min)").value == pytest.approx(0.6)  # still the default


def test_unparseable_json_is_refused_without_crashing_the_page() -> None:
    app = _running_app()
    _uploader(app).upload("s.json", b"{not json at all")
    app.run()  # type: ignore[attr-defined]
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert any("not valid JSON" in text for text in _messages(app)["error"])


def test_the_uploader_is_reachable_before_the_dwell_gate() -> None:
    """A file carries its own dwell, so loading is the fastest way past that screen —
    which only works if the uploader is drawn above the early return."""
    app = AppTest.from_file(str(ENTRY_POINT), default_timeout=120).run()

    assert any(_DWELL_REQUIRED_MARK in text for text in _messages(app)["warning"])
    _uploader(app).upload("s.json", save_session(RESTORED).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert not any(_DWELL_REQUIRED_MARK in text for text in _messages(app)["warning"])
    assert _number(app, "t0 (min)").value == pytest.approx(1.42)


# --- the guided empty state (SPEC §7) -------------------------------------------------


def _worksheet_html(app: object) -> list[str]:
    # The stylesheet mentions the class too, so match the rendered element's own tag.
    marker = '<div class="hs-worksheet">'
    return [m.value for m in app.markdown if marker in m.value]  # type: ignore[attr-defined]


def test_an_empty_screen_paints_the_numbered_worksheet() -> None:
    (worksheet,) = _worksheet_html(_running_app())
    for step in ("1. Method and instrument", "2. Two scouting runs", "3. Read the fit", "4."):
        assert step in worksheet


def test_the_worksheet_gives_way_once_a_session_with_peaks_is_loaded() -> None:
    """SPEC §7's "cockpit layout thereafter", with the peaks arriving via the file —
    which is the only way this suite can fill the peak table at all."""
    app = _running_app()
    _uploader(app).upload("s.json", save_session(RESTORED).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    assert _worksheet_html(app) == []


def test_a_loaded_half_paired_row_reaches_the_screen_as_the_untracked_count() -> None:
    """#18's known gap, closed end to end: the row survives the file and is counted."""
    app = _running_app()
    _uploader(app).upload("s.json", save_session(RESTORED).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    (notice,) = [text for text in _messages(app)["info"] if "untracked" in text]
    assert "1 untracked — not fitted" in notice
    assert "Impurity B" in notice
