"""THROWAWAY maths for ticket #45: the four surfaces #44 decided, computed from the fit.

Not the v0.2 engine — no tests, no edge handling, no home in ``src/``. It exists so the
screen shows numbers the engine's own fit produced rather than drawn ones. Every formula
is the research's: ``docs/research/composition-extrapolation.md`` §7.2–7.3 and §10.1,
``docs/research/phi0-dependent-retention-residual.md`` §7.4. The thresholds are #44's
resolution, both marked provisional there.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from app.diagnostics import Diagnostic
from app.pipeline import Cockpit, CockpitInputs
from hplcsim.model import Gradient, Method, Run, log10_k0_from_ln_k0, percent_b_from_phi

# #44 decision 3: gentle from 0 to ~0.6 window-widths outside, strong beyond. 0.6
# preserves v0.1's "~2× outside" at β = 3 (log₃ 2 = 0.63). Provisional pending #53 E4.
WINDOW_WIDTHS_STRONG = 0.6
# #44 decision 4: gentle for any non-zero φ0 departure, strong from 10 %B. Provisional
# pending #53 E1 and #24.
PHI0_STRONG_PERCENT_B = 10.0
# phi0 research §7.4: every 10 %B raised above the scouting start ≈ ×2.1 retention error.
DOUBLING_FACTOR = 2.1
DOUBLING_PER_PERCENT_B = 10.0
# hplcsim.fit._LOW_K0_LOG10, by value — it is private there and this file is throwaway.
LOW_K0_LOG10 = 2.1


def s_star(method: Method, gradient: Gradient) -> float:
    """s* = t0·Δφ/tG — the normalised steepness the elution composition depends on."""
    return method.t0 * gradient.delta_phi / gradient.t_gradient


@dataclass(frozen=True)
class Bracket:
    lo: float
    hi: float

    @property
    def beta(self) -> float:
        return self.hi / self.lo


def scouting_bracket(method: Method, run1: Run, run2: Run) -> Bracket:
    lo, hi = sorted((s_star(method, run1.gradient), s_star(method, run2.gradient)))
    return Bracket(lo, hi)


def window_widths_outside(bracket: Bracket, s_cand: float) -> float:
    """log_β(s*_edge / s*_cand): the method-level overshoot, identical for every peak."""
    if s_cand <= 0.0:
        return math.inf
    if s_cand > bracket.hi:
        ratio = s_cand / bracket.hi
    elif s_cand < bracket.lo:
        ratio = bracket.lo / s_cand
    else:
        return 0.0
    return math.log(ratio) / math.log(bracket.beta)


def elution_composition(method: Method, gradient: Gradient, t_r: float, regime: str) -> float:
    """φ at the column outlet when the band leaves — the fit's own expression, per regime."""
    if regime == "isocratic_hold":
        return gradient.phi0
    if regime == "post_gradient":
        return gradient.phif
    t_prime = t_r - method.t0 - method.t_dwell - gradient.t_init
    return gradient.phi0 + gradient.delta_phi * t_prime / gradient.t_gradient


@dataclass(frozen=True)
class PeakWindow:
    """One peak's calibrated composition window and where the candidate puts it."""

    name: str
    lo: float
    hi: float
    at_candidate: float
    regime: str

    @property
    def width(self) -> float:
        return self.hi - self.lo

    @property
    def distance(self) -> float:
        """φ beyond the window: positive above, negative below, 0 inside."""
        if self.at_candidate > self.hi:
            return self.at_candidate - self.hi
        if self.at_candidate < self.lo:
            return self.at_candidate - self.lo
        return 0.0

    @property
    def standing(self) -> str:
        pct = percent_b_from_phi
        if self.regime == "post_gradient":
            where = f"post-gradient, at φf = {pct(self.at_candidate):.1f} %B"
        elif self.regime == "isocratic_hold":
            where = f"in the hold, at φ0 = {pct(self.at_candidate):.1f} %B"
        else:
            where = None
        if self.distance == 0.0:
            return "inside" if where is None else f"inside ({where})"
        side = "above" if self.distance > 0 else "below"
        out = f"{abs(pct(self.distance)):.1f} %B {side}"
        return out if where is None else f"{out} ({where})"


