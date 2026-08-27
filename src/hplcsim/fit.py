"""The per-peak two-run fit (SPEC §3; research doc §3).

Two scouting runs give two retention times per peak, and two data buy exactly two
parameters: (k0, S_e). No exact closed form exists (§3.1), so the large-k0 closed
form of §3.2 is used **only** to bracket a 1-D root-find on the run-2 residual
(§3.3). All math is in the natural-log convention.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from scipy.optimize import brentq

from hplcsim.model import Method, Peak, RetentionParams, Run, log10_k0_from_ln_k0
from hplcsim.retention import predict_retention

# Guillarme et al.'s constraint on the closed form: below log10 k0 = 2.1 the large-k0
# approximation is worth tens of percent in S, so the data are thin even though the
# root-find itself stays exact (research doc §3.2).
_LOW_K0_LOG10 = 2.1

# Below this run-spacing ratio, ordinary timing noise starts showing up in S at the
# percent level (research doc §7.2, table).
_MIN_WELL_CONDITIONED_BETA = 2.0

# The SPEC §3 self-check tolerance: the fit must reproduce both input retention times.
_MAX_RESIDUAL = 1e-8

# Cap the search at S_e = 200: past that the exponentials overflow long before any
# real small molecule does (research doc §3.3).
_S_E_MAX = 200.0


@dataclass(frozen=True)
class FitResult:
    """The fitted parameters for one peak, plus the facts that condition them.

    ``phi_e_run1`` / ``phi_e_run2`` are the compositions the band experienced when it
    eluted in each run, in the order the runs were passed; their separation is the
    conditioning number of the whole fit (research doc §7.2). ``seed_s_e`` is the
    §3.2 large-k0 closed form — reported for diagnostics only, never the answer.
    """

    params: RetentionParams
    beta: float
    phi_e_run1: float
    phi_e_run2: float
    seed_s_e: float
    max_residual: float
    low_k0: bool
    low_confidence: bool

    @property
    def delta_phi_e(self) -> float:
        """Separation of the two elution compositions — the fit's conditioning number."""
        return self.phi_e_run1 - self.phi_e_run2


def fit_peak(peak: Peak, method: Method, run1: Run, run2: Run) -> FitResult:
    """Fit (ln k0, S_e) for one peak from its retention time in each scouting run."""
    _check_runs_are_a_scouting_pair(run1, run2)

    steep, shallow = sorted((run1, run2), key=lambda r: r.gradient.t_gradient)
    t_r_steep, t_r_shallow = (
        (peak.t_r_run1, peak.t_r_run2) if steep is run1 else (peak.t_r_run2, peak.t_r_run1)
    )

    t0 = method.t0
    gradient = steep.gradient
    tau = method.t_dwell + gradient.t_init
    beta = shallow.gradient.t_gradient / gradient.t_gradient
    t_prime_steep = t_r_steep - t0 - tau
    t_prime_shallow = t_r_shallow - t0 - tau
    if t_prime_steep <= 0.0 or t_prime_shallow <= 0.0:
        raise ValueError(
            "peak elutes before the gradient reaches the column "
            f"(tR must exceed t0 + τ = {t0 + tau:.4g} min in both runs); nothing to fit"
        )
    # §3.3: the steeper gradient must elute the band at the *higher* composition, or
    # g(b) never turns positive and the data admit no LSS solution.
    if t_prime_steep <= t_prime_shallow / beta:
        raise ValueError(
            "shallower run elutes this peak at a higher %B than the steeper run: "
            "no LSS solution exists — check peak tracking"
        )

    per_run = gradient.t_gradient / (t0 * gradient.delta_phi)
    seed_b_e = _seed_steepness(t_prime_steep, t_prime_shallow, beta, t0)
    b_e = _solve_steepness(
        t_prime_steep, t_prime_shallow, beta, t0, seed=seed_b_e, b_e_max=_S_E_MAX / per_run
    )
    k0 = math.expm1(b_e * t_prime_steep / t0) / b_e + tau / t0

    phi_e_steep = _elution_composition(t_prime_steep, steep)
    phi_e_shallow = _elution_composition(t_prime_shallow, shallow)
    ordered = (phi_e_steep, phi_e_shallow) if steep is run1 else (phi_e_shallow, phi_e_steep)
    params = RetentionParams(ln_k0=math.log(k0), s_e=b_e * per_run, phi_ref=gradient.phi0)

    max_residual = max(
        abs(predict_retention(params, method, run.gradient).t_r - t_r)
        for run, t_r in ((run1, peak.t_r_run1), (run2, peak.t_r_run2))
    )
    low_k0 = log10_k0_from_ln_k0(params.ln_k0) < _LOW_K0_LOG10
    return FitResult(
        params=params,
        beta=beta,
        phi_e_run1=ordered[0],
        phi_e_run2=ordered[1],
        seed_s_e=seed_b_e * per_run,
        max_residual=max_residual,
        low_k0=low_k0,
        low_confidence=(
            low_k0 or beta < _MIN_WELL_CONDITIONED_BETA or max_residual > _MAX_RESIDUAL
        ),
    )


