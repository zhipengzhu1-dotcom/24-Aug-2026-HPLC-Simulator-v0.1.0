"""Forward retention prediction under the LSS model (SPEC §3; research doc §2, §4, §8.2).

All math is in the natural-log convention (S_e, b_e). The closed form of §2.2
is used in the gradient regime; the dwell/hold and post-gradient regimes get
their own branches, derived from the same fundamental equation (§2.1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from hplcsim.model import (
    Gradient,
    Leg,
    Method,
    MultiSegmentNotSupportedError,
    Programme,
    RetentionParams,
    Target,
    as_single_gradient,
)

Regime = Literal["isocratic_hold", "gradient", "post_gradient"]

# Re-exported so a caller reaching for a prediction finds the target type and the
# refusal beside the function that raises it; both are defined in :mod:`hplcsim.model`,
# where the whole Gradient/Programme correspondence lives (SPEC §9).
__all__ = [
    "Gradient",
    "MultiSegmentNotSupportedError",
    "Programme",
    "Regime",
    "RetentionResult",
    "Target",
    "as_single_gradient",
    "gradient_end_time",
    "gradient_steepness",
    "predict_retention",
    "segment_steepness",
    "walk_programme",
]


def _steepness(t0: float, delta_phi: float, s_e: float, duration: float) -> float:
    """b_e = t0·Δφ·S_e/duration — the one expression both steepness functions read.

    The single home for it, and deliberately so: it is the most exposed surface of the
    natural-log convention CLAUDE.md names as the project's #1 hazard. Retention, band
    compression (§5.2), the walker's per-segment steepness and the tests that
    reconstruct counterfactual G conventions must all read the same b_e — a correction
    applied here to one of them and not the others would desync them silently.
    """
    return t0 * delta_phi * s_e / duration


def gradient_steepness(method: Method, gradient: Gradient, s_e: float) -> float:
    """b_e = t0·Δφ·S_e/tG — the natural-log gradient steepness (research doc §1.3)."""
    return _steepness(method.t0, gradient.delta_phi, s_e, gradient.t_gradient)


def segment_steepness(method: Method, leg: Leg, s_e: float) -> float:
    """b_e,seg = t0·Δφ_seg·S_e/duration — one leg's steepness, **signed** (research doc §2.5).

    Zero in a hold and negative for a descending segment: the walker reads the sign, so
    unlike :func:`gradient_steepness` this is not a magnitude. Same expression, same
    home — the two differ only in what they are handed.
    """
    return _steepness(method.t0, leg.delta_phi, s_e, leg.duration)


def gradient_end_time(method: Method, target: Target) -> float:
    """When the final composition φf reaches the detector (min from injection).

    The programmed ramp ends at the pump at ``t_init + t_gradient``; it reaches the
    column head one dwell later and the detector one t0 after that. For a single ramp
    this is exactly the boundary between the gradient and post-gradient regimes below —
    a band still on the column at this instant finishes the run isocratically at φf — so
    the drawn marker and the regime that classifies a peak read the same expression.

    For a programme it is the end of the *last* segment, and only that: ``t_gradient``
    sums every segment's duration, so the arithmetic is unchanged and a multi-segment
    target is answered here rather than refused — where the programme finishes is not
    something the walker has to solve. It stops being a regime boundary, though, as
    soon as the last segment is a hold or descends; what classifies a peak under a
    multi-segment programme is the walker's (#70), not this.
    """
    return method.t_dwell + target.t_init + target.t_gradient + method.t0


@dataclass(frozen=True)
class RetentionResult:
    """Predicted retention for one peak under one gradient.

    ``k_e`` is the retention factor at the instant the band leaves the column.
    ``low_confidence`` is set when the k >> 1 approximation behind the model
    degrades (research doc §4.3: k_e below ~1, or t'_R = tR − t0 − τ below t0,
    with t'_R as defined in the doc's symbol table) or when the band does not
    elute during the ramp (§4.1/§4.2: "flag them").

    ``eluting_segment`` is the index of the programme segment the band left the column
    in — ``None`` when it left before the first segment arrived (the isocratic hold) or
    after the last one ended. For a v0.1 gradient or a one-segment programme it is ``0``
    when the band left inside that one segment, ramp or hold, and ``None`` otherwise —
    what the walker gives too — so the width model can take G from the eluting segment
    without asking which shape it was handed (SPEC §3, "Band compression for a
    programme"). Diagnostic 1 brackets per eluting segment on it (#72).

    ``b_e_seg`` is that segment's own signed steepness (SPEC §3's b_e,seg — not the
    whole-gradient b_e) and ``k_seg_entry`` the retention factor where the band *entered*
    it (not ``k_e``, which is k at elution). They are carried out of the walker, which
    already holds both, so the width model need not re-walk the programme to rebuild
    them. The three travel together: ``eluting_segment``, ``b_e_seg`` and ``k_seg_entry``
    are ``None`` together, or all three describe the leg the band left in. In a hold
    ``b_e_seg`` is ``0.0``, since a hold has Δφ = 0.

    A flat one-segment candidate (Δφ = 0) reports segment 0 when the band leaves inside
    that hold, and ``None`` when it is still on-column at the programme's end — the same
    two answers the walker gives over the same programme (#94).
    """

    t_r: float
    k_e: float
    regime: Regime
    low_confidence: bool = False
    eluting_segment: int | None = None
    b_e_seg: float | None = None
    k_seg_entry: float | None = None


def predict_retention(params: RetentionParams, method: Method, target: Target) -> RetentionResult:
    """Predict tR (min) for ``params`` run under ``target`` on ``method``.

    ``target`` is a v0.1 :class:`Gradient` or a v0.2 :class:`Programme`. A one-segment
    programme is the gradient it converts to and takes exactly this path — bitwise
    identical to v0.1 by construction (SPEC §10 item 4a). Two or more segments go to
    :func:`walk_programme`, and only they do: the walker is checked against this closed
    form and against numerical integration, never the other way round.
    """
    if method.t0 <= 0.0:
        raise ValueError(f"t0 must be positive, got {method.t0}")
    if isinstance(target, Programme) and target.as_gradient() is None:
        return walk_programme(params, method, target)
    gradient = as_single_gradient(target)
    if gradient.t_gradient <= 0.0:
        raise ValueError(f"t_gradient must be positive, got {gradient.t_gradient}")

    t0 = method.t0
    tau = method.t_dwell + gradient.t_init
    k0 = params.k_at(gradient.phi0)

    # §4.1: test the pre-gradient migration first — the closed form's log argument
    # goes non-positive exactly when the band has already left the column.
    if k0 <= tau / t0:
        return _classify(t_r=t0 * (1.0 + k0), k_e=k0, regime="isocratic_hold", t0=t0, tau=tau)

    # A flat gradient (Δφ = 0) is the same isocratic case for every peak, but it is not
    # the same *place*: its single leg is a hold the band can leave in, and the walker
    # over the same programme calls that leg 0 (#94). The two have to agree on the leg,
    # boundary included — a band still on-column when the programme ends leaves after the
    # last leg, which is no segment's — so the hold test is the walker's, shared. The
    # guard above is v0.1's own form and stays so for SPEC §10 item 4a; at the hairline
    # of τ/(t0·k0) = 1 it can differ from the walker's by an ulp, and that is accepted.
    # What still differs is the *regime* when the band outlives the programme (#100).
    if gradient.delta_phi == 0.0:
        x = tau / (t0 * k0)
        leaves_in_the_hold = _hold_exit_fraction(x, gradient.t_gradient, t0, k0) >= 1.0
        return _classify(
            t_r=t0 * (1.0 + k0),
            k_e=k0,
            regime="isocratic_hold",
            t0=t0,
            tau=tau,
            eluting_segment=0 if leaves_in_the_hold else None,
            b_e_seg=0.0 if leaves_in_the_hold else None,
            k_seg_entry=k0 if leaves_in_the_hold else None,
        )

    b_e = gradient_steepness(method, gradient, params.s_e)

    # §4.2: fraction of the column traversed when the ramp ends. If the band is
    # still on-column it finishes isocratically at phif with k_f.
    k_f = k0 * math.exp(-params.s_e * gradient.delta_phi)
    x_gradient_end = tau / (t0 * k0) + (k0 / k_f - 1.0) / (k0 * b_e)
    if x_gradient_end < 1.0:
        t_r = gradient_end_time(method, gradient) + (1.0 - x_gradient_end) * t0 * k_f
        return _classify(t_r=t_r, k_e=k_f, regime="post_gradient", t0=t0, tau=tau)

    # §2.2: the LSS closed form, valid while the band exits during the ramp.
    log_arg = b_e * (k0 - tau / t0) + 1.0
    t_r = tau + t0 + (t0 / b_e) * math.log(log_arg)
    return _classify(
        t_r=t_r,
        k_e=k0 / log_arg,
        regime="gradient",
        t0=t0,
        tau=tau,
        eluting_segment=0,
        b_e_seg=b_e,
        k_seg_entry=k0,
    )


def walk_programme(
    params: RetentionParams, method: Method, programme: Programme
) -> RetentionResult:
    """Retention under a programme of any number of segments (research doc §2.5).

    The fundamental equation of §2.1 walked piecewise. The band's migration fraction x
    advances through the dwell and initial hold isocratically at φ0, then through each
    leg in turn: a ramp by the §2.2 closed form with k taken at the leg's entry
    composition and the leg's own signed steepness (a descending leg slows the band), a
    hold isocratically at 1/(t0·k). The leg in which x reaches 1 gives tR in closed form;
    a band still on-column after the last leg finishes isocratically at the final
    composition — §4.2's post-gradient branch, now reached from any programme. The inlet
    composition is the pump programme delayed by the dwell, which is why every leg
    starts τ = t_D + t_init after injection plus the durations before it.

    Regimes: leaving before any ramp is the early-eluter's ``isocratic_hold`` (§4.1, and
    a flat first segment at φ0 is the same physics as t_init); leaving on a ramp —
    ascending or descending — is ``gradient``; leaving in a hold *after* a ramp, or after
    the last leg, is ``post_gradient``, the flag SPEC §6 diagnostic 9 reads.

    Callable on one segment too, where it reproduces :func:`predict_retention` to 1e-12
    (SPEC §10 item 4a): the same algebra arranged as a walk. :func:`predict_retention`
    sends only two or more segments here, so the one-segment path stays v0.1's bitwise.
    """
    if method.t0 <= 0.0:
        raise ValueError(f"t0 must be positive, got {method.t0}")

    t0 = method.t0
    tau = method.t_dwell + programme.t_init
    k0 = params.k_at(programme.phi0)

    # §4.1: the pre-gradient migration, tested first for the same reason as the closed
    # form — it is where every later log argument would go non-positive.
    x = tau / (t0 * k0)
    if x >= 1.0:
        return _classify(t_r=t0 * (1.0 + k0), k_e=k0, regime="isocratic_hold", t0=t0, tau=tau)

    leg_start = tau  # when the current leg reaches the column inlet
    ramped = False  # has any non-hold leg been traversed yet?
    for index, leg in enumerate(programme.legs()):
        k_entry = params.k_at(leg.phi_start)
        if leg.is_hold:
            x_end = _hold_exit_fraction(x, leg.duration, t0, k_entry)
            if x_end >= 1.0:
                t_r = _isocratic_exit(leg_start, x, t0, k_entry)
                regime: Regime = "post_gradient" if ramped else "isocratic_hold"
                return _classify(
                    t_r=t_r,
                    k_e=k_entry,
                    regime=regime,
                    t0=t0,
                    tau=tau,
                    eluting_segment=index,
                    b_e_seg=0.0,
                    k_seg_entry=k_entry,
                )
        else:
            # §2.2 inside one leg: x(s) = x + (e^{b·s/t0} − 1)/(k_entry·b) for s in [0, D],
            # and e^{b·D/t0} = e^{S_e·Δφ} = k_entry/k_end at the leg's end. Signed b:
            # descending is b < 0, where both numerator and denominator flip sign.
            b_e = segment_steepness(method, leg, params.s_e)
            k_end = params.k_at(leg.phi_end)
            x_end = x + (k_entry / k_end - 1.0) / (k_entry * b_e)
            if x_end >= 1.0:
                log_arg = 1.0 + b_e * k_entry * (1.0 - x)
                t_r = leg_start + (t0 / b_e) * math.log(log_arg) + t0
                return _classify(
                    t_r=t_r,
                    k_e=k_entry / log_arg,
                    regime="gradient",
                    t0=t0,
                    tau=tau,
                    eluting_segment=index,
                    b_e_seg=b_e,
                    k_seg_entry=k_entry,
                )
            ramped = True
        x = x_end
        leg_start += leg.duration

    # §4.2 for a programme: still on-column when the last leg ends; finish isocratically
    # at the final composition. ``leg_start`` is now the programme's end at the inlet,
    # and one t0 later is exactly :func:`gradient_end_time`.
    k_final = params.k_at(programme.phif)
    t_r = _isocratic_exit(leg_start, x, t0, k_final)
    return _classify(t_r=t_r, k_e=k_final, regime="post_gradient", t0=t0, tau=tau)


def _hold_exit_fraction(x: float, duration: float, t0: float, k: float) -> float:
    """Migration fraction at the end of a hold entered at ``x``: isocratic, so 1/(t0·k) per min.

    One expression for the walker's hold leg and the closed form's flat candidate (#94),
    so the two cannot disagree about whether a band left inside it.
    """
    return x + duration / (t0 * k)


def _isocratic_exit(leg_start: float, x: float, t0: float, k: float) -> float:
    """tR for a band that finishes isocratically at ``k`` from migration fraction ``x``.

    The remaining fraction 1 − x takes (1 − x)·t0·k at the inlet clock started at
    ``leg_start``, plus the t0 the eluted band needs to reach the detector. One shape
    for a hold and for the tail after the last leg (§2.5 steps 3 and 4).
    """
    return leg_start + (1.0 - x) * t0 * k + t0


def _classify(
    *,
    t_r: float,
    k_e: float,
    regime: Regime,
    t0: float,
    tau: float,
    eluting_segment: int | None = None,
    b_e_seg: float | None = None,
    k_seg_entry: float | None = None,
) -> RetentionResult:
    """Attach the §4.3 / §4.1–4.2 low-confidence classification to a prediction."""
    t_r_prime = t_r - t0 - tau
    low_confidence = regime != "gradient" or k_e < 1.0 or t_r_prime < t0
    return RetentionResult(
        t_r=t_r,
        k_e=k_e,
        regime=regime,
        low_confidence=low_confidence,
        eluting_segment=eluting_segment,
        b_e_seg=b_e_seg,
        k_seg_entry=k_seg_entry,
    )
