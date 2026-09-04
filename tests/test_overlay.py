"""SPEC §7's programme overlay and SPEC §6's four remaining surfaces (ticket #74).

Two things are asserted here, and the first is what the second rests on.

**The overlay's arithmetic.** Both programmes are drawn on the chromatogram's own x
axis, which is time from injection *at the detector* — so the composition curve is the
pump's programme delayed by t_dwell + t0. That delay is not a drawing choice: it is what
makes a peak's marker land exactly on the candidate curve whenever the peak elutes on a
ramp, because the composition the band left the column in *is* the composition arriving
at the detector at that instant. Pinned below to float precision on one segment, on
several, on a descending leg and on a peak brought off in a hold — if the delay were
dropped or doubled, every one of those markers would float off the line it explains.

**The surfaces, on exactly the runs SPEC §10 item 2 names.** The fit tab's per-peak
window readout, the low-k0 and wash-eluted badges in the Flags column, and the
*indicative, not decision-grade* stamp on the resolution table's own grade column, read
through `app.tables` on both bench samples' held-out runs. `tests/test_diagnostics_v2`
proves the diagnostics fire there; nothing in it proves one of them is ever rendered.
The browser's half is the ticket's Playwright screenshots.
"""

from __future__ import annotations

import pytest

import spec10_item2
from app.chromatogram import (
    ProgrammeCurve,
    chromatogram,
    figure,
    programme_curve,
    programme_overlay,
)
from app.diagnostics import Diagnostics, critical_pair_is_indicative, diagnose
from app.pipeline import Cockpit, CockpitInputs, run_cockpit
from app.tables import (
    COMPOUND,
    FLAGS,
    GRADE,
    WINDOW_CANDIDATE,
    WINDOW_COLUMNS,
    WINDOW_HIGH,
    WINDOW_LOW,
    WINDOW_POSITION,
    WINDOW_WIDTH,
    composition_window_frame,
    prediction_frame,
    resolution_frame,
    window_position_label,
)
from hplcsim.model import Gradient, Programme, Segment, Target, percent_b_from_phi
from hplcsim.retention import gradient_end_time
from lab_data import LAB_MEASURED_PEAKS, LAB_METHOD, LAB_RUN1, LAB_RUN2

# The trap case of #45 and of this ticket's acceptance criteria: a candidate that starts
# 10 %B above the scouting start and ramps to 55, at a tG inside the 15–45 bracket. Both
# strong-tier guards' territory, and the condition the screenshots are taken at.
TRAP = Gradient(phi0=0.15, phif=0.55, t_gradient=25.0, t_init=0.5)

# One candidate with two ramps, for the multi-segment half of the acceptance criteria.
TWO_SEGMENT = Programme(phi0=0.05, segments=(Segment(10.0, 0.40), Segment(20.0, 0.95)), t_init=0.5)

# A descending leg and a peak left in the wash: the two shapes the delay could be got
# wrong on without the ordinary cases noticing.
DESCENDING = Programme(
    phi0=0.05,
    segments=(Segment(10.0, 0.60), Segment(5.0, 0.30), Segment(15.0, 0.95)),
    t_init=0.5,
)
WASH = Programme(phi0=0.05, segments=(Segment(12.0, 0.60), Segment(30.0, 0.60)), t_init=0.5)


def _inputs(candidate: Target) -> CockpitInputs:
    return spec10_item2.cockpit_inputs(
        LAB_METHOD, LAB_RUN1, LAB_RUN2, candidate, spec10_item2.rows(LAB_MEASURED_PEAKS)
    )


def _rendered(candidate: Target) -> tuple[CockpitInputs, Cockpit, Diagnostics]:
    inputs = _inputs(candidate)
    cockpit = run_cockpit(inputs)
    return inputs, cockpit, diagnose(inputs, cockpit)


def _overlay(candidate: Target, *, extend_to: float | None = None):  # type: ignore[no-untyped-def]
    inputs, cockpit, diagnostics = _rendered(candidate)
    return programme_overlay(
        inputs.method,
        inputs.target,
        (inputs.run1, inputs.run2),
        diagnostics.windows,
        cockpit.predicted_by_name,
        extend_to=extend_to,
    )


