"""SPEC §10 layer 3: the engine against measured reality.

Layers 1 and 2 (`test_retention.py`, `test_fit.py`) ask whether the math is
self-consistent and whether it reproduces a published reference implementation.
This layer asks the only question a chromatographer cares about: fit two
scouting runs, predict a *third* condition, and compare against what the
instrument actually did.

Every target gradient here is held out of the fit that predicts it.
"""

import math
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from statistics import fmean, median, stdev

import pytest

from den_uijl_data import SET_X, SET_Y, ScanningGradientSet
from hplcsim.fit import FitResult, fit_peak, fit_peaks
from hplcsim.model import Gradient, Method, Peak, Run
from hplcsim.resolution import ResolutionTable, resolution_table
from hplcsim.retention import gradient_steepness, predict_retention
from hplcsim.width import band_compression_factor, peak_width, plate_count_from_width
from lab_data import (
    LAB_MEASURED_AREA,
    LAB_MEASURED_PEAKS,
    LAB_MEASURED_TG25,
    LAB_MEASURED_TG60,
    LAB_MEASURED_W_HALF,
    LAB_METHOD,
    LAB_RUN1,
    LAB_RUN2,
    LAB_RUN3,
    LAB_RUN4,
    LAB_W_HALF_ULP,
)
from validation2_data import (
    VALIDATION2_HELD_OUT,
    VALIDATION2_MEASURED_AREA,
    VALIDATION2_MEASURED_TR,
    VALIDATION2_MEASURED_W_HALF,
    VALIDATION2_METHOD,
    VALIDATION2_PEAKS,
    VALIDATION2_RUN1,
    VALIDATION2_RUN2,
    VALIDATION2_RUNS_BY_NAME,
    VALIDATION2_SOURCE_FILES,
    VALIDATION2_TR_GRANULARITY,
    VALIDATION2_W_HALF_ULP,
)

_VALIDATION2_DIR = Path(__file__).resolve().parents[1] / "validation/Validation_2"


def _predict_held_out(
    peaks: list[Peak], method: Method, run1: Run, run2: Run, target: Run
) -> list[float]:
    """Fit the scouting pair, then predict every peak at a condition it never saw."""
    return [
        predict_retention(fit.params, method, target.gradient).t_r
        for fit in fit_peaks(peaks, method, run1, run2)
    ]


def _signed_percent_errors(predicted: list[float], measured: list[float]) -> list[float]:
    return [100.0 * (p - m) / m for p, m in zip(predicted, measured, strict=True)]


def _elution_order(retention_times: list[float]) -> list[int]:
    return sorted(range(len(retention_times)), key=retention_times.__getitem__)


_LN10 = math.log(10.0)
_W_HALF_PER_SIGMA = math.sqrt(8.0 * math.log(2.0))

# --- the lab dataset in validation/ (SPEC §10's end-to-end trust bar) ---

_LAB_AVERAGE_BAR = 2.0
_LAB_WORST_CASE_BAR = 5.0


def _lab_predictions(
    target: Run, measured_by_name: dict[str, float]
) -> tuple[list[float], list[float]]:
    """Predicted and measured tR for the three lab peaks at a held-out gradient time."""
    predicted = _predict_held_out(LAB_MEASURED_PEAKS, LAB_METHOD, LAB_RUN1, LAB_RUN2, target)
    measured = [measured_by_name[peak.name] for peak in LAB_MEASURED_PEAKS]
    return predicted, measured


@pytest.mark.parametrize(
    ("target", "measured", "tripwire", "is_extrapolation"),
    [
        # SPEC §10's trust bar is avg ≤ 2%, worst ≤ 5%, order correct. `tripwire` is the
        # tighter regression guard: pre-build validation put these at 0.35% and 0.26%,
        # so a drift to 1.9% would clear the contract without anyone noticing.
        (LAB_RUN3, LAB_MEASURED_TG25, 0.5, False),
        (LAB_RUN4, LAB_MEASURED_TG60, 0.4, True),
    ],
    ids=["tG25-confirmation", "tG60-extrapolation"],
)
def test_lab_held_out_runs_are_predicted_within_the_trust_bar(
    target: Run, measured: dict[str, float], tripwire: float, is_extrapolation: bool
) -> None:
    """Fit run1+run2 (tG = 15/45), predict run3 (interpolation) and run4 (extrapolation)."""
    # The issue asks for tG = 60 "asserted as the extrapolation case" — so assert it,
    # rather than leaving the word in a test id. tG = 25 sits inside the 15/45 scouting
    # bracket and tG = 60 outside it, which is the whole reason the two are separate
    # criteria: one interpolates between measured slopes, the other reaches past them.
    scouting = (LAB_RUN1.gradient.t_gradient, LAB_RUN2.gradient.t_gradient)
    within_bracket = min(scouting) <= target.gradient.t_gradient <= max(scouting)
    assert within_bracket is not is_extrapolation

    predicted, measured_times = _lab_predictions(target, measured)
    magnitudes = [abs(error) for error in _signed_percent_errors(predicted, measured_times)]

    assert fmean(magnitudes) <= _LAB_AVERAGE_BAR
    assert max(magnitudes) <= _LAB_WORST_CASE_BAR
    # "Order correct": a method is only usable if the peaks come off in the predicted
    # sequence, however close the individual times are.
    assert _elution_order(predicted) == _elution_order(measured_times)

    assert fmean(magnitudes) <= tripwire


def test_lab_residual_bias_flips_sign_between_the_two_held_out_conditions() -> None:
    """SPEC §10's residual note: +0.35% at tG = 25, −0.26% at tG = 60.

    Worth pinning because it constrains the *shape* of the residual, not just its size.
    A dropped τ term, a mishandled hold or a t0 slip biases every condition the same
    way — the den Uijl Set X table in the research doc §1.4 is exactly that signature.
    Only genuine curvature in log k vs φ, which the two-parameter LSS model cannot
    absorb, puts the interpolated and extrapolated conditions on opposite sides.
    """
    inside = fmean(_signed_percent_errors(*_lab_predictions(LAB_RUN3, LAB_MEASURED_TG25)))
    outside = fmean(_signed_percent_errors(*_lab_predictions(LAB_RUN4, LAB_MEASURED_TG60)))

    assert inside > 0.0
    assert outside < 0.0
    # Chromatographically negligible on both sides — this is curvature, not a defect.
    assert abs(inside) < 0.5
    assert abs(outside) < 0.5


# --- den Uijl et al. 2021 scanning-gradient sets (research doc §1, §2) ---

# SPEC §10 layer 3's three tolerances for the literature sets. The lab dataset upstream
# has its own, looser pair (_LAB_AVERAGE_BAR / _LAB_WORST_CASE_BAR) — do not cross them.
_DEN_UIJL_MEDIAN_BAR = 0.5
_DEN_UIJL_WORST_CASE_BAR = 2.0
_DEN_UIJL_MEAN_SIGNED_BAR = 0.2


def _den_uijl_signed_errors(
    dataset: ScanningGradientSet,
    *,
    fit_at: tuple[float, float],
    predict_at: tuple[float, ...],
) -> list[float]:
    """Fit every fittable compound on one pair of gradient times, predict at others."""
    run1, run2 = dataset.run(fit_at[0]), dataset.run(fit_at[1])
    peaks = [dataset.peak(compound, *fit_at) for compound in dataset.fittable]

    errors: list[float] = []
    for t_gradient in predict_at:
        target = dataset.run(t_gradient)
        predicted = _predict_held_out(peaks, dataset.method, run1, run2, target)
        measured = [dataset.t_r(compound, t_gradient) for compound in dataset.fittable]
        errors += _signed_percent_errors(predicted, measured)
    return errors


