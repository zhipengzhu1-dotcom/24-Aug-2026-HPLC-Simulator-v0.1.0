"""Forward retention prediction (SPEC §3, research doc §2 and §4)."""

import math

import pytest

from hplcsim.model import (
    Gradient,
    Method,
    RetentionParams,
    ln_k0_from_log10_k0,
    s_e_from_s_base10,
)
from hplcsim.retention import predict_retention

# Lab method (validation/method.csv): t0 measured 0.6 min, dwell 0.375 mL @ 0.4 mL/min.
LAB_METHOD = Method(t0=0.6, t_dwell=0.9375, flow=0.4)

# Per-peak parameters fitted pre-build from runs at tG = 15 / 45 min (handoff, 2026-08-27),
# quoted in the base-10 display convention and converted at the boundary.
LAB_PEAKS = [
    RetentionParams(ln_k0=ln_k0_from_log10_k0(2.76), s_e=s_e_from_s_base10(5.08), phi_ref=0.05),
    RetentionParams(ln_k0=ln_k0_from_log10_k0(3.24), s_e=s_e_from_s_base10(4.99), phi_ref=0.05),
    RetentionParams(ln_k0=ln_k0_from_log10_k0(4.76), s_e=s_e_from_s_base10(5.18), phi_ref=0.05),
]


@pytest.mark.parametrize(
    ("t_gradient", "measured"),
    [
        (25.0, [13.787, 16.658, 24.358]),  # validation/run3.csv (interpolation)
        (60.0, [25.587, 32.320, 50.821]),  # validation/run4.csv (extrapolation)
    ],
)
def test_predicts_lab_retention_times_within_one_percent(
    t_gradient: float, measured: list[float]
) -> None:
    gradient = Gradient(phi0=0.05, phif=0.95, t_gradient=t_gradient, t_init=0.5)
    for params, t_r_measured in zip(LAB_PEAKS, measured, strict=True):
        result = predict_retention(params, LAB_METHOD, gradient)
        assert result.t_r == pytest.approx(t_r_measured, rel=0.01)
        assert result.regime == "gradient"


# --- SPEC §10 layer 1: closed form vs numerical integration of the fundamental equation ---


def _integrate_fundamental_equation(
    params: RetentionParams, method: Method, gradient: Gradient
) -> float:
    """Solve ∫0^(tR−t0) dt / (t0·k(φ_in(t))) = 1 numerically (research doc §2.1).

    φ_in(t) is the programmed profile delayed by the dwell: φ0 during the dwell and
    initial hold, the linear ramp, then φf after the ramp ends. Independent of any
    closed form: it only knows the LSS model and the inlet profile.
    """
    from scipy.integrate import quad
    from scipy.optimize import brentq

    t0 = method.t0
    tau = method.t_dwell + gradient.t_init
    slope = gradient.delta_phi / gradient.t_gradient

    def phi_in(t: float) -> float:
        if t <= tau:
            return gradient.phi0
        if t >= tau + gradient.t_gradient:
            return gradient.phif
        return gradient.phi0 + slope * (t - tau)

    def rate(t: float) -> float:
        k = math.exp(params.ln_k0 - params.s_e * (phi_in(t) - params.phi_ref))
        return 1.0 / (t0 * k)

    def migrated(t: float) -> float:
        breakpoints = [b for b in (tau, tau + gradient.t_gradient) if 0.0 < b < t]
        value, _ = quad(
            rate, 0.0, t, points=breakpoints or None, epsabs=1e-13, epsrel=1e-13, limit=500
        )
        return float(value)

    t_upper = 10.0
    while migrated(t_upper) < 1.0:
        t_upper *= 2.0
    t_exit: float = brentq(lambda t: migrated(t) - 1.0, 0.0, t_upper, xtol=1e-14, rtol=1e-15)
    return t_exit + t0


INTEGRATION_CASES = [
    # (label, params, method, gradient)
    ("lab-peak-2-tG25", LAB_PEAKS[1], LAB_METHOD, Gradient(0.05, 0.95, 25.0, t_init=0.5)),
    (
        "no-dwell-no-hold",
        LAB_PEAKS[0],
        Method(t0=1.0, t_dwell=0.0, flow=1.0),
        Gradient(0.05, 0.95, 20.0),
    ),
    (
        "shallow-gradient",
        RetentionParams(ln_k0=math.log(50.0), s_e=8.0, phi_ref=0.1),
        Method(t0=2.0, t_dwell=1.5, flow=0.5),
        Gradient(0.1, 0.6, 40.0, t_init=2.0),
    ),
    # k0 = 2 with tau/t0 = 2.4: leaves the column before the gradient arrives (§4.1)
    (
        "elutes-in-hold",
        RetentionParams(ln_k0=math.log(2.0), s_e=10.0, phi_ref=0.05),
        LAB_METHOD,
        Gradient(0.05, 0.95, 15.0, t_init=0.5),
    ),
    # weak S_e and a 5-min ramp: still on-column when the ramp ends (§4.2)
    (
        "post-gradient",
        RetentionParams(ln_k0=math.log(20.0), s_e=1.0, phi_ref=0.05),
        LAB_METHOD,
        Gradient(0.05, 0.95, 5.0, t_init=0.5),
    ),
]


