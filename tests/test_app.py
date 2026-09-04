"""The Cockpit's logic layer, exercised without a browser (SPEC §7, ticket #19).

Streamlit is nowhere in this file. `app.streamlit_app` is widgets and layout; every
number it renders comes from `app.entry`, `app.pipeline`, `app.chromatogram` and
`app.tables`, which is what makes the ticket's third acceptance criterion — the
app's run-3 prediction against the engine's own fixtures — an assertion rather than
a habit.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import fields, replace

import numpy as np
import pandas as pd
import pytest

from app.chromatogram import AxisRequest, Chromatogram, axis_view, chromatogram
from app.diagnostics import Diagnostics, diagnose
from app.entry import (
    MethodEntry,
    ScoutingEntry,
    dwell_from_volume,
    split_rows,
    t0_autofill,
)
from app.pipeline import Cockpit, CockpitInputs, area_shares, run_cockpit
from app.tables import (
    COMPOUND,
    FIT_COLUMNS,
    FLAGS,
    N_RATIO,
    PEAK_COLUMNS,
    PREDICTION_COLUMNS,
    RESOLUTION_COLUMNS,
    TR_RUN1,
    TR_RUN2,
    blank_peak_frame,
    fit_frame,
    peak_frame_from_rows,
    peak_rows_from_frame,
    prediction_frame,
    resolution_frame,
)
from hplcsim.fit import fit_peaks
from hplcsim.model import Peak, PeakRow, Programme, log10_k0_from_ln_k0, s_base10_from_s_e
from hplcsim.resolution import PredictedPeak, ResolutionTable
from hplcsim.retention import gradient_end_time, predict_retention
from hplcsim.session import Session, save_session
from lab_data import (
    LAB_MEASURED_AREA,
    LAB_MEASURED_PEAKS,
    LAB_MEASURED_TG25,
    LAB_METHOD,
    LAB_RUN1,
    LAB_RUN2,
    LAB_RUN3,
)

# The engine's prediction of validation/run3.csv from runs 1–2 at t0 = 0.525 (the
# pre-build blind prediction in the #14–#17 handoff was 13.861 / 16.729 / 24.383 at 0.6),
# re-asserted in test_reality.py — the "engine fixture values" the ticket's third
# acceptance criterion says the app must match.
_TG25_PREDICTED = {"Unknown-1": 13.871, "Unknown-2": 16.740, "Unknown-3": 24.395}


def _row(peak: Peak) -> PeakRow:
    """A lab fixture peak as the peak table would hold it after typing."""
    return PeakRow(
        name=peak.name,
        t_r_run1=peak.t_r_run1,
        t_r_run2=peak.t_r_run2,
        area_run1=peak.area_run1,
        area_run2=peak.area_run2,
        w_half_run1=peak.w_half_run1,
        w_half_run2=peak.w_half_run2,
    )


def _lab_inputs(**overrides: object) -> CockpitInputs:
    inputs = CockpitInputs(
        method=LAB_METHOD,
        run1=LAB_RUN1,
        run2=LAB_RUN2,
        candidate=LAB_RUN3.gradient,
        rows=tuple(_row(peak) for peak in LAB_MEASURED_PEAKS),
    )
    return replace(inputs, **overrides)  # type: ignore[arg-type]


def _by_name(cockpit: Cockpit) -> dict[str, float]:
    return {name: peak.retention.t_r for name, peak in cockpit.predicted_by_name.items()}


# --- the acceptance criteria -----------------------------------------------------------


def test_the_apps_run3_prediction_is_the_engines_own() -> None:  # AC 3
    """The Cockpit adds no arithmetic of its own between the fit and the screen.

    Not "within a tolerance": the app is supposed to be a thin layer over the engine,
    so the two paths must agree exactly. A rounding, a re-derived b_e or a stray unit
    conversion sneaking into the UI would show up here as an inequality, which is the
    failure this ticket is most exposed to.
    """
    engine = {
        peak.name: predict_retention(fit.params, LAB_METHOD, LAB_RUN3.gradient).t_r
        for peak, fit in zip(
            LAB_MEASURED_PEAKS,
            fit_peaks(LAB_MEASURED_PEAKS, LAB_METHOD, LAB_RUN1, LAB_RUN2),
            strict=True,
        )
    }

    assert _by_name(run_cockpit(_lab_inputs())) == engine


def test_the_apps_run3_prediction_matches_the_pinned_fixture_values() -> None:  # AC 3
    """And that shared number is still the one the reality bar recorded pre-build."""
    predicted = _by_name(run_cockpit(_lab_inputs()))

    assert predicted == pytest.approx(_TG25_PREDICTED, abs=0.001)
    # The measured run-3 times are held out of the fit entirely: SPEC §10's trust bar.
    errors = [
        100.0 * abs(predicted[name] - measured) / measured
        for name, measured in LAB_MEASURED_TG25.items()
    ]
    assert max(errors) <= 2.0


def test_an_untracked_row_is_counted_and_kept_out_of_every_result() -> None:  # AC 2
    """SPEC §5: visible, named, counted — and absent from fit, prediction and resolution."""
    half_paired = PeakRow(name="Unknown-4", t_r_run1=12.0)
    cockpit = run_cockpit(_lab_inputs(rows=(*_lab_inputs().rows, half_paired)))

    assert cockpit.entry.untracked_count == 1
    assert [row.name for row in cockpit.entry.untracked] == ["Unknown-4"]
    assert "Unknown-4" not in _by_name(cockpit)
    assert all("Unknown-4" not in outcome.peak.name for outcome in cockpit.outcomes)
    assert cockpit.resolution is not None
    assert all("Unknown-4" not in pair.earlier.name for pair in cockpit.resolution.pairs)
    # It still reaches the screen — as a row saying why it was held back.
    note = fit_frame(cockpit).set_index(COMPOUND).loc["Unknown-4", "Note"]
    assert note == "untracked — not fitted"


def test_sliding_the_candidate_moves_every_prediction() -> None:  # AC 1
    """The live half of the flow: the candidate gradient is the only thing that changed."""
    shallower = replace(LAB_RUN3.gradient, t_gradient=60.0)

    at_25 = _by_name(run_cockpit(_lab_inputs()))
    at_60 = _by_name(run_cockpit(_lab_inputs(candidate=shallower)))

    assert at_25.keys() == at_60.keys()
    assert all(at_60[name] > at_25[name] for name in at_25)


# --- entry: what counts as a row, and as a tracked one ----------------------------------


def test_blank_rows_are_not_peaks_and_do_not_take_a_number() -> None:
    """The editor's spare rows are not half-entered compounds; numbering skips them."""
    entry = split_rows(
        [PeakRow(), PeakRow(t_r_run1=9.9, t_r_run2=20.8), PeakRow(), PeakRow(t_r_run1=11.6)]
    )

    assert [peak.name for peak in entry.tracked] == ["P1"]
    assert [row.name for row in entry.untracked] == ["P2"]