@pytest.mark.parametrize(
    ("dataset", "n_predictions"),
    [(SET_X, 38), (SET_Y, 30)],
    ids=["set-X", "set-Y"],
)
def test_den_uijl_predictions_meet_the_reality_bar(
    dataset: ScanningGradientSet, n_predictions: int
) -> None:
    """SPEC §10 layer 3: median |ΔtR| ≤ 0.5%, worst ≤ 2%, mean signed error ≤ 0.2%.

    Fit on tG = 3 and 9 min — the paper's recommended benchmark pair, Γ = 3 — and
    predict the two interpolated conditions the fit never saw.

    The mean-signed bar is the load-bearing one. Research doc §1.4: dropping the
    0.25 min pre-gradient hold leaves the per-peak errors inside ±2% but swings the
    mean signed error from −0.03% to +1.09%. Scatter tolerances miss that; this
    does not.
    """
    errors = _den_uijl_signed_errors(dataset, fit_at=(3.0, 9.0), predict_at=(4.5, 7.5))
    magnitudes = [abs(error) for error in errors]

    # A fixture that quietly loses compounds would otherwise pass every bar below.
    assert len(errors) == n_predictions

    assert median(magnitudes) <= _DEN_UIJL_MEDIAN_BAR
    assert max(magnitudes) <= _DEN_UIJL_WORST_CASE_BAR
    assert abs(fmean(errors)) <= _DEN_UIJL_MEAN_SIGNED_BAR


@pytest.mark.parametrize(
    ("dataset", "documented_bias"),
    [
        # Research doc §1.4: ignore Set X's 0.25 min pre-gradient hold and the mean signed
        # error goes from −0.03% to +1.09%.
        (replace(SET_X, t_init=0.0), 1.09),
        # Research doc §2.1: feed Set Y the bare column dead time (0.171 min) instead of the
        # measured uracil time, dropping the 0.058 min of extra-column volume, and it goes
        # from +0.04% to +0.41%.
        (replace(SET_Y, method=Method(t0=0.171, t_dwell=0.0324, flow=2.5)), 0.41),
    ],
    ids=["set-X-hold-ignored", "set-Y-column-only-t0"],
)
def test_mean_signed_bar_is_what_catches_a_dropped_time_term(
    dataset: ScanningGradientSet, documented_bias: float
) -> None:
    """Both documented ways of losing a time term must break the bar — and only via the mean.

    This is the test that keeps the reality bar honest. Dropping a term ahead of the
    column (the hold, the dwell, extra-column volume) shifts every peak the same way
    rather than scattering them, so it survives per-peak tolerances: both slips below
    stay inside the ±2% worst-case bar, which is asserted here to make the point
    unmissable. Only the mean signed error sees them.

    If a future change ever makes these variants pass, the bar has stopped measuring
    what SPEC §10 wrote it to measure.
    """
    errors = _den_uijl_signed_errors(dataset, fit_at=(3.0, 9.0), predict_at=(4.5, 7.5))

    assert fmean(errors) == pytest.approx(documented_bias, abs=0.05)
    assert abs(fmean(errors)) > _DEN_UIJL_MEAN_SIGNED_BAR
    # The slip is a systematic shift, not scatter: the per-peak bar never notices it.
    assert max(abs(error) for error in errors) <= _DEN_UIJL_WORST_CASE_BAR


_REFUSED = "refused"
_LOW_CONFIDENCE_FIT = "low-confidence fit"

# The split is pinned per compound because the research doc's amended §1.2 now states it.
# If the engine's behaviour here changes, this list and that paragraph must move together
# — a green test alongside a stale doc is exactly what the amendment was fixing.
_UNRETAINED_CASES = [
    (SET_X, "Uracil", _REFUSED),
    (SET_X, "Cytosine", _REFUSED),
    (SET_X, "Tyramine", _REFUSED),
    (SET_X, "Peptide 1", _REFUSED),
    (SET_Y, "Uracil", _REFUSED),
    (SET_Y, "Cytosine", _REFUSED),
    # Set Y's t0 + τ is only 0.261 min, so unlike Set X these two clear it and do move
    # with gradient time — a real if badly-conditioned LSS solution, not an impossibility.
    (SET_Y, "Tyramine", _LOW_CONFIDENCE_FIT),
    (SET_Y, "Peptide 1", _LOW_CONFIDENCE_FIT),
]


def test_every_flat_compound_has_a_pinned_expectation() -> None:
    """The case list above must not drift from the fixtures' own `unretained` tuples."""
    assert {(dataset.name, compound) for dataset, compound, _ in _UNRETAINED_CASES} == {
        (dataset.name, compound) for dataset in (SET_X, SET_Y) for compound in dataset.unretained
    }


@pytest.mark.parametrize(
    ("dataset", "compound", "expected"),
    _UNRETAINED_CASES,
    ids=[
        f"{dataset.name.rsplit(' ', 1)[-1]}-{compound}"
        for dataset, compound, _ in _UNRETAINED_CASES
    ],
)
def test_unretained_compounds_never_come_back_as_a_confident_fit(
    dataset: ScanningGradientSet, compound: str, expected: str
) -> None:
    """Uracil, Cytosine, Tyramine and Peptide 1 are flat across tG (research doc §1.2).

    An earlier version of §1.2 said the engine "should refuse to fit them rather than
    emit garbage parameters". This ticket amended that, because it overstates what SPEC
    permits. Six of these eight cases do refuse: the band is already off the column when
    the gradient arrives, so both runs are literally the same isocratic measurement and
    there is nothing to fit.

    Set Y's Tyramine and Peptide 1 are not that case. They elute after t0 + τ and do move
    with gradient time (0.3320 → 0.3456 min), so an LSS solution genuinely exists — it is
    merely badly conditioned. CLAUDE.md reserves hard failure for impossibilities, so
    those two fit and come back low-confidence with log10 k0 ≈ −0.25, i.e. k0 < 1: the
    engine saying "not a retained peak" in the only way the spec permits it to.

    The invariant that holds across all eight, and the one a caller can rely on: an
    unretained compound never returns as a *confident* fit.
    """
    peak = dataset.peak(compound, 3.0, 9.0)
    try:
        fit = fit_peak(peak, dataset.method, dataset.run(3.0), dataset.run(9.0))
    except ValueError as refusal:
        assert expected == _REFUSED, f"expected a {expected}, got refusal: {refusal}"
        # Refused for the documented reason, not by some unrelated failure.
        assert "before the gradient" in str(refusal)
        return

    assert expected == _LOW_CONFIDENCE_FIT, f"expected {expected}, got a fit"
    assert fit.low_confidence
    assert fit.low_k0


# --- the fixtures against their source of record ---

_TRANSCRIPTION_OF_RECORD = (
    Path(__file__).resolve().parents[1] / "docs/research/validation-datasets.md"
)


def _published_table(
    heading: str, stop_at: str
) -> tuple[tuple[float, ...], dict[str, tuple[float, ...]]]:
    """Re-parse a peak table straight out of the research doc's markdown."""
    doc = _TRANSCRIPTION_OF_RECORD.read_text(encoding="utf-8")
    assert heading in doc, f"{_TRANSCRIPTION_OF_RECORD.name} no longer contains {heading!r}"
    body = doc.split(heading, 1)[1].split(stop_at, 1)[0]

    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in body.splitlines()
        if line.strip().startswith("|")
    ]
    rows = [cells for cells in rows if set("".join(cells)) - set("-: ")]

    gradient_times = tuple(float(head.split("=")[1]) for head in rows[0][1:])
    # The corrected Set X cell carries a footnote marker in the published table.
    table = {
        cells[0]: tuple(float(cell.rstrip("*").strip()) for cell in cells[1:]) for cells in rows[1:]
    }
    return gradient_times, table


