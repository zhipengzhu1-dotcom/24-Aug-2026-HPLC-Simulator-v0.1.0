"""THROWAWAY: the four surfaces #44 decided, computed for a candidate programme.

1. Two candidate-control inline warnings: diagnostic 1 re-expressed on s* (overshoot in
   window-widths; gentle to 0.6, strong beyond) and diagnostic 7, the φ0 departure
   (Δφ0 in %B; gentle for any non-zero departure, strong from 10 %B; raising only).
2. One readout row per peak for the fit tab: calibrated window in %B, its width, and
   where the candidate puts that peak's elution composition relative to it.
3. One per-peak badge: low k0 at the candidate φ0 (log10 k0 < 2.1), single tier.
4. One output stamp on Rs and the critical pair — indicative, not decision-grade —
   when 1 or 7 is strong; a low-k0 badge downgrades only that peak's pairs.

Numbers are #44's provisional ones (0.6 window-widths, 10 %B, 2.1); #55 re-pins them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.diagnostics import Diagnostic
from app.pipeline import Cockpit
from hplcsim.model import Method, Run
from prototype import programme as prog
from prototype.programme import Programme

GENTLE_TO_WINDOW_WIDTHS = 0.6
STRONG_DPHI0_PCT = 10.0
DOUBLING_PER_PCT = 10.0
DOUBLING_RATIO = 2.1
LOW_K0_LOG10 = 2.1


@dataclass(frozen=True)
class WindowRow:
    name: str
    lo_pct: float
    hi_pct: float
    width_pct: float  # ln β / S_e, in %B
    phi_e_pct: float  # where the candidate puts this peak's elution composition
    outside_pct: float  # 0 inside; +ve above the window, −ve below
    outside_ww: float  # |outside| in window-widths
    segment: int | None
    regime: str


@dataclass(frozen=True)
class Composition:
    candidate: tuple[Diagnostic, ...]
    rows: tuple[WindowRow, ...]
    low_k0: dict[str, Diagnostic]
    overshoot_ww: float
    dphi0_pct: float
    strong: bool

    @property
    def stamp(self) -> str | None:
        if not self.strong:
            return None
        return (
            "Rs and the critical pair are indicative, not decision-grade — the LSS line was "
            "never pinned where this candidate elutes (SPEC §6, diagnostics 1/7)."
        )

    @property
    def downgraded(self) -> tuple[str, ...]:
        return tuple(self.low_k0)


def compose(
    cockpit: Cockpit, method: Method, run1: Run, run2: Run, candidate: Programme
) -> Composition:
    s1, s2 = prog.steepness(method, run1.gradient), prog.steepness(method, run2.gradient)
    lo, hi = sorted((s1, s2))
    tg_lo, tg_hi = sorted((run1.gradient.t_gradient, run2.gradient.t_gradient))
    beta = tg_hi / tg_lo

    # --- diagnostic 1 on s*, per segment; the tier is the worst segment ----------------
    worst_ww, worst_i, worst_s = 0.0, 0, 0.0
    for i, s_cand in enumerate(candidate.steepness_per_segment(method)):
        if s_cand <= 0.0:
            continue  # a flat segment is a hold; the s* bracket says nothing about it
        if s_cand < lo:
            ww = math.log(lo / s_cand) / math.log(beta)
        elif s_cand > hi:
            ww = math.log(s_cand / hi) / math.log(beta)
        else:
            ww = 0.0
        if ww > worst_ww:
            worst_ww, worst_i, worst_s = ww, i, s_cand

    diags: list[Diagnostic] = []
    if worst_ww > 0.0:
        which = f"segment {worst_i + 1}'s " if not candidate.is_single else ""
        side = "shallower" if worst_s < lo else "steeper"
        head = (
            f"**The candidate's {which}steepness s\\* = {worst_s:.4f} sits "
            f"{worst_ww:.2f} window-widths outside the scouting bracket "
            f"[{lo:.4f}, {hi:.4f}]** ({side} than either scouting run)."
        )
        if worst_ww > GENTLE_TO_WINDOW_WIDTHS:
            diags.append(
                Diagnostic(
                    code="s_star_extrapolation",  # type: ignore[arg-type]
                    severity="strong",
                    message=(
                        f"{head} Every peak elutes at a composition its retention line was "
                        "never pinned at. Confirm by injection, or move a scouting run out "
                        "to meet it."
                    ),
                )
            )
        else:
            diags.append(
                Diagnostic(
                    code="s_star_extrapolation",  # type: ignore[arg-type]
                    severity="info",
                    message=(
                        f"{head} Modest extrapolation of this kind holds on this repo's own "
                        "held-out run (0.26 window-widths out, 0.26 % avg |ΔtR|). Treat it as "
                        "a prediction to confirm, not a reason to stop."
                    ),
                )
            )

    # --- diagnostic 7: φ0 departure ------------------------------------------------------
    dphi0 = (candidate.phi0 - run1.gradient.phi0) * 100.0
    if dphi0 > 1e-9:
        mult = DOUBLING_RATIO ** (dphi0 / DOUBLING_PER_PCT)
        head = (
            f"**The candidate starts {dphi0:g} %B above the scouting runs' "
            f"{run1.gradient.phi0 * 100:g} %B.** The fit was never shown a run starting "
            "anywhere else. On this instrument every 10 %B above the scouting start roughly "
            f"doubles the retention error — ×{mult:.1f} for this candidate. No correction is "
            "fitted."
        )
        diags.append(
            Diagnostic(
                code="phi0_departure",  # type: ignore[arg-type]
                severity="strong" if dphi0 >= STRONG_DPHI0_PCT else "info",
                message=head
                + (
                    " Confirm by injection before acting on the resolution."
                    if dphi0 >= STRONG_DPHI0_PCT
                    else ""
                ),
            )
        )
    elif dphi0 < -1e-9:
        diags.append(
            Diagnostic(
                code="phi0_departure",  # type: ignore[arg-type]
                severity="info",
                message=(
                    f"**The candidate starts {-dphi0:g} %B below the scouting runs' "
                    f"{run1.gradient.phi0 * 100:g} %B.** There is no data either way for a "
                    "lowered start; the doubling rule was measured for raising it only."
                ),
            )
        )

    # --- per-peak window rows and the low-k0 badge -------------------------------------
    rows: list[WindowRow] = []
    low_k0: dict[str, Diagnostic] = {}
    for peak, fit in cockpit.fitted:
        w_lo = min(fit.phi_e_run1, fit.phi_e_run2) * 100.0
        w_hi = max(fit.phi_e_run1, fit.phi_e_run2) * 100.0
        width = 100.0 * math.log(fit.beta) / fit.params.s_e
        e = prog.elute(fit.params, method, candidate)
        phi_e = e.phi_e * 100.0
        outside = phi_e - w_hi if phi_e > w_hi else (phi_e - w_lo if phi_e < w_lo else 0.0)
        rows.append(
            WindowRow(
                name=peak.name,
                lo_pct=w_lo,
                hi_pct=w_hi,
                width_pct=width,
                phi_e_pct=phi_e,
                outside_pct=outside,
                outside_ww=abs(outside) / width if width > 0 else math.inf,
                segment=e.segment,
                regime=e.retention.regime,
            )
        )
        log10_k0 = math.log10(fit.params.k_at(candidate.phi0))
        if log10_k0 < LOW_K0_LOG10:
            low_k0[peak.name] = Diagnostic(
                code="low_k0",  # type: ignore[arg-type]
                severity="warning",
                message=(
                    f"**{peak.name}: log10 k0 = {log10_k0:.2f} at the candidate's "
                    f"{candidate.phi0 * 100:g} %B start** (below 2.1). The band is already "
                    "moving during the hold; the one measured crossing of this floor had the "
                    "dataset's worst residual. Rs on this peak's pairs is indicative only."
                ),
                peaks=(peak.name,),
            )

    strong = any(d.severity == "strong" for d in diags)
    return Composition(
        candidate=tuple(diags),
        rows=tuple(rows),
        low_k0=low_k0,
        overshoot_ww=worst_ww,
        dphi0_pct=dphi0,
        strong=strong,
    )