def test_a_typed_name_survives_the_automatic_numbering() -> None:
    entry = split_rows(
        [PeakRow(name="Caffeine", t_r_run1=9.9, t_r_run2=20.8), PeakRow(t_r_run1=1.0)]
    )

    assert [peak.name for peak in entry.tracked] == ["Caffeine"]
    # Numbering counts every non-blank row, so the named row still consumes P1.
    assert [row.name for row in entry.untracked] == ["P2"]


def test_a_row_carries_its_optional_measurements_into_the_engines_peak() -> None:
    """Areas and widths are what the chromatogram and the fitted N rest on."""
    peak = _row(LAB_MEASURED_PEAKS[0]).as_peak()

    assert peak == LAB_MEASURED_PEAKS[0]


def test_a_half_paired_row_has_no_engine_peak_at_all() -> None:
    assert PeakRow(name="x", t_r_run1=12.0).as_peak() is None
    assert PeakRow(name="x", t_r_run2=12.0).as_peak() is None


# --- the entry boundaries of SPEC §4 ----------------------------------------------------


def test_a_dwell_volume_becomes_a_time_by_dividing_by_the_flow() -> None:
    """SPEC §4: "entered as t_D (min) or V_D (mL, ÷F)". The lab method's own numbers."""
    assert dwell_from_volume(0.375, 0.4) == pytest.approx(0.9375)
    assert dwell_from_volume(0.375, 0.4) == LAB_METHOD.t_dwell


def test_a_dwell_volume_at_zero_flow_is_refused_rather_than_returned_as_infinity() -> None:
    with pytest.raises(ValueError, match="flow must be positive"):
        dwell_from_volume(0.375, 0.0)


def test_percent_b_reaches_the_engine_as_a_fraction_and_only_here() -> None:
    """CLAUDE.md's units rule: %B is an entry boundary, φ is what the engine holds.

    Since #73 the boundary is the rail's scouting table (`ScoutingEntry`), not the
    sidebar; `tests/test_rail.py` owns the table, this keeps the rule's own name."""
    entry = ScoutingEntry(
        percent_b_start=5.0, percent_b_end=95.0, hold=0.5, t_gradient1=15.0, t_gradient2=45.0
    )

    gradient = entry.gradient(15.0)

    assert (gradient.phi0, gradient.phif) == (0.05, 0.95)
    assert gradient.delta_phi == pytest.approx(0.9)
    assert (gradient.t_gradient, gradient.t_init) == (15.0, 0.5)
    assert entry.gradient(LAB_RUN1.gradient.t_gradient) == LAB_RUN1.gradient


