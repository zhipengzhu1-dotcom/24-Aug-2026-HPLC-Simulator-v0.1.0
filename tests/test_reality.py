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
    LAB_CAMPAIGN27_RUNS,
    LAB_CAMPAIGN27_TR,
    LAB_CAMPAIGN27_WASH_ELUTED,
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
    LAB_STAMPED,
    LAB_STAMPED_IN_BRACKET,
    LAB_UNSTAMPED,
    LAB_W_HALF_ULP,
)
from validation2_data import (
    VALIDATION2_HELD_OUT,
    VALIDATION2_HELD_OUT_2026_09_03,
    VALIDATION2_MEASURED_AREA,
    VALIDATION2_MEASURED_TR,
    VALIDATION2_MEASURED_W_HALF,
    VALIDATION2_METHOD,
    VALIDATION2_PEAKS,
    VALIDATION2_REPEATABILITY_TR,
    VALIDATION2_REPEATABILITY_W_HALF,
    VALIDATION2_REPLICATE_BLOCK,
    VALIDATION2_RUN1,
    VALIDATION2_RUN2,
    VALIDATION2_RUN3_DETERMINATIONS,
    VALIDATION2_RUNS_BY_NAME,
    VALIDATION2_SOURCE_FILES,
    VALIDATION2_STAMPED,
    VALIDATION2_STAMPED_IN_BRACKET,
    VALIDATION2_TR_GRANULARITY,
    VALIDATION2_UNSTAMPED,
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

# SPEC §10 item 3(b): no unstamped run exceeds this mean |ΔtR|, in percent, **on either
# sample** — which is why it sits here rather than inside one sample's block. Re-pinned
# by #55 from the provisional 0.4 (breached by three-peak run 3 at 0.42 % since the
# 0.525 re-baseline) to 0.5 — layer 3's median bar on the den Uijl sets, borrowed as a
# mean here so one number serves the reference data and the bench data. Largest
# unstamped today: three-peak run 3 at 0.42 %, four-peak E1 at 0.14 %; the per-run
# tripwires in each sample's block are the tighter guard. Named `_V2_UNSTAMPED_CEILING_
# PERCENT` and kept in the four-peak block until #75 wired the three-peak runs onto it.
_UNSTAMPED_CEILING_PERCENT = 0.5


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
        # tighter regression guard: at t0 = 0.525 these sit at 0.42% and 0.34% (0.35% and
        # 0.26% at the former 0.6), so a drift to 1.9% would clear the contract without
        # anyone noticing.
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
    """SPEC §10's residual note: +0.42% at tG = 25, −0.34% at tG = 60.

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

# Under the shipped convention Unknown-1's implied N is constant to 1.2% across a
# fourfold steepness range (0.92% at the former t0 = 0.6) — at the ±1.5% quantisation
# floor of its own widths, i.e. as tight as this data can resolve. 2% is that floor with
# a little room. The rivals scatter 3.8% (base-10 slip), 7.2% (over-compressed mirror)
# and 9.4% (no compression) at 0.525, against 5–13% at 0.6: the re-baseline narrowed
# the base-10 slip's margin from ~5× to ~3× the shipped scatter, which is why the floor
# below sits at 3% and the test also asks for more than twice the shipped value.
_PLATE_COUNT_CONSTANCY_BAR = 2.0
_RIVAL_SCATTER_FLOOR = 3.0

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
    so the 1.2% the shipped convention achieves is at the floor of what these widths
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

# Held-out W½ with a fitted N: 1.00–1.17× measured at t0 = 0.525 (0.99–1.16× at the
# former 0.6; research doc §0.2), against 0.71–0.95× with the geometry default. The
# band has margin; the sharper claim is per-peak: fitted is closer to measured than
# the default in every case but one, pinned below.
_FITTED_WIDTH_BAND = (0.9, 1.25)
# The one exception the re-baseline produced: Unknown-3 at tG = 60, where the fitted N
# reads 1.067× and the default 0.946× — the default is nearer by 0.013. At 0.6 the
# fitted N won every case; a 12.5% change in t0 moves the fitted N ~2.5% and this pair
# was the closest contest. Pinned by name so the claim above stays exactly as true as
# it is.
_DEFAULT_WIDTH_WINS = {("tG60", "Unknown-3")}

# Held-out Rs with a fitted N: 0.89–0.95× measured — slightly pessimistic now, where
# the default was 1.15–1.37× optimistic.
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
    fourfold range of tG; Unknown-3's two scouting widths disagree by 12%. That is a
    different number from the one §2.4 of plate-count-from-widths.md discusses — its
    N being 1.6× the other compounds', read there as intrinsic because its peaks are
    the narrowest — but it is the same peak and the same question of whether its
    widths are trustworthy. The engine reports the ratio; the threshold is
    diagnostics work (ticket #20), and these are the numbers it will be drawn against.
    """
    ratios = [fit.plate_count.ratio for fit in _lab_fits() if fit.plate_count is not None]

    # At the former t0 = 0.6: 1.011 / 1.074 / 1.162. Unknown-1's ratio crossed 1 with
    # the re-baseline — the two widths now disagree by 2% the other way.
    assert ratios == pytest.approx([0.978, 1.038, 1.121], abs=0.002)


@pytest.mark.parametrize(
    ("run_name", "target"),
    [("tG25", LAB_RUN3), ("tG60", LAB_RUN4)],
    ids=["tG25-confirmation", "tG60-extrapolation"],
)
def test_fitted_plate_counts_predict_the_held_out_widths(run_name: str, target: Run) -> None:
    """Criterion 1's width half: fit N on runs 1–2, predict W½ at a run never seen.

    The default N is a geometry estimate and reads as one (the test above this block
    pins it at 0.6–1.0× measured, every peak, every run). A fitted N lands the
    held-out widths at 1.00–1.17× — and, peak by peak, closer than the default in every
    case but the one `_DEFAULT_WIDTH_WINS` names, where the two are 0.067 and 0.054 out.
    """
    fitted = _width_ratios(target, run_name, fitted=True)
    default = _width_ratios(target, run_name, fitted=False)

    low, high = _FITTED_WIDTH_BAND
    assert all(low <= ratio <= high for ratio in fitted.values()), fitted
    for name, ratio in fitted.items():
        fitted_wins = abs(ratio - 1.0) < abs(default[name] - 1.0)
        assert fitted_wins == ((run_name, name) not in _DEFAULT_WIDTH_WINS), (
            name,
            ratio,
            default[name],
        )


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

    Fit N from runs 1–2, resolve at a run never seen: Rs comes out at 0.89–0.95× measured
    on both held-out conditions, 1.6–12.7 Rs units low at Rs 30–116, where the default
    was 12–24 units high. The residual is slightly pessimistic and no longer a common
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
    """The extrapolation run does resolve it: −7.5% and −11%, outside a ±0.5% band.

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

# Every condition the fit never saw: SPEC §10's two (run3, run4) and #46's five. The
# v0.1 claims (near-rigid residual, the dwell argument, the export-precision band) stay
# on the first two; the coarse bar, Rs ± 0.3, the critical pair, the widths and the
# pinned residual run on all seven.
_V2_ALL_HELD_OUT = VALIDATION2_HELD_OUT + VALIDATION2_HELD_OUT_2026_09_03
_V2_IDS = ["run3-tG-interpolation", "run4-phi0-shifted"]
_V2_2026_09_03_IDS = [
    "run5-trap-hold",
    "run6-phi0-raised",
    "E1-axis-test",
    "run3-rep2",
    "run3-rep3",
]
_V2_ALL_IDS = _V2_IDS + _V2_2026_09_03_IDS

# Regression tripwires on mean |ΔtR| in percent, set just above where each run sits at
# t0 = 0.525 (0.11 / 0.23 / 1.51 / 0.26 / 0.14 / 0.12 / 0.12; at the former 0.6 they were
# 0.07 / 0.18 / 1.33 / 0.20 / 0.10 / 0.08 / 0.08), not at the 2 % contract.
_V2_TR_TRIPWIRE = {
    "run3": 0.15,
    "run4": 0.25,
    "run5": 1.6,
    "run6": 0.30,
    "E1": 0.15,
    "run3_rep2": 0.15,
    "run3_rep3": 0.15,
}
# #46 item 7: the worst Rs miss per run, pinned within half a hundredth of where it was
# measured at t0 = 0.525 (0.040 / 0.047 / 0.054 / 0.116 / 0.029 / 0.040 / 0.045). run5's
# miss grew fivefold from the 0.011 it had at 0.6: in the post-gradient hold t0 enters
# the retention time directly instead of being absorbed by the fit, and the widths there
# are already 6–9 % under. Still 2.6–5.6× inside ±0.3 (run6 / run5).
_V2_RS_TRIPWIRE = {
    "run3": 0.045,
    "run4": 0.05,
    "run5": 0.06,
    "run6": 0.12,
    "E1": 0.03,
    "run3_rep2": 0.045,
    "run3_rep3": 0.05,
}
# Fitted-N widths against measured. On a ramp the fit lands within 1–3 % of every width;
# in run5's hold it under-predicts every width by 6–9 % — the first measurement of the
# width model at post-gradient elution, pinned as its own band so a fix would show.
_V2_FITTED_WIDTH_BAND = {
    "run3": (0.98, 1.02),
    "run4": (0.98, 1.02),
    "run5": (0.90, 0.95),
    "run6": (0.98, 1.03),
    "E1": (0.98, 1.02),
    "run3_rep2": (0.98, 1.02),
    "run3_rep3": (0.97, 1.02),
}
# #46 item 3, layer two: each run's mean signed residual, predicted − measured in
# minutes, pinned where it was measured at t0 = 0.525 (#24's re-baseline, 2026-09-03).
# Research #52 §3's values at the former 0.6 were 0.0122 / 0.0277 / −0.4501 / 0.0339 /
# 0.0174 / 0.0130 / 0.0140: every on-ramp run moved late by 0.007–0.010 min, more than
# the 0.002 min floor, which is exactly why these are pinned rather than bounded.
_V2_PINNED_MEAN_OFFSET = {
    "run3": 0.0189,
    "run4": 0.0364,
    "run5": -0.5112,
    "run6": 0.0441,
    "E1": 0.0258,
    "run3_rep2": 0.0196,
    "run3_rep3": 0.0206,
}
# The unstamped ceiling of SPEC §10 item 3(b) is `_UNSTAMPED_CEILING_PERCENT`, at the
# top of this file: #55 set one number for both samples, so both blocks read the same
# constant. Largest unstamped on this sample: E1 at 0.14 %.
# How far the four per-peak tR offsets may spread within one run, in minutes.
# run3 is rigid to within the 0.001 min export step; run4 carries a real slope.
_V2_OFFSET_SPREAD = {"run3": 0.002, "run4": 0.004}
# The runs whose predicted Rs falls *outside* the repeatability band, with how far below
# its lower edge each pair sits (min, max). Only run5, since the re-baseline to 0.525:
# 0.009 / 0.018 / 0.020. Every run absent from this table is asserted inside the band.
_V2_REPEATABILITY_SHORTFALL = {"run5": (0.005, 0.025)}


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


def _v2_predicted_and_measured(run_name: str) -> tuple[list[float], list[float]]:
    """Predicted and measured tR (min) at a held-out run, both in fixture order."""
    gradient = VALIDATION2_RUNS_BY_NAME[run_name].gradient
    predicted = [
        predict_retention(fit.params, VALIDATION2_METHOD, gradient).t_r for fit in _v2_fits()
    ]
    measured = [VALIDATION2_MEASURED_TR[run_name][peak.name] for peak in VALIDATION2_PEAKS]
    return predicted, measured


def _v2_offsets(run_name: str) -> list[float]:
    """Predicted − measured tR (min) at a held-out run, in fixture order."""
    predicted, measured = _v2_predicted_and_measured(run_name)
    return [p - m for p, m in zip(predicted, measured, strict=True)]


def _v2_mean_magnitude(run_name: str) -> float:
    """Mean |ΔtR| in percent at a held-out run — the coarse bar's statistic."""
    return fmean(abs(e) for e in _signed_percent_errors(*_v2_predicted_and_measured(run_name)))


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


@pytest.mark.parametrize("run_name", sorted(VALIDATION2_SOURCE_FILES))
def test_validation2_fixtures_match_the_source_csvs(run_name: str) -> None:
    """Every fixture cell, re-read from the CSV the instrument wrote.

    The `den_uijl` fixtures get this treatment against the research doc; these get it
    against the raw exports, which is the stronger version — there is no transcription
    step in between to agree with. It reads the embedded `Gradient` programme table
    rather than the `tG_min` header on purpose: run 3's header arrived reading 40 when
    the programme said 20, and a fixture trusted to the header would have scored the
    held-out run against the wrong gradient while every number still looked plausible.
    The header cannot identify run 4 at all — it and run 3 are both tG = 20.

    Two shapes the 2026-09-03 files added: `E4_Run3.csv` carries two peak tables under
    `Replicate-N` headings above one programme, so the block is chosen by name; and
    run 5's programme rises again after its hold (the 95 %B wash), so the ramp ends at
    the first plateau after it starts, not at the programme's maximum %B.
    """
    path = _VALIDATION2_DIR / VALIDATION2_SOURCE_FILES[run_name]
    text = path.read_text(encoding="utf-8-sig")
    rows = [line.strip().split(",") for line in text.splitlines() if line.strip(", ")]

    block = VALIDATION2_REPLICATE_BLOCK.get(run_name)
    if block is not None:
        start = next(i for i, r in enumerate(rows) if r[0] == block)
        stop = next(
            (i for i, r in enumerate(rows) if i > start and r[0].startswith("Replicate-")),
            len(rows),
        )
        peaks = {r[0]: r for r in rows[start:stop] if r[0].startswith("Unknown-")}
    else:
        peaks = {r[0]: r for r in rows if r[0].startswith("Unknown-")}
    programme = [r for r in rows if r[0].isdigit()]

    # The gradient the run was actually acquired with: φ0 holds until the ramp starts,
    # and the ramp ends at the first step after which %B stops rising.
    times = [float(r[1]) for r in programme]
    percent_b = [float(r[4]) for r in programme]
    flows = {float(r[2]) for r in programme}
    ramp_start = next(i for i in range(len(percent_b)) if percent_b[i + 1] > percent_b[i])
    ramp_end = next(
        i for i in range(ramp_start + 1, len(percent_b)) if percent_b[i + 1] <= percent_b[i]
    )
    gradient = VALIDATION2_RUNS_BY_NAME[run_name].gradient

    assert flows == {VALIDATION2_METHOD.flow}
    assert gradient.t_init == pytest.approx(times[ramp_start], abs=0.0)
    assert gradient.t_gradient == pytest.approx(times[ramp_end] - times[ramp_start], abs=0.0)
    # φ is a fraction internally and %B only at the boundary, so the file's %B is
    # converted, not the fixture's φ: 0.55 × 100 is 55.00000000000001, 55 / 100 is 0.55.
    assert gradient.phi0 == pytest.approx(percent_b[ramp_start] / 100.0, abs=0.0)
    assert gradient.phif == pytest.approx(percent_b[ramp_end] / 100.0, abs=0.0)

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


@pytest.mark.parametrize("run_name", _V2_ALL_HELD_OUT, ids=_V2_ALL_IDS)
def test_validation2_held_out_runs_are_predicted_within_the_trust_bar(run_name: str) -> None:
    """Fit tG = 15/40 at 5 → 95 %B, predict seven runs the fit never saw.

    run3 varies only tG and lands at 0.11% mean — the tightest held-out retention
    result in the project, against a 2% bar. run4 also moves φ0 to 15 %B, an axis the
    scouting pair holds fixed, and costs a factor of 2 (0.23%). The 2026-09-03 runs
    (#46 item 3, layer one) follow: run6 at 25 %B (0.26%), E1 (0.14%), run3's two
    replicates (0.12%), and run5, whose peaks the engine puts in the post-gradient hold
    and flags low-confidence, still inside the bar at 1.51%. Every tripwire sits just
    above its run for the usual reason: a drift to 1.9% would clear the contract with
    nobody noticing.
    """
    predicted, measured = _v2_predicted_and_measured(run_name)

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
    growth on independent data — +0.019 min at run3, +0.036 min at run4 — and rules out
    that explanation, which the parent dataset could not do on its own.

    **What this does not say.** run4 differs from run3 in φ0, Δφ *and* s* together (see
    the section preamble), so the growth cannot be attributed to φ0, or to any one of
    the three. The claim here is only that the two conditions differ and that no dwell
    value spans them.

    The argument is one derivative. For these strongly-retained peaks ∂tR/∂τ = 1 − k_e/k0
    is within 0.3% of 1 at both conditions (worst 0.261%, run4), so *any* dwell error
    shifts both runs by the same number of minutes. Two offsets differing by a factor
    of 1.9 therefore cannot both come from one wrong dwell — closing the 0.0175 min gap
    between them by dwell alone would take δτ ≈ 9.5 min, about 3.8 mL of V_D (research
    #52 §2.1 worked it at the former t0 = 0.6: 0.0155 min, 9.7 min, 3.9 mL).

    The derivative is asserted to the 0.3% the sentence above claims, not looser: a
    tolerance wider than the claim would let the claim rot while the test still passed.
    (The bound was written as 0.2% before it was ever asserted; tightening the test to
    match found run4 at 0.223%, and the re-baseline to 0.525 moved it to 0.261% — each
    time the prose was corrected, not the tolerance widened past the claim.)

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
        assert all(s == pytest.approx(1.0, abs=0.003) for s in sensitivities), (
            run_name,
            sensitivities,
        )

    shifted = fmean(_v2_offsets("run4"))
    baseline = fmean(_v2_offsets("run3"))
    assert shifted > baseline, (baseline, shifted)
    # Far larger than the ~1% of itself that a common dwell term could move between them.
    assert shifted - baseline > 10.0 * VALIDATION2_TR_GRANULARITY, (baseline, shifted)


@pytest.mark.parametrize("run_name", _V2_ALL_HELD_OUT, ids=_V2_ALL_IDS)
def test_validation2_fitted_plate_counts_predict_the_held_out_widths(run_name: str) -> None:
    """Widths at 0.988–1.009× measured on runs 3 and 4, against the 0.99–1.16× the parent
    sample gives.

    Rs needs the widths as much as the separations, so this is half the ±0.3 result.
    The bands are deliberately tighter than `_FITTED_WIDTH_BAND`: on this sample the
    fitted N reproduces the held-out widths to within the export's own precision on
    runs 3, 4 and E1, and within 3 % on run6 and the replicates; recording that as
    0.9–1.25× would throw the finding away. run5's band is a different fact: in the
    55 %B hold every width comes out 6–9 % under, pinned as its own band.
    """
    ratios = {
        peak.name: peak.width.w_half / VALIDATION2_MEASURED_W_HALF[run_name][peak.name]
        for peak in _v2_table(run_name).peaks
    }

    low, high = _V2_FITTED_WIDTH_BAND[run_name]
    assert all(low <= ratio <= high for ratio in ratios.values()), ratios


@pytest.mark.parametrize("run_name", _V2_ALL_HELD_OUT, ids=_V2_ALL_IDS)
def test_validation2_critical_pair_is_identified_correctly(run_name: str) -> None:
    """The decision-relevant output: which pair a chromatographer has to work on.

    Unknown-3/Unknown-4 is both the predicted and the measured minimum at every held-out
    condition, and it is a real contest here — the runner-up sits at 2.6, close enough
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


@pytest.mark.parametrize("run_name", _V2_ALL_HELD_OUT, ids=_V2_ALL_IDS)
def test_the_rs_bar_of_spec_10_is_met_on_the_near_critical_pair(run_name: str) -> None:
    """SPEC §10's `Rs ± 0.3`, met at seven held-out conditions on a near-critical pair.

    The counterpart of `test_the_rs_bar_of_spec_10_is_still_unmet_with_fitted_plate_counts`:
    that one pins why the Rs 30–116 sample cannot answer this question, this one answers
    it. run3 gives 2.56 / 5.14 / 1.75 against measured 2.57 / 5.18 / 1.75; run4, with φ0
    moved to 15 %B, gives 2.59 / 5.18 / 1.78 against 2.64 / 5.20 / 1.77. Every pair at
    both conditions is inside ±0.3 by more than an order of magnitude — worst miss 0.05 —
    and the critical pair itself sits at Rs 1.75–1.78, in the 1–2 band where ±0.3 is the
    tolerance a method decision actually turns on.

    #46 item 7 extends it to a raised start (run6, 0.116 worst), a hold (run5, 0.054 —
    peaks leaving in a hold move together, so a 1.5 % retention miss costs the Rs a
    fifth of the bar), the axis test (E1, 0.029) and run3's replicates; the worst
    miss per run is pinned as a tripwire.

    Scope, so the SPEC sentence this backs is not read wider than the evidence: one
    sample, one gradient axis and one composition axis, one post-gradient hold.
    """
    table = _v2_table(run_name)
    measured = _v2_measured_resolutions(run_name)

    misses = [abs(pair.rs - m) for pair, m in zip(table.pairs, measured, strict=True)]
    assert all(miss <= _RS_BAR for miss in misses), misses

    assert max(misses) <= _V2_RS_TRIPWIRE[run_name], misses


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


# --- #46's bar on the 2026-09-03 runs (issue #53's bench session) ---
#
# Five more conditions the fit never saw, on the same sample and the same scouting pair:
# the trap run (peaks in a hold), a raised start, the φ0-vs-Δφ axis test, and run3 twice
# more. The coarse bar, Rs ± 0.3, the critical pair and the widths run on them above,
# alongside runs 3 and 4. What is added here is the rest of #46's resolution, items 3, 5
# and 10 — the pinned residual, the stamp's honesty, and the repeatability floor with the
# Rs band it sets — each as a measurement. E1's reading (φ0 at ~60/40, #55) is SPEC §6
# item 7's; which runs the app's diagnostics stamp is a fixture fact here, and the
# app-level fire/silent table (SPEC §10 item 2) is left to the build.


@pytest.mark.parametrize("run_name", _V2_ALL_HELD_OUT, ids=_V2_ALL_IDS)
def test_validation2_mean_residual_is_pinned_within_the_repeatability_floor(run_name: str) -> None:
    """#46 item 3, layer two: each run's mean signed residual, pinned where it was measured.

    Predicted − measured, mean over the four peaks, in minutes, within E4's floor of
    0.002 min — so a change to the engine that moves any run by more than the instrument
    can repeat is a failing test, whichever direction it moves. This is the tolerance
    #46 item 10 says replaces the interim ± 0.10 %; on a 16 min peak 0.002 min is 0.012 %.
    """
    pinned = _V2_PINNED_MEAN_OFFSET[run_name]
    assert fmean(_v2_offsets(run_name)) == pytest.approx(pinned, abs=VALIDATION2_REPEATABILITY_TR)


def test_validation2_repeatability_floor_is_what_e4_measured() -> None:
    """E4 (#53): run3's condition three times, and how far the instrument repeats itself.

    Every peak's tR spread across the three determinations is at most 0.002 min, and
    every W½ spread is at most one export step. The constants the other tests lean on are
    asserted against the data here, not just typed in next to it. Before E4, every ratio
    in the research rested on single injections and the floor was a literature ±0.002.
    """

    def spread(table: dict[str, dict[str, float]], name: str) -> float:
        values = [table[run][name] for run in VALIDATION2_RUN3_DETERMINATIONS]
        return max(values) - min(values)

    t_r_spreads = [spread(VALIDATION2_MEASURED_TR, peak.name) for peak in VALIDATION2_PEAKS]
    w_half_spreads = [spread(VALIDATION2_MEASURED_W_HALF, peak.name) for peak in VALIDATION2_PEAKS]

    assert all(s <= VALIDATION2_REPEATABILITY_TR + 1e-12 for s in t_r_spreads), t_r_spreads
    assert all(s <= VALIDATION2_REPEATABILITY_W_HALF + 1e-12 for s in w_half_spreads), (
        w_half_spreads
    )
    # And the floor is real, not slack: at least one peak uses all of it.
    assert max(t_r_spreads) == pytest.approx(VALIDATION2_REPEATABILITY_TR, abs=1e-12), t_r_spreads


@pytest.mark.parametrize("run_name", _V2_ALL_HELD_OUT, ids=_V2_ALL_IDS)
def test_validation2_resolution_is_inside_the_repeatability_band(run_name: str) -> None:
    """#46 item 10: the width replicates set the band on every Rs tripwire.

    `test_validation2_resolution_is_inside_the_measurement_band` asks whether the
    prediction is inside what the *export's rounding* allows, and runs 5 and 6 are not
    (run6 by 0.013–0.045 below the band on every pair). This asks the question the
    instrument can
    actually answer: inside what the *instrument's repeatability* allows — E4's 0.002 min
    on tR and one export step on W½. Every predicted Rs on the six on-ramp conditions
    is, run6 included. run5 is not, since the re-baseline to t0 = 0.525: all three of its
    pairs sit 0.009–0.020 below the band's lower edge (0.033–0.054 below the measured
    point estimate), where at 0.6 every one was inside. In the
    post-gradient hold t0 is not absorbed by the fit, so the trap run is the one
    condition whose Rs residual the replicates *can* resolve — pinned in
    `_V2_REPEATABILITY_SHORTFALL` with its size, so the sharper form of "Rs ± 0.3 is
    met" reads exactly as wide as the evidence: every on-ramp condition, not every one.
    """
    bands = _resolution_bands(
        VALIDATION2_MEASURED_TR[run_name],
        VALIDATION2_MEASURED_W_HALF[run_name],
        width_ulp=VALIDATION2_REPEATABILITY_W_HALF,
        t_r_ulp=VALIDATION2_REPEATABILITY_TR / 2.0,
    )
    pairs = list(zip(_v2_table(run_name).pairs, bands, strict=True))
    if run_name in _V2_REPEATABILITY_SHORTFALL:
        least, most = _V2_REPEATABILITY_SHORTFALL[run_name]
        shortfalls = [low - pair.rs for pair, (low, _) in pairs]
        assert all(least <= shortfall <= most for shortfall in shortfalls), shortfalls
        return
    for pair, (low, high) in pairs:
        assert low <= pair.rs <= high, (pair.earlier.name, pair.later.name, pair.rs, low, high)


def test_validation2_residual_at_a_raised_phi0_is_not_below_the_scouting_phi0() -> None:
    """#46 item 3's one structural claim per sample — and what it does not claim.

    Starting above the scouting pair's 5 %B has not, on this sample, made the residual
    smaller: run4 (15 %B) and run6 (25 %B) both sit above run3 (5 %B). The doubling rule
    (×2.1 per 10 %B) is *not* asserted — it fails here (+0.11 / +0.23 / +0.26 %: one step
    up, then flat) while holding on the three-peak sample, and the bar records only the
    ordering both samples share.
    """
    baseline = fmean(_v2_offsets("run3"))
    for run_name in ("run4", "run6"):
        assert fmean(_v2_offsets(run_name)) >= baseline, (run_name, baseline)


def test_validation2_trap_run_elutes_every_peak_in_the_hold_and_says_so() -> None:
    """run5: the engine's regime flag, on the one run that exercises it.

    15 → 55 %B at tG 25 puts s* 0.35 window-widths below the scouting bracket, and the
    engine predicts all four peaks *after* the ramp ends, in the 55 %B hold, flagged
    low-confidence. The measured file agrees: every apex is later than the 25.5 min the
    ramp ends at. This is #46 item 4's regime row at the engine level; the app-level
    diagnostics table is not asserted here.
    """
    gradient = VALIDATION2_RUNS_BY_NAME["run5"].gradient
    ramp_end = gradient.t_init + gradient.t_gradient
    for fit, peak in zip(_v2_fits(), VALIDATION2_PEAKS, strict=True):
        result = predict_retention(fit.params, VALIDATION2_METHOD, gradient)
        assert result.regime == "post_gradient", peak.name
        assert result.low_confidence, peak.name
        assert VALIDATION2_MEASURED_TR["run5"][peak.name] > ramp_end, peak.name


def test_validation2_in_bracket_stamped_runs_miss_by_more_than_every_unstamped_run() -> None:
    """SPEC §10 item 3, as #55 re-pinned it: the falsifiable content of the stamp.

    (a) Every run strong on diagnostic 7 whose s* is inside the scouting bracket has a
    mean |ΔtR| above every run that draws no stamp — today 0.23 % (run4) against 0.14 %
    (E1) at the boundary — which is what makes *indicative, not decision-grade* honest.
    Scoped to in-bracket runs because a run carrying both guards is not ordered by
    |ΔtR| (three-peak run 6's two biases cancel); run5 is stamped but its s* sits
    outside the bracket, so it is not ordered (its residual is the hold's in any case).
    (b) No unstamped run exceeds 0.5 % mean |ΔtR| — layer 3's bar borrowed (a median
    there, a mean here), re-pinned from the provisional 0.4 by #55.

    Which runs are stamped is a fixture fact (`VALIDATION2_STAMPED`), by the two guards
    #44 decided. That the app's diagnostics draw it on exactly those runs is SPEC §10
    item 2, left to the build; it is not asserted here.
    """
    assert set(VALIDATION2_STAMPED_IN_BRACKET) < set(VALIDATION2_STAMPED)
    ordered = {run: _v2_mean_magnitude(run) for run in VALIDATION2_STAMPED_IN_BRACKET}
    unstamped = {run: _v2_mean_magnitude(run) for run in VALIDATION2_UNSTAMPED}

    assert min(ordered.values()) > max(unstamped.values()), (ordered, unstamped)
    assert max(unstamped.values()) <= _UNSTAMPED_CEILING_PERCENT, unstamped


# --- campaign #27: the three-peak sample's gradient-freedom runs (SPEC §10, #75) ---
#
# The four-peak block above pins SPEC §10's v0.2 bar on one sample. These three runs are
# the same bar on the other one, and they are the harder half: the three-peak sample is
# where the φ0-dependent residual is largest (0.42 → 0.82 → 1.67 % at φ0 = 5 / 15 / 25
# %B) and where run 6 pairs a shallow s* with a raised start so the two biases cancel.
# Measured on 2026-09-02 (#27), re-scored at t0 = 0.525 by #24 and tabulated on #55;
# until #75 they sat in `lab_data` unasserted, so nothing failed if they drifted.
#
# The fit is always the same one every other three-peak claim uses: run1 + run2, tG =
# 15/45 at 5 → 95 %B. Scouting s* bracket [0.0105, 0.0315]; s* = t0·Δφ/tG is the only
# way the candidate gradient enters the elution composition (research doc §7).

# Every three-peak condition the fit never saw, keyed the way #55's table names them.
# runs 3 and 4 are the v0.1 pair (asserted for their own reasons above); they are here
# because item 3(a)'s ordering and item 3(b)'s ceiling are claims *across* runs.
_C27_HELD_OUT: dict[str, tuple[Run, dict[str, float]]] = {
    "run3": (LAB_RUN3, LAB_MEASURED_TG25),
    "run4": (LAB_RUN4, LAB_MEASURED_TG60),
    "run5": (LAB_CAMPAIGN27_RUNS["run5"], LAB_CAMPAIGN27_TR["run5"]),
    "run6": (LAB_CAMPAIGN27_RUNS["run6"], LAB_CAMPAIGN27_TR["run6"]),
    "run7": (LAB_CAMPAIGN27_RUNS["run7"], LAB_CAMPAIGN27_TR["run7"]),
}

# The runs #75 wires: SPEC §10 item 1's held-out set minus the two v0.1 runs.
_C27_CAMPAIGN_RUNS = ("run5", "run6", "run7")
_C27_IDS = ["run5-phi0-15-s-star-matched", "run6-ramp-peaks-only", "run7-phi0-25"]

# Which runs draw the *indicative, not decision-grade* stamp is a fixture fact, and it
# lives in `lab_data` (`LAB_STAMPED` / `LAB_UNSTAMPED` / `LAB_STAMPED_IN_BRACKET`)
# exactly as `VALIDATION2_STAMPED` lives in `validation2_data` — the reality layer reads
# it rather than deciding it, and never imports the app to find out.

# The runs whose *only* departure from the scouting pair is a raised φ0: run 5 and run 7
# keep φf at 95 %B and move the start to 15 and 25 %B. That is the comparison SPEC §10
# item 1's monotonicity claim is about, and it is a different scoping from item 3(a)'s
# in-bracket set even though the two coincide today. Run 6 raises φ0 as well, but it also
# drops φf to 55 %B and so moves s*; its +0.039 min sits *below* run 3's +0.068, which is
# exactly why the claim is scoped to a raised start and not to every run above 5 %B.
# `test_campaign27_raised_start_runs_are_the_ones_that_only_move_phi0` derives this
# membership from the gradients rather than trusting the tuple.
_C27_RAISED_START = ("run5", "run7")

# Regression tripwires on mean |ΔtR| in percent, set just above where each run sits at
# t0 = 0.525 (0.8154 / 0.2070 / 1.6706), not at the 2 % contract — a drift to 1.9 % would
# clear the contract with nobody noticing. The 0.6-era figures were 0.73 (run 5) and 1.52
# (run 7), research doc §1.3; run 6 has no 0.6-era figure on record.
_C27_TR_TRIPWIRE = {"run5": 0.85, "run6": 0.22, "run7": 1.75}

# SPEC §10 item 1, layer two: each run's mean signed residual, predicted − measured in
# minutes, pinned where it was measured at t0 = 0.525 (#24's re-baseline, tabulated on
# #55). The 0.6-era values were +0.1025 (run 5) and +0.1802 (run 7), research doc §1.3.
# The four-peak sample pins these within E4's measured repeatability floor; this sample
# has no replicates, so it keeps #46's interim ± 0.10 % — of the run's own retention
# times, not of the residual, which is what `_C27_PIN_TOLERANCE_FRACTION` applies.
_C27_PINNED_MEAN_OFFSET = {"run5": 0.1146, "run6": 0.0387, "run7": 0.1981}
_C27_PIN_TOLERANCE_FRACTION = 0.001


def _c27_fits() -> list[FitResult]:
    """The three-peak sample's one fit: run1 + run2, tG = 15/45 at 5 → 95 %B."""
    return fit_peaks(LAB_MEASURED_PEAKS, LAB_METHOD, LAB_RUN1, LAB_RUN2)


def _c27_scored_peaks(run_name: str) -> list[str]:
    """The peaks of a three-peak held-out run that the single-segment engine may score.

    Run 6 ends at 55 %B, where Unknown-3 never leaves the hold; the 46.8 min on file is
    the 45.1 min wash step bringing it off under a two-segment programme (SPEC §10 item
    4(d), the walker's reality point). Two fixtures say so and both are applied: the tR
    table simply has no run6/Unknown-3 entry, and `LAB_CAMPAIGN27_WASH_ELUTED` names the
    pair and the reason. The second clause is inert while the first holds — deliberately
    so, because it is the clause that carries the *reason*, and it is what would keep the
    exclusion right if a later ticket put the 46.8 min reading into the tR table for the
    walker to score. The companion test pins both halves rather than either alone.
    """
    _, measured = _C27_HELD_OUT[run_name]
    return [
        peak.name
        for peak in LAB_MEASURED_PEAKS
        if peak.name in measured and (run_name, peak.name) not in LAB_CAMPAIGN27_WASH_ELUTED
    ]


def _c27_predicted_and_measured(run_name: str) -> tuple[list[float], list[float]]:
    """Predicted and measured tR (min) at a three-peak held-out run, in fixture order."""
    target, measured = _C27_HELD_OUT[run_name]
    scored = _c27_scored_peaks(run_name)
    predicted = [
        predict_retention(fit.params, LAB_METHOD, target.gradient).t_r
        for fit, peak in zip(_c27_fits(), LAB_MEASURED_PEAKS, strict=True)
        if peak.name in scored
    ]
    return predicted, [measured[name] for name in scored]


def _c27_offsets(run_name: str) -> list[float]:
    """Predicted − measured tR (min) at a three-peak held-out run."""
    predicted, measured = _c27_predicted_and_measured(run_name)
    return [p - m for p, m in zip(predicted, measured, strict=True)]


def _c27_mean_magnitude(run_name: str) -> float:
    """Mean |ΔtR| in percent at a three-peak held-out run — the coarse bar's statistic."""
    return fmean(abs(e) for e in _signed_percent_errors(*_c27_predicted_and_measured(run_name)))


def test_campaign27_scores_run6_on_its_ramp_peaks_only() -> None:
    """The exclusion the rest of this block depends on, asserted rather than assumed.

    Scoring run 6's Unknown-3 against the single-segment engine would be scoring a
    two-segment measurement: the engine puts it at ~110 min in the 55 %B hold and the
    wash brought it off at 46.8. Runs 5 and 7 keep all three peaks.
    """
    assert ("run6", "Unknown-3") in LAB_CAMPAIGN27_WASH_ELUTED
    assert _c27_scored_peaks("run6") == ["Unknown-1", "Unknown-2"]
    assert "Unknown-3" not in LAB_CAMPAIGN27_TR["run6"]
    for run_name in ("run5", "run7"):
        assert _c27_scored_peaks(run_name) == ["Unknown-1", "Unknown-2", "Unknown-3"]


@pytest.mark.parametrize("run_name", _C27_CAMPAIGN_RUNS, ids=_C27_IDS)
def test_campaign27_held_out_runs_are_predicted_within_the_trust_bar(run_name: str) -> None:
    """SPEC §10 item 1, layer one: the v0.1 coarse bar on the three-peak campaign runs.

    Fit tG = 15/45 at 5 → 95 %B, predict three conditions the fit never saw: run 5
    (15 → 95, tG 22.2 — s* matched to run 3, so the falsification test for "only s*
    matters") at 0.82 % mean, run 6 on its two ramp peaks at 0.21 %, run 7 (25 → 95) at
    1.67 %, all against a 2 % average and 5 % worst-case bar with order correct. Run 7's
    worst peak is 2.76 %, the largest single-peak miss anywhere in the project and still
    inside the bar. Each tripwire sits just above its run so drift shows.
    """
    predicted, measured = _c27_predicted_and_measured(run_name)

    magnitudes = [abs(error) for error in _signed_percent_errors(predicted, measured)]
    assert fmean(magnitudes) <= _LAB_AVERAGE_BAR
    assert max(magnitudes) <= _LAB_WORST_CASE_BAR
    assert _elution_order(predicted) == _elution_order(measured)

    assert fmean(magnitudes) <= _C27_TR_TRIPWIRE[run_name]


@pytest.mark.parametrize("run_name", _C27_CAMPAIGN_RUNS, ids=_C27_IDS)
def test_campaign27_mean_residual_is_pinned_within_the_interim_tolerance(run_name: str) -> None:
    """SPEC §10 item 1, layer two: each run's mean signed residual, pinned in minutes.

    +0.115 (run 5), +0.039 (run 6, ramp peaks) and +0.198 min (run 7) at t0 = 0.525.
    The four-peak sample pins these within E4's measured 0.002 min; this sample has no
    replicates, so the tolerance stays #46's interim ± 0.10 %, read as ± 0.10 % of the
    run's own measured retention times (0.015 / 0.021 / 0.015 min here). That is looser
    than the four-peak floor by design, and it is still far tighter than the coarse bar:
    a change that moved run 7 back to its 0.6-era +0.180 min would fail here.
    """
    measured = _c27_predicted_and_measured(run_name)[1]
    tolerance = _C27_PIN_TOLERANCE_FRACTION * fmean(measured)

    assert fmean(_c27_offsets(run_name)) == pytest.approx(
        _C27_PINNED_MEAN_OFFSET[run_name], abs=tolerance
    )


def test_campaign27_in_bracket_stamped_runs_miss_by_more_than_every_unstamped_run() -> None:
    """SPEC §10 item 3, on the three-peak sample, as #55 re-pinned it.

    (a) Every run strong on diagnostic 7 whose s* is inside the scouting bracket misses
    by more than every unstamped run — 0.82 % (run 5) and 1.67 % (run 7) against 0.42 %
    (run 3, in-window) and 0.34 % (run 4) — which is what makes *indicative, not
    decision-grade* honest. Run 6 is stamped and deliberately not ordered: its s* sits
    below the bracket and its two biases cancel at 0.21 %, below run 3. The four-peak
    sample makes the same claim at a much narrower margin (0.23 / 0.26 against 0.14).
    (b) No unstamped three-peak run exceeds 0.5 % mean |ΔtR| — run 3 at 0.42 % is the
    largest unstamped figure on either sample, so this sample is where the ceiling
    binds; run 4 is gentle on diagnostic 1 only, which does not stamp.

    Which runs are stamped is a fixture fact (`LAB_STAMPED`); that the app's diagnostics
    draw it on exactly those runs is SPEC §10 item 2, left to the build.
    """
    assert set(LAB_STAMPED_IN_BRACKET) < set(LAB_STAMPED)
    assert set(LAB_STAMPED) | set(LAB_UNSTAMPED) == set(_C27_HELD_OUT)
    assert not set(LAB_STAMPED) & set(LAB_UNSTAMPED)

    ordered = {run: _c27_mean_magnitude(run) for run in LAB_STAMPED_IN_BRACKET}
    unstamped = {run: _c27_mean_magnitude(run) for run in LAB_UNSTAMPED}

    assert min(ordered.values()) > max(unstamped.values()), (ordered, unstamped)
    assert max(unstamped.values()) <= _UNSTAMPED_CEILING_PERCENT, unstamped


def test_campaign27_raised_start_runs_are_the_ones_that_only_move_phi0() -> None:
    """What `_C27_RAISED_START` means, derived from the gradients rather than asserted.

    A raised-start run starts above the scouting pair's 5 %B and ends where the scouting
    pair ends, so φ0 is its only departure. Run 6 raises φ0 too but drops φf to 55 %B,
    which moves s* as well — a different comparison, and the next test says what that
    costs. This is deliberately *not* the same rule as item 3(a)'s s*-bracket membership,
    though the two pick out the same two runs today.
    """
    scouting_phi0 = LAB_RUN1.gradient.phi0
    scouting_phif = LAB_RUN1.gradient.phif
    raised = tuple(
        name
        for name, (run, _) in _C27_HELD_OUT.items()
        if run.gradient.phi0 > scouting_phi0 and run.gradient.phif == scouting_phif
    )

    assert raised == _C27_RAISED_START
    assert LAB_CAMPAIGN27_RUNS["run6"].gradient.phi0 > scouting_phi0
    assert LAB_CAMPAIGN27_RUNS["run6"].gradient.phif < scouting_phif


def test_campaign27_residual_at_a_raised_phi0_is_not_below_the_scouting_phi0() -> None:
    """SPEC §10 item 1's one structural claim per sample, on the three-peak sample.

    Starting above the scouting pair's 5 %B has not made the residual smaller: run 5
    (15 %B, +0.115 min) and run 7 (25 %B, +0.198) both sit above run 3 (5 %B, +0.068).
    Run 6 is not part of the claim and would break it if it were (+0.039 min, below run
    3): it moves φf and therefore s* as well, and its shallow-s* and raised-start biases
    partly cancel — which is the whole reason SPEC §10 item 1 scopes this to a raised
    start rather than to every run above 5 %B. The doubling rule (×2.1 per 10 %B) is
    *not* asserted: it holds on this sample and fails on the four-peak one, and the bar
    records only the ordering both share.
    """
    baseline = fmean(_c27_offsets("run3"))
    for run_name in _C27_RAISED_START:
        assert fmean(_c27_offsets(run_name)) >= baseline, (run_name, baseline)
    # And the run the claim excludes really is the one that would break it.
    assert fmean(_c27_offsets("run6")) < baseline
