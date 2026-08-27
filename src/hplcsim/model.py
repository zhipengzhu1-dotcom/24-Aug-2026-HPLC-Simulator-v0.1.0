"""Data model for methods, gradients, runs and peaks (SPEC §4).

Unit conventions: minutes, mL, mm, µm, °C. The strong-solvent fraction φ is a
0–1 fraction everywhere inside the engine; %B (0–100) exists only at the entry
and display boundaries via :func:`phi_from_percent_b` / :func:`percent_b_from_phi`.

Retention parameters are held in the natural-log convention (ln k0, S_e). The
base-10 quantities chromatographers quote (S, log10 k0) are display values;
:func:`_to_base10` / :func:`_from_base10` are the only place the ln(10) factor
appears, and the four public converters below are thin names over them.
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


def _to_base10(natural: float) -> float:
    """The log-convention boundary (display side): divide by ln 10."""
    return natural / _LN10


def _from_base10(base10: float) -> float:
    """The log-convention boundary (entry side): multiply by ln 10."""
    return base10 * _LN10


def s_base10_from_s_e(s_e: float) -> float:
    """Display boundary: natural-log S_e -> base-10 S."""
    return _to_base10(s_e)


def s_e_from_s_base10(s: float) -> float:
    """Entry boundary: base-10 S -> natural-log S_e."""
    return _from_base10(s)


def log10_k0_from_ln_k0(ln_k0: float) -> float:
    """Display boundary: ln k0 -> log10 k0."""
    return _to_base10(ln_k0)


def ln_k0_from_log10_k0(log10_k0: float) -> float:
    """Entry boundary: log10 k0 -> ln k0."""
    return _from_base10(log10_k0)


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
class Run:
    """One scouting run: the gradient it was acquired with (SPEC §4).

    The two scouting runs share a :class:`Method` and differ only in
    ``gradient.t_gradient``. Per-peak measurements live on :class:`Peak`,
    one row per compound with both runs side by side (SPEC §5).
    """

    gradient: Gradient
    name: str = ""


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

    def k_at(self, phi: float) -> float:
        """Retention factor at composition ``phi`` under the LSS model."""
        return math.exp(self.ln_k0 - self.s_e * (phi - self.phi_ref))
