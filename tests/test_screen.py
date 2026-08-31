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

from pathlib import Path

import pytest

from app.diagnostics import STRONG_EXTRAPOLATION

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

ENTRY_POINT = Path(__file__).resolve().parent.parent / "streamlit_app.py"

# The sidebar's dwell field opens empty (SPEC §4), and nothing is predicted until it is
# filled — so every test here starts by filling it, exactly as a user must.
_DWELL_ML = 0.375


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
