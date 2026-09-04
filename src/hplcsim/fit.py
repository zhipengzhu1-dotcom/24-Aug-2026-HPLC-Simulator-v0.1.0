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
from typing import Literal, NamedTuple

from scipy.optimize import brentq

from hplcsim.model import Method, Peak, RetentionParams, Run, log10_k0_from_ln_k0
from hplcsim.retention import predict_retention
from hplcsim.width import FittedPlateCount, fit_plate_count

# Guillarme et al.'s constraint on the closed form: below log10 k0 = 2.1 the large-k0
# approximation is worth tens of percent in S, so the data are thin even though the
# root-find itself stays exact (research doc §3.2). Public because SPEC §6 diagnostic 8
# applies the same floor at the *candidate's* start (#72), and a second copy of the
# number in the app layer is how a floor drifts.
LOW_K0_LOG10 = 2.1

# SPEC §4's spacing-ratio tiers — "warning < 2.5, strong < 1.2, never a hard block".
# Research doc §7.2's table is the evidence behind them: at β = 1.2 a 0.6 s timing
# error already moves S by 2%, and by β = 1.05 it moves it by 9%.
#
# Public, and :func:`classify_spacing` with them, because SPEC §4 applies the same two
# tiers at *entry* — before any peak has been fitted — and ticket #20's entry check
# would otherwise be a second copy of these two numbers in the app layer.
BETA_WARNING = 2.5
BETA_STRONG = 1.2

# The SPEC §3 self-check tolerance: the fit must reproduce both input retention times.
_MAX_RESIDUAL = 1e-8

# Cap the search at S_e = 200: past that the exponentials overflow long before any
# real small molecule does (research doc §3.3).
_S_E_MAX = 200.0


BetaSpacing = Literal["ok", "warning", "strong"]


class _Oriented(NamedTuple):
    """The scouting pair re-expressed steeper-run-first, which is what §3.3 assumes."""

    steep: Run
    shallow: Run
    t_prime_steep: float
    t_prime_shallow: float
    beta: float
    steep_is_run1: bool

    def by_argument_order(self, steep_value: float, shallow_value: float) -> tuple[float, float]:
        """Put a (steep, shallow) pair back into the order the caller passed the runs."""
        return (steep_value, shallow_value) if self.steep_is_run1 else (shallow_value, steep_value)


@dataclass(frozen=True)
class FitResult:
    """The fitted parameters for one peak, plus the facts that condition them.

    ``beta_spacing`` is SPEC §6 diagnostic 3's escalation tier.
    ``phi_e_run1`` / ``phi_e_run2`` are the compositions the band experienced when it
    eluted in each run, in the order the runs were passed; their separation is the
    conditioning number of the whole fit (research doc §7.2). ``seed_s_e`` is the
    §3.2 large-k0 closed form — reported for diagnostics only, never the answer.
    ``plate_count`` is the peak's N fitted from whichever scouting widths it carries
    (:func:`~hplcsim.width.fit_plate_count`), ``None`` when it carries none — the
    caller then falls through to the global knob or the column default.
    """

    params: RetentionParams
    beta: float
    phi_e_run1: float
    phi_e_run2: float
    seed_s_e: float
    max_residual: float
    beta_spacing: BetaSpacing
    low_k0: bool
    low_confidence: bool
    plate_count: FittedPlateCount | None

    @property
    def delta_phi_e(self) -> float:
        """Separation of the two elution compositions — the fit's conditioning number."""
        return self.phi_e_run1 - self.phi_e_run2


def fit_peak(peak: Peak, method: Method, run1: Run, run2: Run) -> FitResult:
    """Fit (ln k0, S_e) for one peak from its retention time in each scouting run."""
    oriented = _orient(peak, method, run1, run2)
    gradient = oriented.steep.gradient
    t0 = method.t0
    tau = method.t_dwell + gradient.t_init

    # b_e and S_e differ only by this scale factor, fixed by the steeper run's design.
    s_e_per_b_e = gradient.t_gradient / (t0 * gradient.delta_phi)
    seed_b_e = _seed_steepness(oriented, t0)
    b_e = _solve_steepness(oriented, t0, seed=seed_b_e, b_e_max=_S_E_MAX / s_e_per_b_e)
    k0 = math.expm1(b_e * oriented.t_prime_steep / t0) / b_e + tau / t0
    params = RetentionParams(ln_k0=math.log(k0), s_e=b_e * s_e_per_b_e, phi_ref=gradient.phi0)

    phi_e_run1, phi_e_run2 = oriented.by_argument_order(
        _elution_composition(oriented.t_prime_steep, oriented.steep),
        _elution_composition(oriented.t_prime_shallow, oriented.shallow),
    )
    max_residual = max(
        abs(predict_retention(params, method, run.gradient).t_r - t_r)
        for run, t_r in ((run1, peak.t_r_run1), (run2, peak.t_r_run2))
    )
    low_k0 = log10_k0_from_ln_k0(params.ln_k0) < LOW_K0_LOG10
    beta_spacing = classify_spacing(oriented.beta)
    return FitResult(
        params=params,
        beta=oriented.beta,
        phi_e_run1=phi_e_run1,
        phi_e_run2=phi_e_run2,
        seed_s_e=seed_b_e * s_e_per_b_e,
        max_residual=max_residual,
        beta_spacing=beta_spacing,
        low_k0=low_k0,
        low_confidence=(low_k0 or beta_spacing != "ok" or max_residual > _MAX_RESIDUAL),
        plate_count=fit_plate_count(peak, params, method, run1, run2),
    )


