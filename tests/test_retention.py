"""Forward retention prediction (SPEC §3, research doc §2 and §4)."""

import math

import pytest

from hplcsim.model import Gradient, Method, RetentionParams
from hplcsim.retention import predict_retention
from lab_data import LAB_METHOD, LAB_PEAKS
from numerics import integrate_fundamental_equation

# The method the research doc's §4 edge cases were worked by hand against: the lab
# instrument at the t0 = 0.6 the fixtures carried when they were worked. Kept as its own
# constant so the re-baseline of LAB_METHOD to 0.525 (#24) does not re-derive arithmetic
# whose only point is being checkable by hand.
_HAND_WORKED_METHOD = Method(t0=0.6, t_dwell=0.9375, flow=0.4)


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
    expected = integrate_fundamental_equation(params, method, gradient)
    assert predict_retention(params, method, gradient).t_r == pytest.approx(expected, abs=1e-10)


# --- edge-case branches (research doc §4) ---


def test_peak_that_leaves_during_hold_is_isocratic() -> None:
    # tau/t0 = (0.9375 + 0.5)/0.6 = 2.396; k0 = 2 < that, so tR = t0(1 + k0) = 1.8 min
    params = RetentionParams(ln_k0=math.log(2.0), s_e=10.0, phi_ref=0.05)
    result = predict_retention(params, _HAND_WORKED_METHOD, Gradient(0.05, 0.95, 15.0, t_init=0.5))
    assert result.t_r == pytest.approx(1.8)
    assert result.k_e == pytest.approx(2.0)
    assert result.regime == "isocratic_hold"


def test_peak_still_on_column_at_gradient_end_finishes_isocratically() -> None:
    # Hand-worked (§4.2): k0 = 20, S_e = 1, Δφ = 0.9 -> kf = 20·e^-0.9 = 8.131;
    # b_e = 0.6·0.9·1/5 = 0.108; x_G = 1.4375/12 + (20/8.131 − 1)/(20·0.108) = 0.7955;
    # tR = 1.4375 + 5 + 0.6 + (1 − 0.7955)·0.6·8.131 = 8.035 min.
    params = RetentionParams(ln_k0=math.log(20.0), s_e=1.0, phi_ref=0.05)
    result = predict_retention(params, _HAND_WORKED_METHOD, Gradient(0.05, 0.95, 5.0, t_init=0.5))
    assert result.t_r == pytest.approx(8.035, abs=0.005)
    assert result.k_e == pytest.approx(8.131, abs=0.005)
    assert result.regime == "post_gradient"
    assert result.low_confidence  # §4.2: least trustworthy regime, flag it


def test_gradient_and_post_gradient_branches_join_continuously() -> None:
    """At x_G = 1 both branches give tR = tau + tG + t0 (research doc §4.2)."""
    from scipy.optimize import brentq

    method = _HAND_WORKED_METHOD
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
    result = predict_retention(params, _HAND_WORKED_METHOD, Gradient(0.30, 0.30, 10.0))
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
