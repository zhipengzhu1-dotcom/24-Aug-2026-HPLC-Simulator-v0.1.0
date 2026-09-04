"""The left rail's two programme tables, read and written without a browser (#73).

SPEC §7 (v0.2, #45): the scouting programme and the candidate programme are two
No. / Time / %B tables in the rail. What a table holds is a list of *points* — a time
and a composition — the way an instrument's own gradient table is typed; what the
engine wants is a :class:`~hplcsim.model.Programme`. The crossing between the two is
logic, so it lives in :mod:`app.entry` and is asserted here, and the pandas frame
the editor shows is :mod:`app.tables`'s side of the same crossing.
"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from app.entry import (
    ProgrammePoint,
    ScoutingEntry,
    points_from_programme,
    programme_from_points,
)
from app.pipeline import CockpitInputs, run_cockpit
from app.tables import (
    CANDIDATE_COLUMNS,
    PERCENT_B,
    SCOUTING_COLUMNS,
    T1,
    T2,
    T_CANDIDATE,
    candidate_frame,
    candidate_points_from_frame,
    frames_agree,
    scouting_frame,
    scouting_read_from_frame,
)
from hplcsim.model import Gradient, Programme, Segment
from hplcsim.retention import predict_retention
from lab_data import (
    LAB_MEASURED_PEAKS,
    LAB_METHOD,
    LAB_RUN1,
    LAB_RUN2,
    LAB_RUN3,
    LAB_RUN6_PROGRAMME,
)
from test_app import _lab_inputs, _row

SCOUTING = ScoutingEntry(
    percent_b_start=5.0, percent_b_end=95.0, hold=0.5, t_gradient1=15.0, t_gradient2=45.0
)


# --- the scouting table: one programme at two speeds ------------------------------------


def test_percent_b_reaches_the_engine_as_a_fraction_at_the_scouting_table() -> None:
    """CLAUDE.md's units rule: %B is an entry boundary, φ is what the engine holds."""
    run1, run2 = SCOUTING.runs()
    assert run1 == LAB_RUN1 and run2 == LAB_RUN2
    assert (run1.gradient.phi0, run1.gradient.phif) == (0.05, 0.95)


def test_the_scouting_entry_names_its_runs_by_gradient_time() -> None:
    run1, run2 = replace(SCOUTING, t_gradient1=20.0, t_gradient2=60.0).runs()
    assert (run1.name, run2.name) == ("tG20", "tG60")


def test_the_scouting_entry_reads_back_from_its_own_runs() -> None:
    assert ScoutingEntry.from_runs(LAB_RUN1, LAB_RUN2) == SCOUTING


# --- the candidate table: points in, a programme out ------------------------------------


def _points(*rows: tuple[float, float]) -> tuple[ProgrammePoint, ...]:
    return tuple(ProgrammePoint(t_min=t, percent_b=b) for t, b in rows)


def test_one_ramp_over_the_scouting_range_is_exactly_the_v01_candidate() -> None:
    """Row 1 the start, row 2 the end of the hold, row 3 the end of the ramp — and the
    programme this makes is bitwise the one-segment gradient v0.1 predicted (SPEC §10 4a)."""
    read = programme_from_points(_points((0.0, 5.0), (0.5, 5.0), (25.5, 95.0)))
    assert read.programme == Programme.from_gradient(LAB_RUN3.gradient)
    assert read.programme is not None and read.programme.as_gradient() == LAB_RUN3.gradient
    assert read.blocked is None and read.notes == ()


def test_a_further_row_is_a_further_segment() -> None:
    read = programme_from_points(_points((0.0, 15.0), (0.5, 15.0), (25.5, 55.0), (30.5, 95.0)))
    assert read.programme == Programme(
        phi0=0.15, t_init=0.5, segments=(Segment(25.0, 0.55), Segment(5.0, 0.95))
    )


