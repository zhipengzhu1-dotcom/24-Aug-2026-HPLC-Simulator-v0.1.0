"""SPEC §5's entry checks and SPEC §6's nine diagnostics, computed (tickets #20, #72).

Streamlit-free, like the rest of the app's logic layer, and for a specific reason:
every diagnostic here is a *threshold*, and a threshold whose only expression is a
call inside a widget file can be re-tuned by accident and re-checked by nobody. The
numbers live here as named constants, `tests/test_diagnostics.py` pins them, and
``streamlit_app.py`` decides only where each one is painted.

Placement is SPEC §6's own sentence, which is why :class:`Diagnostics` has the fields
it has rather than one flat list: "per-peak badges (2, 4, 8, 9), fit-page notices (3),
result banners (5), output stamps (6, and the indicative stamp), candidate-control
inline warnings (1, 7)", plus the per-peak composition-window readout for the fit tab.
The entry checks of SPEC §5 get a field of their own, and the dead-time checks another,
painted beside the t0 field they are about.

Nothing here blocks. CLAUDE.md's warnings-over-blocks posture is the whole shape of
the module: :func:`diagnose` returns annotations, and the one impossibility the
Cockpit can produce (two scouting runs at the same tG) is still
``Cockpit.blocked``'s, not a diagnostic's.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from app import wording
from app.entry import Entry
from app.pipeline import Cockpit, CockpitInputs, run_cockpit
from hplcsim.dead_time import DeadTimeCheck, check_measured_t0, classify_marker
from hplcsim.fit import LOW_K0_LOG10, FitResult, classify_spacing
from hplcsim.model import (
    Gradient,
    Leg,
    Method,
    Peak,
    PeakRow,
    Programme,
    RetentionParams,
    Run,
    Target,
    as_programme,
    log10_k0_from_ln_k0,
    percent_b_from_phi,
)
from hplcsim.resolution import PredictedPeak, ResolutionTable

Severity = Literal["info", "warning", "strong"]

# Every diagnostic this module can emit. A Literal rather than a bare str because three
# places downstream switch on it — the table's badge labels, the status bar's stamp, the
# chromatogram's crossing caption — and a typo in any of them would silently match
# nothing. SPEC §6's nine (v0.2's 1, 7, 8, 9 and the indicative stamp first), then SPEC
# §5's two entry checks, then SPEC §4's two checks on a measured dead time (ticket #24).
Code = Literal[
    "steepness_extrapolation",
    "phi0_departure",
    "low_k0",
    "wash_eluted",
    "indicative",
    "early_eluter",
    "beta_spacing",
    "prediction_crossing",
    "defaulted_width",
    "estimated_t0",
    "area_share",
    "entry_crossing",
    "dead_time_check",
    "t0_marker",
]

# SPEC §6 diagnostic 1, re-expressed on s* by #44 and re-pinned by #55: the overshoot
# past the scouting bracket is measured in *window-widths* — log_β(s*_edge / s*_cand),
# the distance beyond every peak's calibrated composition window in units of that
# window's own width (composition-extrapolation.md §7.3; S_e cancels, so it is one
# method-level number). Gentle to ~0.6, strong beyond. 0.6 is v0.1 continuity: log₃ 2 =
# 0.63 is the "~2× outside" tier v0.1 users already had on plain tG extrapolation. Not a
# number the data set — no on-ramp run sits beyond 0.26 window-widths (SPEC §6 item 1).
STRONG_WINDOW_WIDTHS = 0.6

# SPEC §6 diagnostic 7 (#44, re-pinned by #55): Δφ0 = φ0,cand − φ0,scout, the candidate's
# *start* against the scouting start, as a fraction like every φ in the engine. Gentle
# for any departure above; strong from +10 %B, the smallest departure measured — at that
# step the retention error doubled on both samples and reached λ = 1.58 on one. No run
# sits between 0 and +10 %B, so the tier is untested below it.
STRONG_PHI0_DEPARTURE = 0.10

# The ladders those tiers are *described* by live in `app.wording`: they are quoted and
# never compared, and SPEC §6 item 7 turns on their never being evaluated.

# The method-level guards whose strong tier drives the indicative stamp (SPEC §6 items 1
# and 7), and the per-peak badges that downgrade only a peak's own Rs pairs (items 8, 9).
_STAMPING_GUARDS: frozenset[str] = frozenset({"steepness_extrapolation", "phi0_departure"})
_PAIR_DOWNGRADING_BADGES: frozenset[str] = frozenset({"low_k0", "wash_eluted"})

# SPEC §5's area-share tracking check: "default threshold ~30% relative change". The
# change is measured against the *first* run's share, which is the larger base for a
# peak whose share grows and so the more conservative reading of "relative change".
AREA_SHARE_THRESHOLD = 0.30


# Research doc §4.3's other early-eluter test, beside t'R < t0: "Report a low-confidence
# flag when k_e at the fitted parameters is below ~1". The engine already sets
# `RetentionResult.low_confidence` on it; diagnostic 2 is what puts it on screen.
_MIN_RETENTION_FACTOR = 1.0


@dataclass(frozen=True)
class Diagnostic:
    """One thing worth saying about the condition on screen.

    ``code`` is the stable identity — the UI groups and places by it, never by
    matching the prose, so wording can be edited without moving anything on screen.
    ``peaks`` names whichever peaks the diagnostic is about, empty when it is about
    the method or the condition as a whole.
    """

    code: Code
    severity: Severity
    message: str
    peaks: tuple[str, ...] = ()


@dataclass(frozen=True)
class Diagnostics:
    """Every check for one rendering, filed under the placement SPEC §6 gives it."""

    candidate: tuple[Diagnostic, ...] = ()
    fit: tuple[Diagnostic, ...] = ()
    banners: tuple[Diagnostic, ...] = ()
    stamps: tuple[Diagnostic, ...] = ()
    entry: tuple[Diagnostic, ...] = ()
    badges: Mapping[str, tuple[Diagnostic, ...]] = field(default_factory=dict)
    # SPEC §4's checks on the *measured* t0 — beside the field that holds it, in the
    # sidebar, since they are about the number typed rather than about any result.
    method: tuple[Diagnostic, ...] = ()
    # SPEC §6's *indicative, not decision-grade* stamp (#44 decision 8): on Min. Rs, the
    # resolution tab and the status bar, in the manner of 6 — but its own field, not one
    # of ``stamps``, because the two say different things on different surfaces and the
    # t0 stamp's short form must not be painted for this one.
    indicative: Diagnostic | None = None
    # The per-peak composition-window readout for the fit-parameters tab (SPEC §6,
    # presentation): the per-peak fact behind diagnostic 1, whose tier is method-level.
    windows: tuple[CompositionWindow, ...] = ()

    @property
    def all(self) -> tuple[Diagnostic, ...]:
        """Everything, in no particular order — for tests and for counting."""
        return (
            self.candidate
            + self.fit
            + self.banners
            + self.stamps
            + self.entry
            + self.method
            + _zero_or_one(self.indicative)
            + tuple(d for badges in self.badges.values() for d in badges)
        )

    def pair_is_indicative(self, pair: tuple[str, str]) -> bool:
        """Whether the Rs of ``pair`` is indicative rather than decision-grade.

        The stamp downgrades every pair; a low-k0 or wash-eluted badge downgrades only
        the pairs involving that peak (SPEC §6, "What a prediction may claim").
        """
        if self.indicative is not None:
            return True
        return any(
            badge.code in _PAIR_DOWNGRADING_BADGES
            for name in pair
            for badge in self.badges.get(name, ())
        )


WindowPosition = Literal["inside", "below", "above"]

# A candidate on a scouting run's own edge elutes at that run's φ_e up to rounding; the
# tolerance keeps "on the edge" inside, which is where the bracket puts it too.
_WINDOW_EDGE_TOLERANCE = 1e-9


@dataclass(frozen=True)
class CompositionWindow:
    """One peak's calibrated composition window, and where the candidate puts it.

    The window is [φ_e,run2, φ_e,run1] — the two elution compositions the fit was shown,
    which is all it was shown (composition-extrapolation.md §7.1); its width is ln β / S_e
    under the large-k0 law and is ~9 %B per peak on the 5 → 95 %B scouting pairs on
    file, disjoint between peaks. ``candidate_phi_e`` is the composition at which the
    candidate elutes this peak, read back from the predicted k at elution. Every value
    is a fraction; the fit tab converts at its display boundary.
    """

    name: str
    phi_low: float
    phi_high: float
    candidate_phi_e: float

    @property
    def width(self) -> float:
        return self.phi_high - self.phi_low

    @property
    def position(self) -> WindowPosition:
        if self.candidate_phi_e < self.phi_low - _WINDOW_EDGE_TOLERANCE:
            return "below"
        if self.candidate_phi_e > self.phi_high + _WINDOW_EDGE_TOLERANCE:
            return "above"
        return "inside"

    @property
    def distance_in_widths(self) -> float:
        """The per-peak distance past the window, in units of this window's width.

        The same number as the method-level :func:`window_widths_outside` for every peak
        when the candidate is a ramp (S_e cancels, research doc §7.3); different, and
        honest, for a peak brought off in a hold.
        """
        if self.position == "below":
            return (self.phi_low - self.candidate_phi_e) / self.width
        if self.position == "above":
            return (self.candidate_phi_e - self.phi_high) / self.width
        return 0.0


def diagnose(
    inputs: CockpitInputs,
    cockpit: Cockpit | None = None,
    *,
    area_share_threshold: float = AREA_SHARE_THRESHOLD,
) -> Diagnostics:
    """Run every SPEC §5 entry check and SPEC §6 diagnostic over one screen's state.

    ``cockpit`` is the already-computed rendering; the app passes the one it is about
    to paint rather than paying for a second fit. Left out, the fit is run here, which
    is what makes a test a single call.
    """
    if cockpit is None:
        cockpit = run_cockpit(inputs)

    entry = (
        *_area_share_disagreements(cockpit.entry, area_share_threshold),
        *_entry_crossings(cockpit.entry.tracked),
    )

    # SPEC §4's one impossibility, and the line it draws through this function. Two runs
    # at one tG fit nothing and predict nothing, so a β of 1.0 and a bracket of zero
    # width are consequences of the block rather than further findings — but SPEC §5's
    # entry checks read only the rows the user typed, and the peak table is still there
    # and still worth checking while they go and fix the gradient time.
    if cockpit.blocked is not None:
        return Diagnostics(
            stamps=_zero_or_one(_estimated_t0(inputs.method)),
            entry=entry,
            method=dead_time_notices(inputs.method),
        )

    programme = as_programme(inputs.target)
    candidate = (
        *_zero_or_one(
            _steepness_extrapolation(
                inputs.method, programme, inputs.run1, inputs.run2, cockpit.resolution
            )
        ),
        *_zero_or_one(_phi0_departure(programme, inputs.run1.gradient)),
    )
    return Diagnostics(
        candidate=candidate,
        indicative=_indicative(candidate),
        windows=_composition_windows(cockpit),
        fit=_zero_or_one(_beta_spacing(inputs.run1, inputs.run2)),
        stamps=_zero_or_one(_estimated_t0(inputs.method)),
        banners=_zero_or_one(_defaulted_widths(cockpit.defaulted_width_names)),
        entry=entry,
        badges=_badges(cockpit, inputs.method, programme),
        method=dead_time_notices(inputs.method),
    )


def _badges(
    cockpit: Cockpit, method: Method, programme: Programme
) -> dict[str, tuple[Diagnostic, ...]]:
    """SPEC §6's four per-peak diagnostics (2, 4, 8, 9), one entry per predicted peak.

    Every predicted peak gets a key, clean ones with an empty tuple, so the table and
    the selected-peak panel can read ``badges[name]`` for a row without asking first
    whether that row has anything to say.
    """
    if cockpit.resolution is None:
        return {}
    peaks = cockpit.resolution.peaks
    per_peak = (
        _early_eluters(peaks, method, programme),
        _prediction_crossings(cockpit),
        _low_k0_at_start(cockpit, programme),
        _wash_eluted(peaks, programme),
    )
    return {
        peak.name: tuple(
            found for found in (group.get(peak.name) for group in per_peak) if found is not None
        )
        for peak in peaks
    }


def _zero_or_one(diagnostic: Diagnostic | None) -> tuple[Diagnostic, ...]:
    """A check that either fires once or stays quiet, as the group the fields hold."""
    return () if diagnostic is None else (diagnostic,)


# --- diagnostic 1: how far outside the scouting bracket the candidate's steepness sits ---


def scouting_bracket(run1: Run, run2: Run) -> tuple[float, float]:
    """The gradient times the fit is calibrated between, shortest first."""
    lo, hi = sorted((run1.gradient.t_gradient, run2.gradient.t_gradient))
    return lo, hi


def steepness(method: Method, leg: Leg) -> float:
    """s* = t0·|Δφ| / duration for one leg — the one number a candidate enters φ_e through.

    composition-extrapolation.md §7.2: the elution composition depends on the candidate
    only through s*, so the tG question and the composition question are one question.
    Unsigned, because a bracket has no direction; the walker's signed b_e is a different
    quantity with a different home (:func:`hplcsim.retention.segment_steepness`). Zero
    for a hold.
    """
    return method.t0 * abs(leg.delta_phi) / leg.duration


def steepness_bracket(method: Method, run1: Run, run2: Run) -> tuple[float, float]:
    """[s*₂, s*₁]: the steepnesses the scouting pair calibrated between, shallowest first."""
    values = sorted(
        steepness(method, leg)
        for run in (run1, run2)
        for leg in Programme.from_gradient(run.gradient).legs()
    )
    return values[0], values[-1]


def window_widths_outside(method: Method, leg: Leg, run1: Run, run2: Run) -> float:
    """How far past the scouting bracket ``leg``'s s* sits, in window-widths.

    log_β(s*_edge / s*_cand) — research doc §7.3, where dividing the φ overshoot by the
    peak's window width ln β / S_e cancels S_e, so the number is the same for every
    peak. 0 inside the bracket and on its edges, and 0 for a hold: s* = 0 has no
    position in a steepness bracket (SPEC §6 item 1, #58).
    """
    if leg.is_hold:
        return 0.0
    lo, hi = steepness_bracket(method, run1, run2)
    s_star = steepness(method, leg)
    if lo <= s_star <= hi:
        return 0.0
    edge = hi if s_star > hi else lo
    beta = scouting_beta(run1, run2)
    return abs(math.log(edge / s_star)) / math.log(beta)


def _steepness_extrapolation(
    method: Method,
    programme: Programme,
    run1: Run,
    run2: Run,
    resolution: ResolutionTable | None,
) -> Diagnostic | None:
    """SPEC §6 diagnostic 1, at the candidate controls.

    Per ramp segment, tier from the worst segment *in which at least one peak is
    predicted to elute* (#58): an inert trailing wash cannot fire it, and it is silent
    when every peak leaves in a hold or after the programme ends. With nothing predicted
    yet — no peak table, or no peak that fitted — there is no elution to attribute, so
    every ramp is read: the candidate is the programme as typed, which is what a v0.1
    session without peaks was told too.
    """
    legs = programme.legs()
    predicted = resolution.peaks if resolution is not None else ()
    if predicted:
        read = sorted(
            index
            for index in {peak.retention.eluting_segment for peak in predicted}
            if index is not None
        )
    else:
        read = [index for index, leg in enumerate(legs) if not leg.is_hold]
    distances = {index: window_widths_outside(method, legs[index], run1, run2) for index in read}
    if not distances or max(distances.values()) <= 0.0:
        return None
    worst = max(distances, key=lambda index: distances[index])
    widths = distances[worst]
    leg = legs[worst]
    lo, hi = steepness_bracket(method, run1, run2)
    s_star = steepness(method, leg)
    where = "steeper" if s_star > hi else "shallower"

    # The v0.1 reading of the same distance, kept where it still applies: one segment
    # over the scouting range makes the s* ratio the tG ratio, and "1.33× outside the
    # 15–45 min bracket" is the sentence v0.1 users already read.
    single = programme.as_gradient()
    scouting = run1.gradient
    if single is not None and (single.phi0, single.phif) == (scouting.phi0, scouting.phif):
        t_lo, t_hi = scouting_bracket(run1, run2)
        factor = single.t_gradient / t_hi if single.t_gradient > t_hi else t_lo / single.t_gradient
        longer = "longer" if single.t_gradient > t_hi else "shorter"
        head = wording.steepness_head_gradient(
            t_gradient=single.t_gradient,
            factor=factor,
            t_lo=t_lo,
            t_hi=t_hi,
            longer=longer,
            widths=widths,
        )
    else:
        which = f"segment {worst + 1}" if len(legs) > 1 else "the candidate"
        head = wording.steepness_head_segment(
            which=which, s_star=s_star, widths=widths, where=where, lo=lo, hi=hi
        )
    if widths > STRONG_WINDOW_WIDTHS:
        return Diagnostic(
            code="steepness_extrapolation",
            severity="strong",
            message=wording.steepness_strong(head),
        )
    return Diagnostic(
        code="steepness_extrapolation",
        severity="info",
        message=wording.steepness_info(head),
    )


# --- diagnostic 7: the candidate's start against the scouting start ---------------------


def phi0_departure(programme: Programme, scouting: Gradient) -> float:
    """Δφ0 = φ0,cand − φ0,scout as a fraction, rounded so 0.15 − 0.05 is exactly 0.10.

    The candidate's *start* only: a later segment that steps above the scouting start
    earns no term, because every mechanism #52 left standing acts while the band sits
    at the head of the column (#58). Binary floating point puts 0.15 − 0.05 a hair under
    0.1, which would read a +10 %B departure as gentle; the rounding is to the ninth
    decimal, the same place the display boundary rounds.
    """
    return round(programme.phi0 - scouting.phi0, 9)


def _phi0_departure(programme: Programme, scouting: Gradient) -> Diagnostic | None:
    """SPEC §6 diagnostic 7, at the candidate controls beside 1.

    Method-level. Raising is gentle at any amount and strong from +10 %B; lowering is
    gentle at any amount with no data either way. No correction is fitted and no
    multiplier is evaluated — the message quotes the two ladders as observations from
    5 %B starts, so a pair scouted elsewhere has the guard and not the numbers.
    """
    departure = phi0_departure(programme, scouting)
    if departure == 0.0:
        return None
    sign = "+" if departure > 0.0 else "−"
    start = percent_b_from_phi(programme.phi0)
    scout = percent_b_from_phi(scouting.phi0)
    head = wording.phi0_head(start=start, sign=sign, delta=abs(start - scout), scout=scout)
    if departure < 0.0:
        return Diagnostic(
            code="phi0_departure",
            severity="info",
            message=wording.phi0_lowered(head),
        )
    if departure >= STRONG_PHI0_DEPARTURE:
        return Diagnostic(
            code="phi0_departure",
            severity="strong",
            message=wording.phi0_raised_strong(head),
        )
    return Diagnostic(
        code="phi0_departure",
        severity="info",
        message=wording.phi0_raised_info(head),
    )


# --- the indicative stamp: what a prediction may claim (SPEC §6, #44 decision 8) -----------


def _indicative(candidate: Sequence[Diagnostic]) -> Diagnostic | None:
    """Strong on 1 or 7 stamps Rs and the critical pair *indicative, not decision-grade*.

    Driven by the worse of the two guards; gentle on either leaves the numbers
    unstamped. Retention times stay shown as numbers. Nowhere is curvature-corrected
    accuracy claimed — two parameters cannot see curvature.
    """
    strong = [d for d in candidate if d.code in _STAMPING_GUARDS and d.severity == "strong"]
    if not strong:
        return None
    reasons = [
        wording.INDICATIVE_REASON_STEEPNESS
        if guard.code == "steepness_extrapolation"
        else wording.INDICATIVE_REASON_PHI0
        for guard in strong
    ]
    return Diagnostic(
        code="indicative",
        severity="strong",
        message=wording.indicative(reasons),
    )


def critical_pair_is_indicative(cockpit: Cockpit, diagnostics: Diagnostics) -> bool:
    """Whether the Rs the screen leads with is indicative rather than decision-grade.

    The method-level stamp downgrades every pair, so it downgrades this one. But SPEC
    §6 also says "a low-k0 or wash-eluted badge downgrades only the pairs involving that
    peak" — and when the badged peak *is* in the critical pair, Min. Rs and the critical
    pair are exactly the two numbers that must not be read as decision-grade, whether or
    not either method-level guard fired. Asking the pair rather than the method is what
    keeps those surfaces honest for a candidate at the scouting start, inside the
    steepness bracket, with one peak left in a trailing hold: no stamp, and one downgraded pair.
    """
    critical = cockpit.resolution.critical_pair if cockpit.resolution else None
    if critical is None:
        return False
    return diagnostics.pair_is_indicative((critical.earlier.name, critical.later.name))


# --- the per-peak composition-window readout (SPEC §6, presentation) -----------------------


def _composition_windows(cockpit: Cockpit) -> tuple[CompositionWindow, ...]:
    """Each fitted peak's [φ_e,run2, φ_e,run1] and where the candidate elutes it."""
    predicted = cockpit.predicted_by_name
    return tuple(
        _composition_window(peak.name, fit, predicted[peak.name].retention.k_e)
        for peak, fit in cockpit.fitted
        if peak.name in predicted
    )


def _composition_window(name: str, fit: FitResult, k_e: float) -> CompositionWindow:
    low, high = sorted((fit.phi_e_run1, fit.phi_e_run2))
    return CompositionWindow(
        name=name,
        phi_low=low,
        phi_high=high,
        candidate_phi_e=_elution_composition(fit.params, k_e),
    )


def _elution_composition(params: RetentionParams, k_e: float) -> float:
    """φ_e from the k at elution — the LSS line read backwards, natural-log throughout."""
    return params.phi_ref + (params.ln_k0 - math.log(k_e)) / params.s_e


# --- diagnostic 3: the spacing of the two scouting runs ----------------------------------


def scouting_beta(run1: Run, run2: Run) -> float:
    """β = the ratio of the two scouting gradient times, ≥ 1 whichever way they came.

    The same number the engine reports as ``FitResult.beta``, taken from the runs so
    the entry check can speak before any peak has been fitted. A test pins the two
    against each other.
    """
    lo, hi = scouting_bracket(run1, run2)
    return hi / lo


def _beta_spacing(run1: Run, run2: Run) -> Diagnostic | None:
    """SPEC §6 diagnostic 3 / SPEC §4's spacing-ratio tiers — a warning, never a block."""
    beta = scouting_beta(run1, run2)
    tier = classify_spacing(beta)
    if tier == "ok":
        return None
    head = wording.beta_head(
        beta=beta,
        t_gradient1=run1.gradient.t_gradient,
        t_gradient2=run2.gradient.t_gradient,
    )
    if tier == "strong":
        return Diagnostic(
            code="beta_spacing",
            severity="strong",
            message=wording.beta_strong(head),
        )
    return Diagnostic(
        code="beta_spacing",
        severity="warning",
        message=wording.beta_warning(head),
    )


# --- diagnostic 6: predictions made on an estimated dead time ----------------------------


def _estimated_t0(method: Method) -> Diagnostic | None:
    """SPEC §6 diagnostic 6, stamped on every output rather than shown once.

    Worded to the two regimes of `dead-time-from-geometry.md` §6, which differ by a
    factor of forty, rather than as a bare "lower confidence". The two-run fit absorbs
    t0 into k0 (§6.1's cancellation), so predictions of these gradients barely move;
    what a wrong t0 corrupts is the fitted S, k0 and N — and any use of them at a
    different flow or on a different column, where the cancellation is broken (§6.3).
    """
    if method.t0_is_measured:
        return None
    return Diagnostic(
        code="estimated_t0",
        severity="warning",
        message=wording.estimated_t0(method.t0),
    )


# --- SPEC §4's two checks on a measured dead time (ticket #24) ---------------------------


def dead_time_notices(method: Method) -> tuple[Diagnostic, ...]:
    """The reverse check and the marker check, for the sidebar beside the t0 field.

    Both are about a *measured* t0 — an estimated one carries diagnostic 6 instead, and
    has no marker. The reverse check needs the column geometry, and says nothing
    rather than failing when it is absent: the geometry is optional metadata everywhere
    else in SPEC §4.
    """
    if not method.t0_is_measured:
        return ()
    try:
        check = check_measured_t0(method)
    except ValueError:
        readout = None
    else:
        readout = _dead_time_readout(check)
    return (*_zero_or_one(readout), *_zero_or_one(_marker_check(method.t0_marker)))


def _dead_time_readout(check: DeadTimeCheck) -> Diagnostic:
    """What the typed t0 implies — a statement of fact, and a warning only past the edge.

    Geometry excludes the plumbing, so a measured t0 *above* the estimate is the
    expected ordering; the gap is the instrument's extra-column volume, measured from
    numbers already on screen. The tiers are `hplcsim.dead_time`'s; this is the wording.
    """
    porosity = wording.porosity_phrase(check.implied_porosity)

    if check.finding == "impossible_porosity":
        return Diagnostic(
            code="dead_time_check",
            severity="strong",
            message=wording.dead_time_impossible_porosity(
                porosity=porosity, column_volume_ml=check.column_volume_ml
            ),
        )
    if check.finding == "implausible_porosity":
        return Diagnostic(
            code="dead_time_check",
            severity="warning",
            message=wording.dead_time_implausible_porosity(porosity),
        )

    geometry = check.geometry
    if geometry is None or check.extra_column_volume_ml is None:
        return Diagnostic(
            code="dead_time_check",
            severity="info",
            message=wording.dead_time_no_geometry(
                porosity=porosity, column_volume_ml=check.column_volume_ml
            ),
        )

    band_lo, band_hi = geometry.t0_band
    against = wording.geometry_phrase(
        label=geometry.porosity.label,
        t0=geometry.t0,
        porosity_value=geometry.porosity.value,
        band_lo=band_lo,
        band_hi=band_hi,
    )
    if check.finding == "below_geometry":
        return Diagnostic(
            code="dead_time_check",
            severity="warning",
            message=wording.dead_time_below_geometry(
                extra_column_ml=check.extra_column_volume_ml, against=against
            ),
        )
    if check.finding == "marker_retained":
        return Diagnostic(
            code="dead_time_check",
            severity="warning",
            message=wording.dead_time_marker_retained(
                extra_column_ml=check.extra_column_volume_ml,
                porosity=porosity,
                against=against,
            ),
        )
    return Diagnostic(
        code="dead_time_check",
        severity="info",
        message=wording.dead_time_measured(
            porosity=porosity,
            extra_column_ml=check.extra_column_volume_ml,
            against=against,
        ),
    )


def _marker_check(marker: str | None) -> Diagnostic | None:
    """A measured t0 without its marker has no provenance (research doc §5.2, §7.6)."""
    kind = classify_marker(marker)
    if kind == "compound":
        return None
    if kind == "absent":
        message = wording.marker_absent()
    elif kind == "solvent_disturbance":
        message = wording.marker_solvent_disturbance(marker)
    else:
        message = wording.marker_inorganic(marker)
    return Diagnostic(code="t0_marker", severity="warning", message=message)


# --- SPEC §5's entry checks --------------------------------------------------------------


@dataclass(frozen=True)
class _EnteredRow:
    """One typed row, whichever half of :class:`~app.entry.Entry` it came from.

    ``Entry`` splits on completeness, and SPEC §5's checks do not: the area check has
    to normalise over the whole sample or every share is wrong, and the co-elution
    check has to see a half-paired row that shares a tR with a complete one. So both
    halves are flattened back here rather than the checks reaching for one of them.
    """

    name: str
    t_r_run1: float | None
    t_r_run2: float | None
    area_run1: float | None
    area_run2: float | None


def _entered_rows(entry: Entry) -> list[_EnteredRow]:
    """Every non-blank row the user typed, tracked or not.

    The annotation is load-bearing: ``Peak`` and ``PeakRow`` share no base class, so
    without it the concatenation infers as ``object`` and every attribute below fails
    to typecheck.
    """
    rows: list[Peak | PeakRow] = [*entry.tracked, *entry.untracked]
    return [
        _EnteredRow(row.name, row.t_r_run1, row.t_r_run2, row.area_run1, row.area_run2)
        for row in rows
    ]


def _area_rows(entry: Entry) -> list[tuple[str, float, float]]:
    """Every non-blank row carrying an area in *both* runs, as (name, run 1, run 2).

    Untracked rows count: they are part of the sample, so leaving them out of the
    normalisation would move everybody else's share. What they cannot do is be
    compared against a prediction, which is a different check.
    """
    return [
        (row.name, row.area_run1, row.area_run2)
        for row in _entered_rows(entry)
        if row.area_run1 is not None and row.area_run2 is not None
    ]


def _co_eluting(entry: Entry) -> set[str]:
    """Rows sharing a retention time with another row within a run (SPEC §5).

    "Within-run co-elution entry legal (area check relaxes)": an integrator handed two
    bands under one envelope reports one area, so the share of either peak in that run
    is not a measurement of that compound and the check has nothing to compare. Exact
    equality is the right test — these are two numbers a chromatographer typed to say
    "these came out together", not two independent measurements that happen to agree.
    """
    names: set[str] = set()
    rows = _entered_rows(entry)
    for index in (0, 1):
        seen: dict[float, str] = {}
        for row in rows:
            t_r = row.t_r_run1 if index == 0 else row.t_r_run2
            if t_r is None:
                continue
            if t_r in seen:
                names.add(seen[t_r])
                names.add(row.name)
            else:
                seen[t_r] = row.name
    return names


def _area_share_disagreements(entry: Entry, threshold: float) -> list[Diagnostic]:
    """SPEC §5's area-share tracking check, one diagnostic per row that fails it.

    A peak's *share* is compared rather than its area, so a run that simply integrated
    hotter moves nothing. What a share does catch is Molnár's area-ratio argument
    (research doc §7.4): a compound is the same fraction of the sample in both runs,
    so a share that moves a long way says the two rows are not the same compound —
    or that one run's integration of it cannot be trusted.
    """
    rows = _area_rows(entry)
    total1 = sum(area1 for _, area1, _ in rows)
    total2 = sum(area2 for _, _, area2 in rows)
    if len(rows) < 2 or total1 <= 0.0 or total2 <= 0.0:
        return []

    relaxed = _co_eluting(entry)
    found = []
    for name, area1, area2 in rows:
        if name in relaxed:
            continue
        share1 = area1 / total1
        share2 = area2 / total2
        # A peak integrated as nothing in run 1 has no share to measure a change
        # against. Rare, and not a case SPEC §5 gives a rule for — so it is left
        # unchecked rather than given an invented one.
        if share1 <= 0.0:
            continue
        change = abs(share2 - share1) / share1
        if change <= threshold:
            continue
        found.append(
            Diagnostic(
                code="area_share",
                severity="warning",
                message=wording.area_share(
                    name=name,
                    change=change,
                    share1=share1,
                    share2=share2,
                    threshold=threshold,
                ),
                peaks=(name,),
            )
        )
    return found


# --- diagnostic 2: peaks that leave before the gradient has developed --------------------


def _early_eluters(
    peaks: Sequence[PredictedPeak], method: Method, candidate: Target
) -> dict[str, Diagnostic]:
    """SPEC §6 diagnostic 2: "elutes near t0 + dwell + hold".

    Two ways to be early, and research doc §4.1 and §4.3 own one each. A band that never
    meets the gradient at all migrated isocratically at φ0 and carries no gradient
    information; a band that leaves within one t0 of the ramp arriving (t'R < t0) met it
    but had almost no distance left to be separated over, and the k ≫ 1 approximation
    behind the whole model is at its weakest there.
    """
    tau = method.t_dwell + candidate.t_init
    found = {}
    for peak in peaks:
        t_r_prime = peak.retention.t_r - method.t0 - tau
        in_the_hold = peak.retention.regime == "isocratic_hold"
        barely_retained = peak.retention.k_e < _MIN_RETENTION_FACTOR
        if not in_the_hold and t_r_prime >= method.t0 and not barely_retained:
            continue
        if in_the_hold:
            reason = wording.early_reason_never_meets(tau)
        elif t_r_prime < method.t0:
            reason = wording.early_reason_inside_t0(t_r_prime=t_r_prime, t0=method.t0)
        else:
            reason = wording.early_reason_barely_retained(
                k_e=peak.retention.k_e, floor=_MIN_RETENTION_FACTOR
            )
        found[peak.name] = Diagnostic(
            code="early_eluter",
            severity="warning",
            message=wording.early_eluter(name=peak.name, reason=reason),
            peaks=(peak.name,),
        )
    return found


# --- diagnostic 8: k0 at the candidate's start below the closed form's floor ------------


def _low_k0_at_start(cockpit: Cockpit, programme: Programme) -> dict[str, Diagnostic]:
    """SPEC §6 diagnostic 8: log₁₀ k0 at the candidate's φ0 below Guillarme's 2.1 floor.

    The engine's own floor (:data:`hplcsim.fit.LOW_K0_LOG10`), applied where the
    candidate starts rather than where the scouting runs did — the fit's ``low_k0`` is
    the same test at the scouting φ0. A limit of the closed form rather than of the
    arithmetic, and one point of evidence: three-peak run 7 Unknown-1 at log₁₀ k0 ≈ 1.7
    had the dataset's worst λ, 1.90. One point, hence one tier.
    """
    found = {}
    for peak, fit in cockpit.fitted:
        log10_k0 = log10_k0_from_ln_k0(math.log(fit.params.k_at(programme.phi0)))
        if log10_k0 >= LOW_K0_LOG10:
            continue
        found[peak.name] = Diagnostic(
            code="low_k0",
            severity="warning",
            message=wording.low_k0(
                name=peak.name,
                log10_k0=log10_k0,
                percent_b=percent_b_from_phi(programme.phi0),
            ),
            peaks=(peak.name,),
        )
    return found


# --- diagnostic 9: peaks brought off in a later hold or after the programme ends ----------


def _wash_eluted(peaks: Sequence[PredictedPeak], programme: Programme) -> dict[str, Diagnostic]:
    """SPEC §6 diagnostic 9 (#58): the post-gradient regime — a *later* hold or after the end.

    The initial hold is diagnostic 2's. Such a peak's retention rests on k extrapolated
    to a composition the fit never saw. Evidence cutting both ways: three-peak run 6
    Unknown-3 left in the wash at 46.8 min against a pre-registered 47.0 — the
    extrapolation held on the one case measured, which is why this is one tier and not
    a stamp; it was unmarked, which is why it exists.
    """
    legs = programme.legs()
    found = {}
    for peak in peaks:
        if peak.retention.regime != "post_gradient":
            continue
        index = peak.retention.eluting_segment
        composition = programme.phif if index is None else legs[index].phi_end
        percent_b = percent_b_from_phi(composition)
        if index is None:
            where = wording.wash_where_after_end(percent_b)
        else:
            where = wording.wash_where_hold(percent_b=percent_b, segment=index + 1)
        found[peak.name] = Diagnostic(
            code="wash_eluted",
            severity="warning",
            message=wording.wash_eluted(name=peak.name, where=where, percent_b=percent_b),
            peaks=(peak.name,),
        )
    return found


# --- diagnostic 4: peaks that change places at the candidate ------------------------------


def _prediction_crossings(cockpit: Cockpit) -> dict[str, Diagnostic]:
    """SPEC §6 diagnostic 4: order at the candidate differs from the scouting runs.

    Checked against *both* scouting runs, not one: peaks with different S cross as tG
    changes (research doc §7.4), and which run a pair crossed relative to is exactly
    what the chromatographer needs to know before trusting a peak's identity on the
    predicted trace.
    """
    if cockpit.resolution is None:
        return {}
    predicted = tuple(peak.name for peak in cockpit.resolution.peaks)
    fitted = [peak for peak, _ in cockpit.fitted]

    partners: dict[str, set[str]] = {}
    for scouting in (_order_by(fitted, 0), _order_by(fitted, 1)):
        for earlier, later in _swapped_pairs(predicted, scouting):
            partners.setdefault(earlier, set()).add(later)
            partners.setdefault(later, set()).add(earlier)

    return {
        name: Diagnostic(
            code="prediction_crossing",
            severity="warning",
            message=wording.prediction_crossing(name=name, crossed=crossed),
            peaks=(name, *crossed),
        )
        for name in predicted
        if (crossed := tuple(n for n in predicted if n in partners.get(name, ())))
    }


def _order_by(peaks: Sequence[Peak], run: int) -> tuple[str, ...]:
    """Elution order in one scouting run, from the retention times as entered."""
    times = [(peak.name, peak.t_r_run1 if run == 0 else peak.t_r_run2) for peak in peaks]
    return tuple(name for name, _ in sorted(times, key=lambda item: item[1]))


def _swapped_pairs(order: Sequence[str], other: Sequence[str]) -> Iterable[tuple[str, str]]:
    """Pairs whose relative order differs between two orderings, in ``order``'s order."""
    rank = {name: index for index, name in enumerate(other)}
    for index, earlier in enumerate(order):
        for later in order[index + 1 :]:
            if earlier in rank and later in rank and rank[earlier] > rank[later]:
                yield earlier, later


# --- SPEC §5: the scouting runs disagreeing about elution order ---------------------------


def _entry_crossings(tracked: Sequence[Peak]) -> list[Diagnostic]:
    """SPEC §5's "elution-order crossing flags for confirmation".

    A crossing *between the two scouting runs* is where peak tracking does real damage:
    research doc §7.4 is blunt that if two peaks swap and were matched by elution order,
    both fits are garbage. So this asks rather than assumes — the rows are fitted either
    way (warnings over blocks), with the question beside them.
    """
    return [
        Diagnostic(
            code="entry_crossing",
            severity="warning",
            message=wording.entry_crossing(earlier=earlier, later=later),
            peaks=(earlier, later),
        )
        for earlier, later in _swapped_pairs(_order_by(tracked, 0), _order_by(tracked, 1))
    ]


# --- diagnostic 5: widths and Rs resting on a column estimate of N ------------------------

# SPEC §6 diagnostic 5, scoped to peaks whose N is the column estimate. The sentence is
# `app.wording.defaulted_widths`.


def _defaulted_widths(names: Sequence[str]) -> Diagnostic | None:
    """One banner for however many peaks fell through to the column-geometry N."""
    if not names:
        return None
    return Diagnostic(
        code="defaulted_width",
        severity="warning",
        message=wording.defaulted_widths(names),
        peaks=tuple(names),
    )
