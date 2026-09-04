"""The screen and the session file translated into each other (ticket #21).

`tests/test_session.py` proves the file is written and read correctly; nothing there
touches the screen's own shape. These are about the crossing: what the Cockpit holds
becomes a :class:`~hplcsim.session.Session` and comes back as the same table, with the
half-paired rows of SPEC §5 surviving the trip — which is the thing ticket #18 could
not do and left here.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.entry import split_rows
from app.pipeline import CockpitInputs
from app.session_io import (
    Restore,
    inputs_from_session,
    peak_rows_from_session,
    session_filename,
    session_from_inputs,
)
from hplcsim.model import Gradient, Method, PeakRow, Programme, Run, Segment, phi_from_percent_b
from hplcsim.session import load_session, save_session

_SHARED = Gradient(phi0=0.05, phif=0.95, t_gradient=0.0, t_init=0.5)

INPUTS = CockpitInputs(
    method=Method(
        t0=0.6,
        t_dwell=0.9375,
        flow=0.4,
        column_length_mm=100.0,
        column_id_mm=2.1,
        particle_um=1.6,
        temperature_c=45.0,
    ),
    run1=Run(replace(_SHARED, t_gradient=15.0), name="tG15"),
    run2=Run(replace(_SHARED, t_gradient=45.0), name="tG45"),
    candidate=replace(_SHARED, t_gradient=25.0),
    rows=(
        PeakRow(name="Acetanilide", t_r_run1=9.855, t_r_run2=20.831, area_run1=13352.0),
        # Half-paired, and sitting *between* two tracked rows — the order this cannot
        # come back in, which the module documents and the test below pins.
        PeakRow(name="Impurity B", t_r_run1=11.204),
        PeakRow(name="Ketoprofen", t_r_run1=11.592, t_r_run2=25.932),
        PeakRow(),  # the editor's spare
    ),
    plate_count=12000.0,
)


# --- the screen -> the file ----------------------------------------------------------


def test_the_two_lists_of_the_file_are_the_split_the_screen_already_made() -> None:
    session = session_from_inputs(INPUTS)
    assert [peak.name for peak in session.peaks] == ["Acetanilide", "Ketoprofen"]
    assert [row.name for row in session.untracked] == ["Impurity B"]
    assert session.untracked[0].t_r_run1 == pytest.approx(11.204)
    assert session.untracked[0].t_r_run2 is None


def test_blank_rows_are_not_written_down() -> None:
    """The editor's spare is not a peak, and `split_rows` already knows that."""
    session = session_from_inputs(INPUTS)
    assert len(session.peaks) + len(session.untracked) == 3


def test_automatic_names_are_saved_so_a_row_returns_under_the_name_it_was_shown_with() -> None:
    unnamed = replace(INPUTS, rows=(PeakRow(t_r_run1=9.9, t_r_run2=20.8), PeakRow(t_r_run1=11.2)))
    session = session_from_inputs(unnamed)
    assert session.peaks[0].name == "P1"
    assert session.untracked[0].name == "P2"


def test_the_plate_count_is_stored_as_the_whole_count_the_file_asks_for() -> None:
    assert session_from_inputs(replace(INPUTS, plate_count=12345.5)).plate_count == 12346
    assert session_from_inputs(replace(INPUTS, plate_count=None)).plate_count is None


def test_the_session_name_reaches_the_file() -> None:
    assert session_from_inputs(INPUTS, session_name="Screen A").session_name == "Screen A"


def test_a_saved_screen_is_a_file_this_app_can_reopen() -> None:
    """The whole point, end to end: nothing on this screen is unwritable."""
    session = session_from_inputs(INPUTS, session_name="Screen A")
    assert load_session(save_session(session)) == session


# --- the file -> the screen ----------------------------------------------------------


def test_every_row_comes_back_with_its_measurements() -> None:
    rows = peak_rows_from_session(session_from_inputs(INPUTS))
    by_name = {row.name: row for row in rows}
    assert by_name["Acetanilide"].area_run1 == pytest.approx(13352.0)
    assert by_name["Impurity B"].t_r_run1 == pytest.approx(11.204)
    assert by_name["Impurity B"].t_r_run2 is None


def test_the_table_comes_back_tracked_first_which_reorders_a_half_paired_row() -> None:
    """Documented, not accidental: the file has two tables and no row index.

    Every row keeps its name and its numbers; only its position moves. This is asserted
    so that a future change to the file's shape has to face the choice deliberately.
    """
    rows = peak_rows_from_session(session_from_inputs(INPUTS))
    assert [row.name for row in rows] == ["Acetanilide", "Ketoprofen", "Impurity B"]


def test_the_round_trip_keeps_everything_the_cockpit_computes_from() -> None:
    restored = inputs_from_session(session_from_inputs(INPUTS))
    for field in ("method", "run1", "run2", "candidate", "plate_count"):
        assert getattr(restored, field) == getattr(INPUTS, field)
    # The rows are reordered and the blank one is gone, so the table is compared as the
    # split both sides run before anything is fitted — which is what the cockpit sees.
    assert split_rows(restored.rows).tracked == split_rows(INPUTS.rows).tracked
    assert {row.name for row in split_rows(restored.rows).untracked} == {"Impurity B"}


