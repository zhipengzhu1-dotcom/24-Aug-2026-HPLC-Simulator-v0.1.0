"""The diagnostics of SPEC §6 actually reach the rendered page (ticket #20).

This file exists because of what ticket #19 learned the expensive way: **tests do not
see the screen.** Three defects shipped past 200 passing tests and were found by a
person looking at a browser — the app not starting at all, panels clipping their own
values, the status bar hidden behind the sidebar. `tests/test_diagnostics.py` proves the
thresholds are right; nothing in it proves a single one of them is ever painted.

So this runs the real entry point through Streamlit's own `AppTest`, drives the widgets
a user drives, and asserts the notices appear. `st.data_editor` cannot be driven from
`AppTest`, and since #73 the rail's condition is two of them: the scouting and candidate
programme tables are *seeded* here through the session-state frames the entry point
builds each editor from, which is the same road a loaded session file takes. What a
browser does to a cell is `tests/test_rail.py`'s to assert on the frames, and the
Playwright screenshots in the ticket's PR are what proves the editor itself.
"""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import pytest

from app.diagnostics import STRONG_WINDOW_WIDTHS
from app.entry import ProgrammePoint, ScoutingEntry, points_from_programme
from app.screen_state import Keys
from app.tables import (
    COMPOUND,
    FLAGS,
    PERCENT_B,
    T1,
    T2,
    T_CANDIDATE,
    candidate_frame,
    scouting_frame,
)
from hplcsim.model import Gradient, Method, Peak, PeakRow, Programme, Run, Segment
from hplcsim.session import (
    Session,
    save_session,
)
from lab_data import (
    LAB_MEASURED_PEAKS,
    LAB_METHOD,
    LAB_RUN1,
    LAB_RUN2,
    LAB_RUN6_PROGRAMME,
    LAB_RUN7,
)

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

ENTRY_POINT = Path(__file__).resolve().parent.parent / "streamlit_app.py"

# The sidebar's dwell field opens empty (SPEC §4), and nothing is predicted until it is
# filled — so every test here starts by filling it, exactly as a user must.
_DWELL_ML = 0.375

# What the rail opens on (validation/method.csv's scouting pair).
_DEFAULT_SCOUTING = ScoutingEntry(
    percent_b_start=5.0, percent_b_end=95.0, hold=0.5, t_gradient1=15.0, t_gradient2=45.0
)

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
        particle_is_solid_core=True,
        t0_marker="thiourea, apex",
    ),
    runs=(
        Run(replace(_RESTORED_GRADIENT, t_gradient=20.0), name="tG20"),
        Run(replace(_RESTORED_GRADIENT, t_gradient=60.0), name="tG60"),
    ),
    peaks=(
        Peak(t_r_run1=9.855, t_r_run2=20.831, name="Acetanilide"),
        Peak(t_r_run1=11.592, t_r_run2=25.932, name="Ketoprofen"),
    ),
    untracked=(PeakRow(name="Impurity B", t_r_run1=13.204),),
    candidate=Programme.from_gradient(replace(_RESTORED_GRADIENT, t_gradient=37.5, t_init=2.5)),
)

# The same candidate at a tG no v0.1 slider reached; a table cell holds it (#73).
_WILD_CANDIDATE = Programme.from_gradient(replace(_RESTORED_GRADIENT, t_gradient=500.0, t_init=2.5))


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


def _selectbox(app: object, label: str) -> object:
    widgets = [w for w in app.selectbox if w.label == label]  # type: ignore[attr-defined]
    assert len(widgets) == 1, f"{label!r} matched {len(widgets)} selectboxes"
    return widgets[0]


def _messages(app: object) -> dict[str, list[str]]:
    return {
        "info": [element.value for element in app.info],  # type: ignore[attr-defined]
        "warning": [element.value for element in app.warning],  # type: ignore[attr-defined]
        "error": [element.value for element in app.error],  # type: ignore[attr-defined]
    }


def _extrapolation(app: object, severity: str) -> list[str]:
    return [text for text in _messages(app)[severity] if "outside the" in text]


