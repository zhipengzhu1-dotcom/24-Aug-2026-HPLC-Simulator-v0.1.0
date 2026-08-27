"""SPEC §10 layer 3: the engine against measured reality.

Layers 1 and 2 (`test_retention.py`, `test_fit.py`) ask whether the math is
self-consistent and whether it reproduces a published reference implementation.
This layer asks the only question a chromatographer cares about: fit two
scouting runs, predict a *third* condition, and compare against what the
instrument actually did.

Every target gradient here is held out of the fit that predicts it.
"""

import math
from dataclasses import replace
from pathlib import Path
from statistics import fmean, median

import pytest

from den_uijl_data import SET_X, SET_Y, ScanningGradientSet
from hplcsim.fit import fit_peak, fit_peaks
from hplcsim.model import Method, Peak, Run
from hplcsim.retention import predict_retention
from hplcsim.width import band_compression_factor, peak_width
from lab_data import (
    LAB_MEASURED_PEAKS,
    LAB_MEASURED_TG25,
    LAB_MEASURED_TG60,
    LAB_METHOD,
    LAB_RUN1,
    LAB_RUN2,
    LAB_RUN3,
    LAB_RUN4,
)


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
# The engine's width model carries one unknown per compound (its plate count N) and
# one convention-dependent factor (G). Measured W½ therefore cannot test G directly:
# any single width can be matched by moving N. What *is* free of N is the ratio of a
# compound's two measured widths, since both runs share a column:
#
#     W½(run2)/W½(run1) = [G(run2)·(1 + k_e,run2)] / [G(run1)·(1 + k_e,run1)]
#
# That is the statistic these tests use. Its resolving power is bounded by the
# ±1.5–2.7% quantisation of W½ (LAB_W_HALF_ULP) and by N drifting with elution
# composition — the residual trends monotonically with φ_e in *every* candidate
# convention, which is the signature of the latter. Outcome recorded in research doc
# §5.4; these tests and that section must move together.

# The bar sits in the gap the data actually opened: the conventions it admits miss by
# at most 7.2%, the ones it rejects by at least 11.1%. Not a slack tolerance — a
# measured separation. Widening it past ~11% makes the calibration vacuous.
_G_CALIBRATION_BAR = 9.0


def _measured_width_ratios() -> list[float]:
    """Each lab peak's measured W½(run2)/W½(run1) — the N-free statistic."""
    ratios = []
    for peak in LAB_MEASURED_PEAKS:
        assert peak.w_half_run1 is not None and peak.w_half_run2 is not None
        ratios.append(peak.w_half_run2 / peak.w_half_run1)
    return ratios


def _ratio_errors(b_e_scale: float | None) -> list[float]:
    """Signed % error of the predicted W½ ratio against the measured one, per peak.

    ``b_e_scale`` scales the steepness fed to G: 1.0 is the shipped natural-log
    convention, ln 10 and 1/ln 10 are the two directions the 2.303 factor can slip,
    and ``None`` is the no-compression null (G = 1). Only the shipped case goes
    through :func:`peak_width`; the alternatives are reconstructed here because they
    are counterfactuals, not behaviour the engine offers.
    """
    errors = []
    for peak, measured in zip(LAB_MEASURED_PEAKS, _measured_width_ratios(), strict=True):
        params = fit_peak(peak, LAB_METHOD, LAB_RUN1, LAB_RUN2).params
        per_run = []
        for run in (LAB_RUN1, LAB_RUN2):
            width = peak_width(params, LAB_METHOD, run.gradient)
            assert width.g < 1.0, "both lab runs must elute in the compressed regime"
            if b_e_scale is None:
                g = 1.0
            elif b_e_scale == 1.0:
                g = width.g
            else:
                gradient = run.gradient
                b_e = LAB_METHOD.t0 * gradient.delta_phi * params.s_e / gradient.t_gradient
                g = band_compression_factor(b_e * b_e_scale, k0=params.k_at(gradient.phi0))
            per_run.append(g * (1.0 + width.k_e))
        errors.append((per_run[1] / per_run[0] / measured - 1.0) * 100.0)
    return errors


def test_lab_widths_exclude_the_no_compression_model() -> None:
    """Band compression is real, measurable, and not optional.

    Research doc §5.2 warns "do not hard-code G as a ~10% correction or drop it as
    negligible". This is the measurement behind that: with no compression *every*
    lab peak's width ratio falls short, and by more than the quantisation band — a
    bias, not scatter. The strongest statement this dataset supports.
    """
    errors = _ratio_errors(None)

    assert all(error < -_G_CALIBRATION_BAR for error in errors), errors


def test_lab_widths_exclude_the_base10_steepness_slip() -> None:
    """Reading the engine's natural-log b_e as if it were Snyder's base-10 b.

    The under-compressing direction of the project's #1 hazard. Excluded, but more
    weakly than G = 1: only the worst peak clears the bar outright, and what carries
    the finding is that all three miss in the same direction. The opposite direction
    (b_e × ln 10) survives — see the test below.
    """
    errors = _ratio_errors(1.0 / _LN10)

    assert max(abs(error) for error in errors) > _G_CALIBRATION_BAR, errors
    assert all(error < 0.0 for error in errors), f"not a one-sided bias: {errors}"


def test_the_calibrated_convention_reproduces_the_lab_width_ratios() -> None:
    """The shipped natural-log G is consistent with every measured lab width."""
    errors = _ratio_errors(1.0)

    assert max(abs(error) for error in errors) <= _G_CALIBRATION_BAR, errors


def test_the_lab_widths_do_not_by_themselves_settle_the_2303_factor() -> None:
    """The documented *limit* of this evidence — deliberately a fail-loudly guard.

    Research doc §10 item 5 asks for G to be checked "against a measured peak width
    once real data exists". It has been, and the honest answer is asymmetric: six
    widths quantised to 0.001 min exclude G = 1 and the base-10 steepness slip, but
    cannot separate the shipped convention from its over-compressed mirror image
    (b_e × ln 10), which lands *inside* the bar at 4.1%. That direction rests on
    §5.2's two primary sources, not on this dataset.

    If a richer dataset ever pushes the mirror variant outside the bar, this test
    fails — the signal to tighten §5.4 and promote it from "consistent with" to
    "confirms".
    """
    errors = _ratio_errors(_LN10)

    assert max(abs(error) for error in errors) <= _G_CALIBRATION_BAR, (
        "the over-compressed variant is now distinguishable from the shipped one — "
        f"research doc §5.4 understates this dataset and must be revisited: {errors}"
    )


def test_the_column_based_plate_count_underpredicts_real_widths() -> None:
    """The h = 2 default is a textbook estimate, not a fit — and reads as one.

    Real widths carry extra-column broadening and a real reduced plate height above
    2, so the default N over-estimates efficiency and predicted widths come out
    narrow. Pinned as a band rather than left implicit so that a units slip or a
    dropped √N (research doc §5.1's reconstruction caveat) cannot hide inside "the
    default is only an estimate".
    """
    ratios = []
    for peak in LAB_MEASURED_PEAKS:
        params = fit_peak(peak, LAB_METHOD, LAB_RUN1, LAB_RUN2).params
        for run, measured in ((LAB_RUN1, peak.w_half_run1), (LAB_RUN2, peak.w_half_run2)):
            assert measured is not None
            ratios.append(peak_width(params, LAB_METHOD, run.gradient).w_half / measured)

    assert all(0.6 <= ratio <= 1.0 for ratio in ratios), ratios