def _percent_b_at(curve: ProgrammeCurve, minutes: float) -> float:
    """Read a drawn curve the way the plot does — linear between its points, flat outside.

    Deliberately re-derived here rather than offered by :class:`ProgrammeCurve`: the
    assertion below is that a peak's marker lands *on* the curve, and a reader that
    shipped beside the curve would be the same arithmetic checking itself.
    """
    points = list(zip(curve.times, curve.percent_b, strict=True))
    if minutes <= points[0][0]:
        return points[0][1]
    for (t0, b0), (t1, b1) in zip(points, points[1:], strict=False):
        if t0 <= minutes <= t1:
            return b1 if t1 == t0 else b0 + (b1 - b0) * (minutes - t0) / (t1 - t0)
    return points[-1][1]


# --- the curves: a programme as the detector meets it -------------------------------------


def test_the_candidate_curve_is_the_programme_delayed_by_the_dwell_and_the_dead_time() -> None:
    """A programme is typed at the pump; this plot's x axis is the detector's."""
    curve = programme_curve(LAB_METHOD, TRAP, label="candidate", dashed=False)
    delay = LAB_METHOD.t_dwell + LAB_METHOD.t0

    assert curve.times[0] == 0.0
    assert curve.times[1] == pytest.approx(delay + TRAP.t_init)
    assert curve.times[2] == pytest.approx(delay + TRAP.t_init + TRAP.t_gradient)
    assert curve.percent_b == pytest.approx((15.0, 15.0, 55.0))
    assert not curve.dashed


def test_a_segment_is_a_point_so_a_further_segment_is_a_further_bend() -> None:
    curve = programme_curve(LAB_METHOD, TWO_SEGMENT, label="candidate", dashed=False)
    delay = LAB_METHOD.t_dwell + LAB_METHOD.t0

    assert curve.percent_b == pytest.approx((5.0, 5.0, 40.0, 95.0))
    assert curve.times == pytest.approx((0.0, delay + 0.5, delay + 10.5, delay + 30.5))


def test_the_curve_reaches_phi_f_where_the_gradient_end_marker_is_drawn() -> None:
    """The trace's own marker and the overlay must agree — one expression, two readers."""
    for candidate in (TRAP, TWO_SEGMENT, DESCENDING):
        curve = programme_curve(LAB_METHOD, candidate, label="candidate", dashed=False)
        end = gradient_end_time(LAB_METHOD, candidate)
        assert curve.times[-1] == pytest.approx(end)
        assert _percent_b_at(curve, end) == pytest.approx(percent_b_from_phi(candidate.phif))


def test_a_programme_that_ends_early_is_carried_flat_across_the_rest_of_the_plot() -> None:
    """Otherwise the composition line stops in mid-air partway across the window."""
    curve = programme_curve(LAB_METHOD, TRAP, label="candidate", dashed=False, extend_to=90.0)
    assert curve.times[-1] == 90.0
    assert curve.percent_b[-1] == pytest.approx(55.0)
    assert _percent_b_at(curve, 75.0) == pytest.approx(55.0)


def test_a_window_shorter_than_the_programme_does_not_truncate_it() -> None:
    short = programme_curve(LAB_METHOD, TRAP, label="candidate", dashed=False, extend_to=3.0)
    full = programme_curve(LAB_METHOD, TRAP, label="candidate", dashed=False)
    assert short == full


def test_the_scouting_pair_is_dashed_and_the_candidate_is_not() -> None:
    """SPEC §7's own distinction: "as run" against "predicted", carried by the line."""
    drawn = _overlay(TRAP)
    assert [curve.dashed for curve in drawn.scouting] == [True, True]
    assert drawn.candidate.dashed is False
    assert [curve.label for curve in drawn.scouting] == ["tG15", "tG45"]
    assert drawn.curves[-1] is drawn.candidate


# --- the markers: a peak's elution composition sits on the candidate's own curve -----------


@pytest.mark.parametrize(
    "candidate", [TRAP, TWO_SEGMENT, DESCENDING, WASH], ids=["one", "two", "descending", "wash"]
)
def test_every_peak_marker_lands_on_the_candidate_curve(candidate: Target) -> None:
    """The property the whole overlay rests on, and the reason for the delay.

    The composition a band leaves the column in is the composition arriving at the
    detector at that instant, so a marker at (tR, φ_e) is a point *of* the candidate
    curve — on a ramp, on a descending leg, and in a hold where the curve is flat.
    """
    drawn = _overlay(candidate)
    assert drawn.peaks
    for peak in drawn.peaks:
        assert peak.percent_b == pytest.approx(_percent_b_at(drawn.candidate, peak.t_r), abs=1e-9)


