"""The two-run fit (SPEC §3, research doc §3).

Layer 1 (SPEC §10) generates retention times from known parameters with the
independent scipy oracle in `numerics.py` and fits them back: nothing but the
LSS model itself is shared between the generator and the fit under test.
"""

import math

import pytest

from hplcsim.fit import fit_peak, fit_peaks
from hplcsim.model import (
    Gradient,
    Method,
    Peak,
    RetentionParams,
    Run,
    log10_k0_from_ln_k0,
    s_base10_from_s_e,
)
from hplcsim.retention import predict_retention
from lab_data import LAB_MEASURED_PEAKS, LAB_METHOD, LAB_RUN1, LAB_RUN2
from numerics import integrate_fundamental_equation

ROUND_TRIP_METHOD = Method(t0=0.6, t_dwell=0.9375, flow=0.4)
ROUND_TRIP_RUN1 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=15.0, t_init=0.5))
ROUND_TRIP_RUN2 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=45.0, t_init=0.5))

ROUND_TRIP_CASES = [
    # (label, log10 k0, S base-10) — spanning well-retained to low-k0 territory,
    # where the §3.2 closed form is worth 138% error and only the root-find survives.
    ("well-retained", 3.24, 4.99),
    ("very-well-retained", 4.76, 5.18),
    ("low-k0", 0.9, 4.0),
    ("steep-S", 2.5, 8.0),
]


@pytest.mark.parametrize(
    ("log10_k0", "s_base10"),
    [case[1:] for case in ROUND_TRIP_CASES],
    ids=[case[0] for case in ROUND_TRIP_CASES],
)
def test_synthetic_round_trip_recovers_known_parameters(log10_k0: float, s_base10: float) -> None:
    truth = RetentionParams(
        ln_k0=log10_k0 * math.log(10.0),
        s_e=s_base10 * math.log(10.0),
        phi_ref=ROUND_TRIP_RUN1.gradient.phi0,
    )
    peak = Peak(
        t_r_run1=integrate_fundamental_equation(truth, ROUND_TRIP_METHOD, ROUND_TRIP_RUN1.gradient),
        t_r_run2=integrate_fundamental_equation(truth, ROUND_TRIP_METHOD, ROUND_TRIP_RUN2.gradient),
    )

    fitted = fit_peak(peak, ROUND_TRIP_METHOD, ROUND_TRIP_RUN1, ROUND_TRIP_RUN2).params

    assert fitted.phi_ref == truth.phi_ref
    assert fitted.s_e == pytest.approx(truth.s_e, abs=1e-8)
    assert fitted.ln_k0 == pytest.approx(truth.ln_k0, abs=1e-8)


# --- SPEC §10 layer 2: the Guillarme et al. 2022 reference spreadsheet ---
#
# docs/research/validation-datasets.md §3. The spreadsheet fits by regressing the
# elution composition Ce against log β; over two runs that regression is exactly the
# closed-form seed of research doc §3.2, S = log10(β)/(Ce1 − Ce2), so the seed is
# comparable to the published fit to machine precision while the exact root-find is
# not (§3.2: they differ by the large-k0 approximation, a few tenths of a percent).
#
# Note: the spreadsheet's *predicted* retention times are not reproducible to 1e-6 by
# a correct engine — it hard-codes 2.303 where ln 10 belongs, worth ~4e-5 min. Its
# fitted intermediates below carry no such rounding.

GUILLARME_METHOD = Method(t0=0.2147435658361303, t_dwell=0.2, flow=0.5)
GUILLARME_RUN1 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=5.0), name="tG5")
GUILLARME_RUN2 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=15.0), name="tG15")