def test_the_method_entry_is_the_method_and_the_knob_and_nothing_of_the_gradient() -> None:
    """v0.1's sidebar held the %B range and the hold; v0.2's rail does (SPEC §7)."""
    entry = MethodEntry(method=LAB_METHOD, plate_count=12000.0)
    assert {f.name for f in fields(entry)} == {"method", "plate_count"}


# --- warnings over blocks ---------------------------------------------------------------


def test_a_peak_the_engine_refuses_is_a_note_beside_its_row_not_a_crash() -> None:
    """CLAUDE.md's posture, applied to a table someone is still typing into.

    A peak eluting before the gradient reaches the column has no LSS fit — but the
    other rows do, and emptying the screen over one bad row is the wrong trade while
    entry is in progress.
    """
    unfittable = PeakRow(name="Solvent front", t_r_run1=0.7, t_r_run2=0.7)
    cockpit = run_cockpit(_lab_inputs(rows=(unfittable, *_lab_inputs().rows)))

    refused = cockpit.outcomes[0]
    assert refused.fit is None
    assert refused.error is not None and "nothing to fit" in refused.error
    assert len(cockpit.fitted) == 3
    assert set(_by_name(cockpit)) == {"Unknown-1", "Unknown-2", "Unknown-3"}


def test_two_runs_at_the_same_gradient_time_block_once_not_once_per_peak() -> None:
    """SPEC §4's one hard failure. It is a fault of the method, so it is reported once."""
    cockpit = run_cockpit(_lab_inputs(run2=LAB_RUN1))

    assert cockpit.blocked is not None and "same gradient time" in cockpit.blocked
    assert cockpit.outcomes == ()
    assert cockpit.resolution is None
    # The rows are still there to be corrected — the block is on the runs, not the entry.
    assert len(cockpit.entry.tracked) == 3


def test_nothing_entered_yet_is_a_quiet_screen_not_an_error() -> None:
    cockpit = run_cockpit(_lab_inputs(rows=()))

    assert cockpit.blocked is None
    assert cockpit.resolution is None
    assert cockpit.entry.untracked_count == 0


# --- diagnostic 5's scope ----------------------------------------------------------------


def test_the_width_banner_names_only_the_peaks_whose_n_is_the_column_estimate() -> None:
    """SPEC §6 diagnostic 5 is scoped to a *defaulted* N, read off the engine's stamp."""
    widthless = tuple(
        replace(row, w_half_run1=None, w_half_run2=None) for row in _lab_inputs().rows[:1]
    )
    mixed = run_cockpit(_lab_inputs(rows=(*widthless, *_lab_inputs().rows[1:])))

    assert mixed.defaulted_width_names == ("Unknown-1",)
    # Every peak carrying a W½ has its own N fitted, so nothing is caveated.
    assert run_cockpit(_lab_inputs()).defaulted_width_names == ()


def test_the_global_knob_is_not_a_defaulted_plate_count() -> None:
    """A number the user typed is "supplied", not the geometry estimate the banner is about."""
    widthless = tuple(
        replace(row, w_half_run1=None, w_half_run2=None) for row in _lab_inputs().rows
    )

    assert run_cockpit(_lab_inputs(rows=widthless, plate_count=9000.0)).defaulted_width_names == ()
    assert run_cockpit(_lab_inputs(rows=widthless)).defaulted_width_names == (
        "Unknown-1",
        "Unknown-2",
        "Unknown-3",
    )


def test_a_peaks_own_width_outranks_the_global_knob() -> None:
    """Measured-first, the precedence SPEC §4 gives N (fitted > knob > column estimate)."""
    cockpit = run_cockpit(_lab_inputs(plate_count=9000.0))
    used = {name: peak.width.plate_count for name, peak in cockpit.predicted_by_name.items()}

    assert all(n != 9000.0 for n in used.values())
    assert all(
        peak.width.plate_count_source == "fitted" for peak in cockpit.predicted_by_name.values()
    )


# --- area shares --------------------------------------------------------------------------


def test_area_shares_normalise_within_each_run_before_combining_them() -> None:
    """A run that simply ran hotter must not outvote the other."""
    hotter = [
        Peak(t_r_run1=1.0, t_r_run2=2.0, name="A", area_run1=1.0, area_run2=300.0),
        Peak(t_r_run1=1.0, t_r_run2=2.0, name="B", area_run1=3.0, area_run2=100.0),
    ]

    shares = area_shares(hotter)

    assert shares == pytest.approx({"A": 0.5, "B": 0.5})


def test_a_peak_with_no_area_at_all_refuses_the_whole_set_rather_than_inventing_one() -> None:
    """SPEC §7 scales heights by area shares *where areas exist* — this is where they don't."""
    partial = [
        Peak(t_r_run1=1.0, t_r_run2=2.0, name="A", area_run1=10.0),
        Peak(t_r_run1=1.0, t_r_run2=2.0, name="B"),
    ]

    assert area_shares(partial) is None
    assert area_shares([Peak(t_r_run1=1.0, t_r_run2=2.0, name="A")]) is None


