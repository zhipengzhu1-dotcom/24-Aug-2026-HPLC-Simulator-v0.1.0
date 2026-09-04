"""Independent numerical oracles for the engine's closed forms (SPEC §10 layer 1).

Nothing here may reuse an engine closed form: these solvers know only the LSS
model and the programmed inlet profile, so a shared algebra slip cannot hide.
"""

from __future__ import annotations

import math

from scipy.integrate import quad
from scipy.optimize import brentq

from hplcsim.model import Method, RetentionParams, Target, as_programme


def integrate_fundamental_equation(
    params: RetentionParams, method: Method, target: Target
) -> float:
    """Solve ∫0^(tR−t0) dt / (t0·k(φ_in(t))) = 1 numerically (research doc §2.1).

    φ_in(t) is the programmed profile delayed by the dwell: φ0 during the dwell and
    initial hold, then each leg of the programme in turn — linear between its entry and
    end compositions, flat if it is a hold — then the final composition for ever after.
    Independent of any closed form: it only knows the LSS model and the inlet profile,
    and a v0.1 gradient is simply the one-leg profile.
    """
    programme = as_programme(target)
    t0 = method.t0
    tau = method.t_dwell + programme.t_init

    # (start time at the inlet, entry φ, slope, end time) per leg, in order.
    pieces = []
    start = tau
    for leg in programme.legs():
        pieces.append((start, leg.phi_start, leg.delta_phi / leg.duration, start + leg.duration))
        start += leg.duration
    t_end = start

    def phi_in(t: float) -> float:
        if t <= tau:
            return programme.phi0
        if t >= t_end:
            return programme.phif
        for piece_start, phi_start, slope, piece_end in pieces:
            if t < piece_end:
                return phi_start + slope * (t - piece_start)
        return programme.phif  # pragma: no cover — t < t_end is always inside a piece

    def rate(t: float) -> float:
        k = math.exp(params.ln_k0 - params.s_e * (phi_in(t) - params.phi_ref))
        return 1.0 / (t0 * k)

    kinks = [tau, *(piece_end for _, _, _, piece_end in pieces)]

    def migrated(t: float) -> float:
        breakpoints = [b for b in kinks if 0.0 < b < t]
        value, _ = quad(
            rate, 0.0, t, points=breakpoints or None, epsabs=1e-13, epsrel=1e-13, limit=500
        )
        return float(value)

    t_upper = 10.0
    while migrated(t_upper) < 1.0:
        t_upper *= 2.0
    t_exit: float = brentq(lambda t: migrated(t) - 1.0, 0.0, t_upper, xtol=1e-14, rtol=1e-15)
    return t_exit + t0