def classify_spacing(beta: float) -> BetaSpacing:
    """SPEC §4's spacing-ratio tiers — a warning, never a block."""
    if beta < BETA_STRONG:
        return "strong"
    if beta < BETA_WARNING:
        return "warning"
    return "ok"


def _orient(peak: Peak, method: Method, run1: Run, run2: Run) -> _Oriented:
    """Re-express the pair steeper-run-first and reject data that admit no LSS fit."""
    _check_runs_are_a_scouting_pair(run1, run2)

    steep, shallow = sorted((run1, run2), key=lambda r: r.gradient.t_gradient)
    steep_is_run1 = steep is run1
    t_r_steep, t_r_shallow = (
        (peak.t_r_run1, peak.t_r_run2) if steep_is_run1 else (peak.t_r_run2, peak.t_r_run1)
    )

    dead_and_hold = method.t0 + method.t_dwell + steep.gradient.t_init
    t_prime_steep = t_r_steep - dead_and_hold
    t_prime_shallow = t_r_shallow - dead_and_hold
    beta = shallow.gradient.t_gradient / steep.gradient.t_gradient

    # Not the SPEC §6 early-eluter *badge*, which flags peaks that elute soon after the
    # gradient arrives and still fit: this is the case where the band is already off the
    # column before the gradient reaches it, so both runs are the same isocratic
    # measurement and carry no information about S at all. Nothing to warn about — there
    # is no fit to annotate.
    if t_prime_steep <= 0.0 or t_prime_shallow <= 0.0:
        raise ValueError(
            "peak elutes before the gradient reaches the column "
            f"(tR must exceed t0 + τ = {dead_and_hold:.4g} min in both runs); nothing to fit"
        )
    # §3.3: the steeper gradient must elute the band at the *higher* composition, or
    # g(b) never turns positive and the data admit no LSS solution.
    if t_prime_steep <= t_prime_shallow / beta:
        raise ValueError(
            "shallower run elutes this peak at a higher %B than the steeper run: "
            "no LSS solution exists — check peak tracking"
        )
    # The other end of the same bracket, and the one that used to hang. g'(0) has the
    # sign of (t'_steep − t'_shallow), so when the steeper run elutes the band *later*
    # g never dips below zero, the root-find in :func:`_solve_steepness` has nothing to
    # bracket, and its walk down shrinks the lower bound to 0.0 and spins there. A
    # steeper gradient cannot elute a compound later than a shallower one, so these data
    # are inconsistent whatever the cause — found while wiring ticket #20's entry checks,
    # where swapping the two tR columns reaches it from the screen.
    if t_prime_steep >= t_prime_shallow:
        raise ValueError(
            f"steeper run (tG {steep.gradient.t_gradient:g} min) elutes this peak at "
            f"t'R = {t_prime_steep:.4g} min, later than the shallower run "
            f"(tG {shallow.gradient.t_gradient:g} min) at {t_prime_shallow:.4g} min: "
            "no LSS solution exists — check that the two runs' retention times are the "
            "right way round, and check peak tracking"
        )
    return _Oriented(
        steep=steep,
        shallow=shallow,
        t_prime_steep=t_prime_steep,
        t_prime_shallow=t_prime_shallow,
        beta=beta,
        steep_is_run1=steep_is_run1,
    )


def fit_peaks(peaks: Sequence[Peak], method: Method, run1: Run, run2: Run) -> list[FitResult]:
    """Fit every peak independently — no peak's data informs another's (§3.4 step 4)."""
    return [fit_peak(peak, method, run1, run2) for peak in peaks]


def _elution_composition(t_prime: float, run: Run) -> float:
    """φ the band experienced as it left the column (research doc §3.2)."""
    gradient = run.gradient
    return gradient.phi0 + gradient.delta_phi * t_prime / gradient.t_gradient


def _seed_steepness(oriented: _Oriented, t0: float) -> float:
    """The §3.2 large-k0 closed form for b_e of the steeper run — a starting bracket only."""
    return (
        t0
        * math.log(oriented.beta)
        / (oriented.t_prime_steep - oriented.t_prime_shallow / oriented.beta)
    )


def _solve_steepness(oriented: _Oriented, t0: float, *, seed: float, b_e_max: float) -> float:
    """Root of the exact two-run condition g(b) = 0, b = b_e of the steeper run (§3.3).

    g(0) = 0 always and g dips negative just above it, so the bracket starts strictly
    above zero; the §3.2 closed form supplies the scale to expand from, and the search
    stops at the ``b_e_max`` equivalent of S_e = 200 rather than running away.
    """
    beta = oriented.beta
    rate_steep = oriented.t_prime_steep / t0
    rate_shallow = oriented.t_prime_shallow / (beta * t0)

    def g(b: float) -> float:
        return math.expm1(b * rate_steep) - beta * math.expm1(b * rate_shallow)

    upper = min(seed, b_e_max)
    lower = upper * 1e-6
    # g is negative on (0, root), so any lower bound below the root brackets it. Walk
    # down rather than trusting the seed's scale, so a badly-placed seed cannot hand
    # brentq a same-sign bracket.
    while g(lower) >= 0.0:
        lower *= 1e-3
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
