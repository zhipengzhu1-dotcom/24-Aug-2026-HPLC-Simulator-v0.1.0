"""Peak width in gradient elution (SPEC §3; research doc §5).

σ_t = G·t0·(1 + k_e)/√N, with N a global plate-count knob and G the band
compression factor of §5.2. All steepness math is in the natural-log convention
(b_e), which is also the convention G's ``p`` is written in — see
:func:`band_compression_factor` for why, and §5.4 of the research doc for the
calibration evidence against measured widths.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hplcsim.model import Gradient, Method, RetentionParams
from hplcsim.retention import gradient_steepness, predict_retention

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
    ~10–15% at typical steepness — the project's #1 named hazard. The lab
    calibration that bounds it empirically is recorded in research doc §5.4.
    """
    if b_e < 0.0:
        raise ValueError(f"b_e must be non-negative, got {b_e}")
    p = b_e * k0 / (1.0 + k0)
    return math.sqrt(1.0 + p + p * p / 3.0) / (1.0 + p)


@dataclass(frozen=True)
class PeakWidth:
    """Predicted width of one peak under one gradient, in minutes.

    ``g`` and ``plate_count`` are reported rather than hidden because they are the
    two assumptions the number rests on: G is the calibrated compression factor
    actually applied (1.0 outside the gradient regime), and N is the global knob.
    ``k_e`` is the retention factor at elution, carried through from the retention
    prediction so callers need not recompute it.

    ``plate_count_is_default`` stamps a width that rests on the column-geometry
    estimate rather than a user-supplied N — the same posture SPEC §4 takes on an
    estimated t0 ("labeled fallback that stamps predictions lower-confidence").
    It matters: against the lab dataset the h = 2 default lands widths at
    0.67–0.91× measured and Rs 28–47% high (research doc §5.4, §6).
    """

    sigma: float
    w_half: float
    w_base: float
    g: float
    plate_count: float
    k_e: float
    plate_count_is_default: bool


def peak_width(
    params: RetentionParams,
    method: Method,
    gradient: Gradient,
    *,
    plate_count: float | None = None,
) -> PeakWidth:
    """Predict the width of one peak under ``gradient`` (research doc §5.1, §5.3).

    ``plate_count`` defaults to :func:`default_plate_count` for the column.
    """
    plate_count_is_default = plate_count is None
    n = default_plate_count(method) if plate_count_is_default else plate_count
    assert n is not None
    if n <= 0.0:
        raise ValueError(f"plate count must be positive, got {n}")

    retention = predict_retention(params, method, gradient)

    # §5.3: compression is a property of migrating through a rising composition.
    # A band that left before the ramp arrived, or that finishes isocratically at
    # φf after it ends, never experiences one — G = 1 for both (§4.1, §4.2).
    if retention.regime == "gradient":
        b_e = gradient_steepness(method, gradient, params.s_e)
        g = band_compression_factor(b_e, k0=params.k_at(gradient.phi0))
    else:
        g = 1.0

    sigma = g * method.t0 * (1.0 + retention.k_e) / math.sqrt(n)
    return PeakWidth(
        sigma=sigma,
        w_half=_W_HALF_PER_SIGMA * sigma,
        w_base=_W_BASE_PER_SIGMA * sigma,
        g=g,
        plate_count=n,
        k_e=retention.k_e,
        plate_count_is_default=plate_count_is_default,
    )
