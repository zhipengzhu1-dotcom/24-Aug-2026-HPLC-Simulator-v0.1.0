"""SPEC §5's entry checks and SPEC §6's six diagnostics, without a browser (ticket #20).

Streamlit is nowhere in this file, which is the point: SPEC §6 fixes a *threshold* for
each diagnostic, and a threshold that can only be seen by looking at a rendered page is
a threshold nobody re-checks. `app.diagnostics` computes them and `streamlit_app.py`
places them, so every number below is an assertion.

The lab dataset carries the live case SPEC §5 names — peaks 2–3's area inconsistency —
and it is asserted here against `validation/run1.csv` and `run2.csv` rather than against
a hand-made fixture, so a change to the engine or to the data has to survive it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from app.diagnostics import (
    AREA_SHARE_THRESHOLD,
    STRONG_WINDOW_WIDTHS,
    Diagnostic,
    Diagnostics,
    diagnose,
    scouting_beta,
)
from app.pipeline import CockpitInputs, run_cockpit
from hplcsim.fit import BETA_STRONG, BETA_WARNING
from hplcsim.model import (
    Gradient,
    Method,
    Peak,
    PeakRow,
    RetentionParams,
    Run,
    ln_k0_from_log10_k0,
    s_e_from_s_base10,
)
from hplcsim.retention import predict_retention
from lab_data import (
    LAB_MEASURED_AREA,
    LAB_MEASURED_PEAKS,
    LAB_METHOD,
    LAB_PEAKS,
    LAB_RUN1,
    LAB_RUN2,
)


def _row(peak: Peak) -> PeakRow:
    return PeakRow(
        name=peak.name,
        t_r_run1=peak.t_r_run1,
        t_r_run2=peak.t_r_run2,
        area_run1=peak.area_run1,
        area_run2=peak.area_run2,
        w_half_run1=peak.w_half_run1,
        w_half_run2=peak.w_half_run2,
    )


def _lab_rows() -> tuple[PeakRow, ...]:
    """The three lab compounds with their measured areas from both scouting runs."""
    return tuple(
        replace(
            _row(peak),
            area_run1=LAB_MEASURED_AREA["tG15"][peak.name],
            area_run2=LAB_MEASURED_AREA["tG45"][peak.name],
        )
        for peak in LAB_MEASURED_PEAKS
    )


def _lab_inputs(**overrides: object) -> CockpitInputs:
    """The lab dataset as the Cockpit holds it, candidate inside the 15–45 bracket."""
    base = {
        "method": LAB_METHOD,
        "run1": LAB_RUN1,
        "run2": LAB_RUN2,
        "candidate": Gradient(phi0=0.05, phif=0.95, t_gradient=25.0, t_init=0.5),
        "rows": tuple(_row(peak) for peak in LAB_MEASURED_PEAKS),
    }
    return CockpitInputs(**(base | overrides))  # type: ignore[arg-type]


def _codes(diagnostics: tuple[object, ...]) -> list[str]:
    return [d.code for d in diagnostics]  # type: ignore[attr-defined]


def _at(inputs: CockpitInputs) -> Diagnostics:
    return diagnose(inputs)


# --- diagnostic 1: tG extrapolation (SPEC §6) -------------------------------------------


def test_a_candidate_inside_the_scouting_bracket_says_nothing() -> None:
    assert _at(_lab_inputs()).candidate == ()


def test_a_candidate_just_outside_the_bracket_is_an_info_flag_not_a_warning() -> None:
    """SPEC §6: "the near-bracket flag stays gentle" — the tG = 60 evidence, 0.34%."""
    inputs = _lab_inputs(candidate=Gradient(0.05, 0.95, t_gradient=60.0, t_init=0.5))
    (flag,) = _at(inputs).candidate
    assert flag.code == "steepness_extrapolation"
    assert flag.severity == "info"


def test_a_candidate_far_outside_the_bracket_escalates_to_a_strong_warning() -> None:
    """Beyond ~2× outside (SPEC §6). The bracket is 15–45, so 91 min is 2.02× past it."""
    inputs = _lab_inputs(candidate=Gradient(0.05, 0.95, t_gradient=91.0, t_init=0.5))
    (flag,) = _at(inputs).candidate
    assert flag.severity == "strong"


def test_the_escalation_is_symmetric_below_the_bracket() -> None:
    """A tG a factor of two *under* the shorter run extrapolates just as far."""
    gentle = _lab_inputs(candidate=Gradient(0.05, 0.95, t_gradient=10.0, t_init=0.5))
    steep = _lab_inputs(candidate=Gradient(0.05, 0.95, t_gradient=7.0, t_init=0.5))
    assert _at(gentle).candidate[0].severity == "info"
    assert _at(steep).candidate[0].severity == "strong"


def test_the_bracket_edges_themselves_are_inside_it() -> None:
    for t_gradient in (LAB_RUN1.gradient.t_gradient, LAB_RUN2.gradient.t_gradient):
        inputs = _lab_inputs(candidate=Gradient(0.05, 0.95, t_gradient, 0.5))
        assert _at(inputs).candidate == ()


def test_the_extrapolation_flag_says_how_far_outside_the_candidate_sits() -> None:
    """1.33× is the lab dataset's own held-out case — the number that earned "gentle"."""
    inputs = _lab_inputs(candidate=Gradient(0.05, 0.95, t_gradient=60.0, t_init=0.5))
    (flag,) = _at(inputs).candidate
    assert "1.33" in flag.message
    assert "15" in flag.message and "45" in flag.message


