"""Data model for methods, gradients, runs and peaks (SPEC §4).

Unit conventions: minutes, mL, mm, µm, °C. The strong-solvent fraction φ is a
0–1 fraction everywhere inside the engine; %B (0–100) exists only at the entry
and display boundaries via :func:`phi_from_percent_b` / :func:`percent_b_from_phi`.

Retention parameters are held in the natural-log convention (ln k0, S_e). The
base-10 solvent-strength S that chromatographers quote is a display quantity,
and :func:`s_base10_from_s_e` / :func:`s_e_from_s_base10` are the only place
the ln(10) factor appears.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_LN10 = math.log(10.0)


def phi_from_percent_b(percent_b: float) -> float:
    """Entry boundary: %B (0–100) -> φ (0–1)."""
    return percent_b / 100.0


def percent_b_from_phi(phi: float) -> float:
    """Display boundary: φ (0–1) -> %B (0–100)."""
    return phi * 100.0


def s_base10_from_s_e(s_e: float) -> float:
    """Display boundary: natural-log S_e -> base-10 S (the only ln(10) in the engine)."""
    return s_e / _LN10


def s_e_from_s_base10(s: float) -> float:
    """Entry boundary: base-10 S -> natural-log S_e."""
    return s * _LN10


@dataclass(frozen=True)
class Method:
    """Method constants shared by every run (SPEC §4).

    ``t0`` is the column dead time in minutes, ``t_dwell`` the instrument dwell
    time in minutes (V_D / F, converted by the caller). Column geometry and
    temperature are metadata in v0.1.
    """

    t0: float
    t_dwell: float
    flow: float
    column_length_mm: float | None = None
    column_id_mm: float | None = None
    particle_um: float | None = None
    temperature_c: float | None = None
    t0_is_measured: bool = True


@dataclass(frozen=True)
class Gradient:
    """One linear gradient segment: φ0 -> φf over ``t_gradient`` minutes.

    ``t_init`` is the programmed initial isocratic hold at φ0 (0 if none).
    """

    phi0: float
    phif: float
    t_gradient: float
    t_init: float = 0.0

    @property
    def delta_phi(self) -> float:
        return self.phif - self.phi0


@dataclass(frozen=True)
class Peak:
    """One compound as entered: its retention time in each scouting run.

    Optional per-run areas (raw or %; normalised downstream) and width at half
    height (min) are provenance for later tickets.
    """

    t_r_run1: float
    t_r_run2: float
    name: str = ""
    area_run1: float | None = None
    area_run2: float | None = None
    w_half_run1: float | None = None
    w_half_run2: float | None = None


@dataclass(frozen=True)
class RetentionParams:
    """LSS parameters for one peak, natural-log convention, anchored at ``phi_ref``.

    ln k = ln_k0 − S_e·(φ − phi_ref).
    """

    ln_k0: float
    s_e: float
    phi_ref: float
