"""Independent numerical oracles for the engine's closed forms (SPEC §10 layer 1).

Nothing here may reuse an engine closed form: these solvers know only the LSS
model and the programmed inlet profile, so a shared algebra slip cannot hide.
"""

from __future__ import annotations

import math

from scipy.integrate import quad
from scipy.optimize import brentq

from hplcsim.model import Gradient, Method, RetentionParams


def integrate_fundamental_equation(
    params: RetentionParams, method: Method, gradient: Gradient
) -> float:
    """Solve ∫0^(tR−t0) dt / (t0·k(φ_in(t))) = 1 numerically (research doc §2.1).

    φ_in(t) is the programmed profile delayed by the dwell: φ0 during the dwell and
    initial hold, the linear ramp, then φf after the ramp ends. Independent of any
    closed form: it only knows the LSS model and the inlet profile.
    """
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