def _seed_scouting(app: object, entry: ScoutingEntry) -> None:
    """Put a scouting programme into the table, the way a loaded file does."""
    app.session_state[Keys.SCOUTING_FRAME] = scouting_frame(entry)  # type: ignore[attr-defined]
    app.run()  # type: ignore[attr-defined]
    assert not app.exception, app.exception  # type: ignore[attr-defined]


def _seed_candidate(app: object, *rows: tuple[float, float]) -> None:
    """Put candidate rows into the table, as typed — so the table stops following."""
    points = tuple(ProgrammePoint(t_min=t, percent_b=b) for t, b in rows)
    app.session_state[Keys.CANDIDATE_FRAME] = candidate_frame(points)  # type: ignore[attr-defined]
    app.session_state[Keys.CANDIDATE_TOUCHED] = True  # type: ignore[attr-defined]
    app.run()  # type: ignore[attr-defined]
    assert not app.exception, app.exception  # type: ignore[attr-defined]


def _candidate_rows(app: object) -> list[tuple[float, float]]:
    frame = app.session_state[Keys.CANDIDATE_FRAME]  # type: ignore[attr-defined]
    return list(zip(frame[T_CANDIDATE].tolist(), frame[PERCENT_B].tolist(), strict=True))


def _scouting_columns(app: object) -> dict[str, list[float]]:
    frame = app.session_state[Keys.SCOUTING_FRAME]  # type: ignore[attr-defined]
    return {column: frame[column].tolist() for column in (T1, T2, PERCENT_B)}


def _status_bar(app: object) -> str:
    (bar,) = [m.value for m in app.markdown if 'class="hs-status"' in m.value]  # type: ignore[attr-defined]
    return str(bar)


def test_a_candidate_inside_the_bracket_paints_no_extrapolation_notice() -> None:
    """The app opens at tG = 25 inside its 15–45 default bracket — a quiet screen."""
    app = _running_app()
    assert _extrapolation(app, "info") == []
    assert _extrapolation(app, "error") == []


def test_the_gentle_extrapolation_flag_reaches_the_page_as_an_info_notice() -> None:
    """Row 3 of the candidate table typed to end at 60.5 min: tG 60 against the 15–45 pair."""
    app = _running_app()
    _seed_candidate(app, (0.0, 5.0), (0.5, 5.0), (60.5, 95.0))

    (notice,) = _extrapolation(app, "info")
    assert "1.33×" in notice
    assert _extrapolation(app, "error") == []


def test_the_strong_extrapolation_warning_reaches_the_page_as_an_error() -> None:
    """Past ~2× outside the bracket SPEC §6 escalates, and the page must escalate with it."""
    app = _running_app()
    _seed_candidate(app, (0.0, 5.0), (0.5, 5.0), (120.5, 95.0))

    (notice,) = _extrapolation(app, "error")
    assert f"{120.0 / 45.0:.2f}×" in notice
    assert math.log(120.0 / 45.0, 3.0) > STRONG_WINDOW_WIDTHS  # 0.89 window-widths at β = 3
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


# --- SPEC §4's geometry fallback for t0 (ticket #24) -------------------------------------


def _t0_sidebar_texts(app: object) -> list[str]:
    messages = _messages(app)
    captions = [c.value for c in app.caption]  # type: ignore[attr-defined]
    return messages["info"] + messages["warning"] + messages["error"] + captions


def test_choosing_the_estimate_autofills_the_field_with_the_geometry_number() -> None:
    """#34, decision 1: autofill, not helper text — the field holds the estimate, so
    `t0_is_measured = False` is truthful. The lab column at core–shell is 0.450 min."""
    app = _running_app()
    _selectbox(app, "Packing architecture").set_value("Core–shell (solid core)").run()
    _radio(app, "t0 source").set_value("Geometry estimate").run()
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert _number(app, "t0 (min)").value == pytest.approx(0.4503, abs=5e-5)
    assert any(
        "0.450 min" in text and "band 0.390–0.520" in text for text in _t0_sidebar_texts(app)
    )
    status = [m.value for m in app.markdown if "hs-status" in m.value]  # type: ignore[attr-defined]
    assert any("t0 estimated" in bar for bar in status)


