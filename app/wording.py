"""The sentence each diagnostic says, apart from the decision to say it.

SPEC §6 places a diagnostic — badge, banner, stamp, notice — and separately words it.
`streamlit_app.py` owns the placement; this module owns the wording. `app.diagnostics`
decides *whether* a check fires and at what tier, then asks here for the sentence.

**The rule that puts a constant here.** A constant that is only ever quoted lives with
the prose that quotes it; a constant that is compared lives with the check that compares
it. So the two observed ladders below are here — SPEC §6 item 7 is explicit that no
correction is fitted and no multiplier is evaluated, and they are only ever formatted
into a sentence — while `STRONG_PHI0_DEPARTURE` and `STRONG_WINDOW_WIDTHS`, which decide
a tier, stay in `app.diagnostics`. A constant in this module that appears in an `if` is
a bug: it means a decision has leaked into the wording.

Nothing here decides anything, and nothing here imports `app.diagnostics` — the import
runs one way, diagnostics to wording, so a reworded message cannot change which
diagnostic fires. Engine constants that a sentence quotes are imported straight from the
engine rather than passed in, so the number the user reads is the number the engine
uses.
"""

from __future__ import annotations

from collections.abc import Sequence

from hplcsim.dead_time import EXTRA_COLUMN_VOLUME_TYPICAL_ML, POROSITY_PLAUSIBLE
from hplcsim.fit import BETA_STRONG, BETA_WARNING, LOW_K0_LOG10

_UL_PER_ML = 1000.0

# SPEC §6 item 7, #55: what a raised start did to the retention error on each sample, as
# a ladder of mean |ΔtR| in per cent at φ0 = 5, 15 and 25 %B. Quoted in the message as an
# observation and never evaluated for the candidate — which is why they live here and not
# beside the tier thresholds. Figures at t0 = 0.525.
_LADDER_THREE_PEAK = (0.42, 0.82, 1.67)
_LADDER_FOUR_PEAK = (0.11, 0.23, 0.26)
_LADDER_SCOUTING_START_PERCENT_B = 5.0

# The two reasons the indicative stamp can carry, one per stamping guard. Constants
# rather than a lookup on ``Diagnostic.code``, which would need this module to import
# the type it words.
INDICATIVE_REASON_STEEPNESS = "the candidate's steepness is far outside the scouting bracket"
INDICATIVE_REASON_PHI0 = "the candidate starts well above the scouting start"


def _and_list(names: Sequence[str]) -> str:
    if len(names) < 2:
        return names[0]
    return f"{', '.join(names[:-1])} and {names[-1]}"


# --- diagnostic 1: steepness extrapolation ------------------------------------------------


def steepness_head_gradient(
    *, t_gradient: float, factor: float, t_lo: float, t_hi: float, longer: str, widths: float
) -> str:
    """The v0.1 reading, kept where it still applies: one segment over the scouting range."""
    return (
        f"**Candidate tG {t_gradient:g} min is {factor:.2f}× outside the "
        f"{t_lo:g}–{t_hi:g} min scouting bracket** ({longer} than either scouting run) — "
        f"{widths:.2f} window-widths past the calibrated composition window of every peak."
    )


def steepness_head_segment(
    *, which: str, s_star: float, widths: float, where: str, lo: float, hi: float
) -> str:
    """The general reading, in window-widths past the bracket."""
    return (
        f"**The steepness of {which}, s* = {s_star:.4f}, is {widths:.2f} window-widths "
        f"{where} than the scouting bracket** (s* {lo:.4f}–{hi:.4f}), past the "
        "calibrated composition window of every peak that elutes on it."
    )


def steepness_strong(head: str) -> str:
    return (
        f"{head} That is well past the point where the fit is a prediction: "
        "outside the bracket the LSS line is being extended, and log k against "
        "%B is genuinely curved. Confirm by injection before committing to this "
        "method, or move a scouting run out to meet it."
    )


def steepness_info(head: str) -> str:
    return (
        f"{head} Modest extrapolation of this kind holds up on the validation "
        "dataset — its held-out tG = 60 min run sits 0.26 window-widths outside a "
        "15–45 min bracket and predicted to 0.34%. Treat it as a prediction to "
        "confirm, not as a reason to stop."
    )


# --- diagnostic 7: φ0 departure -----------------------------------------------------------


def phi0_head(*, start: float, sign: str, delta: float, scout: float) -> str:
    return (
        f"**The candidate starts at {start:g} %B, a {sign}{delta:g} %B departure "
        f"from the scouting start of {scout:g} %B.** The fit was never shown a run starting "
        "anywhere else."
    )