def test_the_strong_tier_starts_where_spec_6_puts_it() -> None:
    """Pinned so "~0.6 window-widths" cannot drift into a different number unremarked."""
    assert STRONG_WINDOW_WIDTHS == 0.6


# --- the entry-side spacing ratio (SPEC §4, ticket #20's acceptance criteria) -----------


def test_a_three_fold_scouting_pair_draws_no_spacing_warning() -> None:
    assert _codes(_at(_lab_inputs()).fit) == []


def test_a_spacing_ratio_under_2_5_warns() -> None:
    run2 = replace(LAB_RUN2, gradient=replace(LAB_RUN2.gradient, t_gradient=30.0))
    (notice,) = _at(_lab_inputs(run2=run2)).fit
    assert notice.code == "beta_spacing"
    assert notice.severity == "warning"


def test_a_spacing_ratio_under_1_2_escalates_to_strong() -> None:
    run2 = replace(LAB_RUN2, gradient=replace(LAB_RUN2.gradient, t_gradient=16.5))
    (notice,) = _at(_lab_inputs(run2=run2)).fit
    assert notice.severity == "strong"


def test_the_spacing_warning_is_never_a_block() -> None:
    """CLAUDE.md's warnings-over-blocks: a β of 1.1 is noisy, not impossible.

    Retention times come from the engine's own forward prediction at the two runs, so
    the pair really is a β = 1.1 experiment rather than the lab's β = 3 times relabelled
    — which no LSS fit accepts.
    """
    run2 = replace(LAB_RUN2, gradient=replace(LAB_RUN2.gradient, t_gradient=16.5))
    inputs = _lab_inputs(run2=run2, rows=_rows_predicted_at(LAB_RUN1, run2))
    cockpit = run_cockpit(inputs)
    assert cockpit.blocked is None
    assert [outcome.error for outcome in cockpit.outcomes] == [None, None, None]
    assert diagnose(inputs, cockpit).fit[0].severity == "strong"


def _rows_predicted_at(
    run1: Run,
    run2: Run,
    peaks: Sequence[tuple[str, RetentionParams]] | None = None,
) -> tuple[PeakRow, ...]:
    """Retention times as the engine itself predicts them for ``peaks`` at these runs.

    Not tautological for anything in this file: the diagnostics under test read an
    *order*, a *share* or an elapsed time, never a retention time they recompute. What
    the engine buys is a fixture that is a physically possible pair of runs, which
    hand-typed times stop being as soon as β moves away from 3.
    """
    named = peaks if peaks is not None else [(f"P{i}", p) for i, p in enumerate(LAB_PEAKS, 1)]
    return tuple(
        PeakRow(
            name=name,
            t_r_run1=predict_retention(params, LAB_METHOD, run1.gradient).t_r,
            t_r_run2=predict_retention(params, LAB_METHOD, run2.gradient).t_r,
        )
        for name, params in named
    )


def _params(log10_k0: float, s: float) -> RetentionParams:
    return RetentionParams(
        ln_k0=ln_k0_from_log10_k0(log10_k0), s_e=s_e_from_s_base10(s), phi_ref=0.05
    )