GUILLARME_CASES = [
    # (label, peak, Ce run 1, Ce run 2, two-point S, published regression S)
    #
    # Ce and the regression S are the spreadsheet's own stored values (§3.2 tables).
    # The two-point S is log10(3)/(Ce1 − Ce2) evaluated on those published Ce — the
    # spreadsheet's estimator restricted to the tG = 5 / 15 pair this fit is given.
    (
        "compound-1",
        Peak(3.148, 7.111),
        0.5419861581494966,
        0.4517753860498321,
        5.288960992291927,
        5.2693573156076159,
    ),
    (
        "compound-2",
        Peak(1.183, 2.184),
        0.1882861581494966,
        0.1561553860498322,
        14.849355416661352,
        14.849290820729498,
    ),
    (
        "compound-3",
        Peak(1.587, 3.462),
        0.2610061581494966,
        0.2328353860498322,
        16.936747527958115,
        16.975901726974396,
    ),
    (
        "compound-4",
        Peak(2.106, 5.163),
        0.3544261581494965,
        0.3348953860498322,
        24.429205987604647,
        24.461155384269425,
    ),
]


@pytest.mark.parametrize(
    ("peak", "ce_run1", "ce_run2", "s_two_point", "s_published"),
    [case[1:] for case in GUILLARME_CASES],
    ids=[case[0] for case in GUILLARME_CASES],
)
def test_reproduces_guillarme_reference_spreadsheet(
    peak: Peak, ce_run1: float, ce_run2: float, s_two_point: float, s_published: float
) -> None:
    fit = fit_peak(peak, GUILLARME_METHOD, GUILLARME_RUN1, GUILLARME_RUN2)

    assert fit.phi_e_run1 == pytest.approx(ce_run1, abs=1e-12)
    assert fit.phi_e_run2 == pytest.approx(ce_run2, abs=1e-12)
    assert s_base10_from_s_e(fit.seed_s_e) == pytest.approx(s_two_point, abs=1e-9)

    # The seed tracks the published regression closely; a log-base slip would put it
    # off by a factor of ln 10, not a fraction of a percent.
    assert s_base10_from_s_e(fit.seed_s_e) == pytest.approx(s_published, rel=0.005)
    # The exact root-find is a different (better) estimator, so it lands near but not
    # on the published value — research doc §3.2.
    assert s_base10_from_s_e(fit.params.s_e) == pytest.approx(s_published, rel=0.02)


# --- conditioning facts the later diagnostics tickets consume (research doc §7.2) ---


def _synthetic_peak(truth: RetentionParams, method: Method, run1: Run, run2: Run) -> Peak:
    return Peak(
        t_r_run1=integrate_fundamental_equation(truth, method, run1.gradient),
        t_r_run2=integrate_fundamental_equation(truth, method, run2.gradient),
    )


def test_reports_run_spacing_ratio_independent_of_argument_order() -> None:
    peak = LAB_MEASURED_PEAKS[0]
    forward = fit_peak(peak, LAB_METHOD, LAB_RUN1, LAB_RUN2)
    swapped = fit_peak(
        Peak(t_r_run1=peak.t_r_run2, t_r_run2=peak.t_r_run1), LAB_METHOD, LAB_RUN2, LAB_RUN1
    )

    assert forward.beta == pytest.approx(3.0)  # tG 45 / 15
    assert swapped.beta == pytest.approx(3.0)
    assert swapped.params.s_e == pytest.approx(forward.params.s_e, abs=1e-10)
    assert swapped.phi_e_run1 == pytest.approx(forward.phi_e_run2, abs=1e-12)


def test_elution_composition_separation_is_the_conditioning_number() -> None:
    fit = fit_peak(LAB_MEASURED_PEAKS[0], LAB_METHOD, LAB_RUN1, LAB_RUN2)
    assert fit.delta_phi_e == pytest.approx(fit.phi_e_run1 - fit.phi_e_run2)
    assert fit.delta_phi_e > 0.0