def test_the_estimate_tracks_an_edit_to_the_column_geometry() -> None:
    app = _running_app()
    _selectbox(app, "Packing architecture").set_value("Core–shell (solid core)").run()
    _radio(app, "t0 source").set_value("Geometry estimate").run()
    _number(app, "Column length (mm)").set_value(50.0).run()
    assert _number(app, "t0 (min)").value == pytest.approx(0.4503 / 2.0, abs=5e-5)
    _selectbox(app, "Packing architecture").set_value("Fully porous").run()
    assert _number(app, "t0 (min)").value == pytest.approx(0.5369 / 2.0, abs=5e-5)


def test_typing_over_the_estimate_flips_the_source_back_to_measured() -> None:
    """Overwriting the field is a measurement — the source follows the field (#34)."""
    app = _running_app()
    _selectbox(app, "Packing architecture").set_value("Core–shell (solid core)").run()
    _radio(app, "t0 source").set_value("Geometry estimate").run()
    _number(app, "t0 (min)").set_value(0.525).run()
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert _radio(app, "t0 source").value == "Measured marker"
    assert _number(app, "t0 (min)").value == pytest.approx(0.525)
    status = [m.value for m in app.markdown if "hs-status" in m.value]  # type: ignore[attr-defined]
    assert not any("t0 estimated" in bar for bar in status)


def test_without_an_architecture_the_estimate_is_refused_and_the_field_is_kept() -> None:
    """#34, decision 2: no fully-porous default. The typed value stays, stamped."""
    app = _running_app()
    _radio(app, "t0 source").set_value("Geometry estimate").run()
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert _number(app, "t0 (min)").value == pytest.approx(0.525)
    assert any("Choose the packing architecture" in text for text in _messages(app)["warning"])
    status = [m.value for m in app.markdown if "hs-status" in m.value]  # type: ignore[attr-defined]
    assert any("t0 estimated" in bar for bar in status)


def test_the_reverse_check_reads_the_system_volume_off_the_opening_screen() -> None:
    """The driver's column: 0.525 min measured against 0.450 min geometry is 30 µL."""
    app = _running_app()
    assert any("ε_total = 0.606" in text for text in _messages(app)["info"])
    assert not any("extra-column volume**" in text for text in _messages(app)["info"])

    _selectbox(app, "Packing architecture").set_value("Core–shell (solid core)").run()
    assert any("30 µL of extra-column volume" in text for text in _messages(app)["info"])

    _selectbox(app, "Packing architecture").set_value("Fully porous").run()
    assert any("below the geometry estimate" in text for text in _messages(app)["warning"])


def test_the_marker_field_is_asked_for_and_warned_about() -> None:
    app = _running_app()
    assert any("No t0 marker recorded" in text for text in _messages(app)["warning"])
    _text_input(app, "t0 marker").set_value("solvent front, first disturbance").run()
    assert any("solvent disturbance" in text for text in _messages(app)["warning"])
    _text_input(app, "t0 marker").set_value("uracil, apex").run()
    assert not any("marker" in text.lower() for text in _messages(app)["warning"])


def test_the_marker_field_is_absent_while_t0_is_an_estimate() -> None:
    app = _running_app()
    _radio(app, "t0 source").set_value("Geometry estimate").run()
    assert not [w for w in app.text_input if w.label == "t0 marker"]  # type: ignore[attr-defined]


def test_a_narrow_scouting_pair_paints_the_spacing_notice_before_any_peak_is_typed() -> None:
    """SPEC §4's spacing warning is about the experiment, so it does not wait for results.

    Two scouting runs 20 and 15 min apart are β = 1.33 — under SPEC §4's 2.5 warning
    tier — and the page says so with the peak table still empty.
    """
    app = _running_app()
    assert not any("β" in text for text in _messages(app)["warning"])

    _seed_scouting(app, replace(_DEFAULT_SCOUTING, t_gradient2=20.0))

    (notice,) = [text for text in _messages(app)["warning"] if "Scouting runs" in text]
    assert "β = 1.33" in notice


