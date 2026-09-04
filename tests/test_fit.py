"""The two-run fit (SPEC §3, research doc §3).

Layer 1 (SPEC §10) generates retention times from known parameters with the
independent scipy oracle in `numerics.py` and fits them back: nothing but the
LSS model itself is shared between the generator and the fit under test.
"""

import pytest

from hplcsim.fit import fit_peak, fit_peaks
from hplcsim.model import (
    Gradient,
    Method,
    Peak,
    RetentionParams,
    Run,
    ln_k0_from_log10_k0,
    log10_k0_from_ln_k0,
    s_base10_from_s_e,
    s_e_from_s_base10,
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
        ln_k0=ln_k0_from_log10_k0(log10_k0),
        s_e=s_e_from_s_base10(s_base10),
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
    # (label, peak, Ce run 1, Ce run 2, two-point S, published S, published log10 k_i)
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
        2.9192802027110885,
    ),
    (
        "compound-2",
        Peak(1.183, 2.184),
        0.1882861581494966,
        0.1561553860498322,
        14.849355416661352,
        14.849290820729498,
        1.9328222392003582,
    ),
    (
        "compound-3",
        Peak(1.587, 3.462),
        0.2610061581494966,
        0.2328353860498322,
        16.936747527958115,
        16.975901726974396,
        3.4048210474814202,
    ),
    (
        "compound-4",
        Peak(2.106, 5.163),
        0.3544261581494965,
        0.3348953860498322,
        24.429205987604647,
        24.461155384269425,
        7.1100975631839818,
    ),
]


@pytest.mark.parametrize(
    ("peak", "ce_run1", "ce_run2", "s_two_point", "s_published", "log10_k0_published"),
    [case[1:] for case in GUILLARME_CASES],
    ids=[case[0] for case in GUILLARME_CASES],
)
def test_reproduces_guillarme_reference_spreadsheet(
    peak: Peak,
    ce_run1: float,
    ce_run2: float,
    s_two_point: float,
    s_published: float,
    log10_k0_published: float,
) -> None:
    fit = fit_peak(peak, GUILLARME_METHOD, GUILLARME_RUN1, GUILLARME_RUN2)

    assert fit.phi_e_run1 == pytest.approx(ce_run1, abs=1e-12)
    assert fit.phi_e_run2 == pytest.approx(ce_run2, abs=1e-12)
    assert s_base10_from_s_e(fit.seed_s_e) == pytest.approx(s_two_point, abs=1e-9)

    # The seed tracks the published regression closely; a log-base slip would put it
    # off by a factor of ln 10, not a fraction of a percent.
    assert s_base10_from_s_e(fit.seed_s_e) == pytest.approx(s_published, rel=0.005)
    # The exact root-find is a different (better) estimator, so it lands near but not
    # on the published value — research doc §3.2. Both halves of the answer are pinned:
    # a log-base slip in the k0 recovery would move log10 k0 by a factor of ln 10, not
    # by the couple of percent the estimator difference costs.
    assert s_base10_from_s_e(fit.params.s_e) == pytest.approx(s_published, rel=0.02)
    assert log10_k0_from_ln_k0(fit.params.ln_k0) == pytest.approx(log10_k0_published, rel=0.02)

    # Tighter than the ticket's 1e-6, and it pins S_e and ln_k0 jointly: the fitted pair
    # must reproduce the spreadsheet's own input retention times.
    assert fit.max_residual < 1e-8


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
    assert forward.beta_spacing == "ok"
    assert swapped.params.s_e == pytest.approx(forward.params.s_e, abs=1e-10)
    assert swapped.phi_e_run1 == pytest.approx(forward.phi_e_run2, abs=1e-12)


def test_elution_composition_separation_is_the_conditioning_number() -> None:
    fit = fit_peak(LAB_MEASURED_PEAKS[0], LAB_METHOD, LAB_RUN1, LAB_RUN2)
    assert fit.delta_phi_e == pytest.approx(fit.phi_e_run1 - fit.phi_e_run2)
    assert fit.delta_phi_e > 0.0


def test_low_k0_territory_is_flagged_where_the_closed_form_would_have_failed() -> None:
    # Guillarme's log k_i > 2.1 threshold (research doc §3.2): below it the seed is
    # worth tens of percent in S, so the fit stays exact but says the data are thin.
    low = RetentionParams(ln_k0=ln_k0_from_log10_k0(0.9), s_e=s_e_from_s_base10(4.0), phi_ref=0.05)
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

    high = RetentionParams(
        ln_k0=ln_k0_from_log10_k0(3.24), s_e=s_e_from_s_base10(4.99), phi_ref=0.05
    )
    fit_high = fit_peak(
        _synthetic_peak(high, ROUND_TRIP_METHOD, ROUND_TRIP_RUN1, ROUND_TRIP_RUN2),
        ROUND_TRIP_METHOD,
        ROUND_TRIP_RUN1,
        ROUND_TRIP_RUN2,
    )
    assert not fit_high.low_k0
    assert not fit_high.low_confidence