@pytest.mark.parametrize(
    ("params", "method", "gradient"),
    [case[1:] for case in INTEGRATION_CASES],
    ids=[case[0] for case in INTEGRATION_CASES],
)
def test_closed_form_matches_numerical_integration(
    params: RetentionParams, method: Method, gradient: Gradient
) -> None:
    expected = _integrate_fundamental_equation(params, method, gradient)
    assert predict_retention(params, method, gradient).t_r == pytest.approx(expected, abs=1e-10)


# --- edge-case branches (research doc §4) ---


def test_peak_that_leaves_during_hold_is_isocratic() -> None:
    # tau/t0 = (0.9375 + 0.5)/0.6 = 2.396; k0 = 2 < that, so tR = t0(1 + k0) = 1.8 min
    params = RetentionParams(ln_k0=math.log(2.0), s_e=10.0, phi_ref=0.05)
    result = predict_retention(params, LAB_METHOD, Gradient(0.05, 0.95, 15.0, t_init=0.5))
    assert result.t_r == pytest.approx(1.8)
    assert result.k_e == pytest.approx(2.0)
    assert result.regime == "isocratic_hold"


def test_peak_still_on_column_at_gradient_end_finishes_isocratically() -> None:
    # Hand-worked (§4.2): k0 = 20, S_e = 1, Δφ = 0.9 -> kf = 20·e^-0.9 = 8.131;
    # b_e = 0.6·0.9·1/5 = 0.108; x_G = 1.4375/12 + (20/8.131 − 1)/(20·0.108) = 0.7955;
    # tR = 1.4375 + 5 + 0.6 + (1 − 0.7955)·0.6·8.131 = 8.035 min.
    params = RetentionParams(ln_k0=math.log(20.0), s_e=1.0, phi_ref=0.05)
    result = predict_retention(params, LAB_METHOD, Gradient(0.05, 0.95, 5.0, t_init=0.5))
    assert result.t_r == pytest.approx(8.035, abs=0.005)
    assert result.k_e == pytest.approx(8.131, abs=0.005)
    assert result.regime == "post_gradient"
    assert result.low_confidence  # §4.2: least trustworthy regime, flag it


def test_gradient_and_post_gradient_branches_join_continuously() -> None:
    """At x_G = 1 both branches give tR = tau + tG + t0 (research doc §4.2)."""
    from scipy.optimize import brentq

    method = LAB_METHOD
    gradient = Gradient(0.05, 0.95, 5.0, t_init=0.5)
    tau = method.t_dwell + gradient.t_init
    t_boundary = tau + gradient.t_gradient + method.t0

    def excess(s_e: float) -> float:
        return (
            predict_retention(RetentionParams(math.log(20.0), s_e, 0.05), method, gradient).t_r
            - t_boundary
        )

    s_e_star: float = brentq(excess, 0.5, 5.0, xtol=1e-13)
    below = predict_retention(
        RetentionParams(math.log(20.0), s_e_star - 1e-9, 0.05), method, gradient
    )
    above = predict_retention(
        RetentionParams(math.log(20.0), s_e_star + 1e-9, 0.05), method, gradient
    )
    assert {below.regime, above.regime} == {"post_gradient", "gradient"}
    assert below.t_r == pytest.approx(t_boundary, abs=1e-7)
    assert above.t_r == pytest.approx(t_boundary, abs=1e-7)
    assert below.k_e == pytest.approx(above.k_e, abs=1e-6)


def test_flat_gradient_is_isocratic_for_every_peak() -> None:
    # Δφ = 0 makes b_e = 0; the whole run is isocratic at φ0, so tR = t0(1 + k0).
    params = RetentionParams(ln_k0=math.log(6.0), s_e=10.0, phi_ref=0.30)
    result = predict_retention(params, LAB_METHOD, Gradient(0.30, 0.30, 10.0))
    assert result.t_r == pytest.approx(0.6 * 7.0)
    assert result.regime == "isocratic_hold"


@pytest.mark.parametrize("t_gradient", [0.0, -5.0])
def test_non_positive_gradient_time_is_refused(t_gradient: float) -> None:
    with pytest.raises(ValueError, match="t_gradient"):
        predict_retention(LAB_PEAKS[0], LAB_METHOD, Gradient(0.05, 0.95, t_gradient))


def test_non_positive_dead_time_is_refused() -> None:
    with pytest.raises(ValueError, match="t0"):
        predict_retention(
            LAB_PEAKS[0], Method(t0=0.0, t_dwell=0.9, flow=0.4), Gradient(0.05, 0.95, 15.0)
        )


def test_very_early_eluter_is_flagged_low_confidence() -> None:
    # k0 = 3 barely survives the hold (tau/t0 = 2.396) and exits with k_e < 1 (§4.3).
    early = RetentionParams(ln_k0=math.log(3.0), s_e=10.0, phi_ref=0.05)
    assert predict_retention(
        early, LAB_METHOD, Gradient(0.05, 0.95, 15.0, t_init=0.5)
    ).low_confidence
    well_retained = predict_retention(
        LAB_PEAKS[1], LAB_METHOD, Gradient(0.05, 0.95, 25.0, t_init=0.5)
    )
    assert well_retained.k_e > 1.0
    assert not well_retained.low_confidence