# A pair that keeps its order across both scouting runs and swaps outside them: at
# tG = 15 and 45 the steeper-S compound elutes first by 0.4 and 0.2 min, and by tG = 60
# it elutes second. Two peaks that do not cross between the scouting runs can only cross
# outside the bracket — tR is continuous in tG — so diagnostic 4's own case necessarily
# sits where diagnostic 1 is also speaking, which is why they are separate fields.
_SHALLOW_S = ("Shallow S", _params(3.0, 4.0))
_STEEP_S = ("Steep S", _params(3.4, 5.0))

# log10 k0 = 0.5 leaves the column 0.18 min after t0 + τ, inside t0 = 0.525 min of it —
# research doc §4.3's "t'R < t0" early-eluter test, still in the gradient regime.
_EARLY = ("Early", _params(0.5, 3.0))

# Retained enough to clear the badge under a 0.5 min hold and not under a 6 min one.
_MID = ("Mid", _params(1.0, 3.0))


def test_the_spacing_tiers_are_the_engines_own_and_not_a_second_copy() -> None:
    assert (BETA_WARNING, BETA_STRONG) == (2.5, 1.2)


def test_the_spacing_ratio_does_not_care_which_run_is_the_steeper_one() -> None:
    swapped = _lab_inputs(run1=LAB_RUN2, run2=LAB_RUN1)
    assert _codes(_at(swapped).fit) == []


# --- diagnostic 6: the estimated-t0 stamp (SPEC §6) --------------------------------------


def test_a_measured_t0_stamps_nothing() -> None:
    assert _at(_lab_inputs()).stamps == ()


def test_a_geometry_t0_stamps_every_output_lower_confidence() -> None:
    method = replace(LAB_METHOD, t0_is_measured=False)
    (stamp,) = _at(_lab_inputs(method=method)).stamps
    assert stamp.code == "estimated_t0"
    assert stamp.severity == "warning"


def test_the_stamp_is_worded_to_the_two_regimes_not_a_bare_lower_confidence() -> None:
    """Research doc §6.4: the predictions barely move; the fitted S, k0 and N do, and
    must not be transferred. The two numbers differ by a factor of forty."""
    (stamp,) = _at(_lab_inputs(method=replace(LAB_METHOD, t0_is_measured=False))).stamps
    assert "0.005% per 1%" in stamp.message
    assert "a quarter of the t0 error" in stamp.message
    assert "never transfer them to another flow rate or column" in stamp.message
    assert "lower-confidence" not in stamp.message


# --- the entry checks of SPEC §5 ----------------------------------------------------------


def test_the_lab_datasets_area_inconsistency_triggers_the_warning() -> None:  # AC 3
    """SPEC §5's live case. Unknown-2's share moves 40.9% between the scouting runs."""
    entry = _at(_lab_inputs(rows=_lab_rows())).entry
    area = [d for d in entry if d.code == "area_share"]
    assert [d.peaks for d in area] == [("Unknown-2",)]
    assert area[0].severity == "warning"


def test_the_area_check_reports_the_size_of_the_disagreement_it_found() -> None:
    (area,) = [d for d in _at(_lab_inputs(rows=_lab_rows())).entry if d.code == "area_share"]
    assert "41%" in area.message


def test_peak_3_sits_just_under_the_default_threshold() -> None:
    """Pinned because SPEC §5 reads as though both peaks 2 and 3 clear ~30%.

    Measured on `validation/run1.csv` / `run2.csv`, Unknown-3's area share moves 26.7%
    — real, and under the shipped default. Dropping the threshold to 0.26 brings it in
    and still leaves Unknown-1's 22.8% out. The driver's call on this branch was to ship
    SPEC's stated ~30% and pin the number here rather than tune the threshold to the
    sentence; the SPEC §5 parenthetical is the thing that needs softening.
    """
    rows = _lab_rows()
    default = _at(_lab_inputs(rows=rows)).entry
    assert [d.peaks for d in default if d.code == "area_share"] == [("Unknown-2",)]

    lowered = diagnose(_lab_inputs(rows=rows), area_share_threshold=0.26)
    assert [d.peaks for d in lowered.entry if d.code == "area_share"] == [
        ("Unknown-2",),
        ("Unknown-3",),
    ]


def test_the_default_area_threshold_is_the_one_spec_5_names() -> None:
    assert AREA_SHARE_THRESHOLD == 0.30


