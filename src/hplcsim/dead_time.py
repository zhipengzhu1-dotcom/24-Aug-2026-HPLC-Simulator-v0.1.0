"""Dead time from column geometry, and the check a measured one gets (SPEC §4, #24).

The estimate is the textbook relation

    V_M [mL] = ε_total · (π/4) · d_c² · L · 1e-3,     t0 = V_M / F

with d_c and L in mm and F in mL/min — the repo's units (research doc
`dead-time-from-geometry.md` §7.1). ε_total is the *total* porosity, interstitial plus
intraparticle, because t0 is the elution time of a marker that permeates the pores
(that doc's §2.2). Its value is selected by the **declared packing architecture** and
nothing else: fully porous 0.62, core–shell 0.52, each with the credible band the
literature supports (`porosity-for-t0-geometry.md` §5.1). Undeclared architecture is
refused, not defaulted — a silently wrong architecture is a 16% t0 error that would
also disarm the reverse check below (#34, decision 2).

The reverse check is worth more than the estimate. Geometry excludes the plumbing by
construction — injector, tubing, detector cell — so a *measured* t0 should read
**above** the geometry estimate, and the gap is the extra-column volume:

    ε_implied = F·t0 / V_col,     V_ec = F·(t0 − t0_geom)

Both are reported as facts. Warnings fire only on the impossible or implausible side
(:func:`check_measured_t0`), never on "differs from the constant": the project's own
column sits 16% above its architecture's constant and is entirely ordinary.

Measured-first is the caller's rule, not this module's. :class:`~hplcsim.model.Method`
carries ``t0_is_measured``; the app autofills the estimate into the t0 field and stamps
it ``False`` (SPEC §6 diagnostic 6), and a typed value wins outright. Nothing here
touches the fit — which is why a wrong t0 is cheap for the predictions and expensive
only for the fitted parameters (research doc §6).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Final, Literal

from hplcsim.model import Method

# (π/4) × 1e-3 mL·mm⁻³ — the one numeric constant of the estimator, written exactly
# (research doc §7.1: never the rounded 0.000785), as `width.py` writes √(8 ln 2).
_ML_PER_MM3: Final = math.pi / 4.0 / 1000.0

Architecture = Literal["fully_porous", "core_shell"]


@dataclass(frozen=True)
class Porosity:
    """One architecture's total porosity: the default and the band it is quoted with.

    The band is a spread between disagreeing literature sources, not a confidence
    interval (`porosity-for-t0-geometry.md` §5.4) — which is why it is shown as text
    beside the estimate and never as a ± on anything fitted (#34, decision 3).
    """

    architecture: Architecture
    value: float
    band: tuple[float, float]

    @property
    def label(self) -> str:
        return "fully porous" if self.architecture == "fully_porous" else "core–shell"


# `porosity-for-t0-geometry.md` §5.1. Both defaults sit at the low end of their
# structural range on purpose, so that a geometry estimate reads at-or-below a marker
# time (that doc's §2.5 and §4.1). Waters' own 0.66 / 0.49 (WKB28079) fall inside the
# bands and are not used.
POROSITY: Final[dict[Architecture, Porosity]] = {
    "fully_porous": Porosity("fully_porous", 0.62, (0.52, 0.70)),
    "core_shell": Porosity("core_shell", 0.52, (0.45, 0.60)),
}

# The reverse check's tiers (research doc §7.5, decided on #34). Judgement grounded in
# the physical limits, not cited ranges: a packed bed cannot hold more mobile phase
# than an empty tube, and ε_total below ~0.35 or above ~0.80 is outside anything a
# packed column measures (`porosity-for-t0-geometry.md` §5.4).
POROSITY_IMPOSSIBLE: Final = 1.0
POROSITY_PLAUSIBLE: Final = (0.35, 0.80)

# Extra-column volume of a UHPLC system, injector to detector — Handlovic's measured
# 26–78 µL (`porosity-for-t0-geometry.md` §4.1), in the engine's mL. Above it the marker
# is probably retained, or the time includes something that is not plumbing. The warning
# edge is the lower end of #34's "≳ 80–100 µL", just past the top of the measured range.
# µL is a display unit: the app converts at its boundary, as it does %B.
EXTRA_COLUMN_VOLUME_TYPICAL_ML: Final = (0.026, 0.078)
EXTRA_COLUMN_VOLUME_RETAINED_ML: Final = 0.080


def architecture_of(method: Method) -> Architecture | None:
    """The declared packing architecture, or ``None`` when the user has not said."""
    if method.particle_is_solid_core is None:
        return None
    return "core_shell" if method.particle_is_solid_core else "fully_porous"


def porosity_for(method: Method) -> Porosity:
    """The porosity the geometry estimate uses — refused, never guessed, when undeclared."""
    architecture = architecture_of(method)
    if architecture is None:
        raise ValueError(
            "particle_is_solid_core is needed to estimate t0 from geometry: the total "
            "porosity differs by 16% between fully porous and core–shell packings, and "
            "guessing one would hide exactly the error the reverse check exists to catch — "
            "declare the packing architecture instead"
        )
    return POROSITY[architecture]


def column_volume_ml(method: Method) -> float:
    """The empty-tube volume V_col = (π/4)·d_c²·L, in mL, from mm dimensions."""
    if method.column_id_mm is None:
        raise ValueError(
            "column_id_mm is needed to compute the column volume; "
            "enter the column's internal diameter"
        )
    if method.column_length_mm is None:
        raise ValueError(
            "column_length_mm is needed to compute the column volume; enter the column length"
        )
    return _ML_PER_MM3 * method.column_id_mm**2 * method.column_length_mm


@dataclass(frozen=True)
class DeadTimeEstimate:
    """t0 from geometry, with what it rests on: the porosity used and its band in minutes."""

    t0: float
    v_m_ml: float
    column_volume_ml: float
    porosity: Porosity
    t0_band: tuple[float, float]


def estimate_t0(method: Method) -> DeadTimeEstimate:
    """SPEC §4's geometry fallback for t0 — research doc §7.1 with §7.2's constants.

    Raises a ``ValueError`` naming the missing field when the column i.d., the column
    length or the packing architecture is absent, as :func:`~hplcsim.width.default_plate_count`
    does for its inputs. Returns the number; whether it is *used* is the caller's
    measured-first decision, and the stamp is ``Method.t0_is_measured = False``.
    """
    porosity = porosity_for(method)
    volume = column_volume_ml(method)
    _check_flow(method.flow)
    lo, hi = porosity.band
    return DeadTimeEstimate(
        t0=porosity.value * volume / method.flow,
        v_m_ml=porosity.value * volume,
        column_volume_ml=volume,
        porosity=porosity,
        t0_band=(lo * volume / method.flow, hi * volume / method.flow),
    )


Finding = Literal[
    "plausible",
    "impossible_porosity",
    "implausible_porosity",
    "below_geometry",
    "marker_retained",
]


@dataclass(frozen=True)
class DeadTimeCheck:
    """What a measured t0 implies about the column and the plumbing (research doc §7.5).

    ``implied_porosity`` needs only the column geometry. ``geometry`` and
    ``extra_column_volume_ml`` need the architecture as well and are ``None`` without
    it — the accepted cost of refusing to guess: with the architecture undeclared the
    check keeps only its two porosity bounds and loses its sharpest tier (#34), so a
    ``"plausible"`` finding then means only that the porosity bounds passed.
    """

    implied_porosity: float
    column_volume_ml: float
    geometry: DeadTimeEstimate | None
    extra_column_volume_ml: float | None
    finding: Finding


def check_measured_t0(method: Method) -> DeadTimeCheck:
    """The reverse check: read ε_total and V_ec back out of a measured t0.

    A readout, not a warning. ``finding`` is ``"plausible"`` for the expected
    ordering — measured above geometry by a plumbing-sized volume — and names the
    tier otherwise, worst first: more mobile phase than an empty tube (impossible),
    a porosity no packed column has, a marker leaving *before* the mobile phase
    (usually a mis-declared architecture), or a gap too large to be plumbing.
    """
    volume = column_volume_ml(method)
    _check_flow(method.flow)
    implied = method.flow * method.t0 / volume

    geometry: DeadTimeEstimate | None = None
    extra_column_ml: float | None = None
    if architecture_of(method) is not None:
        geometry = estimate_t0(method)
        extra_column_ml = method.flow * (method.t0 - geometry.t0)

    return DeadTimeCheck(
        implied_porosity=implied,
        column_volume_ml=volume,
        geometry=geometry,
        extra_column_volume_ml=extra_column_ml,
        finding=_finding(implied, extra_column_ml),
    )


def _finding(implied_porosity: float, extra_column_ml: float | None) -> Finding:
    lo, hi = POROSITY_PLAUSIBLE
    if implied_porosity > POROSITY_IMPOSSIBLE:
        return "impossible_porosity"
    if not lo <= implied_porosity <= hi:
        return "implausible_porosity"
    if extra_column_ml is None:
        return "plausible"
    if extra_column_ml < 0.0:
        return "below_geometry"
    if extra_column_ml >= EXTRA_COLUMN_VOLUME_RETAINED_ML:
        return "marker_retained"
    return "plausible"


def _check_flow(flow: float) -> None:
    if flow <= 0.0:
        raise ValueError(f"flow must be positive to convert a volume to a time, got {flow}")


# --- the marker ---------------------------------------------------------------------------

MarkerKind = Literal["absent", "solvent_disturbance", "inorganic_salt", "compound"]

# Research doc §5.2. A solvent disturbance is not a compound and is "strongly discouraged"
# as a hold-up marker (Redón 2023); a dilute inorganic salt is Donnan-excluded from the
# pores and measures the interstitial volume only — ~40% low on a fully porous column
# (David 2025). Matched on whole words so "KI" cannot fire inside "Kinetex", and the
# disturbance vocabulary is kept narrow so "uracil, 1 µL injection, apex" stays a compound.
_SOLVENT_DISTURBANCE_WORDS: Final = frozenset({"solvent", "front", "disturbance"})
_SOLVENT_DISTURBANCE_PHRASES: Final = ("system peak", "injection peak", "void peak")
_INORGANIC_SALT_WORDS: Final = frozenset(
    {
        "nitrate",
        "nitrite",
        "bromide",
        "iodide",
        "chloride",
        "salt",
        "nano3",
        "kno3",
        "nano2",
        "kno2",
        "kbr",
        "nabr",
        "ki",
        "nai",
        "nacl",
        "kcl",
    }
)
_WORDS: Final = re.compile(r"[a-z0-9]+")


def classify_marker(marker: str | None) -> MarkerKind:
    """What kind of thing the recorded t0 marker is — the provenance check of §7.6."""
    text = (marker or "").lower()
    words = set(_WORDS.findall(text))
    if not words:
        return "absent"
    if words & _INORGANIC_SALT_WORDS:
        return "inorganic_salt"
    if words & _SOLVENT_DISTURBANCE_WORDS or any(p in text for p in _SOLVENT_DISTURBANCE_PHRASES):
        return "solvent_disturbance"
    return "compound"