def test_one_run_of_areas_is_enough_to_scale_the_chromatogram() -> None:
    single = [
        Peak(t_r_run1=1.0, t_r_run2=2.0, name="A", area_run1=1.0),
        Peak(t_r_run1=1.0, t_r_run2=2.0, name="B", area_run1=3.0),
    ]

    assert area_shares(single) == pytest.approx({"A": 0.25, "B": 0.75})


def test_a_peak_that_was_not_fitted_does_not_dilute_the_shares_of_the_ones_drawn() -> None:
    """Shares are of the sample the chromatogram shows, so they run over the drawn peaks.

    A row the engine refused has no place on the trace, and letting its area sit in the
    denominator would shrink every peak that *is* drawn by a fraction nobody can see.
    """
    with_areas = tuple(replace(row, area_run1=1.0) for row in _lab_inputs().rows)
    refused = PeakRow(name="Solvent front", t_r_run1=0.7, t_r_run2=0.7, area_run1=9.0)

    drawn = run_cockpit(_lab_inputs(rows=with_areas)).shares
    with_a_refused_row = run_cockpit(_lab_inputs(rows=(refused, *with_areas))).shares

    assert drawn == pytest.approx({"Unknown-1": 1 / 3, "Unknown-2": 1 / 3, "Unknown-3": 1 / 3})
    assert with_a_refused_row == drawn


def test_the_lab_dataset_reaches_the_chromatogram_with_its_measured_shares() -> None:
    """The run-1 areas of `validation/run1.csv`, as the trace would scale them."""
    with_areas = tuple(
        replace(
            row,
            area_run1=LAB_MEASURED_AREA["tG15"][row.name],
            area_run2=LAB_MEASURED_AREA["tG45"][row.name],
        )
        for row in _lab_inputs().rows
    )
    shares = run_cockpit(_lab_inputs(rows=with_areas)).shares

    assert shares is not None
    assert sum(shares.values()) == pytest.approx(1.0)
    assert shares["Unknown-1"] > shares["Unknown-2"] > shares["Unknown-3"]


# --- the chromatogram ----------------------------------------------------------------------


def _lab_trace(**overrides: object) -> tuple[ResolutionTable, Chromatogram]:
    cockpit = run_cockpit(_lab_inputs(**overrides))
    assert cockpit.resolution is not None
    return cockpit.resolution, chromatogram(cockpit.resolution.peaks, cockpit.shares)


def test_the_trace_spans_every_peak_it_draws() -> None:
    resolution, trace = _lab_trace()
    times = [peak.retention.t_r for peak in resolution.peaks]

    assert trace.time[0] >= 0.0
    assert trace.time[0] < min(times)
    assert trace.time[-1] > max(times)


def test_the_trace_runs_from_injection_so_the_whole_run_is_on_screen() -> None:
    """The axis is the run, not a crop of it: 0.00 min through the last peak."""
    resolution, trace = _lab_trace()
    last = max(peak.retention.t_r for peak in resolution.peaks)

    assert trace.time[0] == 0.0
    # The end is the last peak plus only enough margin for it to come back to baseline.
    assert last < trace.time[-1] < last + 0.5
    # The lead-in is empty, which is the point of showing it.
    assert (
        trace.signal[trace.time < min(p.retention.t_r for p in resolution.peaks) * 0.9].max() < 1e-3
    )
    # A 13.9 min lead-in on the lab run must not have spent the peaks' sampling budget.
    _assert_every_apex_is_drawn(trace, resolution.peaks)


def _assert_every_apex_is_drawn(trace: Chromatogram, peaks: Sequence[PredictedPeak]) -> None:
    for peak in peaks:
        window = np.abs(trace.time - peak.retention.t_r) < peak.width.sigma
        own_apex = next(lb.height for lb in trace.labels if lb.name == peak.name)
        assert trace.signal[window].max() >= own_apex * 0.995


def test_the_grid_is_fine_enough_that_the_narrowest_peak_is_drawn_as_a_peak() -> None:
    """A 1.6 µm column puts σ near 0.01 min in a 25 min window; a fixed grid aliases it.

    The apex the user sees must be the apex the engine predicted, not whatever the
    sampling happened to land on. Half a percent is far inside any line width.
    """
    resolution, trace = _lab_trace()

    for peak in resolution.peaks:
        window = np.abs(trace.time - peak.retention.t_r) < peak.width.sigma
        sampled = trace.signal[window].max()
        assert sampled > 0.0
        # The summed trace at the apex is at least this peak's own contribution.
        own_apex = next(label.height for label in trace.labels if label.name == peak.name)
        assert sampled >= own_apex * 0.995