@dataclass(frozen=True)
class Analysis:
    """Everything the four surfaces need, computed once per rerun."""

    s_cand: float
    bracket: Bracket
    window_widths: float
    steepness: Diagnostic | None
    departure: Diagnostic | None
    windows: tuple[PeakWindow, ...]
    low_k0: dict[str, Diagnostic]

    @property
    def strong(self) -> bool:
        return any(
            d is not None and d.severity == "strong" for d in (self.steepness, self.departure)
        )

    @property
    def candidate_diagnostics(self) -> tuple[Diagnostic, ...]:
        return tuple(d for d in (self.steepness, self.departure) if d is not None)

    def pair_is_decision_grade(self, earlier: str, later: str) -> bool:
        if self.strong:
            return False
        return earlier not in self.low_k0 and later not in self.low_k0

    @property
    def stamp(self) -> str | None:
        """The output stamp on Rs and the critical pair — #44 decision 8."""
        if self.strong:
            which = "steepness" if self.steepness and self.steepness.severity == "strong" else ""
            if self.departure and self.departure.severity == "strong":
                which = f"{which} and φ0 departure" if which else "φ0 departure"
            return (
                f"Rs and the critical pair are indicative, not decision-grade — the "
                f"candidate is strong on {which}. Retention times stay shown as numbers."
            )
        if self.low_k0:
            names = ", ".join(self.low_k0)
            return f"Pairs involving {names} are indicative (low k0 at the candidate's start)."
        return None


def analyse(inputs: CockpitInputs, cockpit: Cockpit) -> Analysis | None:
    if cockpit.blocked is not None:
        return None
    method, candidate = inputs.method, inputs.candidate
    bracket = scouting_bracket(method, inputs.run1, inputs.run2)
    s_cand = s_star(method, candidate)
    ww = window_widths_outside(bracket, s_cand)
    windows = tuple(_windows(cockpit, method, candidate))
    return Analysis(
        s_cand=s_cand,
        bracket=bracket,
        window_widths=ww,
        steepness=_steepness_diagnostic(inputs, bracket, s_cand, ww),
        departure=_departure_diagnostic(inputs.run1.gradient, candidate),
        windows=windows,
        low_k0=_low_k0(cockpit, candidate),
    )


def _windows(cockpit: Cockpit, method: Method, candidate: Gradient) -> list[PeakWindow]:
    predicted = cockpit.predicted_by_name
    found = []
    for peak, fit in cockpit.fitted:
        prediction = predicted.get(peak.name)
        if prediction is None:
            continue
        lo, hi = sorted((fit.phi_e_run1, fit.phi_e_run2))
        at = elution_composition(
            method, candidate, prediction.retention.t_r, prediction.retention.regime
        )
        found.append(PeakWindow(peak.name, lo, hi, at, prediction.retention.regime))
    return found


def _steepness_diagnostic(
    inputs: CockpitInputs, bracket: Bracket, s_cand: float, ww: float
) -> Diagnostic | None:
    """#44 decision 1–3: diagnostic 1 re-expressed on s*, tiered in window-widths."""
    if ww == 0.0:
        return None
    c = inputs.candidate
    tg1, tg2 = inputs.run1.gradient.t_gradient, inputs.run2.gradient.t_gradient
    b0, b1 = percent_b_from_phi(c.phi0), percent_b_from_phi(c.phif)
    if not math.isfinite(ww):
        return Diagnostic(
            code="s_star_bracket",  # type: ignore[arg-type]
            severity="strong",
            message=(
                f"**Candidate {b0:g} → {b1:g} %B is flat or descending** — s* ≤ 0. The fit "
                "was pinned on rising gradients only and has nothing to say here."
            ),
        )
    where = "steeper" if s_cand > bracket.hi else "shallower"
    head = (
        f"**Candidate steepness s\\* = {s_cand:.4f} sits {ww:.2f} window-widths outside "
        f"the scouting bracket** [{bracket.lo:.4f}, {bracket.hi:.4f}] — {where} than either "
        f"scouting run (tG {tg1:g} and {tg2:g} min, "
        f"{percent_b_from_phi(inputs.run1.gradient.phi0):g} → "
        f"{percent_b_from_phi(inputs.run1.gradient.phif):g} %B). Every peak elutes {ww:.2f} of its "
        "own calibrated window past the edge it was pinned at."
    )
    if ww > WINDOW_WIDTHS_STRONG:
        return Diagnostic(
            code="s_star_bracket",  # type: ignore[arg-type]
            severity="strong",
            message=(
                f"{head} Past {WINDOW_WIDTHS_STRONG:g} window-widths the LSS line was never "
                "pinned there and log k against %B is genuinely curved: Rs and the critical "
                "pair are indicative, not decision-grade. Confirm by injection, or move a "
                "scouting run out to meet it."
            ),
        )
    return Diagnostic(
        code="s_star_bracket",  # type: ignore[arg-type]
        severity="info",
        message=(
            f"{head} Up to ~{WINDOW_WIDTHS_STRONG:g} window-widths this repo's held-out run "
            "shows no detectable penalty (run 4: 0.26 window-widths out, 0.26 % |ΔtR|). "
            "A prediction to confirm, not a reason to stop."
        ),
    )