# --- the rail's two programme tables (SPEC §7, v0.2, #73) -----------------------------
#
# The condition is two `st.data_editor`s now, and `AppTest` cannot type into one. What it
# can do is what a loaded file does: put a frame under the entry point's key and run. So
# these seed the frames and assert what the rail makes of them — the same road the file
# takes — and leave the editor itself to `tests/test_rail.py` and the browser.


def test_the_rail_opens_on_the_two_tables_with_no_slider_anywhere() -> None:
    """SPEC §7: no slider pairs and no tG slider — the table cell steps with the keyboard."""
    app = _running_app()
    assert app.slider == []  # type: ignore[attr-defined]
    # The scouting table, the candidate table and the peak table.
    assert len(app.dataframe) == 3  # type: ignore[attr-defined]
    assert _scouting_columns(app) == {
        T1: [0.0, 0.5, 15.5],
        T2: [0.0, 0.5, 45.5],
        PERCENT_B: [5.0, 5.0, 95.0],
    }
    assert _candidate_rows(app) == [(0.0, 5.0), (0.5, 5.0), (25.5, 95.0)]
    assert "5 → 95 %B · tG 25 min · hold 0.5 min · 1 segment" in _status_bar(app)


def test_the_candidate_follows_the_scouting_table_until_it_is_typed_into() -> None:
    app = _running_app()
    _seed_scouting(
        app, replace(_DEFAULT_SCOUTING, percent_b_start=10.0, percent_b_end=90.0, hold=1.0)
    )
    assert _candidate_rows(app) == [(0.0, 10.0), (1.0, 10.0), (26.0, 90.0)]

    _seed_candidate(app, (0.0, 15.0), (0.5, 15.0), (25.5, 55.0))
    _seed_scouting(app, replace(_DEFAULT_SCOUTING, percent_b_start=20.0))

    assert _candidate_rows(app) == [(0.0, 15.0), (0.5, 15.0), (25.5, 55.0)]
    assert "15 → 55 %B · tG 25 min · hold 0.5 min · 1 segment" in _status_bar(app)


def test_reset_puts_the_candidate_back_to_following_the_scouting_table() -> None:
    app = _running_app()
    _seed_candidate(app, (0.0, 15.0), (0.5, 15.0), (25.5, 55.0))
    (reset,) = [b for b in app.button if b.label == "Reset"]  # type: ignore[attr-defined]

    reset.click().run()
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert _candidate_rows(app) == [(0.0, 5.0), (0.5, 5.0), (25.5, 95.0)]


def test_a_cell_that_follows_another_is_put_back_when_typed_over() -> None:
    """Row 2's %B follows row 1's, and row 2's second time its first (read-mostly)."""
    app = _running_app()
    frame = scouting_frame(_DEFAULT_SCOUTING)
    frame.loc[1, PERCENT_B] = 40.0
    frame.loc[1, T2] = 7.0
    frame.loc[0, T1] = 3.0
    app.session_state[Keys.SCOUTING_FRAME] = frame  # type: ignore[attr-defined]
    app.run()  # type: ignore[attr-defined]
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert _scouting_columns(app) == {
        T1: [0.0, 0.5, 15.5],
        T2: [0.0, 0.5, 45.5],
        PERCENT_B: [5.0, 5.0, 95.0],
    }


def test_a_two_row_candidate_predicts_through_the_walker_and_says_so() -> None:
    """The trap run as run: ramp to 55 %B, hold, then the wash — two segments and more."""
    app = _running_app()
    _uploader(app).upload("s.json", save_session(RESTORED).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]
    _seed_candidate(app, (0.0, 15.0), (0.5, 15.0), (25.5, 55.0), (45.0, 55.0), (45.1, 95.0))

    bar = _status_bar(app)
    assert "15 → 95 %B · tG 44.6 min · hold 0.5 min · 3 segments" in bar
    assert "3 segments, piecewise linear" in bar
    assert "Rs" in bar  # predicted: the peaks came with the file


def test_a_candidate_with_no_ramp_blocks_the_prediction_in_the_rail() -> None:
    app = _running_app()
    _seed_candidate(app, (0.0, 5.0), (0.5, 5.0))

    assert any("needs a ramp" in text for text in _messages(app)["error"])
    assert "no ramp yet" in _status_bar(app)