@pytest.mark.parametrize(
    ("dataset", "heading", "stop_at"),
    [
        (SET_X, "### 1.2 Measured retention", "Data-quality correction"),
        (SET_Y, "### 2.2 Measured retention", "Cytosine's tR"),
    ],
    ids=["set-X", "set-Y"],
)
def test_fixture_matches_the_transcription_of_record(
    dataset: ScanningGradientSet, heading: str, stop_at: str
) -> None:
    """Every published cell, re-read from the research doc and compared to the fixture.

    `den_uijl_data.py` claims to be nothing but a restatement of the tables in
    `docs/research/validation-datasets.md`. This is that claim, executed.

    It matters most for the columns the reality bar never touches. The bar fits on
    tG = 3/9 and predicts 4.5/7.5; a digit lost in the tG = 1.5 or 18 column would sit
    there silently forever, and no amount of reading the fixture catches what the eye
    slides over. Comparing against the source does.
    """
    gradient_times, published = _published_table(heading, stop_at)

    assert dataset.gradient_times == gradient_times
    assert list(dataset.retention) == list(published), "compound set or row order drifted"
    for compound, times in published.items():
        assert dataset.retention[compound] == pytest.approx(times, abs=0.0), compound


# --- the G-convention calibration against the measured lab widths (SPEC §3) ---
#
# A measured W½ cannot test G on its own: the width model carries an unknown plate
# count N per compound, and any single width can be matched by moving N. But N is a
# property of the *column*, not of the run — so for the right convention, the N implied
# by each of a compound's measured widths must agree across every gradient time. The
# scatter of implied N within a compound is therefore the discriminator, and it uses
# all four runs rather than a single ratio.
#
# Runs 3 and 4 are held out of the fit that supplies (k0, S_e), so this is a prediction
# test. Run 4 is what settled the question: at tG = 60 against run 1's tG = 15 it gives
# a fourfold lever on b_e, where the original scouting pair gave threefold.
#
# Outcome recorded in research doc §5.4; these tests and that section move together.

# The three runs whose W½ is recorded to three decimals. run3 (tG25) carries two, a
# ±10% band on a 0.05 min peak, so it cannot discriminate a ~5% effect — it is included
# only in the robustness test below, never in the primary verdict.
_CALIBRATION_RUNS = ("tG15", "tG45", "tG60")
_RUNS_BY_NAME = {"tG15": LAB_RUN1, "tG25": LAB_RUN3, "tG45": LAB_RUN2, "tG60": LAB_RUN4}

# Unknown-1 is the only compound whose area follows the expected run-time trend
# without a break, so it is the only one whose widths are trustworthy peak by peak.
# SPEC §5 names the other two independently — "the lab dataset's peaks 2–3 exceed it".
_CLEAN_COMPOUND = "Unknown-1"

# SPEC §5's area-share warning threshold, "~30% relative change", as a max/min ratio.
_AREA_SHARE_THRESHOLD = 1.3

# Under the shipped convention Unknown-1's implied N is constant to 0.92% across a
# fourfold steepness range — at or below the ±1.5% quantisation floor of its own
# widths, i.e. as tight as this data can resolve. 2% is that floor with a little room;
# every rival convention scatters by more than 5%.
_PLATE_COUNT_CONSTANCY_BAR = 2.0
_RIVAL_SCATTER_FLOOR = 4.0

Compression = Callable[[float, float], float]


def _scaled_compression(b_e_scale: float) -> Compression:
    """A 2.303 slip: the steepness fed to G scaled by ln 10 or its reciprocal."""
    return lambda b_e, k0: band_compression_factor(b_e * b_e_scale, k0=k0)


def _no_compression(_b_e: float, _k0: float) -> float:
    """The null model: no band compression at all."""
    return 1.0


_RIVAL_CONVENTIONS = {
    "no-compression": _no_compression,
    "base10-steepness-slip": _scaled_compression(1.0 / _LN10),
    "over-compressed-mirror": _scaled_compression(_LN10),
}


def _implied_plate_count(name: str, run_name: str, compression: Compression | None) -> float:
    """N that one measured width implies, under a candidate G convention.

    ``compression`` of ``None`` routes through :func:`peak_width` and uses the G the
    engine actually ships, so the shipped verdict exercises production code rather
    than a reimplementation of it.
    """
    peak = next(p for p in LAB_MEASURED_PEAKS if p.name == name)
    params = fit_peak(peak, LAB_METHOD, LAB_RUN1, LAB_RUN2).params
    gradient = _RUNS_BY_NAME[run_name].gradient
    width = peak_width(params, LAB_METHOD, gradient)
    assert width.g < 1.0, "every lab run must elute this peak in the compressed regime"
    if compression is None:
        g = width.g
    else:
        b_e = gradient_steepness(LAB_METHOD, gradient, params.s_e)
        g = compression(b_e, params.k_at(gradient.phi0))
    sigma = LAB_MEASURED_W_HALF[run_name][name] / _W_HALF_PER_SIGMA
    return (g * LAB_METHOD.t0 * (1.0 + width.k_e) / sigma) ** 2


def _plate_count_scatter(
    name: str, compression: Compression | None, runs: tuple[str, ...] = _CALIBRATION_RUNS
) -> float:
    """Coefficient of variation (%) of one compound's implied N across runs."""
    counts = [_implied_plate_count(name, run_name, compression) for run_name in runs]
    return stdev(counts) / fmean(counts) * 100.0


def _mean_scatter(compression: Compression | None, runs: tuple[str, ...]) -> float:
    """Mean scatter over every compound — the verdict without any exclusions."""
    return fmean(_plate_count_scatter(peak.name, compression, runs) for peak in LAB_MEASURED_PEAKS)


def test_the_shipped_convention_holds_plate_count_constant_across_steepness() -> None:
    """The primary calibration result (research doc §5.4).

    One column has one plate count. Under the shipped natural-log convention the
    clean compound's implied N agrees across a fourfold range of gradient steepness
    to within the precision its own widths were recorded at. That is what a correct
    band-compression factor looks like.
    """
    assert _plate_count_scatter(_CLEAN_COMPOUND, None) <= _PLATE_COUNT_CONSTANCY_BAR


@pytest.mark.parametrize("rival", sorted(_RIVAL_CONVENTIONS), ids=sorted(_RIVAL_CONVENTIONS))
def test_every_rival_convention_scatters_the_plate_count(rival: str) -> None:
    """Each rival makes the same column look like a different column per run.

    This covers all three: dropping compression entirely, and both directions of the
    2.303 slip — including the over-compressed mirror, which the scouting pair alone
    could not separate from the shipped convention. Run 4's fourfold lever is what
    separates it.
    """
    scatter = _plate_count_scatter(_CLEAN_COMPOUND, _RIVAL_CONVENTIONS[rival])

    assert scatter > _RIVAL_SCATTER_FLOOR
    assert scatter > 2.0 * _plate_count_scatter(_CLEAN_COMPOUND, None)


@pytest.mark.parametrize(
    "runs",
    [_CALIBRATION_RUNS, ("tG15", "tG25", "tG45", "tG60")],
    ids=["three-decimal-runs", "including-the-coarse-run3"],
)
def test_the_verdict_survives_every_compound_and_every_run(runs: tuple[str, ...]) -> None:
    """No exclusion is doing the work.

    §5.4 sets Unknown-2 aside as an unreliable measurement and down-weights run 3 for
    being recorded to two decimals. Neither choice is load-bearing: averaged over all
    three compounds, with and without run 3, the shipped convention still scatters N
    least of the four candidates. A verdict that needed the exclusions would be a
    verdict about the exclusions.
    """
    shipped = _mean_scatter(None, runs)

    for name, rival in _RIVAL_CONVENTIONS.items():
        assert shipped < _mean_scatter(rival, runs), name