def test_areas_that_only_scale_between_runs_are_not_a_disagreement() -> None:
    """A run that simply integrated hotter moves every raw area and no share."""
    rows = tuple(
        replace(row, area_run2=(row.area_run1 or 0.0) * 7.5)
        for row in (replace(_row(peak), area_run1=area) for peak, area in _paired_areas())
    )
    assert [d for d in _at(_lab_inputs(rows=rows)).entry if d.code == "area_share"] == []


def _paired_areas() -> list[tuple[Peak, float]]:
    return [(peak, LAB_MEASURED_AREA["tG15"][peak.name]) for peak in LAB_MEASURED_PEAKS]


def test_rows_without_areas_are_not_checked_rather_than_failed() -> None:
    assert [d for d in _at(_lab_inputs()).entry if d.code == "area_share"] == []


# --- diagnostic 2: the early-eluter badge (SPEC §6) ---------------------------------------


def test_a_peak_leaving_within_t0_of_the_gradient_arriving_gets_the_early_badge() -> None:
    """SPEC §6 diagnostic 2: "elutes near t0 + dwell + hold" — research doc §4.3's t'R < t0."""
    inputs = _lab_inputs(rows=_rows_predicted_at(LAB_RUN1, LAB_RUN2, [_EARLY, _SHALLOW_S]))
    badges = _at(inputs).badges
    # log10 k0 = 0.5 is also below diagnostic 8's floor — the same physics from the
    # other side (SPEC §6 item 8), so both badges are right here.
    assert _codes(badges["Early"]) == ["early_eluter", "low_k0"]
    assert _codes(badges["Shallow S"]) == []


def test_a_peak_that_never_meets_the_gradient_at_all_is_early_too() -> None:
    """The §4.1 case: the band is off the column before the ramp reaches it."""
    inputs = _lab_inputs(
        rows=_rows_predicted_at(LAB_RUN1, LAB_RUN2, [_EARLY, _SHALLOW_S]),
        candidate=Gradient(0.05, 0.95, t_gradient=180.0, t_init=8.0),
    )
    assert "early_eluter" in _codes(_at(inputs).badges["Early"])


def test_the_early_badge_is_about_the_candidate_not_the_scouting_runs() -> None:
    """A hold long enough to swallow a peak makes it early where it was not before.

    "Mid" (log10 k0 = 1.0) leaves the column 3.05 min past t0 + τ under a 0.5 min hold
    and never meets the gradient at all under a 6 min one — same peak, same fit, two
    different candidates.
    """
    rows = _rows_predicted_at(LAB_RUN1, LAB_RUN2, [_MID, _SHALLOW_S])
    quick = _lab_inputs(rows=rows, candidate=Gradient(0.05, 0.95, 25.0, t_init=0.5))
    held = _lab_inputs(rows=rows, candidate=Gradient(0.05, 0.95, 25.0, t_init=6.0))
    assert "early_eluter" not in _codes(_at(quick).badges["Mid"])
    assert "early_eluter" in _codes(_at(held).badges["Mid"])


def test_the_lab_compounds_are_not_early_eluters() -> None:
    assert all(_codes(badges) == [] for badges in _at(_lab_inputs()).badges.values())


def test_every_predicted_peak_has_a_badge_entry_even_when_it_is_clean() -> None:
    """The UI reads badges[name] per row, so a clean peak is an empty tuple, not a miss."""
    badges = _at(_lab_inputs()).badges
    assert sorted(badges) == ["Unknown-1", "Unknown-2", "Unknown-3"]
    assert all(value == () for value in badges.values())


# --- diagnostic 4: prediction crossing flags (SPEC §6) ------------------------------------


def test_a_pair_that_swaps_at_the_candidate_badges_both_peaks() -> None:
    rows = _rows_predicted_at(LAB_RUN1, LAB_RUN2, [_SHALLOW_S, _STEEP_S])
    inputs = _lab_inputs(rows=rows, candidate=Gradient(0.05, 0.95, 60.0, 0.5))
    badges = _at(inputs).badges
    assert _codes(badges["Shallow S"]) == ["prediction_crossing"]
    assert _codes(badges["Steep S"]) == ["prediction_crossing"]