def test_a_row_out_of_order_is_named_beneath_the_table_and_the_rest_stands() -> None:
    app = _running_app()
    _seed_candidate(app, (0.0, 5.0), (0.5, 5.0), (25.5, 95.0), (20.0, 50.0))

    (note,) = [text for text in _messages(app)["warning"] if "Row 4" in text]
    assert "20 min" in note
    assert "5 → 95 %B · tG 25 min · hold 0.5 min · 1 segment" in _status_bar(app)


def test_the_first_rows_time_is_put_back_to_the_start_of_the_run() -> None:
    app = _running_app()
    _seed_candidate(app, (3.0, 5.0), (0.5, 5.0), (25.5, 95.0))
    assert _candidate_rows(app) == [(0.0, 5.0), (0.5, 5.0), (25.5, 95.0)]


# --- the session file of SPEC §8: load, restore, save ---------------------------------
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

    _seed_scouting(app, replace(_DEFAULT_SCOUTING, t_gradient2=30.0))

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
    # The scouting programme lands in its table: 10 → 90 %B after a 1.25 min hold, at
    # tG 20 and 60 — rows of start, end of hold, end of each ramp.
    assert _scouting_columns(app) == {
        T1: [0.0, 1.25, 21.25],
        T2: [0.0, 1.25, 61.25],
        PERCENT_B: [10.0, 10.0, 90.0],
    }
    assert _text_input(app, "Session name").value == "Reopened"
    assert _selectbox(app, "Packing architecture").value == "Core–shell (solid core)"
    assert _text_input(app, "t0 marker").value == "thiourea, apex"