def test_only_the_clean_compound_tracks_the_expected_area_trend() -> None:
    """The outcome-independent grounds for resting the verdict on Unknown-1.

    Peak area is *expected* to grow slowly with run time — a longer gradient keeps the
    band in the flow cell longer — so growth on its own says nothing. All three
    compounds do show it, mildly: 1.08×, 1.01× and 1.14× end to end across a fourfold
    range of gradient time. What separates them is the *shape* of the trend.

    Unknown-1 tracks it monotonically. Unknown-2 and Unknown-3 do not: both spike by
    1.54–1.67× at tG = 45 specifically and then fall back, which a run-time trend
    cannot produce. That localises the problem to one run's integration of those two
    peaks, and SPEC §5 already names them — "the lab dataset's peaks 2–3 exceed it",
    of its ~30% area-share threshold. If the integrator is not measuring the same
    thing there, those compounds' widths in that run are not trustworthy either.

    Pinned so §5.4's choice rests on something a reader can check independently of the
    conclusion it supports.
    """
    by_gradient_time = sorted(
        LAB_MEASURED_AREA, key=lambda run: _RUNS_BY_NAME[run].gradient.t_gradient
    )

    def areas(name: str) -> list[float]:
        return [LAB_MEASURED_AREA[run][name] for run in by_gradient_time]

    def rises_monotonically(name: str) -> bool:
        return all(a <= b for a, b in zip(areas(name), areas(name)[1:], strict=False))

    assert rises_monotonically(_CLEAN_COMPOUND)
    for peak in LAB_MEASURED_PEAKS:
        if peak.name == _CLEAN_COMPOUND:
            continue
        assert not rises_monotonically(peak.name), peak.name
        # And the break is a spike at one run, not drift: tG = 45 stands well above
        # both of its neighbours in gradient time.
        spike = LAB_MEASURED_AREA["tG45"][peak.name] / max(
            LAB_MEASURED_AREA["tG25"][peak.name], LAB_MEASURED_AREA["tG60"][peak.name]
        )
        assert spike > _AREA_SHARE_THRESHOLD, (peak.name, spike)


def test_the_calibration_statistic_clears_the_measurement_quantisation() -> None:
    """The bar has to be tighter than nothing and wider than the noise floor.

    W½ is recorded to three decimals in the runs the verdict rests on, giving a ±1.5%
    band on the clean compound's narrowest peak. The constancy bar sits just above it,
    so the 0.92% the shipped convention achieves is at the floor of what these widths
    can resolve — it cannot be beaten, only matched. If the recorded precision ever
    coarsened, this test says so before the verdict silently softens.
    """
    worst_band = max(
        LAB_W_HALF_ULP[run_name] / LAB_MEASURED_W_HALF[run_name][_CLEAN_COMPOUND] * 100.0
        for run_name in _CALIBRATION_RUNS
    )

    assert worst_band < _PLATE_COUNT_CONSTANCY_BAR


def test_width_fixtures_agree_with_the_peak_fixtures() -> None:
    """LAB_MEASURED_W_HALF restates runs 1–2, which LAB_MEASURED_PEAKS also carries."""
    for peak in LAB_MEASURED_PEAKS:
        assert LAB_MEASURED_W_HALF["tG15"][peak.name] == peak.w_half_run1
        assert LAB_MEASURED_W_HALF["tG45"][peak.name] == peak.w_half_run2


def test_the_column_based_plate_count_underpredicts_real_widths() -> None:
    """The h = 2 default is a textbook estimate, not a fit — and reads as one.

    Real widths carry extra-column broadening and a real reduced plate height above
    2, so the default N over-estimates efficiency and predicted widths come out
    narrow, across every run including the two held out. Pinned as a band so that a
    units slip or a dropped √N (research doc §5.1's reconstruction caveat) cannot
    hide inside "the default is only an estimate".
    """
    ratios = []
    for peak in LAB_MEASURED_PEAKS:
        params = fit_peak(peak, LAB_METHOD, LAB_RUN1, LAB_RUN2).params
        for run_name, run in _RUNS_BY_NAME.items():
            predicted = peak_width(params, LAB_METHOD, run.gradient).w_half
            ratios.append(predicted / LAB_MEASURED_W_HALF[run_name][peak.name])

    assert all(0.6 <= ratio <= 1.0 for ratio in ratios), ratios


# --- the plate count fitted from the scouting widths (ticket #23) ---
#
# The §5.4 statistic above already computes the N each measured width implies; #23
# makes that a function and fits one N per peak from the scouting pair (research doc
# plate-count-from-widths.md §3). What changes downstream is every absolute width and
# every Rs — so this block re-asks the held-out questions with the fitted N and keeps
# the defaulted-N answers alongside, because width-less sessions still get those.

# Held-out W½ with a fitted N: 0.99–1.16× measured (research doc §0.2), against
# 0.69–0.92× with the geometry default. The band has margin; the sharper claim is
# per-peak: fitted is closer to measured than the default in every case.
_FITTED_WIDTH_BAND = (0.9, 1.25)

# Held-out Rs with a fitted N: 0.90–0.96× measured — slightly pessimistic now, where
# the default was 1.18–1.39× optimistic.
_FITTED_RS_BAND = (0.85, 1.05)


def _lab_fits() -> list[FitResult]:
    return fit_peaks(LAB_MEASURED_PEAKS, LAB_METHOD, LAB_RUN1, LAB_RUN2)


def _resolution_at(
    peaks: list[Peak], method: Method, run1: Run, run2: Run, gradient: Gradient, *, fitted: bool
) -> ResolutionTable:
    """Fit a scouting pair and resolve every peak at a condition it never saw."""
    fits = fit_peaks(peaks, method, run1, run2)
    return resolution_table(
        [fit.params for fit in fits],
        method,
        gradient,
        names=[peak.name for peak in peaks],
        plate_counts=[fit.plate_count for fit in fits] if fitted else None,
    )


def _lab_table(target: Run, *, fitted: bool) -> ResolutionTable:
    """The three lab peaks resolved at a held-out condition, with or without fitted N."""
    return _resolution_at(
        LAB_MEASURED_PEAKS, LAB_METHOD, LAB_RUN1, LAB_RUN2, target.gradient, fitted=fitted
    )


def _width_ratios(target: Run, run_name: str, *, fitted: bool) -> dict[str, float]:
    """Predicted / measured W½ per peak at a held-out condition."""
    return {
        peak.name: peak.width.w_half / LAB_MEASURED_W_HALF[run_name][peak.name]
        for peak in _lab_table(target, fitted=fitted).peaks
    }


def test_the_production_inverse_agrees_with_the_calibration_statistic() -> None:
    """`plate_count_from_width` is §5.4's implied-N statistic, written by hand above.

    The by-hand form multiplies G, t0 and (1 + k_e) out explicitly; production inverts
    `peak_width` at N = 1. Two routes to one number — kept separate on purpose, so the
    calibration tests stay an oracle for the function rather than a call to it.
    """
    peak = next(p for p in LAB_MEASURED_PEAKS if p.name == _CLEAN_COMPOUND)
    params = fit_peak(peak, LAB_METHOD, LAB_RUN1, LAB_RUN2).params
    for run_name, run in _RUNS_BY_NAME.items():
        w_half = LAB_MEASURED_W_HALF[run_name][_CLEAN_COMPOUND]
        production = plate_count_from_width(params, LAB_METHOD, run.gradient, w_half)
        assert production == pytest.approx(
            _implied_plate_count(_CLEAN_COMPOUND, run_name, None), rel=1e-12
        )


def test_the_implied_plate_count_ratio_is_the_data_quality_signal_per_peak() -> None:
    """How far a peak's two scouting widths disagree about N — characterised, not judged.

    Research doc §5.4 showed a correctly modelled peak holds implied N to ~1% across a
    fourfold range of tG; Unknown-3's two scouting widths disagree by 16%. That is a
    different number from the one §2.4 of plate-count-from-widths.md discusses — its
    N being 1.6× the other compounds', read there as intrinsic because its peaks are
    the narrowest — but it is the same peak and the same question of whether its
    widths are trustworthy. The engine reports the ratio; the threshold is
    diagnostics work (ticket #20), and these are the numbers it will be drawn against.
    """
    ratios = [fit.plate_count.ratio for fit in _lab_fits() if fit.plate_count is not None]

    assert ratios == pytest.approx([1.011, 1.074, 1.162], abs=0.002)