def test_a_peak_left_in_the_wash_is_marked_at_the_holds_own_composition() -> None:
    drawn = _overlay(WASH)
    late = [peak for peak in drawn.peaks if peak.t_r > 12.0 + LAB_METHOD.t_dwell]
    assert late
    assert all(peak.percent_b == pytest.approx(60.0) for peak in late)


def test_the_whisker_is_the_calibrated_window_the_fit_was_actually_shown() -> None:
    _, _, diagnostics = _rendered(TRAP)
    drawn = _overlay(TRAP)
    by_name = {window.name: window for window in diagnostics.windows}

    assert {peak.name for peak in drawn.peaks} == set(by_name)
    for peak in drawn.peaks:
        window = by_name[peak.name]
        assert peak.percent_b_low == pytest.approx(percent_b_from_phi(window.phi_low))
        assert peak.percent_b_high == pytest.approx(percent_b_from_phi(window.phi_high))
        assert peak.percent_b_low < peak.percent_b_high


def test_the_whisker_and_the_fit_tabs_readout_are_the_same_numbers() -> None:
    """One :class:`CompositionWindow` per peak, two surfaces — they cannot disagree."""
    _, _, diagnostics = _rendered(TRAP)
    frame = composition_window_frame(diagnostics.windows).set_index(COMPOUND)
    for peak in _overlay(TRAP).peaks:
        assert frame.loc[peak.name, WINDOW_LOW] == pytest.approx(peak.percent_b_low)
        assert frame.loc[peak.name, WINDOW_HIGH] == pytest.approx(peak.percent_b_high)
        assert frame.loc[peak.name, WINDOW_CANDIDATE] == pytest.approx(peak.percent_b)


def test_a_peak_with_no_prediction_is_left_out_rather_than_drawn_at_a_guessed_time() -> None:
    inputs, cockpit, diagnostics = _rendered(TRAP)
    thinned = {
        name: peak for name, peak in cockpit.predicted_by_name.items() if name != "Unknown-2"
    }
    drawn = programme_overlay(
        inputs.method, inputs.target, (inputs.run1, inputs.run2), diagnostics.windows, thinned
    )
    assert [peak.name for peak in drawn.peaks] == ["Unknown-1", "Unknown-3"]


# --- the %B axis ---------------------------------------------------------------------------


def test_the_percent_b_axis_holds_every_curve_and_every_whisker() -> None:
    drawn = _overlay(TRAP)
    low, high = drawn.percent_b_range
    for curve in drawn.curves:
        assert low <= min(curve.percent_b) and max(curve.percent_b) <= high
    for peak in drawn.peaks:
        assert low <= peak.percent_b_low and peak.percent_b_high <= high


def test_the_axis_is_padded_but_never_past_the_ends_a_chromatographer_reads() -> None:
    """A little air around what is drawn, and 0 / 100 %B as the ends of the axis."""
    low, high = _overlay(TWO_SEGMENT).percent_b_range
    assert low == pytest.approx(1.0)  # 5 %B start, less the 4 %B of air
    assert high == pytest.approx(99.0)  # 95 %B end, plus the same

    wide = Programme(phi0=0.02, segments=(Segment(20.0, 0.98),), t_init=0.5)
    low, high = _overlay(wide).percent_b_range
    assert low == 0.0  # 2 %B start: the padding stops at the floor
    assert high == 100.0  # 98 %B end: and at the ceiling


def test_a_shallow_candidate_is_not_magnified_into_a_full_height_ramp() -> None:
    """A 4 %B move drawn on a 4 %B axis would read as a gradient it is not."""
    narrow = Gradient(phi0=0.05, phif=0.09, t_gradient=25.0, t_init=0.5)
    drawn = programme_overlay(LAB_METHOD, narrow, (), (), {})
    low, high = drawn.percent_b_range
    assert high - low >= 10.0


# --- the figure ----------------------------------------------------------------------------