def test_with_areas_a_share_is_spent_as_area_so_a_broader_peak_is_drawn_shorter() -> None:
    """SPEC §7's "heights scaled by area shares", read the way a detector reads it."""
    equal_areas = tuple(replace(row, area_run1=1.0, area_run2=1.0) for row in _lab_inputs().rows)
    resolution, trace = _lab_trace(rows=equal_areas)

    assert trace.scaled_by_area is True
    widths = {peak.name: peak.width.sigma for peak in resolution.peaks}
    heights = {label.name: label.height for label in trace.labels}
    broadest = max(widths, key=lambda name: widths[name])
    narrowest = min(widths, key=lambda name: widths[name])
    assert heights[broadest] < heights[narrowest]


def test_without_areas_every_peak_is_drawn_to_the_same_height() -> None:
    """No areas is not an amount of zero, and not an amount of one — it is no claim."""
    _, trace = _lab_trace()

    assert trace.scaled_by_area is False
    assert {label.height for label in trace.labels} == {1.0}


def test_the_marker_says_when_the_ramp_reaches_the_detector() -> None:
    """The same instant the engine uses to call a peak post-gradient (SPEC §3).

    A steep candidate puts the lab peaks on both sides of it: two elute during the ramp,
    one after. The marker has to fall between them, or it is not the boundary it claims.
    """
    steep = replace(LAB_RUN3.gradient, t_gradient=4.0)
    inputs = _lab_inputs(candidate=steep)
    cockpit = run_cockpit(inputs)
    assert cockpit.resolution is not None
    end = gradient_end_time(inputs.method, steep)

    trace = chromatogram(cockpit.resolution.peaks, cockpit.shares, gradient_end=end)

    assert trace.gradient_end == pytest.approx(end)
    regimes = {peak.retention.regime for peak in cockpit.resolution.peaks}
    assert regimes == {"gradient", "post_gradient"}
    for peak in cockpit.resolution.peaks:
        if peak.retention.regime == "post_gradient":
            assert peak.retention.t_r > end
        else:
            assert peak.retention.t_r < end


def test_a_ramp_that_outlasts_the_peaks_is_still_on_the_axis() -> None:
    """The marker explains the picture, so it must not be the thing cropped out of it."""
    cockpit = run_cockpit(_lab_inputs())
    assert cockpit.resolution is not None
    last = max(peak.retention.t_r for peak in cockpit.resolution.peaks)

    trace = chromatogram(cockpit.resolution.peaks, cockpit.shares, gradient_end=last + 30.0)

    # Past the marker, not on it: a line on the plot frame is a line nobody sees.
    assert trace.time[-1] > last + 30.0
    assert trace.time[0] == 0.0
    # The long empty tail must not have starved the peaks of sampling.
    _assert_every_apex_is_drawn(trace, cockpit.resolution.peaks)


def test_without_a_method_the_trace_draws_no_marker_it_cannot_place() -> None:
    _, trace = _lab_trace()

    assert trace.gradient_end is None


# --- the drawn window ----------------------------------------------------------------------


def test_by_default_the_window_is_the_whole_run_from_injection_and_from_zero() -> None:
    _, trace = _lab_trace()

    view = axis_view(trace)

    assert view.x_range == (float(trace.time[0]), float(trace.time[-1]))
    assert view.x_range[0] == 0.0
    assert view.y_range[0] == 0.0
    assert view.y_range[1] > float(trace.signal.max())
    assert view.notes == ()
    # The extents the controls seed from are the ones the ranges defaulted to.
    assert (view.run_x, view.run_y) == (view.x_range, view.y_range)


def test_a_later_start_crops_the_view_without_touching_the_prediction() -> None:
    """The control is a window onto the run, not a different run."""
    _, trace = _lab_trace()
    before = trace.signal.copy()

    view = axis_view(trace, AxisRequest(x_start=5.0, y_start=0.25))

    assert view.x_range == (5.0, float(trace.time[-1]))
    assert view.y_range[0] == 0.25
    assert view.notes == ()
    assert np.array_equal(trace.signal, before)


def test_both_ends_of_both_axes_are_the_readers_to_set() -> None:
    _, trace = _lab_trace()

    # A window that still holds every lab peak (13.9–24.4 min, equal heights of 1.0).
    view = axis_view(trace, AxisRequest(x_start=10.0, x_end=30.0, y_start=0.1, y_end=1.2))

    assert view.x_range == (10.0, 30.0)
    assert view.y_range == (0.1, 1.2)
    assert view.notes == ()


def test_an_x_end_past_the_run_draws_the_baseline_out_to_it() -> None:
    """A wider window onto a shorter trace would stop the line in mid-air."""
    cockpit = run_cockpit(_lab_inputs())
    assert cockpit.resolution is not None

    trace = chromatogram(cockpit.resolution.peaks, cockpit.shares, extend_to=40.0)
    view = axis_view(trace, AxisRequest(x_end=40.0))

    assert trace.time[-1] >= 40.0
    assert view.x_range == (0.0, 40.0)
    # Drawn all the way out, and flat once the peaks are done.
    assert float(trace.signal[trace.time > 30.0].max()) < 1e-6