def test_the_crossing_badge_names_the_peak_that_was_crossed() -> None:
    rows = _rows_predicted_at(LAB_RUN1, LAB_RUN2, [_SHALLOW_S, _STEEP_S])
    inputs = _lab_inputs(rows=rows, candidate=Gradient(0.05, 0.95, 60.0, 0.5))
    (badge,) = _at(inputs).badges["Shallow S"]
    assert badge.peaks == ("Shallow S", "Steep S")
    assert "Steep S" in badge.message


def test_the_same_pair_inside_the_bracket_keeps_its_order_and_says_nothing() -> None:
    rows = _rows_predicted_at(LAB_RUN1, LAB_RUN2, [_SHALLOW_S, _STEEP_S])
    inputs = _lab_inputs(rows=rows, candidate=Gradient(0.05, 0.95, 25.0, 0.5))
    assert all(_codes(badges) == [] for badges in _at(inputs).badges.values())


# --- SPEC §5: elution-order crossing, confirmed at entry -----------------------------------

# Two rows that swap between the scouting runs as typed. Hand-written rather than
# predicted, because the point of the check is that the *entered* pairing may be wrong —
# a crossing the chromatographer has to confirm, not one the engine derived.
_CROSSING_ROWS = (
    PeakRow(name="A", t_r_run1=10.0, t_r_run2=25.0),
    PeakRow(name="B", t_r_run1=11.0, t_r_run2=24.0),
)


def test_scouting_runs_that_disagree_on_order_ask_for_confirmation() -> None:
    entry = _at(_lab_inputs(rows=_CROSSING_ROWS)).entry
    (crossing,) = [d for d in entry if d.code == "entry_crossing"]
    assert crossing.severity == "warning"
    assert crossing.peaks == ("A", "B")


def test_rows_in_the_same_order_in_both_runs_are_not_asked_about() -> None:
    entry = _at(_lab_inputs(rows=_lab_rows())).entry
    assert [d for d in entry if d.code == "entry_crossing"] == []


def test_an_untracked_row_cannot_cross_anything() -> None:
    """Half a pairing is not an elution order — SPEC §5 keeps such rows out of the checks."""
    rows = (*_CROSSING_ROWS[:1], replace(_CROSSING_ROWS[1], t_r_run2=None))
    assert [d for d in _at(_lab_inputs(rows=rows)).entry if d.code == "entry_crossing"] == []


def test_co_eluting_rows_relax_the_area_check_rather_than_failing_it() -> None:
    """SPEC §5: "within-run co-elution entry legal (area check relaxes)".

    Two bands under one envelope are integrated as one, so neither row's share in that
    run is a measurement of that compound and there is nothing to compare it against.
    """
    rows = _lab_rows()
    flagged = [d.peaks for d in _at(_lab_inputs(rows=rows)).entry if d.code == "area_share"]
    assert flagged == [("Unknown-2",)]

    co_eluting = (
        rows[0],
        replace(rows[1], t_r_run1=rows[2].t_r_run1),
        rows[2],
    )
    relaxed = _at(_lab_inputs(rows=co_eluting)).entry
    assert [d for d in relaxed if d.code == "area_share"] == []


def test_co_elution_relaxes_only_the_rows_that_co_elute() -> None:
    rows = _lab_rows()
    co_eluting = (replace(rows[0], t_r_run1=rows[2].t_r_run1), rows[1], rows[2])
    flagged = [d.peaks for d in _at(_lab_inputs(rows=co_eluting)).entry if d.code == "area_share"]
    assert flagged == [("Unknown-2",)]


# --- diagnostic 5: the width/Rs caveat banner (SPEC §6, wording from ticket #19) -----------


def test_peaks_with_a_measured_width_draw_no_banner() -> None:
    """The lab rows carry W½ in both runs, so every N is fitted and nothing is caveated."""
    assert _at(_lab_inputs()).banners == ()


def test_peaks_without_a_width_draw_the_column_estimate_banner() -> None:
    rows = tuple(
        replace(_row(peak), w_half_run1=None, w_half_run2=None) for peak in LAB_MEASURED_PEAKS
    )
    (banner,) = _at(_lab_inputs(rows=rows)).banners
    assert banner.code == "defaulted_width"
    assert banner.peaks == ("Unknown-1", "Unknown-2", "Unknown-3")