def fit_peaks(peaks: Sequence[Peak], method: Method, run1: Run, run2: Run) -> list[FitResult]:
    """Fit every peak independently — no peak's data informs another's (§3.4 step 4)."""
    return [fit_peak(peak, method, run1, run2) for peak in peaks]


def _elution_composition(t_prime: float, run: Run) -> float:
    """φ the band experienced as it left the column (research doc §3.2)."""
    gradient = run.gradient
    return gradient.phi0 + gradient.delta_phi * t_prime / gradient.t_gradient


def _seed_steepness(t_prime_steep: float, t_prime_shallow: float, beta: float, t0: float) -> float:
    """The §3.2 large-k0 closed form for b_e of the steeper run — a starting bracket only."""
    return t0 * math.log(beta) / (t_prime_steep - t_prime_shallow / beta)


def _solve_steepness(
    t_prime_steep: float,
    t_prime_shallow: float,
    beta: float,
    t0: float,
    *,
    seed: float,
    b_e_max: float,
) -> float:
    """Root of the exact two-run condition g(b) = 0, b = b_e of the steeper run (§3.3).

    g(0) = 0 always and g dips negative just above it, so the bracket starts strictly
    above zero; the §3.2 closed form supplies the scale to expand from, and the search
    stops at the ``b_e_max`` equivalent of S_e = 200 rather than running away.
    """
    rate_steep = t_prime_steep / t0
    rate_shallow = t_prime_shallow / (beta * t0)

    def g(b: float) -> float:
        return math.expm1(b * rate_steep) - beta * math.expm1(b * rate_shallow)

    lower = min(seed, b_e_max) * 1e-6
    upper = min(seed, b_e_max)
    while g(upper) <= 0.0:
        if upper >= b_e_max:
            raise ValueError(
                f"no solution below S_e = {_S_E_MAX:g}: the two runs place this peak "
                "at an implausible solvent strength — check the retention times"
            )
        upper = min(upper * 2.0, b_e_max)
    root: float = brentq(g, lower, upper, xtol=1e-15, rtol=8.9e-16)
    return root


def _check_runs_are_a_scouting_pair(run1: Run, run2: Run) -> None:
    """The §3.3 elimination holds only for runs identical but for gradient time."""
    if run1.gradient.t_gradient == run2.gradient.t_gradient:
        raise ValueError(
            "the two scouting runs have the same gradient time "
            f"({run1.gradient.t_gradient:g} min): they carry one measurement, not two"
        )
    fixed1 = (run1.gradient.phi0, run1.gradient.phif, run1.gradient.t_init)
    fixed2 = (run2.gradient.phi0, run2.gradient.phif, run2.gradient.t_init)
    if fixed1 != fixed2:
        raise ValueError(
            "the two scouting runs must differ only in gradient time; "
            f"got (φ0, φf, t_init) = {fixed1} and {fixed2}"
        )
