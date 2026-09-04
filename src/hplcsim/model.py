"""Data model for methods, gradients, programmes, runs and peaks (SPEC §4).

Two shapes describe a composition profile. :class:`Gradient` is v0.1's two-field ramp
and remains what the scouting runs are acquired with; :class:`Programme` is v0.2's
candidate — φ0, an initial hold and an ordered list of :class:`Segment` — and is what
the user is free to move (SPEC §3). They are not rivals: a one-segment programme *is* a
gradient, and :meth:`Programme.as_gradient` / :meth:`Programme.from_gradient` are the
only place that correspondence is written down.

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
from typing import Final

_LN10 = math.log(10.0)

PERCENT_B_RANGE: Final = (0.0, 100.0)
"""SPEC §4's %B domain: the entry and display boundary.

φ is a 0–1 fraction everywhere inside the engine; %B on 0–100 exists only here and at
the screen. The file format (SPEC §8) and the rail's editable tables both check against
this, so there is one number to change and one to read.
"""


def phi_from_percent_b(percent_b: float) -> float:
    """Entry boundary: %B (0–100) -> φ (0–1)."""
    return percent_b / 100.0


def percent_b_from_phi(phi: float) -> float:
    """Display boundary: φ (0–1) -> %B (0–100).

    Rounded to nine decimals so a %B that was typed comes back as it was typed:
    0.55 × 100 is 55.00000000000001 in binary, and a session file is a transcript of
    what was entered (SPEC §8), not of the float that stood in for it.
    """
    return round(phi * 100.0, 9)


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


@dataclass(frozen=True)
class Segment:
    """One linear leg of a gradient programme: ramp to ``phif`` over ``duration`` minutes.

    A segment says where the composition *ends* and how long it takes to get there;
    where it starts is whatever the previous segment left behind (the programme's
    ``phi0`` for the first). That is why a segment cannot tell you on its own whether
    it is a hold or which way it runs — :meth:`Programme.legs` resolves it against its
    entry composition, and :class:`Leg` is what carries the answer.

    ``duration`` must be positive (SPEC §4, validation posture). ``phif`` is free:
    repeating the entry composition is a hold, and a value below it is a descending
    segment, which is allowed — the signed steepness is the walker's business
    (`#70 <https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/70>`_).
    """

    duration: float
    phif: float

    def __post_init__(self) -> None:
        if self.duration <= 0.0:
            raise ValueError(f"a segment duration must be positive, got {self.duration}")


@dataclass(frozen=True)
class Leg:
    """One :class:`Segment` resolved against the composition it starts from.

    A segment records only where it ends, so nothing about it — not whether it is a
    hold, not which way it runs — can be read without the composition it starts from.
    Chaining that through the list is what :meth:`Programme.legs` does, and this is the
    shape it hands back: the one the walker (#70) and the per-segment diagnostics (#72)
    both read, so neither re-derives entry compositions for itself.
    """

    phi_start: float
    phi_end: float
    duration: float

    @property
    def delta_phi(self) -> float:
        """Signed composition change: negative for a descending segment."""
        return self.phi_end - self.phi_start

    @property
    def is_hold(self) -> bool:
        """A segment that repeats its entry composition is a hold (SPEC §3).

        Exact equality, deliberately: a hold is the *same* composition, and the walker's
        Δφ = 0 branch has to agree with this predicate exactly. A tolerance would open a
        band where a leg reads as a hold while its steepness is non-zero, which is worse
        than either answer alone.
        """
        return self.phi_end == self.phi_start


@dataclass(frozen=True)
class Programme:
    """A candidate gradient programme: φ0, an initial hold, and ordered segments (SPEC §3, §4).

    v0.2's prediction target. It lands *beside* :class:`Gradient` rather than replacing
    it: the scouting runs keep their two-field gradient — the two runs sharing φ0/φf/t_init
    is what makes the two-run fit well-posed (SPEC §4, #46 decision 9) — and freedom is a
    property of the candidate alone.

    ``segments`` is non-empty and ordered; the segment count is open, with no cap and
    nothing keyed to it (SPEC §3, #58). A one-segment programme *is* a v0.1 gradient —
    :meth:`as_gradient` and :meth:`from_gradient` are the only place that correspondence
    is written down, and it is exact, so a one-segment programme takes v0.1's closed-form
    path and predicts bitwise identically to it.
    """

    phi0: float
    segments: tuple[Segment, ...]
    t_init: float = 0.0

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("a programme needs at least one segment")
        if self.t_init < 0.0:
            raise ValueError(f"t_init must be non-negative, got {self.t_init}")

    @property
    def phif(self) -> float:
        """The composition the last segment ends at."""
        return self.segments[-1].phif

    @property
    def t_gradient(self) -> float:
        """Total programmed ramp time: the sum of every segment's duration."""
        return math.fsum(segment.duration for segment in self.segments)

    def legs(self) -> tuple[Leg, ...]:
        """Every segment paired with the composition it starts from."""
        legs = []
        phi_start = self.phi0
        for segment in self.segments:
            legs.append(Leg(phi_start=phi_start, phi_end=segment.phif, duration=segment.duration))
            phi_start = segment.phif
        return tuple(legs)

    @classmethod
    def from_gradient(cls, gradient: Gradient) -> Programme:
        """The one-segment programme that is exactly ``gradient`` (the entry side)."""
        return cls(
            phi0=gradient.phi0,
            segments=(Segment(duration=gradient.t_gradient, phif=gradient.phif),),
            t_init=gradient.t_init,
        )

    def as_gradient(self) -> Gradient | None:
        """The :class:`Gradient` this programme *is*, or ``None`` if it has two or more segments.

        The exit side of the same correspondence as :meth:`from_gradient`. Total rather
        than raising, because asking *whether* a programme is a single segment is a fair
        question with a non-exceptional answer — the app's rail has to know without
        catching. :func:`as_single_gradient` is the variant that refuses.
        """
        if len(self.segments) != 1:
            return None
        return Gradient(
            phi0=self.phi0,
            phif=self.segments[0].phif,
            t_gradient=self.segments[0].duration,
            t_init=self.t_init,
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


# The two shapes a prediction target may take (SPEC §4). v0.1's :class:`Gradient` and
# v0.2's :class:`Programme` are accepted wherever either is: the programme lands beside
# the gradient rather than replacing it, so no v0.1 caller changes.
Target = Gradient | Programme


class MultiSegmentNotSupportedError(NotImplementedError):
    """A programme of two or more segments reached a path that only knows one.

    Prediction and width no longer raise it — the piecewise walker (#70,
    :func:`hplcsim.retention.walk_programme`) predicts any segment count. It remains the
    typed answer of :func:`as_single_gradient`, the door for paths that genuinely need a
    single ramp, so a caller that must have one still learns so by type rather than from
    the number the first segment alone would give — a wrong retention time is
    indistinguishable from a right one on screen.
    """


def as_programme(target: Target) -> Programme:
    """The programme ``target`` is: itself, or the one-segment programme a gradient is.

    The other direction of the same correspondence as :func:`as_single_gradient`, for
    the paths that read a target leg by leg (the width model's G rule, the numerical
    oracle). Total, since every gradient is a programme.
    """
    return target if isinstance(target, Programme) else Programme.from_gradient(target)


def as_single_gradient(target: Target) -> Gradient:
    """The one-segment gradient ``target`` is, or :class:`MultiSegmentNotSupportedError`.

    The single door into v0.1's closed form, so the bitwise identity of a one-segment
    programme is structural: it is not *reproduced* by the gradient path, it *is* the
    gradient path. :func:`hplcsim.retention.predict_retention` sends two or more segments
    to the walker before reaching this door; anything that reaches it with more than one
    segment is a path that only knows one, and is told so. It sits here beside
    :meth:`Programme.as_gradient` and :meth:`Programme.from_gradient` so the whole
    correspondence between the two shapes is written down in one place.
    """
    if isinstance(target, Gradient):
        return target
    gradient = target.as_gradient()
    if gradient is None:
        raise MultiSegmentNotSupportedError(
            f"a {len(target.segments)}-segment programme reached a path that takes one "
            "segment only; predict it through hplcsim.retention.predict_retention, "
            "which walks any number of segments"
        )
    return gradient