def test_the_banner_carries_the_numbers_ticket_19_worded_it_with() -> None:
    """Moved from `streamlit_app.py` verbatim — SPEC §6 assigns the wording to #19."""
    rows = tuple(
        replace(_row(peak), w_half_run1=None, w_half_run2=None) for peak in LAB_MEASURED_PEAKS
    )
    (banner,) = _at(_lab_inputs(rows=rows)).banners
    assert "0.69–0.92×" in banner.message
    assert "18–39%" in banner.message
    assert "0.99–1.16×" in banner.message
    assert "critical pair is identified correctly" in banner.message


def test_the_banner_names_only_the_peaks_that_lost_their_width() -> None:
    rows = (
        _row(LAB_MEASURED_PEAKS[0]),
        replace(_row(LAB_MEASURED_PEAKS[1]), w_half_run1=None, w_half_run2=None),
        _row(LAB_MEASURED_PEAKS[2]),
    )
    (banner,) = _at(_lab_inputs(rows=rows)).banners
    assert banner.peaks == ("Unknown-2",)


# --- the seams between the layers -----------------------------------------------------------


def test_the_entry_side_beta_is_the_number_the_fit_reports() -> None:
    """One β, two readers. The entry check speaks before a fit exists; they must agree."""
    cockpit = run_cockpit(_lab_inputs())
    assert {fit.beta for _, fit in cockpit.fitted} == {scouting_beta(LAB_RUN1, LAB_RUN2)}


def test_a_blocked_cockpit_says_nothing_the_two_runs_would_have_implied() -> None:
    """Two runs at one tG is SPEC §4's single impossibility, and `Cockpit.blocked` says so.

    Nothing is fitted and nothing is predicted, so a β = 1.0 spacing warning and an
    extrapolation flag against a zero-width bracket would be noise stacked on a block.
    """
    inputs = _lab_inputs(run2=replace(LAB_RUN1, name="tG15 again"))
    diagnostics = _at(inputs)

    assert run_cockpit(inputs).blocked is not None
    assert (diagnostics.candidate, diagnostics.fit, diagnostics.banners) == ((), (), ())
    assert diagnostics.badges == {}


def test_a_blocked_cockpit_still_checks_the_rows_the_user_typed() -> None:
    """The §5 entry checks read only typed rows, and the peak table is still on screen.

    Silencing them would mean a chromatographer who has also mis-paired two peaks learns
    about it only after fixing an unrelated gradient time.
    """
    inputs = _lab_inputs(run2=replace(LAB_RUN1, name="tG15 again"), rows=_lab_rows())
    assert [d.code for d in _at(inputs).entry] == ["area_share"]


def test_nothing_entered_at_all_leaves_every_result_surface_quiet() -> None:
    """Only the method's own checks speak on an empty screen — t0 is a typed input.

    The lab fixture declares no packing architecture and no marker, so the sidebar
    carries SPEC §4's readout of what its measured t0 implies and the missing-marker
    warning; everything that is about a *result* stays silent.
    """
    diagnostics = _at(_lab_inputs(rows=()))
    assert diagnostics.all == diagnostics.method
    assert [d.code for d in diagnostics.method] == ["dead_time_check", "t0_marker"]


# --- SPEC §4's checks on a measured t0 (ticket #24) -----------------------------------------

# The driver's column as method.csv records it: t0 0.525, architecture declared,
# solvent-front marker — the fixture itself since the 2026-09-03 re-baseline.
_LAB_COLUMN = LAB_METHOD


def _dead_time(method: Method) -> list[Diagnostic]:
    return [d for d in _at(_lab_inputs(method=method)).method if d.code == "dead_time_check"]


def _marker(method: Method) -> list[Diagnostic]:
    return [d for d in _at(_lab_inputs(method=method)).method if d.code == "t0_marker"]


def test_the_reverse_check_is_a_readout_on_the_drivers_own_column() -> None:
    """#34, decision 4: implied ε_total and V_ec stated as fact, and no warning on
    correct data — 0.606 is 16.6% over the core–shell constant, and that tier is gone."""
    (readout,) = _dead_time(_LAB_COLUMN)
    assert readout.severity == "info"
    assert "ε_total = 0.606" in readout.message
    assert "30 µL of extra-column volume" in readout.message
    assert "typical 26–78 µL" in readout.message
    assert "0.450 min" in readout.message and "band 0.390–0.520 min" in readout.message