def test_a_window_that_leaves_a_peak_out_says_so() -> None:
    """A stale or deliberate crop is honoured, and named — fewer peaks on the plot than
    in the table must never read as a prediction with fewer peaks."""
    resolution, trace = _lab_trace()
    times = sorted(peak.retention.t_r for peak in resolution.peaks)
    apex = max(label.height for label in trace.labels)

    view = axis_view(trace, AxisRequest(x_end=(times[-1] + times[-2]) / 2.0, y_end=apex / 2.0))

    assert view.x_range[1] < times[-1]
    assert len(view.notes) == 1
    assert "outside the x range" in view.notes[0]
    assert "taller than the y range" in view.notes[0]
    assert "the prediction still has them" in view.notes[0]


def test_the_view_never_reaches_the_session_file() -> None:
    """SPEC §8: inputs only. The window is not an input, so the file cannot carry it."""
    session = Session(
        method=LAB_METHOD,
        runs=(LAB_RUN1, LAB_RUN2),
        peaks=tuple(LAB_MEASURED_PEAKS),
        candidate=Programme.from_gradient(LAB_RUN3.gradient),
    )

    assert not any("axis" in f.name or "view" in f.name for f in fields(Session))
    assert "axis" not in save_session(session).lower()


def test_an_end_below_its_own_start_warns_and_shows_everything_rather_than_a_blank_plot() -> None:
    """CLAUDE.md: warn and annotate; block only on an impossibility."""
    _, trace = _lab_trace()
    full = (float(trace.time[0]), float(trace.time[-1]))

    view = axis_view(trace, AxisRequest(x_start=20.0, x_end=3.0, y_start=0.9, y_end=0.2))

    assert view.x_range == full
    assert view.y_range[0] == 0.0
    assert len(view.notes) == 2
    assert "x-axis end" in view.notes[0]
    assert "y-axis end" in view.notes[1]


def test_a_chromatogram_of_nothing_is_refused_rather_than_drawn_empty() -> None:
    with pytest.raises(ValueError, match="at least one predicted peak"):
        chromatogram([])


# --- the display boundary ---------------------------------------------------------------


def test_the_peak_table_round_trips_through_the_editors_frame() -> None:
    """What the editor hands back must be what the pipeline was given."""
    rows = list(_lab_inputs().rows)
    frame = pd.DataFrame([_as_record(row) for row in rows], columns=list(PEAK_COLUMNS))

    assert peak_rows_from_frame(frame) == rows


def test_an_empty_cell_is_none_not_a_nan_that_reaches_the_engine() -> None:
    frame = blank_peak_frame(rows=2)
    frame.loc[0, COMPOUND] = "A"
    frame.loc[0, TR_RUN1] = 9.855
    frame.loc[0, TR_RUN2] = 20.831

    rows = peak_rows_from_frame(frame)

    assert rows[0] == PeakRow(name="A", t_r_run1=9.855, t_r_run2=20.831)
    assert rows[1].is_blank


def test_the_blank_frame_offers_every_column_the_input_contract_names() -> None:
    """SPEC §4's optional per-peak entries are columns, not a second screen."""
    assert tuple(blank_peak_frame().columns) == PEAK_COLUMNS


def test_a_restored_table_goes_back_into_the_editor_as_the_rows_it_came_from() -> None:
    """Ticket #21's load path: the frame the editor is re-seeded with must read back."""
    rows = [row for row in _lab_inputs().rows if not row.is_blank]
    frame = peak_frame_from_rows(rows)

    assert tuple(frame.columns) == PEAK_COLUMNS
    assert [row for row in peak_rows_from_frame(frame) if not row.is_blank] == rows


def test_a_restored_table_keeps_the_dtypes_a_fresh_one_has() -> None:
    """Otherwise the editor offers text fields for the numbers of a loaded session."""
    frame = peak_frame_from_rows([PeakRow(name="A", t_r_run1=9.855, t_r_run2=20.831)])
    assert list(frame.dtypes) == list(blank_peak_frame().dtypes)


def test_a_half_paired_row_comes_back_with_its_gap_still_empty() -> None:
    """The missing tR must return as None, not as a NaN the engine would try to fit."""
    frame = peak_frame_from_rows([PeakRow(name="P1", t_r_run1=9.855)])
    restored = peak_rows_from_frame(frame)[0]
    assert restored == PeakRow(name="P1", t_r_run1=9.855)


def test_a_restored_table_carries_spare_rows_to_go_on_typing_into() -> None:
    frame = peak_frame_from_rows([PeakRow(name="A", t_r_run1=9.855, t_r_run2=20.831)])
    assert sum(row.is_blank for row in peak_rows_from_frame(frame)) > 0