@pytest.mark.parametrize(
    ("run_name", "target"),
    [("tG25", LAB_RUN3), ("tG60", LAB_RUN4)],
    ids=["tG25-confirmation", "tG60-extrapolation"],
)
def test_fitted_plate_counts_predict_the_held_out_widths(run_name: str, target: Run) -> None:
    """Criterion 1's width half: fit N on runs 1–2, predict W½ at a run never seen.

    The default N is a geometry estimate and reads as one (the test above this block
    pins it at 0.6–1.0× measured, every peak, every run). A fitted N lands the
    held-out widths at 0.99–1.16× — and, peak by peak, always closer than the default.
    """
    fitted = _width_ratios(target, run_name, fitted=True)
    default = _width_ratios(target, run_name, fitted=False)

    low, high = _FITTED_WIDTH_BAND
    assert all(low <= ratio <= high for ratio in fitted.values()), fitted
    for name, ratio in fitted.items():
        assert abs(ratio - 1.0) < abs(default[name] - 1.0), (name, ratio, default[name])


# --- resolution against the held-out runs (SPEC §10's Rs bar, tickets #17 and #23) ---
#
# SPEC §10 wanted "Rs ± 0.3 asserted once the G convention is calibrated". It is
# calibrated (§5.4) and runs 3–4 carry W½, so measured Rs exists at held-out
# conditions. #17 found the bar unmet for a reason about N, not G: the defaulted N is
# column geometry, so every Rs came out 18–39% optimistic. #23 closed that obstacle
# by fitting N — and the bar is *still* unmet, now for the reason that was always
# second: the sample sits at Rs 30–116, where ±0.3 is a 0.3–1% tolerance, and the
# fitted-N residual is −4% to −10%. Recorded in research doc §6 and SPEC §10. What is
# asserted instead: the right critical pair (both paths), the fitted-N bands, and
# the unmet ±0.3 pinned as a number so the SPEC sentence cannot rot silently.

_RS_OPTIMISM_BAND = (1.1, 1.6)
_RS_BAR = 0.3


def _resolutions_from(
    measured_t_r: dict[str, float],
    widths: dict[str, float],
    *,
    width_offset: float = 0.0,
    separation_offset: float = 0.0,
) -> list[float]:
    """Rs from measured tR and measured W½, in elution order — both samples use this.

    ``width_offset`` shifts every width and ``separation_offset`` every neighbour
    separation: 0/0 gives the point estimate, and the two offsets at ±their rounding
    step give the edges of the band the recorded precision allows (`_resolution_bands`).
    """
    ordered = sorted(measured_t_r, key=lambda name: measured_t_r[name])
    return [
        _W_HALF_PER_SIGMA
        / 2.0
        * (measured_t_r[later] - measured_t_r[earlier] + separation_offset)
        / (widths[earlier] + widths[later] + 2.0 * width_offset)
        for earlier, later in zip(ordered, ordered[1:], strict=False)
    ]


def _resolution_bands(
    measured_t_r: dict[str, float],
    widths: dict[str, float],
    *,
    width_ulp: float,
    t_r_ulp: float,
) -> list[tuple[float, float]]:
    """The interval each measured Rs can occupy, given the precision the data carries.

    Rs is a separation over a sum of widths and *both* are rounded, so both feed the
    band. Which one dominates depends on the sample: on the lab set a separation is
    6–18 min, so its ±0.001 min is 0.01% against the widths' ±0.5% and the tR term is
    invisible. On a sample whose neighbours are 0.15 min apart it is the larger of the
    two, and leaving it out invents a precision the instrument never delivered — that
    error previously made a 0.01 Rs miss look like a real disagreement.

    ``t_r_ulp`` is the half-ULP of one retention time; a separation is a difference of
    two, so it carries twice that.
    """
    return list(
        zip(
            _resolutions_from(
                measured_t_r,
                widths,
                width_offset=width_ulp,
                separation_offset=-2.0 * t_r_ulp,
            ),
            _resolutions_from(
                measured_t_r,
                widths,
                width_offset=-width_ulp,
                separation_offset=2.0 * t_r_ulp,
            ),
            strict=True,
        )
    )


def _measured_resolutions(
    run_name: str, measured_t_r: dict[str, float], *, width_offset: float = 0.0
) -> list[float]:
    """The lab sample's Rs at one run."""
    return _resolutions_from(measured_t_r, LAB_MEASURED_W_HALF[run_name], width_offset=width_offset)


# Every lab run records tR to 0.001 min, so one time carries a half-ULP of 0.0005.
_LAB_TR_ULP = 0.0005


def _measured_resolution_bands(
    run_name: str, measured_t_r: dict[str, float]
) -> list[tuple[float, float]]:
    """The lab sample's Rs band at one run, from that run's own recorded precision.

    Derived from the data rather than typed in, so a re-measured run moves it
    automatically. The tR term is negligible at this sample's 6–18 min separations
    and is included only so the two datasets compute a band the same way.
    """
    return _resolution_bands(
        measured_t_r,
        LAB_MEASURED_W_HALF[run_name],
        width_ulp=LAB_W_HALF_ULP[run_name],
        t_r_ulp=_LAB_TR_ULP,
    )


_HELD_OUT = [("tG25", LAB_RUN3, LAB_MEASURED_TG25), ("tG60", LAB_RUN4, LAB_MEASURED_TG60)]
_HELD_OUT_IDS = ["tG25-confirmation", "tG60-extrapolation"]


@pytest.mark.parametrize(("run_name", "target", "measured_t_r"), _HELD_OUT, ids=_HELD_OUT_IDS)
@pytest.mark.parametrize("fitted", [False, True], ids=["default-N", "fitted-N"])
def test_the_critical_pair_is_identified_correctly_at_held_out_conditions(
    run_name: str, target: Run, measured_t_r: dict[str, float], fitted: bool
) -> None:
    """The decision-relevant output survives either plate count.

    With the default N every Rs is optimistic by a near-common factor; with fitted N
    every Rs is slightly pessimistic. Neither disturbs the *ranking*: the pair the
    engine calls critical is the pair the instrument says is worst.
    """
    table = _lab_table(target, fitted=fitted)

    measured = _measured_resolutions(run_name, measured_t_r)
    assert table.critical_pair is not None
    predicted_critical = min(range(len(table.pairs)), key=lambda i: table.pairs[i].rs)
    measured_critical = min(range(len(measured)), key=lambda i: measured[i])
    assert predicted_critical == measured_critical


@pytest.mark.parametrize(("run_name", "target", "measured_t_r"), _HELD_OUT, ids=_HELD_OUT_IDS)
def test_resolution_with_a_defaulted_plate_count_stays_uniformly_optimistic(
    run_name: str, target: Run, measured_t_r: dict[str, float]
) -> None:
    """The width-less path, characterised: why a defaulted N is caveated (SPEC §6.5).

    Every predicted Rs runs high by a similar factor on both held-out runs — the h = 2
    default overstating this column's efficiency, not a defect in G and not scatter.
    Under #17 this band was the deliberately-failing guard that would trip the day N
    became fitted; it did (the fitted ratios sit at 0.90–0.96, below 1.0, let alone
    1.1), and the next test is its replacement. This one stays because sessions
    without widths still get exactly this behaviour, and it must not drift.
    """
    table = _lab_table(target, fitted=False)

    measured = _measured_resolutions(run_name, measured_t_r)
    ratios = [pair.rs / m for pair, m in zip(table.pairs, measured, strict=True)]
    low, high = _RS_OPTIMISM_BAND
    assert all(low <= ratio <= high for ratio in ratios), ratios
    assert all(ratio > 1.0 for ratio in ratios), f"optimism is one-sided: {ratios}"