def test_a_second_round_trip_changes_nothing_further() -> None:
    """Reordering once is a documented consequence; reordering every time is a bug."""
    once = inputs_from_session(session_from_inputs(INPUTS))
    twice = inputs_from_session(session_from_inputs(once))
    assert twice.rows == once.rows


# --- the download's filename (AC-1) --------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Impurity screen 2026-08-27", "Impurity-screen-2026-08-27.json"),
        ("", "hplcsim-session.json"),
        ("   ", "hplcsim-session.json"),
        # A name a path could read as structure must not become one.
        ("../../etc/passwd", "etc-passwd.json"),
        ("batch/07: caffeine", "batch-07-caffeine.json"),
        (".hidden", "hidden.json"),
        # Two different names must not collapse into one file.
        ("a b", "a-b.json"),
    ],
)
def test_the_session_name_becomes_the_suggested_filename(name: str, expected: str) -> None:
    assert session_filename(name) == expected


def test_a_very_long_name_is_cut_to_a_filename_a_filesystem_will_take() -> None:
    filename = session_filename("x" * 500)
    assert filename.endswith(".json")
    assert len(filename) <= 90


# --- values a file may hold that no widget can show -----------------------------------
#
# `load_session` refuses an impossible number; it has no opinion about a merely large
# one. A 500-minute candidate tG is a real method, and it is past the end of a slider
# that stops at 180 — written into the widget's state raw, Streamlit raises on the next
# run and the page becomes a traceback rather than a screen.


def test_a_value_inside_the_range_is_untouched_and_unreported() -> None:
    restore = Restore()
    assert restore.within("candidate tG", 25.0, 1.0, 180.0) == 25.0
    assert restore.adjusted == []
    assert restore.note is None


def test_a_value_past_the_end_is_brought_to_the_limit() -> None:
    restore = Restore()
    assert restore.within("candidate tG", 500.0, 1.0, 180.0) == 180.0
    assert restore.within("t0", 0.0, 0.001, 100.0) == 0.001


def test_a_squeeze_is_reported_by_name_and_by_both_numbers() -> None:
    """Silence is the failure mode: the user must be able to see which number moved."""
    restore = Restore()
    restore.within("candidate tG", 500.0, 1.0, 180.0)
    note = restore.note

    assert note is not None
    assert "candidate tG 500 → 180" in note
    # And that the file was not rewritten behind them.
    assert "file itself is unchanged" in note


def test_every_squeeze_is_named_not_just_the_first() -> None:
    restore = Restore()
    restore.within("candidate tG", 500.0, 1.0, 180.0)
    restore.within("run 1 tG", 900.0, 0.1, 600.0)

    assert len(restore.adjusted) == 2
    note = restore.note
    assert note is not None and "candidate tG" in note and "run 1 tG" in note


# --- the candidate: programme rows in the file, programme rows on the screen (#71, #73) ---
#
# SPEC §8 stores the candidate as programme rows and, since #73, the rail's candidate
# table shows them — so the crossing is exact in both directions, whatever the segment
# count or the %B range. Nothing about the candidate is squeezed or reported any more.


def test_a_one_segment_candidate_is_saved_as_the_programme_it_is() -> None:
    candidate = session_from_inputs(INPUTS).candidate
    assert candidate.phi0 == pytest.approx(0.05)
    assert candidate.t_init == pytest.approx(0.5)
    assert candidate.segments == (Segment(duration=25.0, phif=0.95),)


def test_a_one_segment_candidate_comes_back_as_the_gradient_it_was() -> None:
    restored = inputs_from_session(session_from_inputs(INPUTS))
    assert restored.candidate == INPUTS.candidate
    assert restored.programme == Programme.from_gradient(INPUTS.candidate)
    assert restored.target == restored.programme


def test_a_two_segment_candidate_reaches_the_screen_as_the_programme_it_is() -> None:
    two = Programme(
        phi0=0.05,
        segments=(Segment(duration=10.0, phif=0.40), Segment(duration=15.0, phif=0.95)),
        t_init=0.5,
    )
    session = replace(session_from_inputs(INPUTS), candidate=two)
    restored = inputs_from_session(session)
    assert restored.programme == two
    assert restored.target == two
    assert session_from_inputs(restored).candidate == two


def test_a_candidate_off_the_scouting_range_is_shown_as_typed() -> None:
    raised = Programme(
        phi0=phi_from_percent_b(15), segments=(Segment(duration=25.0, phif=phi_from_percent_b(55)),)
    )
    restored = inputs_from_session(replace(session_from_inputs(INPUTS), candidate=raised))
    assert restored.programme == raised
    assert restored.candidate == Gradient(phi0=0.15, phif=0.55, t_gradient=25.0, t_init=0.0)


def test_a_programme_on_screen_is_saved_as_itself() -> None:
    inputs = CockpitInputs.with_programme(
        method=INPUTS.method, run1=INPUTS.run1, run2=INPUTS.run2, programme=_TWO, rows=INPUTS.rows
    )
    assert session_from_inputs(inputs).candidate == _TWO
    assert load_session(save_session(session_from_inputs(inputs))).candidate == _TWO


_TWO = Programme(
    phi0=0.10,
    segments=(Segment(duration=12.5, phif=0.50), Segment(duration=25.0, phif=0.90)),
    t_init=2.5,
)