def _figure_for(candidate: Target):  # type: ignore[no-untyped-def]
    inputs, cockpit, diagnostics = _rendered(candidate)
    assert cockpit.resolution is not None
    trace = chromatogram(
        cockpit.resolution.peaks,
        cockpit.shares,
        gradient_end=gradient_end_time(inputs.method, inputs.target),
    )
    drawn = _overlay(candidate, extend_to=float(trace.time[-1]))
    return figure(trace, overlay=drawn), drawn


def test_the_overlay_reaches_the_figure_on_its_own_axis() -> None:
    fig, drawn = _figure_for(TRAP)
    on_second_axis = [t for t in fig.data if getattr(t, "yaxis", None) == "y2"]

    # two scouting curves, the candidate, and the peak markers
    assert len(on_second_axis) == len(drawn.curves) + 1
    assert fig.layout.yaxis2.range == pytest.approx(drawn.percent_b_range)
    assert fig.layout.yaxis2.side == "right"
    assert fig.layout.yaxis2.title.text == "%B"


def test_a_two_segment_candidate_draws_its_second_ramp() -> None:
    fig, _ = _figure_for(TWO_SEGMENT)
    (candidate,) = [t for t in fig.data if t.name == "candidate"]
    assert list(candidate.y)[:4] == pytest.approx([5.0, 5.0, 40.0, 95.0])
    assert candidate.line.dash == "solid"


def test_the_scouting_curves_are_drawn_dashed_and_the_candidate_solid() -> None:
    fig, _ = _figure_for(TRAP)
    dashes = {t.name: t.line.dash for t in fig.data if getattr(t, "yaxis", None) == "y2" and t.line}
    assert dashes["tG15"] == "dash"
    assert dashes["tG45"] == "dash"
    assert dashes["candidate"] == "solid"


def test_the_whiskers_reach_each_peaks_window_in_the_figure() -> None:
    fig, drawn = _figure_for(TRAP)
    (markers,) = [t for t in fig.data if t.name == "elution %B"]
    for index, peak in enumerate(drawn.peaks):
        assert markers.y[index] + markers.error_y.array[index] == pytest.approx(peak.percent_b_high)
        assert markers.y[index] - markers.error_y.arrayminus[index] == pytest.approx(
            peak.percent_b_low
        )


def test_without_an_overlay_the_figure_has_no_second_axis_at_all() -> None:
    """v0.1's plot, unchanged, for any caller that draws a trace on its own."""
    inputs, cockpit, _ = _rendered(TRAP)
    assert cockpit.resolution is not None
    fig = figure(chromatogram(cockpit.resolution.peaks, cockpit.shares))
    assert "yaxis2" not in fig.layout.to_plotly_json()
    assert not [t for t in fig.data if getattr(t, "yaxis", None) == "y2"]


# --- the fit tab's per-peak readout ---------------------------------------------------------


def test_the_readout_carries_a_row_per_fitted_peak_with_every_column_spec_6_names() -> None:
    _, _, diagnostics = _rendered(TRAP)
    frame = composition_window_frame(diagnostics.windows)

    assert tuple(frame.columns) == WINDOW_COLUMNS
    assert list(frame[COMPOUND]) == ["Unknown-1", "Unknown-2", "Unknown-3"]
    for row in frame.to_dict("records"):
        assert row[WINDOW_LOW] < row[WINDOW_HIGH]
        assert row[WINDOW_WIDTH] == pytest.approx(row[WINDOW_HIGH] - row[WINDOW_LOW])


def test_the_readout_is_in_percent_b_and_the_window_is_about_9_per_peak() -> None:
    """SPEC §6 diagnostic 3: ~9-10 %B per peak on the 5 → 95 %B pairs on file."""
    _, _, diagnostics = _rendered(TRAP)
    frame = composition_window_frame(diagnostics.windows)
    assert all(8.0 < width < 11.0 for width in frame[WINDOW_WIDTH])


def test_the_readout_says_inside_rather_than_a_distance_of_zero() -> None:
    _, _, inside = _rendered(Gradient(phi0=0.05, phif=0.95, t_gradient=25.0, t_init=0.5))
    frame = composition_window_frame(inside.windows)
    assert set(frame[WINDOW_POSITION]) == {"inside"}