def test_uploading_a_session_restores_the_dwell_as_the_time_the_file_stores() -> None:
    """V_D ÷ F is an entry boundary and does not run backwards (SPEC §8) — so the
    radio moves to the time, rather than a volume being invented at the current flow."""
    app = _running_app()
    _uploader(app).upload("s.json", save_session(RESTORED).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    assert _radio(app, "Dwell entered as").value == "Time (min)"
    assert _number(app, "Dwell time t_D (min)").value == pytest.approx(RESTORED.method.t_dwell)


def test_uploading_a_session_restores_the_candidate_into_its_table_as_the_files_own() -> None:
    """The file's candidate — hold 2.5, tG 37.5 over 10 → 90 %B — is the table's rows,
    and the table stops following the scouting programme the moment a file lands."""
    app = _running_app()
    _uploader(app).upload("s.json", save_session(RESTORED).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    assert _candidate_rows(app) == [(0.0, 10.0), (2.5, 10.0), (40.0, 90.0)]
    assert app.session_state[Keys.CANDIDATE_TOUCHED] is True  # type: ignore[attr-defined]
    assert "10 → 90 %B · tG 37.5 min · hold 2.5 min · 1 segment" in _status_bar(app)


def test_a_restored_estimated_t0_still_stamps_the_outputs() -> None:
    """A restored input has to reach the diagnostics, not just the widget it sits in."""
    estimated = replace(RESTORED, method=replace(RESTORED.method, t0_is_measured=False))
    app = _running_app()
    _uploader(app).upload("s.json", save_session(estimated).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    status = [m.value for m in app.markdown if "hs-status" in m.value]  # type: ignore[attr-defined]
    assert any("t0 estimated" in bar for bar in status)


def test_a_restored_estimate_is_recomputed_from_the_files_geometry() -> None:
    """The estimate is derived from inputs, so it recomputes on load as the fit does
    (SPEC §8). RESTORED is 4.6 × 150 mm at 1.2 mL/min, core–shell: 0.52 × 2.493 mL / 1.2."""
    estimated = replace(RESTORED, method=replace(RESTORED.method, t0_is_measured=False))
    app = _running_app()
    _uploader(app).upload("s.json", save_session(estimated).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert _radio(app, "t0 source").value == "Geometry estimate"
    assert _number(app, "t0 (min)").value == pytest.approx(1.0802, abs=5e-5)


def test_a_restored_estimate_without_an_architecture_keeps_the_files_number() -> None:
    method = replace(RESTORED.method, t0_is_measured=False, particle_is_solid_core=None)
    app = _running_app()
    _uploader(app).upload("s.json", save_session(replace(RESTORED, method=method)).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    assert _number(app, "t0 (min)").value == pytest.approx(1.42)
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

    loaded = ScoutingEntry.from_runs(*RESTORED.runs)
    _seed_scouting(app, replace(loaded, t_gradient2=30.0))
    assert _download_url(app) != restored
    _seed_scouting(app, loaded)

    assert _download_url(app) == restored


def test_a_corrupt_file_is_refused_by_name_and_leaves_the_screen_alone() -> None:
    """SPEC §8's hard rejection, worded to name the field — and nothing else disturbed."""
    app = _running_app()
    _uploader(app).upload("s.json", b'{"schema_version": 99, "app_version": "0.1.0"}')
    app.run()  # type: ignore[attr-defined]
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert any("schema_version 99" in text for text in _messages(app)["error"])
    assert _number(app, "t0 (min)").value == pytest.approx(0.525)  # still the default


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


def test_the_worksheet_gives_way_once_a_session_that_predicts_is_loaded() -> None:
    """SPEC §7's "cockpit layout thereafter", with the peaks arriving via the file —
    which is the only way this suite can fill the peak table at all."""
    app = _running_app()
    _uploader(app).upload("s.json", save_session(RESTORED).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    assert _worksheet_html(app) == []


def test_a_stuck_screen_keeps_the_worksheet_and_ticks_the_steps_that_are_done() -> None:
    """The ✅ on steps 2 and 3 is only worth computing if it can reach a screen.

    Two scouting runs at one tG: the peaks are loaded, nothing can be fitted, and the
    guidance stays up with step 2 open and naming the reason.
    """
    stuck = replace(RESTORED, runs=(RESTORED.runs[0], RESTORED.runs[0]))
    app = _running_app()
    _uploader(app).upload("s.json", save_session(stuck).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    (worksheet,) = _worksheet_html(app)
    assert "different gradient times" in worksheet
    assert "✅" in worksheet and "⬜" in worksheet


def test_a_loaded_half_paired_row_reaches_the_screen_as_the_untracked_count() -> None:
    """#18's known gap, closed end to end: the row survives the file and is counted."""
    app = _running_app()
    _uploader(app).upload("s.json", save_session(RESTORED).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    (notice,) = [text for text in _messages(app)["info"] if "untracked" in text]
    assert "1 untracked — not fitted" in notice
    assert "Impurity B" in notice


# --- a file that is valid but does not fit the screen ---------------------------------


def test_a_500_minute_candidate_loads_into_the_table_as_typed() -> None:
    """v0.1 clamped this to the slider's end and said so. A table cell has no end (#73):
    a 500-minute tG is a real method and the file's own number is what shows."""
    wild = replace(RESTORED, candidate=_WILD_CANDIDATE)
    app = _running_app()
    _uploader(app).upload("s.json", save_session(wild).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    assert not app.exception, app.exception  # type: ignore[attr-defined]
    assert _candidate_rows(app) == [(0.0, 10.0), (2.5, 10.0), (502.5, 90.0)]
    assert not any("outside what this screen" in text for text in _messages(app)["warning"])


def test_a_900_minute_scouting_run_loads_into_its_table_as_typed_too() -> None:
    wild = replace(
        RESTORED,
        runs=(
            replace(
                RESTORED.runs[0], gradient=replace(RESTORED.runs[0].gradient, t_gradient=900.0)
            ),
            RESTORED.runs[1],
        ),
    )
    app = _running_app()
    _uploader(app).upload("s.json", save_session(wild).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    assert not app.exception, app.exception  # type: ignore[attr-defined]
    assert _scouting_columns(app)[T1] == [0.0, 1.25, 901.25]
    assert not any("outside what this screen" in text for text in _messages(app)["warning"])


def test_a_two_segment_candidate_loads_into_the_table_and_is_predicted_as_itself() -> None:
    """SPEC §8 stores the candidate as programme rows and the table shows them (#73):
    a segment is a row, and the file is neither squeezed nor reported."""
    two = Programme(
        phi0=0.10,
        segments=(Segment(duration=12.5, phif=0.50), Segment(duration=25.0, phif=0.90)),
        t_init=2.5,
    )
    app = _running_app()
    _uploader(app).upload("s.json", save_session(replace(RESTORED, candidate=two)).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    assert not app.exception, app.exception  # type: ignore[attr-defined]
    assert _candidate_rows(app) == [(0.0, 10.0), (2.5, 10.0), (15.0, 50.0), (40.0, 90.0)]
    assert "10 → 90 %B · tG 37.5 min · hold 2.5 min · 2 segments" in _status_bar(app)
    assert not any("no control on this screen" in text for text in _messages(app)["warning"])
    # What the table shows is what a save would write: the same rows, read back.
    assert list(app.session_state[Keys.CANDIDATE_FRAME][T_CANDIDATE]) == [  # type: ignore[attr-defined]
        point.t_min for point in points_from_programme(two)
    ]


def test_a_file_that_fits_the_screen_says_nothing_about_limits() -> None:
    app = _running_app()
    _uploader(app).upload("s.json", save_session(RESTORED).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]

    assert not any("outside what this screen" in text for text in _messages(app)["warning"])


def test_a_refused_file_does_not_leave_the_last_files_warning_standing_beside_it() -> None:
    """Both notices describe the last file handled, so they have to move together.

    Load a session whose column length is past the box's end (warned about), then load
    a corrupt one. The error is the new file's; the warning would be the old file's, and
    it names a number no longer anywhere on screen.
    """
    wild = replace(RESTORED, method=replace(RESTORED.method, column_length_mm=5000.0))
    app = _running_app()
    _uploader(app).upload("wild.json", save_session(wild).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]
    assert any("outside what this screen" in text for text in _messages(app)["warning"])

    _uploader(app).upload("bad.json", b'{"schema_version": 99, "app_version": "0.1.0"}')
    app.run()  # type: ignore[attr-defined]
    assert not app.exception, app.exception  # type: ignore[attr-defined]

    assert any("schema_version 99" in text for text in _messages(app)["error"])
    assert not any("outside what this screen" in text for text in _messages(app)["warning"])


# --- ticket #74: the overlay, the readout, the badges and the indicative stamp -----------
#
# `tests/test_overlay.py` proves the four surfaces are built correctly; these prove they
# are painted. The condition is the trap case of #45 — a candidate starting 10 %B above
# the scouting start and ramping to 55 %B at a tG inside the bracket — which is strong on
# diagnostic 7 and so carries the stamp. It arrives through a session file, because
# `AppTest` cannot type into the peak table's editor.

_TRAP_CANDIDATE = Programme.from_gradient(
    Gradient(phi0=0.15, phif=0.55, t_gradient=25.0, t_init=0.5)
)
_QUIET_CANDIDATE = Programme.from_gradient(
    Gradient(phi0=0.05, phif=0.95, t_gradient=25.0, t_init=0.5)
)


def _lab_session(candidate: Programme) -> Session:
    return Session(
        session_name="Lab dataset",
        method=LAB_METHOD,
        runs=(LAB_RUN1, LAB_RUN2),
        peaks=tuple(LAB_MEASURED_PEAKS),
        candidate=candidate,
    )


def _loaded(candidate: Programme) -> object:
    app = _running_app()
    _uploader(app).upload("s.json", save_session(_lab_session(candidate)).encode("utf-8"))
    app.run()  # type: ignore[attr-defined]
    assert not app.exception, app.exception  # type: ignore[attr-defined]
    return app


def _captions(app: object) -> list[str]:
    return [caption.value for caption in app.caption]  # type: ignore[attr-defined]


def _flag_column(app: object) -> list[object]:
    """The rendered prediction table — the one data grid carrying a Flags column."""
    return [
        frame.value
        for frame in app.dataframe  # type: ignore[attr-defined]
        if FLAGS in list(frame.value.columns)
    ]


def _panel(app: object, title: str) -> str:
    blocks = [m.value for m in app.markdown if f">{title}</div>" in m.value]  # type: ignore[attr-defined]
    assert len(blocks) == 1, f"{title!r} matched {len(blocks)} panels"
    return str(blocks[0])


def test_the_chromatogram_says_which_line_is_the_candidate_and_which_the_pair() -> None:
    """SPEC §7's overlay is always on, so the caption explaining it is too."""
    app = _loaded(_QUIET_CANDIDATE)
    assert any("Candidate solid, scouting pair dashed" in c for c in _captions(app))
    assert any("calibrated window" in c for c in _captions(app))


def test_the_fit_tab_carries_the_per_peak_composition_window_readout() -> None:
    app = _loaded(_QUIET_CANDIDATE)
    headings = [m.value for m in app.markdown]  # type: ignore[attr-defined]
    assert any("Calibrated composition windows" in text for text in headings)
    assert any("ln β / S_e" in caption for caption in _captions(app))


def test_the_indicative_stamp_reaches_every_surface_spec_6_names_it_on() -> None:
    """Min. Rs, the resolution tab and the status bar, in the manner of diagnostic 6."""
    app = _loaded(_TRAP_CANDIDATE)

    summary = _panel(app, "Method summary")
    assert "Min. Rs (indicative)" in summary
    assert "Critical pair (indicative)" in summary
    # Retention stays shown as numbers at the same condition (SPEC §6).
    assert "Run time (indicative)" not in summary

    assert any("indicative, not decision-grade" in text for text in _messages(app)["error"])
    assert any("indicative, not decision-grade" in caption for caption in _captions(app))
    assert "Rs indicative — not decision-grade" in _status_bar(app)


def test_a_candidate_the_fit_was_shown_carries_no_stamp_anywhere() -> None:
    """The same screen inside the bracket at the scouting start: v0.1's, unstamped."""
    app = _loaded(_QUIET_CANDIDATE)

    assert "indicative" not in _panel(app, "Method summary")
    assert not any("indicative, not decision-grade" in text for text in _messages(app)["error"])
    assert "Rs indicative" not in _status_bar(app)


def test_the_low_k0_badge_reaches_the_flags_column_and_the_selected_peak_panel() -> None:
    """Three-peak run 7: 8 fires on Unknown-1 and nowhere else (SPEC §10 item 2)."""
    app = _loaded(Programme.from_gradient(LAB_RUN7.gradient))

    # The selected-peak panel opens on the first peak, which is the badged one, and
    # paints the badge in full beside it.
    assert any("Unknown-1: log₁₀ k0" in text for text in _messages(app)["warning"]), _messages(app)[
        "warning"
    ]

    (flags,) = _flag_column(app)
    assert set(flags.loc[flags[FLAGS].str.contains("low k0"), COMPOUND]) == {"Unknown-1"}


def test_the_wash_eluted_badge_reaches_the_flags_column() -> None:
    """Three-peak run 6 as the instrument ran it: 9 fires on Unknown-3 alone."""
    app = _loaded(LAB_RUN6_PROGRAMME)
    (flags,) = _flag_column(app)
    marked = set(flags.loc[flags[FLAGS].str.contains("wash-eluted"), COMPOUND])

    assert marked == {"Unknown-3"}


# A candidate at the scouting start, inside the steepness bracket, whose later peaks are
# brought off in a trailing hold: no method-level stamp, and a wash-eluted peak inside
# the critical pair. The screen has to downgrade the Rs it leads with anyway (SPEC §6).
_WASH_CANDIDATE = Programme(
    phi0=0.05,
    segments=(Segment(duration=12.0, phif=0.60), Segment(duration=30.0, phif=0.60)),
    t_init=0.5,
)


def test_a_badged_critical_pair_downgrades_min_rs_with_no_method_level_stamp() -> None:
    """SPEC §6 scopes a badge to its own peak's pairs — including the leading one."""
    app = _loaded(_WASH_CANDIDATE)

    # No method-level guard fired: the long sentence must not appear.
    assert not any("indicative, not decision-grade" in text for text in _messages(app)["error"])

    summary = _panel(app, "Method summary")
    assert "Min. Rs (indicative)" in summary
    assert "Critical pair (indicative)" in summary
    assert "Rs indicative — not decision-grade" in _status_bar(app)
    assert any("one of its peaks carries a badge" in caption for caption in _captions(app))