def phi0_lowered(head: str) -> str:
    return (
        f"{head} Lowering the start is a departure too, and there is no data either "
        "way: no run on file started below its scouting start. Read the prediction "
        "as one to confirm."
    )


def _phi0_observed() -> str:
    """The two ladders as an observation. No multiplier is evaluated for the candidate."""
    three = _LADDER_THREE_PEAK
    four = _LADDER_FOUR_PEAK
    return (
        "What was observed on this instrument, from scouting pairs starting at "
        f"{_LADDER_SCOUTING_START_PERCENT_B:g} %B: the first 10 %B above the scouting start "
        f"roughly doubled the retention error on both samples ({three[0]:.2f} → {three[1]:.2f} % "
        f"on the three-peak sample, {four[0]:.2f} → {four[1]:.2f} % on the four-peak); beyond "
        f"that, one sample kept doubling ({three[2]:.2f} % at +20 %B) and the other flattened "
        f"({four[2]:.2f} %). An observation, not a rule. No correction is fitted and no "
        "multiplier is evaluated for this candidate — the ladders were measured from "
        f"{_LADDER_SCOUTING_START_PERCENT_B:g} %B starts, so a pair scouted elsewhere has the "
        "guard and not the numbers."
    )


def phi0_raised_strong(head: str) -> str:
    return (
        f"{head} {_phi0_observed()} At +10 %B the retention error already stood at over one "
        "peak width (λ = 1.58) on the three-peak sample: confirm by injection before "
        "committing to this method."
    )


def phi0_raised_info(head: str) -> str:
    return (
        f"{head} {_phi0_observed()} No run sits between the scouting start and +10 %B, so the "
        "tier below +10 %B is untested: treat the prediction as one to confirm."
    )


# --- the indicative stamp ------------------------------------------------------------------


def indicative(reasons: Sequence[str]) -> str:
    return (
        "**Rs and the critical pair are indicative, not decision-grade** at this "
        f"candidate: {_and_list(reasons)}, so the LSS line was never pinned where "
        "these peaks are being predicted. The retention times stay shown as numbers "
        "and nothing here is a curvature-corrected accuracy claim — two parameters "
        "cannot see curvature. Confirm by injection before a method decision rests "
        "on this resolution."
    )


# --- diagnostic 3: scouting spacing ---------------------------------------------------------


def beta_head(*, beta: float, t_gradient1: float, t_gradient2: float) -> str:
    return (
        f"**Scouting runs are only β = {beta:.2f} apart** "
        f"(tG {t_gradient1:g} and {t_gradient2:g} min)."
    )


def _beta_tail() -> str:
    return (
        "Every peak is still fitted — this is a warning about how much the two runs "
        "can tell you, not a refusal. About 3× is the usual recommendation. A narrow β "
        "also narrows every peak's calibrated composition window, ln β / S_e — about "
        "10 %B per peak on the 5 → 95 %B scouting pairs on file, and disjoint between "
        "peaks."
    )


def beta_strong(head: str) -> str:
    return (
        f"{head} Below β = {BETA_STRONG:g} the two runs elute each peak at "
        "nearly the same %B, so S is the ratio of two small differences: 0.6 s "
        "of timing error moves it about 2% at β = 1.2 and about 9% by β = 1.05. "
        f"Re-run one of the scouting gradients further away. {_beta_tail()}"
    )


def beta_warning(head: str) -> str:
    return (
        f"{head} Under β = {BETA_WARNING:g} the fit starts amplifying ordinary "
        "timing noise into visible error in S — about 0.3% at β = 2, against 0.13% "
        f"at β = 3. {_beta_tail()}"
    )


# --- diagnostic 6: an estimated dead time ---------------------------------------------------


def estimated_t0(t0: float) -> str:
    return (
        f"**t0 = {t0:.4g} min is a geometry estimate, not a measured marker.** "
        "Two things follow, and they differ by a factor of forty. The retention times "
        "predicted for *these* gradients barely move — about 0.005% per 1% of t0 "
        "error, because the two-run fit absorbs t0 into k0. The fitted S, k0 and N "
        "do not: they carry roughly a quarter of the t0 error as a systematic shift, "
        "so read them as indicative and never transfer them to another flow rate or "
        "column. Inject an unretained marker and enter the measured time when you can."
    )


# --- SPEC §4's checks on a measured dead time ------------------------------------------------


def porosity_phrase(implied_porosity: float) -> str:
    return f"ε_total = {implied_porosity:.3f}"


def geometry_phrase(
    *, label: str, t0: float, porosity_value: float, band_lo: float, band_hi: float
) -> str:
    return (
        f"against the {label} geometry estimate of {t0:.3f} min "
        f"(ε_total {porosity_value:.2f}, band {band_lo:.3f}–{band_hi:.3f} min)"
    )


