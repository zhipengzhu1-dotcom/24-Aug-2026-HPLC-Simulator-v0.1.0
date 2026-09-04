"""Peak width in gradient elution (SPEC §3; research doc §5).

σ_t = G·t0·(1 + k_e)/√N, with G the band compression factor of §5.2 and N the plate
count per peak — fitted from that peak's measured scouting widths when it has any
(:func:`fit_plate_count`), else the user's global knob, else the column default
(SPEC §3, §4). All steepness math is in the natural-log convention
(b_e), which is also the convention G's ``p`` is written in — see
:func:`band_compression_factor` for why, and §5.4 of the research doc for the
calibration that settled it against measured widths.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean
from typing import Literal

from hplcsim.model import Gradient, Method, Peak, RetentionParams, Run, Target
from hplcsim.retention import predict_retention

# Reduced plate height for a well-packed sub-2 µm column: N = L/(h·dp) with h = 2.
# A documented textbook basis for the default, not a fit to any one instrument —
# the lab column's measured widths imply h ≈ 2.4–4.1 once extra-column broadening
# is folded in, which is exactly the instrument-specific part a global default
# should not absorb (research doc §5.1).
_REDUCED_PLATE_HEIGHT = 2.0

_UM_PER_MM = 1000.0

# W½ = √(8 ln 2)·σ. §6 is explicit that the exact constant is used, not the 2.355
# or 1.178 roundings the literature quotes — those cost ~0.04% on every Rs.
_W_HALF_PER_SIGMA = math.sqrt(8.0 * math.log(2.0))
_W_BASE_PER_SIGMA = 4.0


def default_plate_count(method: Method) -> float:
    """Column-based default for the plate-count knob N (SPEC §4)."""
    if method.column_length_mm is None or method.particle_um is None:
        raise ValueError(
            "a column length and particle size are needed to estimate a default "
            "plate count; supply N explicitly instead"
        )
    particle_mm = method.particle_um / _UM_PER_MM
    return method.column_length_mm / (_REDUCED_PLATE_HEIGHT * particle_mm)


def band_compression_factor(b_e: float, k0: float) -> float:
    """Band compression factor G for steepness ``b_e`` and retention ``k0`` at φ0.

    G(p) = √(1 + p + p²/3)/(1 + p) with p = b_e·k0/(1 + k0) — research doc §5.2,
    from Wilson et al. (2016) Eqs. 8–9 and Hao et al. (2021) Eq. 3, which agree
    exactly and both attribute it to Poppe et al. (1981).

    ``p`` is in the **natural-log convention**: neither source writes a 2.303
    beside b, and Snyder's base-10 form p = 2.303·b·k0/(1 + k0) is the same
    number because b = b_e/ln 10. Slipping that factor either way moves G by
    ~10–15% at typical steepness — the project's #1 named hazard.

    Settled empirically as well as textually: this convention holds a real
    column's plate count constant to 0.92% across a fourfold range of gradient
    steepness, where every alternative scatters by 5–13% (research doc §5.4,
    on held-out lab runs).
    """
    if b_e < 0.0:
        raise ValueError(f"b_e must be non-negative, got {b_e}")
    p = b_e * k0 / (1.0 + k0)
    return math.sqrt(1.0 + p + p * p / 3.0) / (1.0 + p)


# Where a width's N came from: the column-geometry estimate, the user's global knob,
# or a fit to that peak's own measured widths. Measured-first, the posture SPEC §4
# takes on t0 — and the signal SPEC §6 diagnostic 5 reads: only "default" is caveated.
PlateCountSource = Literal["default", "supplied", "fitted"]


@dataclass(frozen=True)
class FittedPlateCount:
    """A peak's plate count fitted from its measured scouting widths.

    ``plate_count`` is the geometric mean of the plate counts each width implies —
    least squares in ln W, the maximum-likelihood estimate when width error scales
    with width (research doc ``plate-count-from-widths.md`` §3.2–3.3). It is an
    *apparent*, instrument-inclusive efficiency conditional on the calibrated G
    (§1.4, §2.2–2.3): the number that reproduces this instrument's gradient widths,
    not the column's intrinsic N and not a pharmacopoeial plate number.

    ``implied_run1`` / ``implied_run2`` are the per-width values (``None`` where the
    peak carries no width in that run), and ``ratio`` is their disagreement — the
    consistency diagnostic of §6 item 3. A correctly modelled peak holds it near 1
    (gradient-math doc §5.4: 0.92% across a fourfold range of tG); thresholding it
    is the diagnostics ticket's job, not this module's.

    ``low_confidence`` marks a fit that rests *only* on post-gradient widths — where
    the band was compressed under the ramp and then broadened isocratically, so
    inverting with G = 1 inherits an unquantified model error (§4.3). Such a width is
    left out of ``plate_count`` whenever the other run's width is usable (its
    ``implied_run`` value is still reported, so ``ratio`` shows the disagreement); it
    is used, and stamped, only when it is all the peak has.
    """

    plate_count: float
    implied_run1: float | None
    implied_run2: float | None
    low_confidence: bool

    @property
    def ratio(self) -> float | None:
        """implied_run1 / implied_run2, or ``None`` unless both runs carried a width."""
        if self.implied_run1 is None or self.implied_run2 is None:
            return None
        return self.implied_run1 / self.implied_run2


@dataclass(frozen=True)
class PeakWidth:
    """Predicted width of one peak under one gradient, in minutes.

    ``g`` and ``plate_count`` are reported rather than hidden because they are the
    two assumptions the number rests on: G is the calibrated compression factor
    actually applied (1.0 outside the gradient regime), and N is the plate count the
    width rests on, with ``plate_count_source`` saying where it came from.
    ``k_e`` is the retention factor at elution, carried through from the retention
    prediction so callers need not recompute it.

    ``plate_count_source`` records where N came from — the same posture SPEC §4
    takes on an estimated t0 ("labeled fallback that stamps predictions
    lower-confidence"). It matters: against the lab dataset the h = 2 default lands
    widths at 0.69–0.92× measured and Rs 18–39% high at held-out conditions, while
    an N fitted from the peak's own widths lands them at 0.99–1.16× (research docs
    ``gradient-elution-math.md`` §6 and ``plate-count-from-widths.md`` §0.2).
    """

    sigma: float
    w_half: float
    w_base: float
    g: float
    plate_count: float
    k_e: float
    plate_count_source: PlateCountSource


def peak_width(
    params: RetentionParams,
    method: Method,
    target: Target,
    *,
    plate_count: float | FittedPlateCount | None = None,
) -> PeakWidth:
    """Predict the width of one peak under ``target`` (research doc §5.1, §5.3).

    ``target`` is a v0.1 :class:`~hplcsim.model.Gradient` or a v0.2
    :class:`~hplcsim.model.Programme`; a one-segment programme is bitwise identical to
    its gradient, and two or more segments take the walker's retention with G from the
    segment the band leaves on.

    ``plate_count`` is a number the user supplied, a :class:`FittedPlateCount` from
    that peak's own measured widths, or ``None`` for :func:`default_plate_count`.
    """
    n, plate_count_source = _resolve_plate_count(plate_count, method)
    if n <= 0.0:
        raise ValueError(f"plate count must be positive, got {n}")

    retention = predict_retention(params, method, target)

    # §5.3: compression is a property of migrating through a rising composition.
    # A band that left before the ramp arrived, or that finishes isocratically at
    # φf after it ends, never experiences one — G = 1 for both (§4.1, §4.2).
    #
    # For a programme, SPEC §3's rule ("Band compression for a programme"): G comes from
    # the *segment in which the band elutes* — p formed from that segment's own b_e,seg
    # and the k at the band's entry to that segment — and G = 1 for a band leaving in a
    # hold or after the last segment ends. On one segment the entry composition is φ0
    # and b_e,seg is b_e, so this is exactly the v0.1 branch. The cumulative compression
    # integral (Hao et al. Eq. 10) was considered and deferred; this is the approximation
    # that ships, unvalidated by any multi-segment width (SPEC §10 makes no Rs claim).
    #
    # A band leaving on a *descending* leg gets G = 1 as well: Poppe's G is derived for
    # a composition rising across the band, and no source here extends it to a falling
    # one, so nothing is claimed — the same posture as the hold.
    # The eluting leg's steepness and entry k ride on the prediction (#89); the programme
    # is not re-walked here. A hold arrives as b_e,seg = 0.0 and a descending leg as
    # b_e,seg < 0.0, so both reach G = 1 through the one test below.
    g = 1.0
    b_e_seg, k_seg_entry = retention.b_e_seg, retention.k_seg_entry
    if (
        retention.regime == "gradient"
        and b_e_seg is not None
        and k_seg_entry is not None
        and b_e_seg > 0.0
    ):
        g = band_compression_factor(b_e_seg, k0=k_seg_entry)

    sigma = g * method.t0 * (1.0 + retention.k_e) / math.sqrt(n)
    return PeakWidth(
        sigma=sigma,
        w_half=_W_HALF_PER_SIGMA * sigma,
        w_base=_W_BASE_PER_SIGMA * sigma,
        g=g,
        plate_count=n,
        k_e=retention.k_e,
        plate_count_source=plate_count_source,
    )


def _resolve_plate_count(
    plate_count: float | FittedPlateCount | None, method: Method
) -> tuple[float, PlateCountSource]:
    """The N a width rests on, and where it came from."""
    if plate_count is None:
        return default_plate_count(method), "default"
    if isinstance(plate_count, FittedPlateCount):
        return plate_count.plate_count, "fitted"
    return plate_count, "supplied"


def plate_count_from_width(
    params: RetentionParams, method: Method, gradient: Gradient, w_half: float
) -> float:
    """N implied by one measured W½ (min) — the inverse of :func:`peak_width`.

    σ ∝ 1/√N, so N = (W½ predicted at N = 1 / W½ measured)². Going through
    :func:`peak_width` rather than restating the equation keeps the width model, its
    regime branch and G in one place: the inverse cannot drift from the forward form
    (research doc ``plate-count-from-widths.md`` §4.1). In the hold regime this is
    exactly the pharmacopoeial N = 8 ln 2·(tR/W½)² (§4.2).
    """
    if w_half <= 0.0:
        raise ValueError(f"a measured width must be positive, got {w_half}")
    unit_width = peak_width(params, method, gradient, plate_count=1.0).w_half
    return (unit_width / w_half) ** 2


def fit_plate_count(
    peak: Peak, params: RetentionParams, method: Method, run1: Run, run2: Run
) -> FittedPlateCount | None:
    """Fit one peak's N from whichever scouting widths it carries; ``None`` if none.

    ``params`` is that peak's retention fit: the inverse needs G and k_e at each
    scouting run, and both come from (k0, S_e). One width is enough — §3.2's estimator
    is written for n widths and n = 1 is its degenerate case; that a single width still
    beats a geometry estimate is the build brief's call (design item 4). Two widths give
    the ``ratio`` diagnostic as well.

    A post-gradient width (§4.3) is left out of ``plate_count`` when the other run's
    width is usable — dropping a known-biased measurement is not a block — and used,
    with the result stamped ``low_confidence``, only when it is all the peak has.
    """
    widths = ((run1, peak.w_half_run1), (run2, peak.w_half_run2))
    implied = [
        None if w_half is None else plate_count_from_width(params, method, run.gradient, w_half)
        for run, w_half in widths
    ]
    present = [n for n in implied if n is not None]
    if not present:
        return None
    usable = [
        n
        for (run, _), n in zip(widths, implied, strict=True)
        if n is not None
        and predict_retention(params, method, run.gradient).regime != "post_gradient"
    ]
    return FittedPlateCount(
        plate_count=math.exp(fmean(math.log(n) for n in usable or present)),
        implied_run1=implied[0],
        implied_run2=implied[1],
        low_confidence=not usable,
    )