def test_a_repeated_composition_after_the_ramp_is_a_hold_segment() -> None:
    """The trap run as run: ramp to 55, hold there 19.5 min, step to 95 (three-peak run 6)."""
    points = points_from_programme(LAB_RUN6_PROGRAMME)
    assert programme_from_points(points).programme == LAB_RUN6_PROGRAMME


def test_without_a_flat_second_row_there_is_no_initial_hold() -> None:
    read = programme_from_points(_points((0.0, 5.0), (25.0, 95.0)))
    assert read.programme == Programme(phi0=0.05, t_init=0.0, segments=(Segment(25.0, 0.95),))


def test_a_flat_second_row_at_zero_is_a_hold_of_nothing() -> None:
    """The hold row is always shown, so a candidate with no hold carries it at t = 0."""
    read = programme_from_points(_points((0.0, 5.0), (0.0, 5.0), (25.0, 95.0)))
    assert read.programme == Programme(phi0=0.05, t_init=0.0, segments=(Segment(25.0, 0.95),))
    assert read.notes == ()


def test_the_first_row_is_the_start_of_the_run_whatever_time_was_typed() -> None:
    read = programme_from_points(_points((3.0, 5.0), (0.5, 5.0), (25.5, 95.0)))
    assert read.points[0] == ProgrammePoint(t_min=0.0, percent_b=5.0)
    assert read.programme == Programme.from_gradient(LAB_RUN3.gradient)


def test_a_row_that_does_not_move_forward_in_time_is_left_out_and_named() -> None:
    """Warnings over blocks: the row is ignored, the rest of the programme stands."""
    read = programme_from_points(_points((0.0, 5.0), (0.5, 5.0), (25.5, 95.0), (20.0, 50.0)))
    assert read.programme == Programme.from_gradient(LAB_RUN3.gradient)
    (note,) = read.notes
    assert "Row 4" in note and "20 min" in note and "25.5 min" in note


def test_a_row_still_being_typed_is_left_out_quietly() -> None:
    read = programme_from_points(
        _points((0.0, 5.0), (0.5, 5.0), (25.5, 95.0)) + (ProgrammePoint(None, None),)
    )
    assert read.programme == Programme.from_gradient(LAB_RUN3.gradient)
    assert read.notes == ()


def test_a_candidate_with_no_ramp_after_the_start_cannot_be_predicted() -> None:
    read = programme_from_points(_points((0.0, 5.0), (0.5, 5.0)))
    assert read.programme is None
    assert read.blocked is not None and "later time" in read.blocked


def test_an_empty_table_cannot_be_predicted_either() -> None:
    assert programme_from_points(()).programme is None


def test_durations_are_read_at_the_tables_own_precision() -> None:
    """25.4 − 0.4 is not 25.0 in binary; the table is typed to hundredths, and a
    duration read off it must come back as the number that was meant (SPEC §8)."""
    read = programme_from_points(_points((0.0, 5.0), (0.4, 5.0), (25.4, 95.0)))
    assert read.programme is not None
    assert read.programme.segments[0].duration == 25.0


def test_points_and_programme_round_trip_both_ways() -> None:
    programme = Programme(
        phi0=0.10, t_init=2.5, segments=(Segment(12.5, 0.50), Segment(25.0, 0.90))
    )
    points = points_from_programme(programme)
    assert points == _points((0.0, 10.0), (2.5, 10.0), (15.0, 50.0), (40.0, 90.0))
    assert programme_from_points(points).programme == programme


# --- the programme reaches the engine -----------------------------------------------------


def test_the_inputs_carry_the_programme_and_its_one_segment_reading_together() -> None:
    inputs = CockpitInputs.with_programme(
        method=LAB_METHOD, run1=LAB_RUN1, run2=LAB_RUN2, programme=LAB_RUN6_PROGRAMME
    )
    assert inputs.programme is LAB_RUN6_PROGRAMME
    assert inputs.target is LAB_RUN6_PROGRAMME
    # The v0.1 diagnostics still read a gradient (until #72): the programme's own range
    # over its total ramp time, never the scouting runs'.
    assert inputs.candidate == Gradient(phi0=0.15, phif=0.25, t_gradient=51.7, t_init=0.5)