@pytest.mark.parametrize(("run_name", "target", "measured_t_r"), _HELD_OUT, ids=_HELD_OUT_IDS)
def test_resolution_with_fitted_plate_counts_lands_within_a_tenth_of_measured(
    run_name: str, target: Run, measured_t_r: dict[str, float]
) -> None:
    """Criterion 1's Rs half — the tightened assertion that replaces the optimism band.

    Fit N from runs 1–2, resolve at a run never seen: Rs comes out at 0.90–0.96× measured
    on both held-out conditions, 1.5–11.6 Rs units low at Rs 30–116, where the default
    was 13–26 units high. The residual is slightly pessimistic and no longer a common
    factor — see the two tests below for what each condition can actually resolve.
    """
    table = _lab_table(target, fitted=True)

    measured = _measured_resolutions(run_name, measured_t_r)
    ratios = [pair.rs / m for pair, m in zip(table.pairs, measured, strict=True)]
    low, high = _FITTED_RS_BAND
    assert all(low <= ratio <= high for ratio in ratios), ratios


def test_at_tg25_the_fitted_resolution_is_inside_the_measurement_band() -> None:
    """The confirmation run cannot resolve the fitted-N residual at all.

    run3.csv records W½ to two decimals, so its measured Rs is only known to ±9–13%
    (−9.1..+11.1% and −10.0..+12.5%, pair by pair).
    Both fitted-N predictions sit inside that band: at tG = 25 the engine and the
    instrument agree to within what the instrument wrote down.
    """
    table = _lab_table(LAB_RUN3, fitted=True)

    bands = _measured_resolution_bands("tG25", LAB_MEASURED_TG25)
    for pair, (low, high) in zip(table.pairs, bands, strict=True):
        assert low <= pair.rs <= high, (pair.earlier.name, pair.later.name, pair.rs, low, high)


def test_at_tg60_the_fitted_resolution_residual_is_real() -> None:
    """The extrapolation run does resolve it: −6.5% and −10%, outside a ±0.5% band.

    run4.csv carries three decimals, so this residual is a genuine statement about the
    model — one N per compound across a fourfold range of tG, and a G that is itself
    known to ~10% (research doc plate-count-from-widths.md §2.3). Pinned as *outside*
    the band so that SPEC §10's wording ("real at tG = 60") is tied to the data: if a
    better width model ever lands inside, this fails and the sentence gets rewritten.
    """
    table = _lab_table(LAB_RUN4, fitted=True)

    bands = _measured_resolution_bands("tG60", LAB_MEASURED_TG60)
    for pair, (low, high) in zip(table.pairs, bands, strict=True):
        assert pair.rs < low, (pair.earlier.name, pair.later.name, pair.rs, low, high)


@pytest.mark.parametrize(("run_name", "target", "measured_t_r"), _HELD_OUT, ids=_HELD_OUT_IDS)
def test_the_rs_bar_of_spec_10_is_still_unmet_with_fitted_plate_counts(
    run_name: str, target: Run, measured_t_r: dict[str, float]
) -> None:
    """Rs ± 0.3 — recorded as unmet in SPEC §10, and pinned so the record stays true.

    With N fitted the first obstacle (#17's defaulted N) is gone, and what remains is
    the second: this sample's pairs sit at Rs 30–116, where ±0.3 is a 0.3–1% tolerance
    the width model cannot meet and no chromatographer needs. Meeting the bar needs a
    sample with a near-critical pair, not a better fit. The day every held-out pair
    lands within 0.3, this fails and SPEC §10 gets its status changed on evidence.
    """
    table = _lab_table(target, fitted=True)

    measured = _measured_resolutions(run_name, measured_t_r)
    misses = [abs(pair.rs - m) for pair, m in zip(table.pairs, measured, strict=True)]
    assert all(miss > _RS_BAR for miss in misses), misses


# --- Validation_2: the near-critical-pair sample (SPEC §10's Rs bar, ticket #49) ---
#
# Everything above this line is one sample whose adjacent pairs sit at Rs 30–116. SPEC
# §10 recorded the ±0.3 criterion as unmet on it and said why: not a defect in G or N,
# but a sample where ±0.3 is a 0.3–1% tolerance. The bar "needs a sample containing a
# near-critical pair". This is that sample — four compounds inside a 0.5 min window,
# critical pair at Rs ≈ 1.75, on the same instrument, column and 0.4 mL/min.
#
# Two held-out runs, and they are evidence about different things:
#   run3  tG 20,  5 → 95 %B  — Δφ 0.90, s* 0.0270
#   run4  tG 20, 15 → 95 %B  — Δφ 0.80, s* 0.0240
#
# Note what run4 is NOT: an isolated φ0 change. Moving φ0 with φf pinned moves Δφ too,
# and therefore s* = t0·Δφ/tG. Both of its s* values sit inside the scouting bracket
# [0.0135, 0.0360], so by composition-extrapolation.md §7.2 — where the candidate
# gradient enters the elution composition *only* through s* — neither run extrapolates
# the fit. Any difference between them is a difference across three coupled variables,
# and nothing here may attribute it to φ0 alone. Issue #49 records the one injection
# that would separate them: 5 → 85 %B at tG 20 shares φ0 with run3 and Δφ, tG and s*
# with run4.

_V2_RS_TRIPWIRE = 0.1
_V2_TR_TRIPWIRE = {"run3": 0.15, "run4": 0.25}
_V2_FITTED_WIDTH_BAND = (0.98, 1.02)
# How far the four per-peak tR offsets may spread within one run, in minutes.
# run3 is rigid to within the 0.001 min export step; run4 carries a real slope.
_V2_OFFSET_SPREAD = {"run3": 0.002, "run4": 0.004}
_V2_IDS = ["run3-tG-interpolation", "run4-phi0-shifted"]


def _v2_fits() -> list[FitResult]:
    return fit_peaks(VALIDATION2_PEAKS, VALIDATION2_METHOD, VALIDATION2_RUN1, VALIDATION2_RUN2)


def _v2_table(run_name: str) -> ResolutionTable:
    """The four peaks resolved at a held-out condition, N fitted from the scouting pair.

    Always fitted: unlike the lab sample there is no width-less path to characterise
    here, because every Validation_2 run carries W½.
    """
    return _resolution_at(
        VALIDATION2_PEAKS,
        VALIDATION2_METHOD,
        VALIDATION2_RUN1,
        VALIDATION2_RUN2,
        VALIDATION2_RUNS_BY_NAME[run_name].gradient,
        fitted=True,
    )


def _v2_offsets(run_name: str) -> list[float]:
    """Predicted − measured tR (min) at a held-out run, in fixture order."""
    measured = VALIDATION2_MEASURED_TR[run_name]
    gradient = VALIDATION2_RUNS_BY_NAME[run_name].gradient
    return [
        predict_retention(fit.params, VALIDATION2_METHOD, gradient).t_r - measured[peak.name]
        for fit, peak in zip(_v2_fits(), VALIDATION2_PEAKS, strict=True)
    ]


def _v2_measured_resolutions(run_name: str, *, width_offset: float = 0.0) -> list[float]:
    """Rs from measured tR and measured W½ at a held-out run, in elution order."""
    return _resolutions_from(
        VALIDATION2_MEASURED_TR[run_name],
        VALIDATION2_MEASURED_W_HALF[run_name],
        width_offset=width_offset,
    )


def _v2_measured_resolution_bands(run_name: str) -> list[tuple[float, float]]:
    """The interval each measured Rs can occupy, given the precision the data carries.

    On this sample the tR term is the one that matters: neighbours are 0.09–0.30 min
    apart, so a separation's ±0.001 min is up to ±1.1% against the widths' ±1.6–2.2%.
    """
    return _resolution_bands(
        VALIDATION2_MEASURED_TR[run_name],
        VALIDATION2_MEASURED_W_HALF[run_name],
        width_ulp=VALIDATION2_W_HALF_ULP,
        t_r_ulp=VALIDATION2_TR_GRANULARITY / 2.0,
    )


