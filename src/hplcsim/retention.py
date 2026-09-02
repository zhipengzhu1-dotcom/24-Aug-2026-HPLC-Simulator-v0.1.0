"""Forward retention prediction under the LSS model (SPEC §3; research doc §2, §4, §8.2).

All math is in the natural-log convention (S_e, b_e). The closed form of §2.2
is used in the gradient regime; the dwell/hold and post-gradient regimes get
their own branches, derived from the same fundamental equation (§2.1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from hplcsim.model import Gradient, Method, RetentionParams

Regime = Literal["isocratic_hold", "gradient", "post_gradient"]


def gradient_steepness(method: Method, gradient: Gradient, s_e: float) -> float:
    """b_e = t0·Δφ·S_e/tG — the natural-log gradient steepness (research doc §1.3).

    The single home for this expression, and deliberately so: it is the most
    exposed surface of the natural-log convention CLAUDE.md names as the project's
    #1 hazard. Retention, band compression (§5.2) and the tests that reconstruct
    counterfactual G conventions must all read the same b_e — a correction applied
    here to one of them and not the others would desync them silently.
    """
    return method.t0 * gradient.delta_phi * s_e / gradient.t_gradient


def gradient_end_time(method: Method, gradient: Gradient) -> float:
    """When the final composition φf reaches the detector (min from injection).

    The programmed ramp ends at the pump at ``t_init + t_gradient``; it reaches the
    column head one dwell later and the detector one t0 after that. This is exactly the
    boundary between the gradient and post-gradient regimes below — a band still on the
    column at this instant finishes the run isocratically at φf — so the drawn marker
    and the regime that classifies a peak read the same expression.
    """
    return method.t_dwell + gradient.t_init + gradient.t_gradient + method.t0


@dataclass(frozen=True)
class RetentionResult:
    """Predicted retention for one peak under one gradient.

    ``k_e`` is the retention factor at the instant the band leaves the column.
    ``low_confidence`` is set when the k >> 1 approximation behind the model
    degrades (research doc §4.3: k_e below ~1, or t'_R = tR − t0 − τ below t0,
    with t'_R as defined in the doc's symbol table) or when the band does not
    elute during the ramp (§4.1/§4.2: "flag them").
    """

    t_r: float
    k_e: float
    regime: Regime
    low_confidence: bool = False


def predict_retention(
    params: RetentionParams, method: Method, gradient: Gradient
) -> RetentionResult:
    """Predict tR (min) for ``params`` run under ``gradient`` on ``method``."""
    if method.t0 <= 0.0:
        raise ValueError(f"t0 must be positive, got {method.t0}")
    if gradient.t_gradient <= 0.0:
        raise ValueError(f"t_gradient must be positive, got {gradient.t_gradient}")

    t0 = method.t0
    tau = method.t_dwell + gradient.t_init
    k0 = params.k_at(gradient.phi0)

    # §4.1: test the pre-gradient migration first — the closed form's log argument
    # goes non-positive exactly when the band has already left the column. A flat
    # gradient (Δφ = 0) is the same isocratic case for every peak.
    if k0 <= tau / t0 or gradient.delta_phi == 0.0:
        return _classify(t_r=t0 * (1.0 + k0), k_e=k0, regime="isocratic_hold", t0=t0, tau=tau)

    b_e = gradient_steepness(method, gradient, params.s_e)

    # §4.2: fraction of the column traversed when the ramp ends. If the band is
    # still on-column it finishes isocratically at phif with k_f.
    k_f = k0 * math.exp(-params.s_e * gradient.delta_phi)
    x_gradient_end = tau / (t0 * k0) + (k0 / k_f - 1.0) / (k0 * b_e)
    if x_gradient_end < 1.0:
        t_r = gradient_end_time(method, gradient) + (1.0 - x_gradient_end) * t0 * k_f
        return _classify(t_r=t_r, k_e=k_f, regime="post_gradient", t0=t0, tau=tau)

    # §2.2: the LSS closed form, valid while the band exits during the ramp.
    log_arg = b_e * (k0 - tau / t0) + 1.0
    t_r = tau + t0 + (t0 / b_e) * math.log(log_arg)
    return _classify(t_r=t_r, k_e=k0 / log_arg, regime="gradient", t0=t0, tau=tau)


def _classify(*, t_r: float, k_e: float, regime: Regime, t0: float, tau: float) -> RetentionResult:
    """Attach the §4.3 / §4.1–4.2 low-confidence classification to a prediction."""
    t_r_prime = t_r - t0 - tau
    low_confidence = regime != "gradient" or k_e < 1.0 or t_r_prime < t0
    return RetentionResult(t_r=t_r, k_e=k_e, regime=regime, low_confidence=low_confidence)