def test_restoring_an_empty_table_is_the_blank_table() -> None:
    assert peak_frame_from_rows([]).equals(blank_peak_frame())


def test_the_fit_table_quotes_the_base10_parameters_a_chromatographer_reads() -> None:
    """CLAUDE.md's log-convention rule: the ln→log10 turn happens at the display boundary.

    The engine holds ln k0 and S_e; the table must show log10 k0 and S, and must get
    them from ``model``'s converters rather than from a 2.303 typed in here — the
    project's #1 named hazard, in the one file most likely to re-introduce it.
    """
    cockpit = run_cockpit(_lab_inputs())
    frame = fit_frame(cockpit).set_index(COMPOUND)

    for peak, fit in cockpit.fitted:
        assert frame.loc[peak.name, "log10 k0"] == log10_k0_from_ln_k0(fit.params.ln_k0)
        assert frame.loc[peak.name, "S"] == s_base10_from_s_e(fit.params.s_e)
    # The fitted values at t0 = 0.525, in the convention the screen shows them in.
    assert list(frame["S"]) == pytest.approx([4.919, 4.836, 5.016], abs=0.01)
    assert list(frame["log10 k0"]) == pytest.approx([2.777, 3.249, 4.711], abs=0.01)


def test_the_fit_table_carries_the_plate_count_its_widths_rest_on() -> None:
    cockpit = run_cockpit(_lab_inputs())
    frame = fit_frame(cockpit).set_index(COMPOUND)

    assert list(frame["N from"]) == ["fitted from W½"] * 3
    # The consistency diagnostic of `plate-count-from-widths.md` §6, per peak.
    assert list(frame[N_RATIO]) == pytest.approx([0.978, 1.038, 1.121], abs=0.002)


def test_the_fit_table_says_which_of_the_three_plate_counts_each_peak_got() -> None:
    """The precedence of SPEC §4, spelled out per row: fitted > global knob > column estimate.

    The provenance is the whole point of the column — a defaulted N is what SPEC §6
    diagnostic 5 caveats, and a fitted one is what it does not.
    """
    widthless = tuple(
        replace(row, w_half_run1=None, w_half_run2=None) for row in _lab_inputs().rows
    )
    mixed = (*widthless[:1], *_lab_inputs().rows[1:])

    def sources(**overrides: object) -> list[str]:
        return list(fit_frame(run_cockpit(_lab_inputs(**overrides)))["N from"])

    assert sources(rows=widthless) == ["column estimate"] * 3
    assert sources(rows=widthless, plate_count=9000.0) == ["global knob"] * 3
    assert sources(rows=mixed, plate_count=9000.0) == [
        "global knob",
        "fitted from W½",
        "fitted from W½",
    ]


def test_every_table_keeps_its_columns_when_there_is_nothing_to_put_in_them() -> None:
    """An empty screen must not be a differently-shaped screen."""
    empty = run_cockpit(_lab_inputs(rows=()))

    assert tuple(fit_frame(empty).columns) == FIT_COLUMNS
    assert tuple(prediction_frame(empty, {}).columns) == PREDICTION_COLUMNS
    assert tuple(resolution_frame(empty, Diagnostics()).columns) == RESOLUTION_COLUMNS


def test_the_prediction_and_resolution_tables_are_in_elution_order() -> None:
    """Order is a property of the condition, not of the typed list (research doc §7.4)."""
    cockpit = run_cockpit(_lab_inputs())
    times = list(prediction_frame(cockpit, {})["tR (min)"])
    pairs = list(resolution_frame(cockpit, Diagnostics())["Pair"])

    assert times == sorted(times)
    assert pairs == ["Unknown-1 / Unknown-2", "Unknown-2 / Unknown-3"]


def test_the_resolution_table_agrees_with_the_times_and_widths_beside_it() -> None:
    """Rs = ΔtR / 2(σ₁+σ₂) — the same numbers, not a second calculation."""
    cockpit = run_cockpit(_lab_inputs())
    assert cockpit.resolution is not None
    predicted = prediction_frame(cockpit, {}).set_index(COMPOUND)
    resolutions = resolution_frame(cockpit, Diagnostics())
    w_half_per_sigma = math.sqrt(8.0 * math.log(2.0))

    for row, pair in zip(resolutions.to_dict("records"), cockpit.resolution.pairs, strict=True):
        earlier, later = str(row["Pair"]).split(" / ")
        widths = predicted.loc[earlier, "W½ (min)"] + predicted.loc[later, "W½ (min)"]
        assert row["Rs"] == pytest.approx(w_half_per_sigma * row["ΔtR (min)"] / (2.0 * widths))
        assert row["ΔtR (min)"] == pytest.approx(
            predicted.loc[later, "tR (min)"] - predicted.loc[earlier, "tR (min)"]
        )
        assert pair.rs == pytest.approx(row["Rs"])