def _departure_diagnostic(scouting: Gradient, candidate: Gradient) -> Diagnostic | None:
    """#44 decision 4–5: diagnostic 7, the φ0 departure, raising and lowering treated apart."""
    delta = percent_b_from_phi(candidate.phi0 - scouting.phi0)
    if abs(delta) < 1e-9:
        return None
    b0c, b0s = percent_b_from_phi(candidate.phi0), percent_b_from_phi(scouting.phi0)
    if delta < 0:
        return Diagnostic(
            code="phi0_departure",  # type: ignore[arg-type]
            severity="info",
            message=(
                f"**Candidate starts at {b0c:g} %B, {abs(delta):.1f} %B below the scouting "
                f"runs' {b0s:g} %B.** There is no data either way for a lowered start — the "
                "doubling rule below was measured for raising only. Read the prediction as "
                "unconfirmed at this start."
            ),
        )
    multiplier = DOUBLING_FACTOR ** (delta / DOUBLING_PER_PERCENT_B)
    head = (
        f"**Candidate starts at {b0c:g} %B, {delta:.1f} %B above the scouting runs' "
        f"{b0s:g} %B.** The fit was never shown a run starting anywhere else. On this "
        f"instrument every {DOUBLING_PER_PERCENT_B:g} %B of raised start roughly doubled the "
        f"retention error — an observation on this instrument, not a law — so expect about "
        f"×{multiplier:.1f} the in-bracket residual here. No correction is fitted."
    )
    if delta >= PHI0_STRONG_PERCENT_B:
        return Diagnostic(
            code="phi0_departure",  # type: ignore[arg-type]
            severity="strong",
            message=(
                f"{head} From {PHI0_STRONG_PERCENT_B:g} %B up (×2 and beyond) Rs and the "
                "critical pair are indicative, not decision-grade: on Validation_2 the "
                "near-critical pair reached λ ≈ 0.5 at exactly this departure."
            ),
        )
    return Diagnostic(code="phi0_departure", severity="info", message=head)  # type: ignore[arg-type]


def _low_k0(cockpit: Cockpit, candidate: Gradient) -> dict[str, Diagnostic]:
    """#44 decision 6: the per-peak low-k0 badge at the candidate's φ0, single tier."""
    found = {}
    b0 = percent_b_from_phi(candidate.phi0)
    for peak, fit in cockpit.fitted:
        value = log10_k0_from_ln_k0(math.log(fit.params.k_at(candidate.phi0)))
        if value >= LOW_K0_LOG10:
            continue
        found[peak.name] = Diagnostic(
            code="low_k0",  # type: ignore[arg-type]
            severity="warning",
            message=(
                f"**{peak.name}: log₁₀ k0 = {value:.2f} at the candidate's starting {b0:g} %B, "
                f"below the {LOW_K0_LOG10:g} floor.** The band is weakly retained at the start "
                "and the k ≫ 1 basis of the model is thin for it; the one measured crossing of "
                "this floor (campaign #27 run 7, peak 1) had the dataset's worst λ. Pairs "
                "involving this peak are indicative."
            ),
            peaks=(peak.name,),
        )
    return found


def programme_points(method: Method, gradient: Gradient, until: float) -> list[tuple[float, float]]:
    """The %B seen at the detector against time from injection — dwell and t0 later."""
    arrives = method.t_dwell + method.t0
    b0, b1 = percent_b_from_phi(gradient.phi0), percent_b_from_phi(gradient.phif)
    ramp_end = arrives + gradient.t_init + gradient.t_gradient
    points = [(0.0, b0), (arrives + gradient.t_init, b0), (ramp_end, b1)]
    if until > ramp_end:
        points.append((until, b1))
    return points


def as_dict(analysis: Analysis) -> dict[str, Any]:
    """For a caption or a status cell — the headline numbers only."""
    return {
        "s*": analysis.s_cand,
        "bracket": (analysis.bracket.lo, analysis.bracket.hi),
        "window-widths": analysis.window_widths,
    }
