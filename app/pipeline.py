"""Entry to fit to prediction, with no Streamlit in sight (SPEC §7, ticket #19).

Everything the Cockpit shows is computed here, from the values the widgets hold to
the tables and the chromatogram's inputs. Keeping the whole path in plain functions
is what makes the ticket's third acceptance criterion — the app's run-3 prediction
against the engine fixtures — an assertion in `tests/test_app.py` instead of a
screenshot someone has to repeat.

**Untracked rows live here, not in the engine.** SPEC §5 asks for two things at once:
rows missing a tR "stay visible as untracked — not fitted ... with a visible count",
and "the engine receives only confirmed, complete pairs". :class:`PeakRow` is the
first line and :class:`~hplcsim.model.Peak` stays the second: a row becomes a ``Peak``
only when both retention times are there. That was #19's call to make (the ticket
comment carried it forward from #18); ticket #21 extends the session schema to store
the incomplete rows.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from statistics import fmean

from hplcsim.fit import FitResult, fit_peak
from hplcsim.model import Gradient, Method, Peak, Run
from hplcsim.resolution import PredictedPeak, ResolutionTable, resolution_table


@dataclass(frozen=True)
class PeakRow:
    """One row of the peak table exactly as typed — every measurement optional.

    The engine's :class:`~hplcsim.model.Peak` requires both retention times; a row
    being filled in does not have them yet. ``name`` is blank until :func:`prepare`
    fills in SPEC §5's automatic P1…Pn.
    """

    name: str = ""
    t_r_run1: float | None = None
    t_r_run2: float | None = None
    area_run1: float | None = None
    area_run2: float | None = None
    w_half_run1: float | None = None
    w_half_run2: float | None = None

    @property
    def measurements(self) -> tuple[float | None, ...]:
        return (
            self.t_r_run1,
            self.t_r_run2,
            self.area_run1,
            self.area_run2,
            self.w_half_run1,
            self.w_half_run2,
        )

    @property
    def is_blank(self) -> bool:
        """A row with nothing in it at all — the editor's spare, not a peak."""
        return not self.name.strip() and all(value is None for value in self.measurements)

    @property
    def is_tracked(self) -> bool:
        """Both scouting runs pinned: the pairing SPEC §5 says the engine may have."""
        return self.t_r_run1 is not None and self.t_r_run2 is not None

    def as_peak(self) -> Peak | None:
        """The engine's ``Peak``, or ``None`` while the row is still half-paired."""
        if self.t_r_run1 is None or self.t_r_run2 is None:
            return None
        return Peak(
            t_r_run1=self.t_r_run1,
            t_r_run2=self.t_r_run2,
            name=self.name,
            area_run1=self.area_run1,
            area_run2=self.area_run2,
            w_half_run1=self.w_half_run1,
            w_half_run2=self.w_half_run2,
        )


@dataclass(frozen=True)
class Entry:
    """The peak table sorted into what the engine may see and what it may not."""

    tracked: tuple[Peak, ...]
    untracked: tuple[PeakRow, ...]

    @property
    def untracked_count(self) -> int:
        """SPEC §5's "visible count" of rows held back from fit and prediction."""
        return len(self.untracked)


def prepare(rows: Sequence[PeakRow]) -> Entry:
    """Drop blank rows, fill in the automatic names, and split on completeness.

    Names are numbered across every non-blank row, tracked or not, so the number a
    user reads beside an untracked row does not shift the moment they finish pairing it.
    """
    named = [
        row if row.name.strip() else replace(row, name=f"P{index}")
        for index, row in enumerate((row for row in rows if not row.is_blank), start=1)
    ]
    tracked = tuple(peak for row in named if (peak := row.as_peak()) is not None)
    return Entry(tracked=tracked, untracked=tuple(row for row in named if not row.is_tracked))


@dataclass(frozen=True)
class PeakOutcome:
    """One tracked peak after the fit was attempted: the answer, or why there is none.

    ``fit`` and ``error`` are exactly one apiece. A peak the engine refuses (it elutes
    before the gradient arrives, or the two runs admit no LSS solution) is a warning
    beside its row, not an exception that empties the screen — CLAUDE.md's
    warnings-over-blocks posture, applied to a table someone is still typing into.
    """

    peak: Peak
    fit: FitResult | None
    error: str | None


@dataclass(frozen=True)
class CockpitInputs:
    """Everything the widgets hold — deliberately the shape of a saved session.

    Field for field this is :class:`hplcsim.session.Session` with ``PeakRow`` in place
    of ``Peak``, so ticket #21 wires save/load by mapping the peak list and nothing else.
    """

    method: Method
    run1: Run
    run2: Run
    candidate: Gradient
    rows: tuple[PeakRow, ...] = ()
    plate_count: float | None = None


