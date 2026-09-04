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
    time in minutes (V_D / F, converted by the caller). Temperature is metadata.
    Column geometry is the basis of two estimates — the plate-count default
    (:mod:`hplcsim.width`) and the dead-time fallback (:mod:`hplcsim.dead_time`).

    ``particle_is_solid_core`` is the packing architecture: ``True`` for
    superficially porous (core–shell, solid-core) particles, ``False`` for fully
    porous ones, ``None`` when the user has not said. It selects the porosity the
    geometry estimate uses, and there is deliberately no default — the estimator
    refuses rather than guesses (ticket #24, decided on #34).

    ``t0_marker`` is what was injected to measure ``t0`` and which point of its
    trace was read ("uracil, apex"; "solvent front, first disturbance"). A measured
    dead time without its marker has no provenance; the field is free text so the
    time-point convention travels with the compound.
    """

    t0: float
    t_dwell: float
    flow: float
    column_length_mm: float | None = None
    column_id_mm: float | None = None
    particle_um: float | None = None
    temperature_c: float | None = None
    t0_is_measured: bool = True
    particle_is_solid_core: bool | None = None
    t0_marker: str | None = None


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


class ProgrammeNotSupportedError(NotImplementedError):
    """Something a programme may legally describe that the v0.1 engine cannot yet answer.

    ``NotImplementedError`` and not ``ValueError`` on purpose: the programme is a valid
    method — SPEC §3 says so — and the engine is the incomplete party. Every subclass
    names the ticket that will complete it, so a refusal is never a dead end. Catching
    the base is how a caller says "anything v0.2 has not finished".
    """


class MultiSegmentProgrammeError(ProgrammeNotSupportedError):
    """A programme of two or more segments, asked of an engine that has only v0.1's path.

    Raised where a :class:`Programme` must become a :class:`Gradient` — the one door
    into v0.1's closed form.
    """


class DescendingSegmentCompressionError(ProgrammeNotSupportedError):
    """A band asked to elute in a *descending* segment, whose G nothing has settled.

    The type allows a descending segment and :func:`~hplcsim.retention.segment_steepness`
    signs it correctly (SPEC §3: "a descending segment slows the band"). What is missing
    is only the *width*: G(p) was derived for a band compressed by a rising composition,
    so the band-compression rule declines rather than inventing a dilation factor. A
    typed, named refusal rather than a bare ``ValueError`` because the method is legal —
    the same posture the multi-segment refusal takes.
    """


@dataclass(frozen=True)
class Segment:
    """One linear leg of a gradient programme: ``duration`` minutes ending at ``phi_end``.

    The composition it *starts* from is not stored — it is the previous segment's end,
    or the programme's φ0 for the first, which is what makes an ordered list of segments
    a programme rather than a bag of ramps (:meth:`Programme.phi_at_entry`).

    A segment whose ``phi_end`` repeats the composition it starts from is a **hold**
    (SPEC §3); one whose ``phi_end`` is lower is a **descending** segment, which is
    allowed. The sign of the resulting steepness is the walker's business (#70), not
    the type's.
    """

    duration: float
    phi_end: float


@dataclass(frozen=True)
class Programme:
    """A candidate gradient programme: φ0, an initial hold, and ordered segments (SPEC §3).

    The v0.2 shape of a candidate. It lands *beside* :class:`Gradient` rather than
    replacing it: the scouting runs keep their single-segment gradient (SPEC §4,
    "Unchanged in v0.2"), and a one-segment programme is exactly what a v0.1 candidate
    always was — :func:`programme_from_gradient` and :func:`gradient_from_programme`
    are the one place the two meet.

    ``segments`` is ordered and non-empty, every duration positive (SPEC §4's validation
    posture: an impossibility, so this one hard-fails); the segment count itself is open
    (SPEC §3). φ is a fraction 0–1, as everywhere inside the engine.
    """

    phi0: float
    segments: tuple[Segment, ...]
    t_init: float = 0.0

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("a programme needs at least one segment")
        if self.t_init < 0.0:
            raise ValueError(f"the initial hold must not be negative, got {self.t_init}")
        for index, segment in enumerate(self.segments):
            if segment.duration <= 0.0:
                raise ValueError(
                    f"every segment duration must be positive; segment {index + 1} "
                    f"has duration {segment.duration}"
                )

    def phi_at_entry(self, index: int) -> float:
        """Composition the programme holds when segment ``index`` begins."""
        return self.phi0 if index == 0 else self.segments[index - 1].phi_end

    def delta_phi(self, index: int) -> float:
        """Signed composition change across segment ``index`` — negative when descending."""
        return self.segments[index].phi_end - self.phi_at_entry(index)

    def is_hold(self, index: int) -> bool:
        """Whether segment ``index`` repeats the composition it started from (SPEC §3)."""
        return self.delta_phi(index) == 0.0


def programme_from_gradient(gradient: Gradient) -> Programme:
    """The one-segment programme a v0.1 gradient *is*."""
    return Programme(
        phi0=gradient.phi0,
        segments=(Segment(duration=gradient.t_gradient, phi_end=gradient.phif),),
        t_init=gradient.t_init,
    )


def gradient_from_programme(programme: Programme) -> Gradient:
    """The v0.1 gradient a one-segment programme *is*; refuses two or more segments.

    The single conversion point in both directions, and therefore the single door into
    v0.1's closed-form path. Every field passes through untouched, so a prediction or a
    width taken through this door is bitwise identical to the gradient's — SPEC §10
    item 4(a) is then a property of this function rather than of a tolerance.

    Two or more segments need the piecewise walker of SPEC §3, which is ticket #70;
    until it lands they are refused here rather than silently linearised.
    """
    if len(programme.segments) != 1:
        raise MultiSegmentProgrammeError(
            f"this programme has {len(programme.segments)} segments; the piecewise walker "
            f"that predicts two or more is ticket #70. Only a one-segment programme takes "
            f"v0.1's closed-form path."
        )
    segment = programme.segments[0]
    return Gradient(
        phi0=programme.phi0,
        phif=segment.phi_end,
        t_gradient=segment.duration,
        t_init=programme.t_init,
    )


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
