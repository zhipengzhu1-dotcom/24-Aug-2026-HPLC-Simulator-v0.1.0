"""Fit to prediction, with no Streamlit in sight (SPEC §7, ticket #19).

Everything the Cockpit shows is computed here, from the values the widgets hold to
the tables and the chromatogram's inputs. Keeping the whole path in plain functions
is what makes the ticket's third acceptance criterion — the app's run-3 prediction
against the engine fixtures — an assertion in `tests/test_app.py` instead of a
screenshot someone has to repeat.

What the user typed becomes engine units in :mod:`app.entry`, one module upstream; this
one starts from :class:`~app.entry.Entry` and carries it to the fit and the prediction
(#92).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import fmean

from app.entry import Entry, split_rows
from hplcsim.fit import FitResult, fit_peak
from hplcsim.model import (
    Gradient,
    Method,
    Peak,
    PeakRow,
    Programme,
    Run,
    Target,
)
from hplcsim.resolution import PredictedPeak, ResolutionTable, resolution_table


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
    """Everything the widgets hold: the method, the two scouting runs, the candidate.

    Close to :class:`hplcsim.session.Session` but not identical: the runs are two
    fields here against Session's ``runs`` pair, ``PeakRow`` stands in for ``Peak`` so
    half-paired rows have somewhere to live, ``plate_count`` is a float here and an int
    there, and Session's ``session_name`` has no counterpart — the name is a property of
    the file, not of the condition being predicted. :mod:`app.session_io` is where the
    two are translated into each other, and every one of those differences lives there.
    """

    method: Method
    run1: Run
    run2: Run
    candidate: Gradient
    rows: tuple[PeakRow, ...] = ()
    plate_count: float | None = None
    # v0.2 (#73): the candidate as the rail's programme table holds it — its own start,
    # hold and any number of segments (SPEC §3, §7). ``candidate`` is then that
    # programme's *one-segment reading* (:func:`single_segment_reading`) and nothing
    # else, which :meth:`__post_init__` enforces: the v0.1 diagnostics still read a
    # gradient, until #72 teaches them the programme, and two fields that could disagree
    # would be two candidates. The engine predicts :attr:`target`. ``None`` is the v0.1
    # shape — a gradient with no programme behind it — kept for the callers built on it.
    programme: Programme | None = None

    def __post_init__(self) -> None:
        if self.programme is not None and self.candidate != single_segment_reading(self.programme):
            raise ValueError(
                "candidate must be the programme's one-segment reading: "
                f"{self.candidate} is not {single_segment_reading(self.programme)}"
            )

    @classmethod
    def with_programme(
        cls,
        *,
        method: Method,
        run1: Run,
        run2: Run,
        programme: Programme,
        rows: tuple[PeakRow, ...] = (),
        plate_count: float | None = None,
    ) -> CockpitInputs:
        """The inputs for a programme, with the one-segment reading derived, never typed."""
        return cls(
            method=method,
            run1=run1,
            run2=run2,
            candidate=single_segment_reading(programme),
            rows=rows,
            plate_count=plate_count,
            programme=programme,
        )

    @property
    def target(self) -> Target:
        """What the engine predicts: the programme when there is one, else the gradient."""
        return self.candidate if self.programme is None else self.programme


def single_segment_reading(programme: Programme) -> Gradient:
    """A programme as the one gradient the v0.1 surfaces can read (until #72).

    Exact for one segment — :meth:`~hplcsim.model.Programme.as_gradient`, the same
    correspondence the engine's one-segment path takes. For two or more it is the
    programme's own start and end over its total ramp time: the honest one-number
    summary for a tG bracket, and never the scouting runs' range in disguise.
    """
    gradient = programme.as_gradient()
    if gradient is not None:
        return gradient
    return Gradient(
        phi0=programme.phi0,
        phif=programme.phif,
        t_gradient=programme.t_gradient,
        t_init=programme.t_init,
    )


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
        return _fitted_pairs(self.outcomes)

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


def run_cockpit(inputs: CockpitInputs, *, blocked: str | None = None) -> Cockpit:
    """Fit every tracked peak, then predict the candidate from the survivors.

    ``blocked`` is a reason the caller already knows — the rail's candidate table with no
    ramp on it yet (#73) — and it stops the prediction the same way the engine's own
    impossibility does: painted in the rail, the peak table still read.
    """
    entry = split_rows(inputs.rows)
    blocked = _blocking_reason(inputs.run1, inputs.run2) or blocked
    if blocked is not None:
        return Cockpit(entry, (), None, None, blocked)

    outcomes = tuple(_fit_one(peak, inputs) for peak in entry.tracked)
    fitted = _fitted_pairs(outcomes)
    if not fitted:
        return Cockpit(entry, outcomes, None, None, None)

    table = resolution_table(
        [fit.params for _, fit in fitted],
        inputs.method,
        inputs.target,
        names=[peak.name for peak, _ in fitted],
        plate_count=inputs.plate_count,
        plate_counts=[fit.plate_count for _, fit in fitted],
    )
    return Cockpit(entry, outcomes, table, area_shares([peak for peak, _ in fitted]), None)


def _fitted_pairs(outcomes: Sequence[PeakOutcome]) -> tuple[tuple[Peak, FitResult], ...]:
    """The outcomes that carry a fit, narrowed. ``Cockpit.fitted`` is this, read back."""
    return tuple((outcome.peak, outcome.fit) for outcome in outcomes if outcome.fit is not None)


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