def test_validation2_method_restates_the_parent_set() -> None:
    """`Validation_2/` carries no method.csv; it reuses `validation/method.csv`.

    Driver-confirmed 2026-09-02: same column, same instrument, same t0 and dwell. The
    constants are restated in `validation2_data` rather than imported so the two
    datasets stay independently editable — which is only safe if the restatement is
    pinned. If the parent method is ever re-baselined (t0 is #24's open call), this
    fails and forces the question of whether this sample moves with it.
    """
    assert VALIDATION2_METHOD == LAB_METHOD


@pytest.mark.parametrize("run_name", ["run1", "run2", "run3", "run4"])
def test_validation2_fixtures_match_the_source_csvs(run_name: str) -> None:
    """Every fixture cell, re-read from the CSV the instrument wrote.

    The `den_uijl` fixtures get this treatment against the research doc; these get it
    against the raw exports, which is the stronger version — there is no transcription
    step in between to agree with. It reads the embedded `Gradient` programme table
    rather than the `tG_min` header on purpose: run 3's header arrived reading 40 when
    the programme said 20, and a fixture trusted to the header would have scored the
    held-out run against the wrong gradient while every number still looked plausible.
    The header cannot identify run 4 at all — it and run 3 are both tG = 20.
    """
    path = _VALIDATION2_DIR / VALIDATION2_SOURCE_FILES[run_name]
    text = path.read_text(encoding="utf-8-sig")
    rows = [line.strip().split(",") for line in text.splitlines() if line.strip(", ")]

    peaks = {r[0]: r for r in rows if r[0].startswith("Unknown-")}
    programme = [r for r in rows if r[0].isdigit()]

    # The gradient the run was actually acquired with: φ0 holds until the ramp starts,
    # and the ramp ends where %B first reaches its maximum.
    times = [float(r[1]) for r in programme]
    percent_b = [float(r[4]) for r in programme]
    flows = {float(r[2]) for r in programme}
    ramp_start = next(i for i in range(len(percent_b)) if percent_b[i + 1] > percent_b[i])
    ramp_end = percent_b.index(max(percent_b))
    gradient = VALIDATION2_RUNS_BY_NAME[run_name].gradient

    assert flows == {VALIDATION2_METHOD.flow}
    assert gradient.t_init == pytest.approx(times[ramp_start], abs=0.0)
    assert gradient.t_gradient == pytest.approx(times[ramp_end] - times[ramp_start], abs=0.0)
    assert gradient.phi0 * 100.0 == pytest.approx(percent_b[ramp_start], abs=0.0)
    assert gradient.phif * 100.0 == pytest.approx(percent_b[ramp_end], abs=0.0)

    measured_t_r = VALIDATION2_MEASURED_TR.get(run_name) or {
        peak.name: (peak.t_r_run1 if run_name == "run1" else peak.t_r_run2)
        for peak in VALIDATION2_PEAKS
    }
    assert set(peaks) == set(measured_t_r), "compound set drifted from the export"
    for name, row in peaks.items():
        assert measured_t_r[name] == pytest.approx(float(row[1]), abs=0.0), name
        assert VALIDATION2_MEASURED_AREA[run_name][name] == pytest.approx(float(row[2]), abs=0.0), (
            name
        )
        assert VALIDATION2_MEASURED_W_HALF[run_name][name] == pytest.approx(
            float(row[3]), abs=0.0
        ), name


def test_validation2_scouting_pair_fits_without_a_low_confidence_flag() -> None:
    """The conditions under which everything below is allowed to mean anything.

    β = 40/15 = 2.67 clears the 2.5 floor without reaching the preferred 3.0, and the
    peaks are strongly retained (log10 k0 ≈ 3.7–3.8). If a future change made this
    pair marginal, every held-out claim below would still pass while resting on a fit
    the engine itself would warn about — so the preconditions are asserted, not assumed.
    """
    for fit, peak in zip(_v2_fits(), VALIDATION2_PEAKS, strict=True):
        assert fit.beta == pytest.approx(40.0 / 15.0, rel=1e-12), peak.name
        assert fit.beta_spacing == "ok", peak.name
        assert not fit.low_k0, peak.name
        assert not fit.low_confidence, peak.name
        assert fit.max_residual < 1e-6, peak.name
        assert fit.plate_count is not None, peak.name


@pytest.mark.parametrize("run_name", VALIDATION2_HELD_OUT, ids=_V2_IDS)
def test_validation2_held_out_runs_are_predicted_within_the_trust_bar(run_name: str) -> None:
    """Fit tG = 15/40 at 5 → 95 %B, predict two runs the fit never saw.

    run3 varies only tG and lands at 0.07% mean — the tightest held-out retention
    result in the project, against a 2% bar. run4 also moves φ0 to 15 %B, an axis the
    scouting pair holds fixed, and costs a factor of 2.4 (0.18%). Both tripwires sit an
    order of magnitude below the contract for the usual reason: a drift to 1.9% would
    clear the bar with nobody noticing.
    """
    gradient = VALIDATION2_RUNS_BY_NAME[run_name].gradient
    predicted = [
        predict_retention(fit.params, VALIDATION2_METHOD, gradient).t_r for fit in _v2_fits()
    ]
    measured = [VALIDATION2_MEASURED_TR[run_name][peak.name] for peak in VALIDATION2_PEAKS]

    magnitudes = [abs(error) for error in _signed_percent_errors(predicted, measured)]
    assert fmean(magnitudes) <= _LAB_AVERAGE_BAR
    assert max(magnitudes) <= _LAB_WORST_CASE_BAR
    assert _elution_order(predicted) == _elution_order(measured)

    assert fmean(magnitudes) <= _V2_TR_TRIPWIRE[run_name]


@pytest.mark.parametrize("run_name", VALIDATION2_HELD_OUT, ids=_V2_IDS)
def test_validation2_residual_is_near_rigid_within_each_held_out_run(run_name: str) -> None:
    """Why the Rs claims below survive the retention residual: the residual's *shape*.

    Rs is built from neighbour separations, so what matters is not how big the
    over-prediction is but how much of it varies across the elution window. A perfectly
    rigid shift of the whole chromatogram cancels completely; only the part that
    changes from peak to peak can move an Rs.

    The two runs differ, and the difference is the point:

    * run3's four offsets span 0.0014 min against tR exported to 0.001 min — one number
      as far as this instrument can tell.
    * run4's span 0.0036 min, a few export steps, and so cost one separation 0.002 min.

    Whether run4's larger spread is a real slope or accumulated rounding is *not*
    decidable from four apexes recorded to 0.001 min, and nothing here asserts it is.
    What is asserted is the part the ±0.3 result actually needs: at both conditions the
    spread is small against the offset it rides on, and every separation is reproduced
    to within two export steps.
    """
    offsets = _v2_offsets(run_name)
    spread = max(offsets) - min(offsets)

    assert all(offset > 0.0 for offset in offsets), offsets
    assert spread <= _V2_OFFSET_SPREAD[run_name], offsets
    # Small against the offset it rides on, at both conditions.
    assert spread < 0.25 * fmean(offsets), offsets

    # And therefore the separations survive it, to within a couple of export steps.
    measured = VALIDATION2_MEASURED_TR[run_name]
    ordered = sorted(measured, key=lambda name: measured[name])
    neighbours = zip(ordered, ordered[1:], strict=False)
    for pair, (earlier, later) in zip(_v2_table(run_name).pairs, neighbours, strict=True):
        predicted_gap = pair.later.retention.t_r - pair.earlier.retention.t_r
        measured_gap = measured[later] - measured[earlier]
        drift = abs(predicted_gap - measured_gap)
        assert drift <= 2.0 * VALIDATION2_TR_GRANULARITY, (earlier, later, drift)