def dead_time_impossible_porosity(*, porosity: str, column_volume_ml: float) -> str:
    return (
        f"**Your measured t0 implies {porosity} — more mobile phase than an empty "
        f"tube of this column's size ({column_volume_ml:.3f} mL) would "
        "hold.** That is not a property any packed column can have. Check the flow "
        "rate, the column dimensions and their units, and whether the time entered "
        "is the marker's and in minutes."
    )


def dead_time_implausible_porosity(porosity: str) -> str:
    lo, hi = POROSITY_PLAUSIBLE
    return (
        f"**Your measured t0 implies {porosity}, outside the {lo:.2f}–{hi:.2f} a "
        "packed column can have.** Check the flow rate, the column dimensions and "
        "their units — and whether the marker is retained, or excluded from the "
        "pores."
    )


def dead_time_no_geometry(*, porosity: str, column_volume_ml: float) -> str:
    return (
        f"**Your measured t0 implies {porosity}** for a "
        f"{column_volume_ml:.3f} mL column. Declare the packing architecture "
        "above to see how much of that is extra-column volume — without it there "
        "is no geometry estimate to compare against."
    )


def dead_time_below_geometry(*, extra_column_ml: float, against: str) -> str:
    extra_column_ul = extra_column_ml * _UL_PER_ML
    return (
        f"**Your measured t0 is below the geometry estimate** — {extra_column_ul:.0f} µL of "
        f"extra-column volume {against}, which is impossible: geometry leaves the "
        "plumbing out, so the marker cannot leave before the mobile phase does. "
        "Usually the packing architecture is mis-declared (a core–shell column "
        "entered as fully porous); otherwise check the column dimensions, the flow "
        "rate, or whether the marker is excluded from the pores."
    )


def dead_time_marker_retained(*, extra_column_ml: float, porosity: str, against: str) -> str:
    extra_column_ul = extra_column_ml * _UL_PER_ML
    typical_lo, typical_hi = (v * _UL_PER_ML for v in EXTRA_COLUMN_VOLUME_TYPICAL_ML)
    return (
        f"**Your measured t0 implies {extra_column_ul:.0f} µL of extra-column volume** "
        f"({porosity}, {against}) — above the {typical_lo:.0f}–{typical_hi:.0f} µL "
        "a UHPLC system measures injector to detector. The marker is probably "
        "retained, or the time includes something that is not plumbing: the wrong "
        "point of the disturbance, or a delayed injection."
    )


def dead_time_measured(*, porosity: str, extra_column_ml: float, against: str) -> str:
    extra_column_ul = extra_column_ml * _UL_PER_ML
    typical_lo, typical_hi = (v * _UL_PER_ML for v in EXTRA_COLUMN_VOLUME_TYPICAL_ML)
    return (
        f"**Your measured t0 implies {porosity} and {extra_column_ul:.0f} µL of extra-column "
        f"volume** (typical {typical_lo:.0f}–{typical_hi:.0f} µL), {against}. Geometry "
        "leaves the plumbing out, so a marker time above the estimate is the expected "
        "order — this is your system volume, measured."
    )


def marker_absent() -> str:
    return (
        "**No t0 marker recorded.** A measured dead time without its marker has no "
        "provenance — note what was injected and which point of its trace was read "
        "(apex, or first baseline disturbance), so the number can be checked later."
    )


def marker_solvent_disturbance(marker: str | None) -> str:
    return (
        f"**t0 was read from a solvent disturbance** ({marker}), not from a compound. "
        "Solvent peaks are complex to interpret and depend on the eluent's ionic "
        "strength, and injecting them as hold-up markers is strongly discouraged. "
        "Confirm with uracil or another unretained compound when you can, and record "
        "which point of the disturbance was read."
    )


def marker_inorganic(marker: str | None) -> str:
    return (
        f"**The t0 marker is an inorganic salt** ({marker}). At the dilute "
        "concentrations injected, its ions are excluded from the pores and the time "
        "measures the interstitial volume only — about 40% low on a fully porous "
        "column. Use uracil or another permeating, unretained compound."
    )


# --- SPEC §5's entry checks -------------------------------------------------------------------


def area_share(*, name: str, change: float, share1: float, share2: float, threshold: float) -> str:
    return (
        f"**{name}: area share moves {change:.0%} between the scouting "
        f"runs** ({share1:.1%} → {share2:.1%}, past the {threshold:.0%} "
        "tracking check). A compound is the same fraction of the sample in "
        "both runs, so either these two rows are not the same peak, or one "
        "run's integration of it is not measuring the same thing. Confirm "
        "the pairing before trusting this row's fit — and treat its W½ in "
        "that run with the same suspicion."
    )