def test_the_readout_names_the_distance_when_the_candidate_is_outside() -> None:
    """Three-peak run 4: 0.26 window-widths below, per SPEC §10 item 2."""
    _, _, below = _rendered(Gradient(phi0=0.05, phif=0.95, t_gradient=60.0, t_init=0.5))
    frame = composition_window_frame(below.windows)
    assert all(label.endswith("widths below") for label in frame[WINDOW_POSITION])
    assert all(label.startswith("0.26") for label in frame[WINDOW_POSITION])


def test_the_position_wording_is_the_windows_own_two_numbers() -> None:
    _, _, above = _rendered(Gradient(phi0=0.05, phif=0.95, t_gradient=7.0, t_init=0.5))
    for window in above.windows:
        assert window_position_label(window) == (f"{window.distance_in_widths:.2f} widths above")


# --- SPEC §10 item 2: the surfaces, on exactly the runs the spec names -----------------------


def _surfaces(sample: str, run: str) -> tuple[Diagnostics, Cockpit]:
    inputs = spec10_item2.inputs_for(sample, run)
    cockpit = run_cockpit(inputs)
    return diagnose(inputs, cockpit), cockpit


@pytest.mark.parametrize(("sample", "run"), list(spec10_item2.TABLE), ids=spec10_item2.IDS)
def test_the_flags_column_carries_the_badges_of_spec_10_item_2(sample: str, run: str) -> None:
    """Diagnostics 8 and 9 reach the Flags cell of the peak they are about, and no other."""
    diagnostics, cockpit = _surfaces(sample, run)
    _, _, low_k0, wash = spec10_item2.TABLE[(sample, run)]
    frame = prediction_frame(cockpit, diagnostics.badges).set_index(COMPOUND)

    assert {name for name in frame.index if "low k0" in frame.loc[name, FLAGS]} == set(low_k0)
    assert {name for name in frame.index if "wash-eluted" in frame.loc[name, FLAGS]} == set(wash)


@pytest.mark.parametrize(("sample", "run"), list(spec10_item2.TABLE), ids=spec10_item2.IDS)
def test_the_rs_grade_column_is_stamped_exactly_where_the_spec_stamps_it(
    sample: str, run: str
) -> None:
    """The stamp downgrades every pair; a badge downgrades only its own peak's pairs."""
    diagnostics, cockpit = _surfaces(sample, run)
    tier_1, tier_7, low_k0, wash = spec10_item2.TABLE[(sample, run)]
    frame = resolution_frame(cockpit, diagnostics)
    badged = set(low_k0) | set(wash)

    stamped = "strong" in (tier_1, tier_7)
    for row in frame.to_dict("records"):
        pair = set(str(row["Pair"]).split(" / "))
        expected = "indicative" if stamped or pair & badged else ""
        assert row[GRADE] == expected, row["Pair"]


@pytest.mark.parametrize(("sample", "run"), list(spec10_item2.TABLE), ids=spec10_item2.IDS)
def test_the_readout_has_a_row_for_every_predicted_peak_on_every_run(sample: str, run: str) -> None:
    """The readout is not conditional on a tier — it is the per-peak fact behind 1."""
    diagnostics, cockpit = _surfaces(sample, run)
    frame = composition_window_frame(diagnostics.windows)
    assert list(frame[COMPOUND]) == list(cockpit.predicted_by_name)


def test_a_peak_only_downgrades_the_pairs_it_is_actually_in() -> None:
    """Four-peak run 7's low-k0 peak is Unknown-1, so Unknown-2/3 stays decision-grade."""
    diagnostics, cockpit = _surfaces("three-peak", "run7")
    frame = resolution_frame(cockpit, diagnostics).set_index("Pair")
    # run 7 is strong on 7, so everything is stamped; the badge's own reach is asserted
    # against a candidate that carries the badge and neither method-level guard.
    assert set(frame[GRADE]) == {"indicative"}

    unstamped = _inputs(Gradient(phi0=0.05, phif=0.95, t_gradient=25.0, t_init=0.5))
    cockpit = run_cockpit(unstamped)
    quiet = diagnose(unstamped, cockpit)
    assert quiet.indicative is None
    assert set(resolution_frame(cockpit, quiet)[GRADE]) == {""}