def test_validation2_offset_growth_is_not_explained_by_any_dwell_error() -> None:
    """A finding that belongs to #44, pinned here because this sample is what shows it.

    Campaign #27 carries an over-prediction that grows as the programme changes, and
    `lab_data.py` records it as a known dwell-shaped offset. This sample reproduces the
    growth on independent data — +0.012 min at run3, +0.028 min at run4 — and rules out
    that explanation, which the parent dataset could not do on its own.

    **What this does not say.** run4 differs from run3 in φ0, Δφ *and* s* together (see
    the section preamble), so the growth cannot be attributed to φ0, or to any one of
    the three. The claim here is only that the two conditions differ and that no dwell
    value spans them.

    The argument is one derivative. For these strongly-retained peaks ∂tR/∂τ = 1 − k_e/k0
    is within 0.25% of 1 at both conditions (worst 0.223%, run4), so *any* dwell error
    shifts both runs by the same number of minutes. Two offsets differing by a factor
    of 2.3 therefore cannot both come from one wrong dwell — closing the 0.0155 min gap
    between them by dwell alone would take δτ ≈ 9.7 min, about 3.9 mL of V_D (research
    #52 §2.1).

    The derivative is asserted to the 0.25% the sentence above claims, not looser: a
    tolerance wider than the claim would let the claim rot while the test still passed.
    (The bound was written as 0.2% before it was ever asserted; tightening the test to
    match found run4 at 0.223% and the prose was corrected, not the tolerance.)

    **Insensitivity is this sample's argument, not the general one** (research #52 §2.2,
    restated under #54). It holds *here* because every peak is strongly retained at both
    conditions. On campaign #27 it fails: k_e/k0 reaches 2.2% on run5 and 8.8% on run7
    (Unknown-1, φ0 = 25 %B), and there a dwell error *does* close the residual growth,
    at δτ ≈ 1.9–2.4 min. Read on #27 alone, the dwell hypothesis survives. What rules it
    out is that no single δτ fits both samples — ≈ 2 min for #27 against ≈ 10 min here —
    on one instrument with one V_D. That cross-dataset inconsistency, not insensitivity,
    is the reason to leave V_D at the instrument's 0.375 mL rather than revisit it.

    Kept small and factual: this says what the residual is *not*. Naming what it is
    needs the injection #49 records, and is `docs/research/` work, not this test's.
    """
    bumped = replace(VALIDATION2_METHOD, t_dwell=VALIDATION2_METHOD.t_dwell + 0.01)
    for run_name in VALIDATION2_HELD_OUT:
        gradient = VALIDATION2_RUNS_BY_NAME[run_name].gradient
        sensitivities = [
            (
                predict_retention(fit.params, bumped, gradient).t_r
                - predict_retention(fit.params, VALIDATION2_METHOD, gradient).t_r
            )
            / 0.01
            for fit in _v2_fits()
        ]
        assert all(s == pytest.approx(1.0, abs=0.0025) for s in sensitivities), (
            run_name,
            sensitivities,
        )

    shifted = fmean(_v2_offsets("run4"))
    baseline = fmean(_v2_offsets("run3"))
    assert shifted > baseline, (baseline, shifted)
    # Far larger than the ~1% of itself that a common dwell term could move between them.
    assert shifted - baseline > 10.0 * VALIDATION2_TR_GRANULARITY, (baseline, shifted)


@pytest.mark.parametrize("run_name", VALIDATION2_HELD_OUT, ids=_V2_IDS)
def test_validation2_fitted_plate_counts_predict_the_held_out_widths(run_name: str) -> None:
    """Widths at 0.988–1.009× measured, against the 0.99–1.16× the parent sample gives.

    Rs needs the widths as much as the separations, so this is half the ±0.3 result.
    The band is deliberately tighter than `_FITTED_WIDTH_BAND`: on this sample the
    fitted N reproduces the held-out widths to within the export's own precision, and
    recording that as 0.9–1.25× would throw the finding away.
    """
    ratios = {
        peak.name: peak.width.w_half / VALIDATION2_MEASURED_W_HALF[run_name][peak.name]
        for peak in _v2_table(run_name).peaks
    }

    low, high = _V2_FITTED_WIDTH_BAND
    assert all(low <= ratio <= high for ratio in ratios.values()), ratios


@pytest.mark.parametrize("run_name", VALIDATION2_HELD_OUT, ids=_V2_IDS)
def test_validation2_critical_pair_is_identified_correctly(run_name: str) -> None:
    """The decision-relevant output: which pair a chromatographer has to work on.

    Unknown-3/Unknown-4 is both the predicted and the measured minimum at both held-out
    conditions, and it is a real contest here — the runner-up sits at 2.6, close enough
    that getting the ranking right is an actual claim rather than an artefact of one
    pair being 100× worse than the others.
    """
    table = _v2_table(run_name)
    measured = _v2_measured_resolutions(run_name)

    assert table.critical_pair is not None
    assert (table.critical_pair.earlier.name, table.critical_pair.later.name) == (
        "Unknown-3",
        "Unknown-4",
    )
    predicted_critical = min(range(len(table.pairs)), key=lambda i: table.pairs[i].rs)
    assert predicted_critical == min(range(len(measured)), key=lambda i: measured[i])


@pytest.mark.parametrize("run_name", VALIDATION2_HELD_OUT, ids=_V2_IDS)
def test_the_rs_bar_of_spec_10_is_met_on_the_near_critical_pair(run_name: str) -> None:
    """SPEC §10's `Rs ± 0.3`, met at two held-out conditions on a near-critical pair.

    The counterpart of `test_the_rs_bar_of_spec_10_is_still_unmet_with_fitted_plate_counts`:
    that one pins why the Rs 30–116 sample cannot answer this question, this one answers
    it. run3 gives 2.56 / 5.13 / 1.75 against measured 2.57 / 5.18 / 1.75; run4, with φ0
    moved to 15 %B, gives 2.59 / 5.18 / 1.78 against 2.64 / 5.20 / 1.77. Every pair at
    both conditions is inside ±0.3 by more than an order of magnitude — worst miss 0.05 —
    and the critical pair itself sits at Rs 1.75–1.78, in the 1–2 band where ±0.3 is the
    tolerance a method decision actually turns on.

    Scope, so the SPEC sentence this backs is not read wider than the evidence: one
    sample, two held-out conditions, one gradient axis and one composition axis.
    """
    table = _v2_table(run_name)
    measured = _v2_measured_resolutions(run_name)

    misses = [abs(pair.rs - m) for pair, m in zip(table.pairs, measured, strict=True)]
    assert all(miss <= _RS_BAR for miss in misses), misses

    assert max(misses) <= _V2_RS_TRIPWIRE, misses


def test_validation2_resolution_is_inside_the_measurement_band() -> None:
    """The sharper statement than ±0.3: the engine agrees to within what was written down.

    Every predicted Rs at both held-out conditions lands inside the interval its own
    recorded precision allows. That is a real claim rather than an absence of one,
    because this sample *could* have failed it: three-decimal W½ on peaks this narrow
    gives a ±1.6–2.2% width term, unlike run 3 of the parent sample whose two-decimal
    widths left a ±9–13% band that could not resolve anything.

    An earlier version of this test asserted that run4's Unknown-1/Unknown-2 fell 0.01
    below its band and called that the one place daylight showed. It was wrong: the
    band it compared against varied only the widths and held the retention times exact.
    Restoring the ±0.001 min those two rounded tR carry widens that pair's interval from
    2.601–2.681 to 2.583–2.699, and the prediction (2.586) is inside it. There is no
    daylight here — the dataset simply cannot resolve a miss that small.
    """
    for run_name in VALIDATION2_HELD_OUT:
        pairs = zip(_v2_table(run_name).pairs, _v2_measured_resolution_bands(run_name), strict=True)
        for pair, (low, high) in pairs:
            assert low <= pair.rs <= high, (
                run_name,
                pair.earlier.name,
                pair.later.name,
                pair.rs,
                low,
                high,
            )
