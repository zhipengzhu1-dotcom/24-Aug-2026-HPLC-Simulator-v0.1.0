"""SPEC §5's entry checks and SPEC §6's six diagnostics, computed (ticket #20).

Streamlit-free, like the rest of the app's logic layer, and for a specific reason:
every diagnostic here is a *threshold*, and a threshold whose only expression is a
call inside a widget file can be re-tuned by accident and re-checked by nobody. The
numbers live here as named constants, `tests/test_diagnostics.py` pins them, and
``streamlit_app.py`` decides only where each one is painted.

Placement is SPEC §6's own sentence, which is why :class:`Diagnostics` has the fields
it has rather than one flat list: "per-peak badges (2, 4), fit-page notices (3),
result banners (5), output stamps (6), candidate-control inline warnings (1)". The
entry checks of SPEC §5 get a sixth field of their own.

Nothing here blocks. CLAUDE.md's warnings-over-blocks posture is the whole shape of
the module: :func:`diagnose` returns annotations, and the one impossibility the
Cockpit can produce (two scouting runs at the same tG) is still
``Cockpit.blocked``'s, not a diagnostic's.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from app.pipeline import Cockpit, CockpitInputs, Entry, run_cockpit
from hplcsim.fit import BETA_STRONG, BETA_WARNING, classify_spacing
from hplcsim.model import Gradient, Method, Peak, Run
from hplcsim.resolution import PredictedPeak

Severity = Literal["info", "warning", "strong"]

# SPEC §6 diagnostic 1: "info flag when candidate tG leaves [tG1, tG2]; strong warning
# beyond ~2× outside". "Outside" is multiplicative — the candidate's tG against the
# bracket edge it passed — which is the measure the spec's own evidence is quoted in:
# the lab dataset's tG = 60 sits 1.33× outside a 15–45 bracket and scored 0.26%.
STRONG_EXTRAPOLATION = 2.0

# SPEC §5's area-share tracking check: "default threshold ~30% relative change". The
# change is measured against the *first* run's share, which is the larger base for a
# peak whose share grows and so the more conservative reading of "relative change".
AREA_SHARE_THRESHOLD = 0.30


@dataclass(frozen=True)
class Diagnostic:
    """One thing worth saying about the condition on screen.

    ``code`` is the stable identity — the UI groups and places by it, never by
    matching the prose, so wording can be edited without moving anything on screen.
    ``peaks`` names whichever peaks the diagnostic is about, empty when it is about
    the method or the condition as a whole.
    """

    code: str
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

    @property
    def all(self) -> tuple[Diagnostic, ...]:
        """Everything, in no particular order — for tests and for counting."""
        return (
            self.candidate
            + self.fit
            + self.banners
            + self.stamps
            + self.entry
            + tuple(d for badges in self.badges.values() for d in badges)
        )


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

    # SPEC §4's one impossibility. Nothing was fitted and nothing predicted, so every
    # check below would be describing a screen that is not there — a β of 1.0 and a
    # bracket of zero width are consequences of the block, not further findings.
    if cockpit.blocked is not None:
        return Diagnostics()

    entry = (
        *_area_share_disagreements(cockpit.entry, area_share_threshold),
        *_entry_crossings(cockpit.entry.tracked),
    )
    return Diagnostics(
        candidate=_optional(_tg_extrapolation(inputs.candidate, inputs.run1, inputs.run2)),
        fit=_optional(_beta_spacing(inputs.run1, inputs.run2)),
        stamps=_optional(_estimated_t0(inputs.method)),
        banners=_optional(_defaulted_widths(cockpit.defaulted_width_names)),
        entry=entry,
        badges=_badges(cockpit, inputs.method, inputs.candidate),
    )


def _badges(
    cockpit: Cockpit, method: Method, candidate: Gradient
) -> dict[str, tuple[Diagnostic, ...]]:
    """SPEC §6's two per-peak diagnostics, one entry per predicted peak.

    Every predicted peak gets a key, clean ones with an empty tuple, so the table and
    the selected-peak panel can read ``badges[name]`` for a row without asking first
    whether that row has anything to say.
    """
    if cockpit.resolution is None:
        return {}
    early = _early_eluters(cockpit.resolution.peaks, method, candidate)
    crossing = _prediction_crossings(cockpit)
    return {
        peak.name: tuple(
            found for found in (early.get(peak.name), crossing.get(peak.name)) if found is not None
        )
        for peak in cockpit.resolution.peaks
    }


def _optional(diagnostic: Diagnostic | None) -> tuple[Diagnostic, ...]:
    return () if diagnostic is None else (diagnostic,)


# --- diagnostic 1: how far outside the scouting bracket the candidate sits --------------


def scouting_bracket(run1: Run, run2: Run) -> tuple[float, float]:
    """The gradient times the fit is calibrated between, shortest first."""
    lo, hi = sorted((run1.gradient.t_gradient, run2.gradient.t_gradient))
    return lo, hi


def extrapolation_factor(candidate: Gradient, run1: Run, run2: Run) -> float:
    """How far past the nearer bracket edge the candidate sits, as a multiple.

    1.0 anywhere inside the bracket, including on either edge. Multiplicative rather
    than additive because gradient steepness b_e goes as 1/tG: a candidate 10 min past
    a 15 min run is a different animal from one 10 min past a 120 min run, and the
    ratio is what research doc §7.3's "predict inside the bracket" is really about.
    """
    lo, hi = scouting_bracket(run1, run2)
    t_gradient = candidate.t_gradient
    if t_gradient > hi:
        return t_gradient / hi
    if t_gradient < lo:
        return lo / t_gradient
    return 1.0


def _tg_extrapolation(candidate: Gradient, run1: Run, run2: Run) -> Diagnostic | None:
    """SPEC §6 diagnostic 1, at the candidate controls."""
    factor = extrapolation_factor(candidate, run1, run2)
    if factor <= 1.0:
        return None
    lo, hi = scouting_bracket(run1, run2)
    where = "longer" if candidate.t_gradient > hi else "shorter"
    head = (
        f"**Candidate tG {candidate.t_gradient:g} min is {factor:.2f}× outside the "
        f"{lo:g}–{hi:g} min scouting bracket** ({where} than either scouting run)."
    )
    if factor > STRONG_EXTRAPOLATION:
        return Diagnostic(
            code="tg_extrapolation",
            severity="strong",
            message=(
                f"{head} That is well past the point where the fit is a prediction: "
                "outside the bracket the LSS line is being extended, and log k against "
                "%B is genuinely curved. Run a confirmation injection before committing "
                "to this method, or move a scouting run out to meet it."
            ),
        )
    return Diagnostic(
        code="tg_extrapolation",
        severity="info",
        message=(
            f"{head} Modest extrapolation of this kind holds up on the validation "
            "dataset — its held-out tG = 60 min run sits 1.33× outside a 15–45 min "
            "bracket and predicted to 0.26%. Treat it as a prediction to confirm, not "
            "as a reason to stop."
        ),
    )


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
    head = (
        f"**Scouting runs are only β = {beta:.2f} apart** "
        f"(tG {run1.gradient.t_gradient:g} and {run2.gradient.t_gradient:g} min)."
    )
    tail = (
        "Every peak is still fitted — this is a warning about how much the two runs "
        "can tell you, not a refusal. About 3× is the usual recommendation."
    )
    if tier == "strong":
        return Diagnostic(
            code="beta_spacing",
            severity="strong",
            message=(
                f"{head} Below β = {BETA_STRONG:g} the two runs elute each peak at "
                "nearly the same %B, so S is the ratio of two small differences: 0.6 s "
                "of timing error moves it about 2% at β = 1.2 and about 9% by β = 1.05. "
                f"Re-run one of the scouting gradients further away. {tail}"
            ),
        )
    return Diagnostic(
        code="beta_spacing",
        severity="warning",
        message=(
            f"{head} Under β = {BETA_WARNING:g} the fit starts amplifying ordinary "
            "timing noise into visible error in S — about 0.3% at β = 2, against 0.13% "
            f"at β = 3. {tail}"
        ),
    )


# --- diagnostic 6: predictions made on an estimated dead time ----------------------------


def _estimated_t0(method: Method) -> Diagnostic | None:
    """SPEC §6 diagnostic 6, stamped on every output rather than shown once."""
    if method.t0_is_measured:
        return None
    return Diagnostic(
        code="estimated_t0",
        severity="warning",
        message=(
            f"**t0 = {method.t0:g} min is an estimate, not a measured marker.** Every "
            "retention time, width and resolution below inherits it: t0 sets the "
            "gradient steepness b_e and the τ/t0 the band migrates through before the "
            "gradient arrives, so an error in it biases the whole chromatogram one way. "
            "Inject an unretained marker and enter the measured value when you can."
        ),
    )


# --- SPEC §5's entry checks --------------------------------------------------------------


@dataclass(frozen=True)
class _AreaRow:
    """One row's areas, as the tracking check needs them: a name and two numbers."""

    name: str
    area_run1: float
    area_run2: float