def test_low_k0_territory_is_flagged_where_the_closed_form_would_have_failed() -> None:
    # Guillarme's log k_i > 2.1 threshold (research doc §3.2): below it the seed is
    # worth tens of percent in S, so the fit stays exact but says the data are thin.
    low = RetentionParams(ln_k0=0.9 * math.log(10.0), s_e=4.0 * math.log(10.0), phi_ref=0.05)
    fit_low = fit_peak(
        _synthetic_peak(low, ROUND_TRIP_METHOD, ROUND_TRIP_RUN1, ROUND_TRIP_RUN2),
        ROUND_TRIP_METHOD,
        ROUND_TRIP_RUN1,
        ROUND_TRIP_RUN2,
    )
    assert fit_low.low_k0
    assert fit_low.low_confidence
    # Down here the §3.2 closed form is worth tens of percent (doc's k0 table), while
    # the returned root-find is still exact: the seed can never be the answer.
    assert s_base10_from_s_e(fit_low.seed_s_e) > 1.5 * 4.0
    assert fit_low.params.s_e == pytest.approx(low.s_e, abs=1e-8)

    high = RetentionParams(ln_k0=3.24 * math.log(10.0), s_e=4.99 * math.log(10.0), phi_ref=0.05)
    fit_high = fit_peak(
        _synthetic_peak(high, ROUND_TRIP_METHOD, ROUND_TRIP_RUN1, ROUND_TRIP_RUN2),
        ROUND_TRIP_METHOD,
        ROUND_TRIP_RUN1,
        ROUND_TRIP_RUN2,
    )
    assert not fit_high.low_k0
    assert not fit_high.low_confidence


def test_narrowly_spaced_runs_are_low_confidence_but_still_fit() -> None:
    # β = 1.5 fits, but §7.2 puts ordinary timing noise at ~0.7% error in S there.
    close_run2 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=22.5, t_init=0.5))
    truth = RetentionParams(ln_k0=3.24 * math.log(10.0), s_e=4.99 * math.log(10.0), phi_ref=0.05)
    fit = fit_peak(
        _synthetic_peak(truth, ROUND_TRIP_METHOD, ROUND_TRIP_RUN1, close_run2),
        ROUND_TRIP_METHOD,
        ROUND_TRIP_RUN1,
        close_run2,
    )
    assert fit.beta == pytest.approx(1.5)
    assert fit.low_confidence
    assert fit.params.s_e == pytest.approx(truth.s_e, abs=1e-8)


def test_reports_the_round_trip_residual_against_both_input_retention_times() -> None:
    """SPEC §3's self-check: the fitted parameters must reproduce the inputs."""
    for peak in LAB_MEASURED_PEAKS:
        fit = fit_peak(peak, LAB_METHOD, LAB_RUN1, LAB_RUN2)
        assert fit.max_residual < 1e-8
        for t_r_measured, run in ((peak.t_r_run1, LAB_RUN1), (peak.t_r_run2, LAB_RUN2)):
            predicted = predict_retention(fit.params, LAB_METHOD, run.gradient)
            assert predicted.t_r == pytest.approx(t_r_measured, abs=1e-8)


def test_fits_every_peak_independently() -> None:
    fits = fit_peaks(LAB_MEASURED_PEAKS, LAB_METHOD, LAB_RUN1, LAB_RUN2)
    assert [fit.params for fit in fits] == [
        fit_peak(peak, LAB_METHOD, LAB_RUN1, LAB_RUN2).params for peak in LAB_MEASURED_PEAKS
    ]


# --- degenerate and impossible inputs (SPEC §3; research doc §7.2) ---


def test_equal_scouting_gradient_times_are_refused() -> None:
    """SPEC §3 names this the one degenerate input that must refuse, not warn."""
    twin = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=15.0, t_init=0.5))
    with pytest.raises(ValueError, match="gradient time"):
        fit_peak(LAB_MEASURED_PEAKS[0], LAB_METHOD, LAB_RUN1, twin)


