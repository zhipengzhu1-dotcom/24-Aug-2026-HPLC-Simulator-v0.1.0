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

from app.pipeline import CockpitInputs, PeakRow, split_rows
from app.session_io import (
    inputs_from_session,
    peak_rows_from_session,
    session_filename,
    session_from_inputs,
)
from hplcsim.model import Gradient, Method, Run
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