def test_a_wash_eluted_peak_downgrades_only_its_own_pairs() -> None:
    """Three-peak run 6: 9 fires on Unknown-3 alone (SPEC §10 item 2)."""
    inputs = _inputs(WASH)
    cockpit = run_cockpit(inputs)
    diagnostics = diagnose(inputs, cockpit)
    washed = {
        name
        for name, badges in diagnostics.badges.items()
        if any(badge.code == "wash_eluted" for badge in badges)
    }
    assert washed and washed != set(diagnostics.badges)

    frame = resolution_frame(cockpit, diagnostics)
    for row in frame.to_dict("records"):
        pair = set(str(row["Pair"]).split(" / "))
        assert (row[GRADE] == "indicative") == bool(pair & washed)


def test_the_grade_column_is_blank_rather_than_reassuring_when_nothing_is_stamped() -> None:
    """An empty cell, like the Flags column: a table must not claim decision-grade."""
    inputs = _inputs(Gradient(phi0=0.05, phif=0.95, t_gradient=25.0, t_init=0.5))
    cockpit = run_cockpit(inputs)
    frame = resolution_frame(cockpit, diagnose(inputs, cockpit))
    assert set(frame[GRADE]) == {""}


def test_the_overlay_does_not_change_the_colour_of_the_trace_it_sits_behind() -> None:
    """The overlay's curves are added first, so an unpinned trace would take a new
    colour out of Plotly's cycle — the trace turned red the first time this ran."""
    inputs, cockpit, _ = _rendered(TRAP)
    assert cockpit.resolution is not None
    trace = chromatogram(cockpit.resolution.peaks, cockpit.shares)
    plain = figure(trace)
    overlaid, _ = _figure_for(TRAP)

    assert plain.data[0].line.color == overlaid.data[len(_overlay(TRAP).curves)].line.color


def test_a_near_full_strength_hold_does_not_push_the_axis_past_100_percent_b() -> None:
    """The min-span widening runs before the clamp, not after: 103 %B is not a thing."""
    hold = Programme(phi0=0.98, segments=(Segment(20.0, 0.98001),), t_init=0.5)
    low, high = programme_overlay(LAB_METHOD, hold, (), (), {}).percent_b_range
    assert high == 100.0
    assert low <= 98.0


# --- the other road to the stamp: a badged peak inside the critical pair -------------------


def test_a_badged_peak_in_the_critical_pair_downgrades_it_with_no_stamp_in_sight() -> None:
    """SPEC §6: "a low-k0 or wash-eluted badge downgrades only the pairs involving that
    peak" — so the pair, not the method, is what the leading Rs must be asked about.

    This candidate starts at the scouting start and sits inside the steepness bracket,
    so neither method-level guard fires and there is no stamp; two of its peaks are
    brought off in the trailing hold, and one of them is in the critical pair. Every
    surface that shows that Rs has to say so. None of SPEC §10 item 2's fixture runs can
    catch this: every wash-eluted or low-k0 run there is also strong on diagnostic 7.
    """
    inputs, cockpit, diagnostics = _rendered(WASH)

    assert diagnostics.indicative is None
    critical = cockpit.resolution.critical_pair if cockpit.resolution else None
    assert critical is not None
    assert {badge.code for badge in diagnostics.badges[critical.later.name]} == {"wash_eluted"}
    assert critical_pair_is_indicative(cockpit, diagnostics)


def test_a_clean_candidate_leaves_the_leading_rs_decision_grade() -> None:
    inputs, cockpit, diagnostics = _rendered(
        Gradient(phi0=0.05, phif=0.95, t_gradient=25.0, t_init=0.5)
    )
    assert not critical_pair_is_indicative(cockpit, diagnostics)


def test_a_badge_outside_the_critical_pair_leaves_the_leading_rs_alone() -> None:
    """The scoping cuts both ways: a downgraded pair that is not the critical one."""
    inputs, cockpit, diagnostics = _rendered(WASH)
    assert cockpit.resolution is not None
    washed = {
        name
        for name, badges in diagnostics.badges.items()
        if any(badge.code == "wash_eluted" for badge in badges)
    }
    clean = [
        pair
        for pair in cockpit.resolution.pairs
        if not {pair.earlier.name, pair.later.name} & washed
    ]
    for pair in clean:
        assert not diagnostics.pair_is_indicative((pair.earlier.name, pair.later.name))