def test_the_one_segment_reading_cannot_disagree_with_the_programme() -> None:
    with pytest.raises(ValueError, match="one-segment reading"):
        CockpitInputs(
            method=LAB_METHOD,
            run1=LAB_RUN1,
            run2=LAB_RUN2,
            candidate=LAB_RUN3.gradient,
            programme=LAB_RUN6_PROGRAMME,
        )


def test_without_a_programme_the_candidate_gradient_is_the_target() -> None:
    inputs = _lab_inputs()
    assert inputs.programme is None and inputs.target is LAB_RUN3.gradient


def test_a_one_row_candidate_predicts_every_number_v01_did() -> None:
    """SPEC §10 item 4a on the app's own path: the same fixtures, `==` on every field."""
    v01 = run_cockpit(_lab_inputs())
    v02 = run_cockpit(
        CockpitInputs.with_programme(
            method=LAB_METHOD,
            run1=LAB_RUN1,
            run2=LAB_RUN2,
            programme=Programme.from_gradient(LAB_RUN3.gradient),
            rows=tuple(_row(peak) for peak in LAB_MEASURED_PEAKS),
        )
    )
    assert v02 == v01


def test_a_two_segment_candidate_predicts_through_the_walker() -> None:
    """Run 6 as run: Unknown-3 is carried off by the wash the single segment never had."""
    inputs = CockpitInputs.with_programme(
        method=LAB_METHOD,
        run1=LAB_RUN1,
        run2=LAB_RUN2,
        programme=LAB_RUN6_PROGRAMME,
        rows=tuple(_row(peak) for peak in LAB_MEASURED_PEAKS),
    )
    cockpit = run_cockpit(inputs)
    assert cockpit.blocked is None and cockpit.resolution is not None
    unknown3 = cockpit.predicted_by_name["Unknown-3"]
    assert unknown3.retention.regime == "post_gradient"
    # Every number on screen is the engine's own: the walker, from the fit the app made.
    (fit,) = [fit for peak, fit in cockpit.fitted if peak.name == "Unknown-3"]
    assert unknown3.retention == predict_retention(fit.params, LAB_METHOD, LAB_RUN6_PROGRAMME)
    # And it is the reality point of SPEC §10 item 4(d), inside the coarse bar.
    assert abs(unknown3.retention.t_r - 46.8) / 46.8 <= 0.02


def test_a_reason_the_rail_knows_blocks_the_cockpit_like_the_engines_own() -> None:
    cockpit = run_cockpit(_lab_inputs(), blocked="the candidate table has no ramp yet")
    assert cockpit.blocked == "the candidate table has no ramp yet"
    assert cockpit.resolution is None and cockpit.outcomes == ()
    assert len(cockpit.entry.tracked) == 3  # the peak table is still read


# --- the frames the editors show ------------------------------------------------------------
#
# `st.data_editor` cannot be driven from `AppTest`, so the frame each editor shows and
# reads back is asserted here, and the screen tests seed the frames into session state.


def test_the_scouting_frame_is_the_three_rows_of_one_programme_at_two_speeds() -> None:
    frame = scouting_frame(SCOUTING)
    assert list(frame.columns) == list(SCOUTING_COLUMNS)
    assert frame[T1].tolist() == [0.0, 0.5, 15.5]
    assert frame[T2].tolist() == [0.0, 0.5, 45.5]
    assert frame[PERCENT_B].tolist() == [5.0, 5.0, 95.0]