def test_a_mis_declared_architecture_is_caught_by_the_negative_plumbing_volume() -> None:
    # The only thing that catches a wrong packing type once the ~15% tier is dropped.
    (warning,) = _dead_time(replace(_LAB_COLUMN, particle_is_solid_core=False))
    assert warning.severity == "warning"
    assert "below the geometry estimate" in warning.message
    assert "-5 µL" in warning.message
    assert "mis-declared" in warning.message


def test_an_undeclared_architecture_keeps_the_porosity_readout_and_asks_for_the_rest() -> None:
    (readout,) = _dead_time(replace(_LAB_COLUMN, particle_is_solid_core=None))
    assert readout.severity == "info"
    assert "ε_total = 0.606" in readout.message
    assert "Declare the packing architecture" in readout.message
    assert "extra-column volume" in readout.message


def test_a_gap_too_large_for_plumbing_warns_of_a_retained_marker() -> None:
    # 0.675 min is ε_total = 0.78 — still a porosity a column can have — and 90 µL.
    (warning,) = _dead_time(replace(_LAB_COLUMN, t0=0.675))
    assert warning.severity == "warning"
    assert "90 µL of extra-column volume" in warning.message
    assert "retained" in warning.message


def test_a_porosity_no_column_has_is_a_warning_and_more_than_a_tube_holds_is_strong() -> None:
    (implausible,) = _dead_time(replace(_LAB_COLUMN, t0=0.25))
    assert implausible.severity == "warning"
    assert "outside the 0.35–0.80" in implausible.message
    (impossible,) = _dead_time(replace(_LAB_COLUMN, t0=0.95))
    assert impossible.severity == "strong"
    assert "more mobile phase than an empty tube" in impossible.message


def test_without_a_column_id_the_reverse_check_says_nothing_rather_than_failing() -> None:
    assert _dead_time(replace(_LAB_COLUMN, column_id_mm=None)) == []


def test_an_estimated_t0_gets_the_stamp_and_neither_measured_t0_check() -> None:
    estimated = replace(_LAB_COLUMN, t0_is_measured=False, t0_marker=None)
    diagnostics = _at(_lab_inputs(method=estimated))
    assert diagnostics.method == ()
    assert [d.code for d in diagnostics.stamps] == ["estimated_t0"]


def test_the_drivers_solvent_front_marker_is_warned_as_discouraged() -> None:
    (warning,) = _marker(_LAB_COLUMN)
    assert warning.severity == "warning"
    assert "solvent disturbance" in warning.message
    assert "solvent front, first disturbance" in warning.message


def test_a_salt_marker_is_warned_as_size_excluded() -> None:
    (warning,) = _marker(replace(_LAB_COLUMN, t0_marker="sodium nitrate"))
    assert "inorganic salt" in warning.message and "interstitial" in warning.message


def test_a_missing_marker_is_a_provenance_warning() -> None:
    (warning,) = _marker(replace(_LAB_COLUMN, t0_marker=None))
    assert "No t0 marker recorded" in warning.message


def test_a_compound_marker_is_quiet() -> None:
    assert _marker(replace(_LAB_COLUMN, t0_marker="uracil, apex")) == []


def test_a_peak_that_leaves_at_k_below_one_is_early_however_late_it_looks() -> None:
    """Research doc §4.3's other early-eluter test, beside t'R < t0: "k_e ... below ~1".

    The fixture isolates that clause rather than riding on the other two. Under a 2.5 min
    gradient "Mid" leaves at k = 0.95 but 0.95 min after the ramp arrives — comfortably
    past t0 = 0.525 min and squarely in the gradient regime, so neither of the other two
    tests fires. The engine already sets `RetentionResult.low_confidence` on it and
    nothing in the app read that, which is how a barely-retained peak stayed silent.
    """
    rows = _rows_predicted_at(LAB_RUN1, LAB_RUN2, [_MID, _SHALLOW_S])
    inputs = _lab_inputs(rows=rows, candidate=Gradient(0.05, 0.95, 2.5, 0.5))
    predicted = run_cockpit(inputs).predicted_by_name["Mid"].retention

    assert predicted.regime == "gradient"
    assert predicted.k_e < 1.0
    assert predicted.t_r - LAB_METHOD.t0 - (LAB_METHOD.t_dwell + 0.5) > LAB_METHOD.t0

    (badge,) = [b for b in _at(inputs).badges["Mid"] if b.code == "early_eluter"]
    assert "k = 0.95" in badge.message