@dataclass(frozen=True)
class _EnteredRow:
    """One typed row, whichever half of :class:`~app.pipeline.Entry` it came from.

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
    """Every non-blank row the user typed, tracked or not."""
    return [
        _EnteredRow(row.name, row.t_r_run1, row.t_r_run2, row.area_run1, row.area_run2)
        for row in entry.tracked
    ] + [
        _EnteredRow(row.name, row.t_r_run1, row.t_r_run2, row.area_run1, row.area_run2)
        for row in entry.untracked
    ]


def _area_rows(entry: Entry) -> list[_AreaRow]:
    """Every non-blank row carrying an area in *both* runs, tracked or not.

    Untracked rows count: they are part of the sample, so leaving them out of the
    normalisation would move everybody else's share. What they cannot do is be
    compared against a prediction, which is a different check.
    """
    return [
        _AreaRow(name=row.name, area_run1=row.area_run1, area_run2=row.area_run2)
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
    total1 = sum(row.area_run1 for row in rows)
    total2 = sum(row.area_run2 for row in rows)
    if len(rows) < 2 or total1 <= 0.0 or total2 <= 0.0:
        return []

    relaxed = _co_eluting(entry)
    found = []
    for row in rows:
        if row.name in relaxed:
            continue
        share1 = row.area_run1 / total1
        share2 = row.area_run2 / total2
        if share1 <= 0.0:
            continue
        change = abs(share2 - share1) / share1
        if change <= threshold:
            continue
        found.append(
            Diagnostic(
                code="area_share",
                severity="warning",
                message=(
                    f"**{row.name}: area share moves {change:.0%} between the scouting "
                    f"runs** ({share1:.1%} → {share2:.1%}, past the {threshold:.0%} "
                    "tracking check). A compound is the same fraction of the sample in "
                    "both runs, so either these two rows are not the same peak, or one "
                    "run's integration of it is not measuring the same thing. Confirm "
                    "the pairing before trusting this row's fit — and treat its W½ in "
                    "that run with the same suspicion."
                ),
                peaks=(row.name,),
            )
        )
    return found


# --- diagnostic 2: peaks that leave before the gradient has developed --------------------


def _early_eluters(
    peaks: Sequence[PredictedPeak], method: Method, candidate: Gradient
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
        if not in_the_hold and t_r_prime >= method.t0:
            continue
        reason = (
            "never meets the gradient — it leaves the column while the eluent is still "
            f"at the starting %B, {tau:.3g} min of dwell and hold"
            if in_the_hold
            else f"leaves {t_r_prime:.3g} min after the gradient reaches the column, "
            f"inside one t0 ({method.t0:g} min) of it"
        )
        found[peak.name] = Diagnostic(
            code="early_eluter",
            severity="warning",
            message=(
                f"**{peak.name} elutes early**: it {reason}. Its retention time is the "
                "least reliable in the chromatogram — the LSS model assumes k ≫ 1 and "
                "this peak is nowhere near it. Raise the starting %B, shorten the hold, "
                "or read this peak's position as indicative."
            ),
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
            message=(
                f"**{name} changes places with {_and_list(crossed)}** at this candidate: "
                "its elution order here is not the order it came out in the scouting "
                "runs. That is gradient-time optimisation working, and also its main "
                "hazard — confirm which peak is which before reading anything off this "
                "trace, and expect resolution to pass through zero somewhere between."
            ),
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


def _and_list(names: Sequence[str]) -> str:
    if len(names) < 2:
        return names[0]
    return f"{', '.join(names[:-1])} and {names[-1]}"


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
            message=(
                f"**{earlier} and {later} swap elution order between the scouting "
                "runs** — confirm they are paired correctly. Peaks with different S do "
                "cross as tG changes, so this can be real; but it is also exactly what "
                "a mis-paired row looks like, and a pair matched by elution order when "
                "it actually crossed gives two fits that are both wrong."
            ),
            peaks=(earlier, later),
        )
        for earlier, later in _swapped_pairs(_order_by(tracked, 0), _order_by(tracked, 1))
    ]


# --- diagnostic 5: widths and Rs resting on a column estimate of N ------------------------

# SPEC §6 diagnostic 5, scoped to peaks whose N is the column estimate. The numbers are
# research docs `gradient-elution-math.md` §6 and `plate-count-from-widths.md` §0.2, and
# the wording is ticket #19's — moved here verbatim when #20 gave the other five
# diagnostics a home, so that all six are computed in one place and placed in another.
_DEFAULTED_WIDTH = (
    "**Widths and resolution below rest on a column estimate of N for {names}.** Those "
    "peaks carry no measured W½, so their plate count is column geometry — not this "
    "instrument's efficiency. Against the validation dataset that estimate draws peaks "
    "at 0.69–0.92× their measured width and reads resolution 18–39% high, where an N "
    "fitted from a peak's own scouting widths lands at 0.99–1.16× and −4 to −10%. Enter "
    "a W½ for a peak in either scouting run to have its N fitted. The **critical pair is "
    "identified correctly either way**; it is the absolute Rs that is optimistic."
)


def _defaulted_widths(names: Sequence[str]) -> Diagnostic | None:
    """One banner for however many peaks fell through to the column-geometry N."""
    if not names:
        return None
    return Diagnostic(
        code="defaulted_width",
        severity="warning",
        message=_DEFAULTED_WIDTH.format(names=", ".join(names)),
        peaks=tuple(names),
    )