def test_the_scouting_frame_reads_back_as_the_entry_it_was_made_from() -> None:
    read = scouting_read_from_frame(scouting_frame(SCOUTING))
    assert read.entry == SCOUTING
    assert read.frame.equals(scouting_frame(SCOUTING))
    assert read.notes == ()


def test_row_2_follows_row_1s_percent_b_and_row_2s_second_time_follows_its_first() -> None:
    """The read-mostly cells: typed over, they are put back, and the frame says which."""
    frame = scouting_frame(SCOUTING)
    frame.loc[0, PERCENT_B] = 10.0  # the start moved: row 2 follows it
    frame.loc[1, T1] = 1.0  # the hold moved: t₂ follows t₁
    frame.loc[1, PERCENT_B] = 40.0  # typed over a cell that follows row 1
    frame.loc[1, T2] = 7.0  # likewise
    frame.loc[0, T1] = 3.0  # row 1 is the start of the run

    read = scouting_read_from_frame(frame)

    assert read.entry == replace(
        SCOUTING, percent_b_start=10.0, hold=1.0, t_gradient1=14.5, t_gradient2=44.5
    )
    assert read.frame[PERCENT_B].tolist() == [10.0, 10.0, 95.0]
    assert read.frame[T1].tolist() == [0.0, 1.0, 15.5]
    assert read.frame[T2].tolist() == [0.0, 1.0, 45.5]


def test_a_ramp_that_ends_before_the_hold_does_is_put_back_and_named() -> None:
    frame = scouting_frame(SCOUTING)
    frame.loc[2, T1] = 0.2  # before the hold ends at 0.5
    read = scouting_read_from_frame(frame)
    assert read.entry.t_gradient1 > 0.0
    assert read.frame[T1].tolist()[2] == pytest.approx(0.5 + read.entry.t_gradient1)
    (note,) = read.notes
    assert "run 1" in note.lower()


def test_the_candidate_frame_shows_the_points_and_reads_them_back() -> None:
    points = points_from_programme(LAB_RUN6_PROGRAMME)
    frame = candidate_frame(points)
    assert list(frame.columns) == list(CANDIDATE_COLUMNS)
    assert frame[T_CANDIDATE].tolist() == [0.0, 0.5, 25.5, 45.0, 45.1, 48.1, 48.2, 52.2]
    assert candidate_points_from_frame(frame) == points


def test_a_blank_candidate_cell_comes_back_as_none_not_nan() -> None:
    frame = candidate_frame(points_from_programme(LAB_RUN6_PROGRAMME))
    frame.loc[3, PERCENT_B] = pd.NA
    read_back = candidate_points_from_frame(frame)
    assert read_back[3] == ProgrammePoint(t_min=45.0, percent_b=None)
    assert programme_from_points(read_back).programme is not None


def test_the_candidate_frame_keeps_number_dtypes_so_the_editor_offers_number_cells() -> None:
    frame = candidate_frame(points_from_programme(LAB_RUN6_PROGRAMME))
    assert str(frame[T_CANDIDATE].dtype) == "Float64"
    assert str(frame[PERCENT_B].dtype) == "Float64"
    assert str(scouting_frame(SCOUTING)[T1].dtype) == "Float64"


def test_frames_agree_reads_cells_not_dtypes() -> None:
    """The editor hands its frame back in the browser's dtypes; a put-back is decided on
    what a cell reads, and a blank is a blank however it is spelled."""
    shown = candidate_frame(points_from_programme(LAB_RUN6_PROGRAMME))
    edited = shown.astype("float64")
    assert frames_agree(shown, edited)

    edited.loc[2, T_CANDIDATE] = 26.0
    assert not frames_agree(shown, edited)

    blank_na, blank_nan = shown.copy(), shown.astype("float64")
    blank_na.loc[3, PERCENT_B] = pd.NA
    blank_nan.loc[3, PERCENT_B] = float("nan")
    assert frames_agree(blank_na, blank_nan)
    assert not frames_agree(shown, shown.iloc[:-1])