def test_shallower_run_eluting_at_higher_composition_is_refused_as_mistracking() -> None:
    # φ_e1 ≤ φ_e2 makes g(b) monotone-negative: no positive root exists, and the usual
    # cause is a peak matched to the wrong partner across the two runs (§7.2).
    mistracked = Peak(t_r_run1=9.855, t_r_run2=39.796)
    with pytest.raises(ValueError, match="peak tracking"):
        fit_peak(mistracked, LAB_METHOD, LAB_RUN1, LAB_RUN2)


def test_peak_eluting_before_the_gradient_arrives_is_refused() -> None:
    # tR below t0 + τ means the band left during the dwell/hold: the run carries no
    # gradient information about it, so there is nothing to fit.
    unretained = Peak(t_r_run1=1.2, t_r_run2=1.2)
    with pytest.raises(ValueError, match="before the gradient"):
        fit_peak(unretained, LAB_METHOD, LAB_RUN1, LAB_RUN2)


def test_scouting_runs_differing_in_anything_but_gradient_time_are_refused() -> None:
    # The §3.3 elimination assumes the two runs share φ0, φf and the pre-gradient hold.
    different_range = Run(Gradient(phi0=0.05, phif=0.60, t_gradient=45.0, t_init=0.5))
    with pytest.raises(ValueError, match="differ only in gradient time"):
        fit_peak(LAB_MEASURED_PEAKS[0], LAB_METHOD, LAB_RUN1, different_range)


def test_implausibly_steep_solute_is_refused_rather_than_searched_forever() -> None:
    # t'_2 ≈ β·t'_1 drives b_e past any physical value; §3.3 caps the search at S_e = 200.
    steep = Peak(t_r_run1=11.0375, t_r_run2=29.0370)  # t' = 9.0 and 3·9.0 − 0.0005
    with pytest.raises(ValueError, match="S_e"):
        fit_peak(steep, LAB_METHOD, LAB_RUN1, LAB_RUN2)


# --- SPEC §10 layer 3: the lab dataset in validation/ ---

LAB_EXPECTED = [
    # (label, S base-10, log10 k0, predicted tR at tG = 25, measured tR at tG = 25)
    # S / log10 k0 are the values fitted pre-build from run1.csv + run2.csv (handoff,
    # 2026-08-27); the tG = 25 column is run3.csv, held out of the fit.
    ("Unknown-1", 5.08, 2.76, 13.861, 13.787),
    ("Unknown-2", 4.99, 3.24, 16.729, 16.658),
    ("Unknown-3", 5.18, 4.76, 24.383, 24.358),
]


@pytest.mark.parametrize(
    ("peak", "expected"),
    list(zip(LAB_MEASURED_PEAKS, LAB_EXPECTED, strict=True)),
    ids=[case[0] for case in LAB_EXPECTED],
)
def test_fitting_the_lab_scouting_pair_reproduces_the_pre_build_parameters(
    peak: Peak, expected: tuple[str, float, float, float, float]
) -> None:
    _, s_base10, log10_k0, t_r_predicted, t_r_measured = expected

    fit = fit_peak(peak, LAB_METHOD, LAB_RUN1, LAB_RUN2)

    assert s_base10_from_s_e(fit.params.s_e) == pytest.approx(s_base10, abs=0.005)
    assert log10_k0_from_ln_k0(fit.params.ln_k0) == pytest.approx(log10_k0, abs=0.005)
    assert not fit.low_confidence

    # Forward-predicting the held-out tG = 25 run from the fit lands within 1% of the
    # instrument, and on the value the pre-build spreadsheet produced.
    held_out = Gradient(phi0=0.05, phif=0.95, t_gradient=25.0, t_init=0.5)
    predicted = predict_retention(fit.params, LAB_METHOD, held_out)
    assert predicted.t_r == pytest.approx(t_r_predicted, abs=0.005)
    assert predicted.t_r == pytest.approx(t_r_measured, rel=0.01)