@pytest.mark.parametrize(
    ("t_gradient_2", "beta", "spacing"),
    [
        # SPEC §4: "spacing-ratio warning < 2.5, strong < 1.2, never a hard block".
        (45.0, 3.0, "ok"),
        (37.5, 2.5, "ok"),
        (22.5, 1.5, "warning"),
        (16.5, 1.1, "strong"),
    ],
)
def test_narrowly_spaced_runs_escalate_but_still_fit(
    t_gradient_2: float, beta: float, spacing: str
) -> None:
    # §7.2's table is the evidence: at β = 1.5 a 0.6 s timing error is worth 0.7% in S,
    # at β = 1.2 nearly 2%. None of that makes the fit impossible, so none of it blocks.
    run2 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=t_gradient_2, t_init=0.5))
    truth = RetentionParams(
        ln_k0=ln_k0_from_log10_k0(3.24), s_e=s_e_from_s_base10(4.99), phi_ref=0.05
    )
    fit = fit_peak(
        _synthetic_peak(truth, ROUND_TRIP_METHOD, ROUND_TRIP_RUN1, run2),
        ROUND_TRIP_METHOD,
        ROUND_TRIP_RUN1,
        run2,
    )
    assert fit.beta == pytest.approx(beta)
    assert fit.beta_spacing == spacing
    assert fit.low_confidence == (spacing != "ok")
    # Conditioning is not correctness: the root-find stays exact at every spacing.
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
    # S / log10 k0 are fitted from run1.csv + run2.csv at t0 = 0.525 (re-baselined
    # 2026-09-03, #24; the 2026-08-27 pre-build handoff had 5.08 / 2.76, 4.99 / 3.24,
    # 5.18 / 4.76 at the superseded 0.6). The tG = 25 column is run3.csv, held out.
    ("Unknown-1", 4.919, 2.777, 13.871, 13.787),
    ("Unknown-2", 4.836, 3.249, 16.740, 16.658),
    ("Unknown-3", 5.016, 4.711, 24.395, 24.358),
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


# --- the plate count fitted from the scouting widths (ticket #23) ---


def test_lab_peaks_get_a_plate_count_fitted_from_their_scouting_widths() -> None:
    """The fit is everything the two runs say about a peak — retention *and* N.

    Characterisation at t0 = 0.525 (re-baselined 2026-09-03, #24). At the superseded
    0.6 these were 15212 / 14327 / 23968, with Unknown-1's per-run values 15299 and
    15126 — the numbers research doc §5.4 tabulated by hand before the inverse existed
    as a function, and still quotes as computed at 0.6. N moves ~2.5% for a 12.5%
    t0 change, the ~0.2× elasticity dead-time-from-geometry.md §6.2 records. Against the
    h = 2 geometry default of 31250, every peak lands at 15–25 k plates.
    """
    fits = fit_peaks(LAB_MEASURED_PEAKS, LAB_METHOD, LAB_RUN1, LAB_RUN2)

    fitted = [fit.plate_count for fit in fits]
    assert all(value is not None for value in fitted)
    assert [value.plate_count for value in fitted if value is not None] == pytest.approx(
        [15605.0, 14684.0, 24577.0], rel=1e-3
    )

    unknown_1 = fitted[0]
    assert unknown_1 is not None
    assert unknown_1.implied_run1 == pytest.approx(15432.0, abs=1.0)
    assert unknown_1.implied_run2 == pytest.approx(15779.0, abs=1.0)
    assert not unknown_1.low_confidence


def test_a_peak_without_widths_is_fitted_for_retention_only() -> None:
    bare = Peak(t_r_run1=9.855, t_r_run2=20.831)

    fit = fit_peak(bare, LAB_METHOD, LAB_RUN1, LAB_RUN2)

    assert fit.plate_count is None
    assert log10_k0_from_ln_k0(fit.params.ln_k0) == pytest.approx(2.777, abs=0.01)


def test_a_steeper_run_that_elutes_later_is_refused_rather_than_searched_forever() -> None:
    """The upper end of §3.3's bracket — the case that used to hang the whole app.

    g'(0) has the sign of (t'_steep − t'_shallow). When the steeper gradient elutes the
    band later, g never dips below zero, so the root-find's walk down for a lower bound
    shrinks to 0.0 and stays there. Physically the data are impossible: a steeper
    gradient elutes a compound earlier, never later. Found while wiring ticket #20's
    entry checks, where a peak table with its two tR columns transposed reaches it.
    """
    with pytest.raises(ValueError, match="later than the shallower run"):
        fit_peak(LAB_MEASURED_PEAKS[0], LAB_METHOD, LAB_RUN2, LAB_RUN1)