def entry_crossing(*, earlier: str, later: str) -> str:
    return (
        f"**{earlier} and {later} swap elution order between the scouting "
        "runs** — confirm they are paired correctly. Peaks with different S do "
        "cross as tG changes, so this can be real; but it is also exactly what "
        "a mis-paired row looks like, and a pair matched by elution order when "
        "it actually crossed gives two fits that are both wrong."
    )


# --- diagnostic 2: early eluters ----------------------------------------------------------------


def early_reason_never_meets(tau: float) -> str:
    return (
        "never meets the gradient — it leaves the column while the eluent is "
        f"still at the starting %B, {tau:.3g} min of dwell and hold"
    )


def early_reason_inside_t0(*, t_r_prime: float, t0: float) -> str:
    return (
        f"leaves {t_r_prime:.3g} min after the gradient reaches the column, "
        f"inside one t0 ({t0:g} min) of it"
    )


def early_reason_barely_retained(*, k_e: float, floor: float) -> str:
    return (
        f"leaves the column at k = {k_e:.2f}, below the k = {floor:g} the model needs to mean much"
    )


def early_eluter(*, name: str, reason: str) -> str:
    return (
        f"**{name} elutes early**: it {reason}. Its retention time is the "
        "least reliable in the chromatogram — the LSS model assumes k ≫ 1 and "
        "this peak is nowhere near it. Raise the starting %B, shorten the hold, "
        "or read this peak's position as indicative."
    )


# --- diagnostic 8: low k0 at the candidate's start -----------------------------------------------


def low_k0(*, name: str, log10_k0: float, percent_b: float) -> str:
    return (
        f"**{name}: log₁₀ k0 = {log10_k0:.2f} at the candidate's "
        f"{percent_b:g} %B start, below the {LOW_K0_LOG10:g} "
        "floor** the LSS closed form needs. The one measured crossing on this "
        "instrument — three-peak run 7 Unknown-1 at log₁₀ k0 ≈ 1.7 — had the "
        "dataset's worst retention error in peak-width units (λ = 1.90). Read "
        "this peak's position, and every Rs pair it is in, as indicative; a lower "
        "starting %B brings it back inside the model."
    )


# --- diagnostic 9: wash-eluted peaks -------------------------------------------------------------


def wash_where_after_end(percent_b: float) -> str:
    return f"after the programme ends, isocratically at its final {percent_b:g} %B"


def wash_where_hold(*, percent_b: float, segment: int) -> str:
    return f"in the hold at {percent_b:g} %B (segment {segment})"


def wash_eluted(*, name: str, where: str, percent_b: float) -> str:
    return (
        f"**{name} is brought off {where}**, not on a ramp: its retention time "
        f"rests on k at {percent_b:g} %B, a composition the fit never saw, "
        "extrapolated along the LSS line. The one "
        "such case measured — three-peak run 6 Unknown-3, 46.8 min against a "
        "pre-registered 47.0 — held; it was unmarked, which is why this badge "
        "exists. Read the Rs pairs this peak is in as indicative."
    )


# --- diagnostic 4: prediction crossings ----------------------------------------------------------


def prediction_crossing(*, name: str, crossed: Sequence[str]) -> str:
    return (
        f"**{name} changes places with {_and_list(crossed)}** at this candidate: "
        "its elution order here is not the order it came out in the scouting "
        "runs. That is gradient-time optimisation working, and also its main "
        "hazard — confirm which peak is which before reading anything off this "
        "trace, and expect resolution to pass through zero somewhere between."
    )


# --- diagnostic 5: widths resting on a column estimate of N --------------------------------------

# The numbers are research docs `gradient-elution-math.md` §6 and
# `plate-count-from-widths.md` §0.2, and the wording is ticket #19's — moved here verbatim
# when #20 gave the other five diagnostics a home, and moved again when the wording left
# the checks.
_DEFAULTED_WIDTH = (
    "**Widths and resolution below rest on a column estimate of N for {names}.** Those "
    "peaks carry no measured W½, so their plate count is column geometry — not this "
    "instrument's efficiency. Against the validation dataset that estimate draws peaks "
    "at 0.69–0.92× their measured width and reads resolution 18–39% high, where an N "
    "fitted from a peak's own scouting widths lands at 0.99–1.16× and −4 to −10%. Enter "
    "a W½ for a peak in either scouting run to have its N fitted. The **critical pair is "
    "identified correctly either way**; it is the absolute Rs that is optimistic."
)


def defaulted_widths(names: Sequence[str]) -> str:
    return _DEFAULTED_WIDTH.format(names=", ".join(names))