def _as_record(row: PeakRow) -> dict[str, object]:
    return dict(zip(PEAK_COLUMNS, (row.name, *row.measurements), strict=True))


def test_a_typed_name_that_collides_with_an_automatic_one_does_not_lose_a_peak() -> None:
    """Pins a real defect: a duplicate name dropped a peak, and nothing said so.

    Everything downstream looks a peak up by name — ``predicted_by_name`` feeds the
    selected-peak list, and the fit table's width lookup keys on it too. Two rows
    sharing a name collapsed into one entry, so the rail counted three peaks while
    the list offered two and the survivor wore the other's width.
    """
    entry = split_rows(
        [
            PeakRow(name="P2", t_r_run1=9.855, t_r_run2=20.831),
            PeakRow(t_r_run1=11.592, t_r_run2=25.932),
            PeakRow(t_r_run1=16.159, t_r_run2=39.796),
        ]
    )

    names = [peak.name for peak in entry.tracked]
    assert names == ["P2", "P2 (2)", "P3"]
    assert len(set(names)) == len(names)
    assert entry.renamed == (("P2", "P2 (2)"),)


def test_every_fitted_peak_reaches_the_selected_peak_list() -> None:
    """The count in the rail and the length of the list must be the same number."""
    rows = [
        PeakRow(name="P2", t_r_run1=9.855, t_r_run2=20.831),
        PeakRow(t_r_run1=11.592, t_r_run2=25.932),
        PeakRow(t_r_run1=16.159, t_r_run2=39.796),
    ]
    cockpit = run_cockpit(_lab_inputs(rows=tuple(rows)))

    assert cockpit.resolution is not None
    assert len(cockpit.predicted_by_name) == len(cockpit.resolution.peaks) == 3


def test_two_hand_typed_names_that_match_are_both_kept_and_reported() -> None:
    entry = split_rows(
        [
            PeakRow(name="Caffeine", t_r_run1=9.855, t_r_run2=20.831),
            PeakRow(name="Caffeine", t_r_run1=11.592, t_r_run2=25.932),
        ]
    )

    assert [peak.name for peak in entry.tracked] == ["Caffeine", "Caffeine (2)"]
    assert entry.renamed == (("Caffeine", "Caffeine (2)"),)


def test_names_that_are_already_distinct_are_left_exactly_as_typed() -> None:
    """The rename is a repair, not a habit: untouched names must report nothing."""
    entry = split_rows(
        [
            PeakRow(name="Caffeine", t_r_run1=9.855, t_r_run2=20.831),
            PeakRow(name="Theophylline", t_r_run1=11.592, t_r_run2=25.932),
        ]
    )

    assert [peak.name for peak in entry.tracked] == ["Caffeine", "Theophylline"]
    assert entry.renamed == ()


def test_the_prediction_table_carries_each_peaks_badges_beside_it() -> None:
    """SPEC §6's per-peak badges (diagnostics 2 and 4), as a column the eye can scan.

    The sentence belongs to the selected-peak panel; the table needs one scannable word
    per row, and an empty string where a peak has nothing wrong with it.
    """
    inputs = _lab_inputs()
    cockpit = run_cockpit(inputs)
    frame = prediction_frame(cockpit, diagnose(inputs, cockpit).badges)

    assert list(frame.columns) == list(PREDICTION_COLUMNS)
    assert list(frame[FLAGS]) == ["", "", ""]


def test_a_badged_peak_is_labelled_in_the_flags_column() -> None:
    early = PeakRow(name="Early", t_r_run1=2.458, t_r_run2=2.483)
    inputs = _lab_inputs(rows=(*(_row(peak) for peak in LAB_MEASURED_PEAKS), early))
    cockpit = run_cockpit(inputs)
    frame = prediction_frame(cockpit, diagnose(inputs, cockpit).badges)

    flags = dict(zip(frame[COMPOUND], frame[FLAGS], strict=True))
    assert flags["Early"] == "early eluter; low k0"  # k0 at 5 %B is below 8's floor too
    assert flags["Unknown-1"] == ""


# --- the t0 autofill decision (SPEC §4's geometry fallback, ticket #24) -------------------


class TestT0Autofill:
    """Which of the three cases the field is in, from the two numbers it can be compared to."""

    def test_a_fresh_choice_fills_over_whatever_was_typed(self) -> None:
        assert t0_autofill(0.525, None, 0.4503) == pytest.approx(0.4503)

    def test_a_field_still_holding_the_last_autofill_tracks_the_geometry(self) -> None:
        assert t0_autofill(0.4503, 0.4503, 0.2251) == pytest.approx(0.2251)

    def test_a_field_the_user_overwrote_is_left_alone(self) -> None:
        assert t0_autofill(0.525, 0.4503, 0.4503) is None

    def test_an_empty_field_is_filled(self) -> None:
        assert t0_autofill(None, 0.4503, 0.4503) == pytest.approx(0.4503)