@dataclass(frozen=True)
class Cockpit:
    """One rendering of the whole screen: entry, fits, and the candidate prediction."""

    entry: Entry
    outcomes: tuple[PeakOutcome, ...]
    resolution: ResolutionTable | None
    shares: dict[str, float] | None
    blocked: str | None

    @property
    def fitted(self) -> tuple[tuple[Peak, FitResult], ...]:
        """The peaks that reached a fit, paired with it — input order, not elution order."""
        return tuple(
            (outcome.peak, outcome.fit) for outcome in self.outcomes if outcome.fit is not None
        )

    @property
    def predicted_by_name(self) -> dict[str, PredictedPeak]:
        """Each fitted peak as predicted at the candidate gradient, keyed by name."""
        if self.resolution is None:
            return {}
        return {peak.name: peak for peak in self.resolution.peaks}

    @property
    def defaulted_width_names(self) -> tuple[str, ...]:
        """Peaks whose width rests on the column-geometry estimate of N.

        The scope of SPEC §6 diagnostic 5: the banner is about a *defaulted* plate
        count, not about widths in general. Reads the stamp the engine puts on every
        width rather than re-deriving which peaks had a W½ to fit from.
        """
        return tuple(
            peak.name
            for peak in (self.resolution.peaks if self.resolution else ())
            if peak.width.plate_count_source == "default"
        )


def run_cockpit(inputs: CockpitInputs) -> Cockpit:
    """Fit every tracked peak, then predict the candidate gradient from the survivors."""
    entry = prepare(inputs.rows)
    blocked = _blocking_reason(inputs.run1, inputs.run2)
    if blocked is not None:
        return Cockpit(entry, (), None, None, blocked)

    outcomes = tuple(_fit_one(peak, inputs) for peak in entry.tracked)
    fitted = tuple((outcome.peak, outcome.fit) for outcome in outcomes if outcome.fit is not None)
    if not fitted:
        return Cockpit(entry, outcomes, None, None, None)

    table = resolution_table(
        [fit.params for _, fit in fitted],
        inputs.method,
        inputs.candidate,
        names=[peak.name for peak, _ in fitted],
        plate_count=inputs.plate_count,
        plate_counts=[fit.plate_count for _, fit in fitted],
    )
    return Cockpit(entry, outcomes, table, area_shares([peak for peak, _ in fitted]), None)


def _fit_one(peak: Peak, inputs: CockpitInputs) -> PeakOutcome:
    """One peak's fit, with the engine's refusal kept as text beside its row."""
    try:
        fit = fit_peak(peak, inputs.method, inputs.run1, inputs.run2)
    except ValueError as error:
        return PeakOutcome(peak=peak, fit=None, error=str(error))
    return PeakOutcome(peak=peak, fit=fit, error=None)


def _blocking_reason(run1: Run, run2: Run) -> str | None:
    """The one impossibility the Cockpit can produce: two runs at the same tG.

    SPEC §4 makes this a hard failure and ``fit`` raises on it, but raising once per
    peak would report a method-level fault as a table full of row-level ones. The
    remaining half of the engine's check — that the runs share φ0, φf and the hold —
    cannot be violated here, because the Cockpit gives those a single set of inputs.
    """
    if run1.gradient.t_gradient != run2.gradient.t_gradient:
        return None
    return (
        f"Both scouting runs are at tG = {run1.gradient.t_gradient:g} min. Two runs at the "
        "same gradient time are one measurement, not two — give run 2 a different tG "
        "(around 3× run 1) before anything can be fitted."
    )


def area_shares(peaks: Sequence[Peak]) -> dict[str, float] | None:
    """Each peak's share of the sample, or ``None`` when the areas do not cover it.

    Shares are normalised *within* each run before the runs are combined, so a run
    that simply ran hotter cannot outvote the other; a peak's share is then the mean
    of however many run shares it actually has. If any peak carries no area at all
    there is no share to average for it, and the whole set is refused rather than
    given an invented one — the caller draws equal heights and says so (SPEC §7:
    heights scaled by area shares *where areas exist*).
    """
    per_run = [
        [None if area is None else area / total for area in areas]
        for areas in ([peak.area_run1 for peak in peaks], [peak.area_run2 for peak in peaks])
        if (total := sum(area for area in areas if area is not None)) > 0.0
    ]
    if not per_run:
        return None

    means = []
    for index, _ in enumerate(peaks):
        present = [share for run in per_run if (share := run[index]) is not None]
        if not present:
            return None
        means.append(fmean(present))

    total = sum(means)
    return {peak.name: mean / total for peak, mean in zip(peaks, means, strict=True)}
