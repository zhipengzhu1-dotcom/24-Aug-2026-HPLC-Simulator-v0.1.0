"""What the user typed, turned into the shapes the engine accepts (SPEC §4, §5, §7).

**Sorting the rows lives here; the row shape does not.** SPEC §5 asks for two things at
once: rows missing a tR "stay visible as untracked — not fitted ... with a visible
count", and "the engine receives only confirmed, complete pairs".
:class:`~hplcsim.model.PeakRow` is the first line and :class:`~hplcsim.model.Peak` is
the second, and both are the engine's own shapes (#91). What this module owns is
:func:`split_rows`: dropping the editor's spares, filling in the automatic names, and
deciding which list each row lands in. Ticket #21 took the same split into the session
file, where :class:`~hplcsim.session.Session` keeps the two lists apart.

Alongside it are the other boundaries a typed value crosses on its way in: SPEC §4's two
entry conversions, and the rail's two programme tables in both directions. What comes out
is engine units, and :mod:`app.pipeline` takes it from there — the import runs one way,
entry to pipeline, and never back (#92).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

from hplcsim.model import (
    Gradient,
    Method,
    Peak,
    PeakRow,
    Programme,
    Run,
    Segment,
    Target,
    as_programme,
    percent_b_from_phi,
    phi_from_percent_b,
)


@dataclass(frozen=True)
class Entry:
    """The peak table sorted into what the engine may see and what it may not."""

    tracked: tuple[Peak, ...]
    untracked: tuple[PeakRow, ...]
    renamed: tuple[tuple[str, str], ...] = ()

    @property
    def untracked_count(self) -> int:
        """SPEC §5's "visible count" of rows held back from fit and prediction."""
        return len(self.untracked)


def split_rows(rows: Sequence[PeakRow]) -> Entry:
    """Drop blank rows, fill in the automatic names, and split on completeness.

    Names are numbered across every non-blank row, tracked or not, so the number a
    user reads beside an untracked row does not shift the moment they finish pairing it.
    """
    named = [
        row if row.name.strip() else replace(row, name=f"P{index}")
        for index, row in enumerate((row for row in rows if not row.is_blank), start=1)
    ]
    named, renamed = _make_names_unique(named)
    tracked = tuple(peak for row in named if (peak := row.as_peak()) is not None)
    return Entry(
        tracked=tracked,
        untracked=tuple(row for row in named if not row.is_tracked),
        renamed=renamed,
    )


def _make_names_unique(
    rows: Sequence[PeakRow],
) -> tuple[list[PeakRow], tuple[tuple[str, str], ...]]:
    """Give every row its own name, and report the ones that had to change.

    A typed name can collide with another typed name, or with an automatic P1…Pn a
    later row is about to receive. Everything downstream looks a peak up by name —
    the selected-peak list, the fit table's width lookup — so a duplicate dropped a
    peak that the rail went on counting, with nothing said. Suffix the later row
    rather than block on it (CLAUDE.md's warnings-over-blocks) and hand the change
    back, so the screen can report what it did to the name someone typed.
    """
    seen: set[str] = set()
    unique: list[PeakRow] = []
    renamed: list[tuple[str, str]] = []
    for row in rows:
        if row.name not in seen:
            seen.add(row.name)
            unique.append(row)
            continue
        suffix = 2
        while f"{row.name} ({suffix})" in seen:
            suffix += 1
        new_name = f"{row.name} ({suffix})"
        renamed.append((row.name, new_name))
        seen.add(new_name)
        unique.append(replace(row, name=new_name))
    return unique, tuple(renamed)


# --- the entry boundaries of SPEC §4 --------------------------------------------------
#
# These two conversions used to sit in the widget file, where no gate could see them.
# They are the app's side of CLAUDE.md's units rule — %B on 0–100 and a dwell that may
# have been typed as a volume become φ and minutes here, once, and the engine sees only
# its own units.


def dwell_from_volume(volume_ml: float, flow_ml_min: float) -> float:
    """t_D = V_D ÷ F — SPEC §4's dwell entry boundary, where a volume becomes a time.

    The file stores the *time* (SPEC §8), so this conversion never round-trips: it
    happens once, as the user types, and a later edit to the flow does not silently
    restate a dwell that was measured on the instrument.
    """
    if flow_ml_min <= 0.0:
        raise ValueError(f"flow must be positive to convert a dwell volume, got {flow_ml_min}")
    return volume_ml / flow_ml_min


def t0_autofill(
    field_value: float | None, last_autofill: float | None, estimate: float
) -> float | None:
    """What the t0 field should hold once "Geometry estimate" is the source — or ``None``.

    SPEC §4's fallback is *autofilled*, not captioned (#24, decided on #34): the field
    holds the computed number, so ``t0_is_measured = False`` is truthful about what is
    actually in it. Three cases:

    * no autofill yet (the source was just chosen) — fill, overwriting whatever the
      user had typed as a measured value;
    * the field still holds the last autofill — refill, so the estimate tracks an edit
      to the column dimensions or the architecture;
    * the field holds something else — the user overwrote it, and the widget layer has
      already flipped the source back to measured; leave it alone.
    """
    if last_autofill is None or field_value is None or field_value == last_autofill:
        return estimate
    return None


@dataclass(frozen=True)
class MethodEntry:
    """The method constants as the sidebar holds them: the method, and the N knob.

    v0.1's sidebar also held the gradient's %B range and hold; since v0.2 (#73) those
    are the scouting table's, in the rail, as :class:`ScoutingEntry`.
    """

    method: Method
    plate_count: float | None = None


# --- the rail's two programme tables (SPEC §7, v0.2, #73) --------------------------------
#
# Both tables are typed the way an instrument's gradient table is: a list of points,
# each a time from injection and the composition reached at it, in the user's units.
# The engine wants a `Gradient` for the scouting pair and a `Programme` for the
# candidate; the crossing from points to those is here, once, in each direction, and
# `app.tables` only turns the points into a frame the editor can show.

# A time typed into the table has at most a few decimals; a duration read off it is
# the difference of two such times and must come back as the number that was meant,
# not as the binary remainder of the subtraction (25.4 − 0.4 is not 25.0 in a float).
_TABLE_DECIMALS = 6


@dataclass(frozen=True)
class ScoutingEntry:
    """The scouting table's values: one programme at two speeds, %B still on 0–100.

    Row 1 is the start, row 2 the end of the initial hold at the same %B, row 3 the
    end of each run's ramp — so the table holds a start, an end, a hold and two
    gradient times, and this is those five numbers. The %B → φ turn happens in
    :meth:`gradient`, in a single place no matter which run is being made.
    """

    percent_b_start: float
    percent_b_end: float
    hold: float
    t_gradient1: float
    t_gradient2: float

    def gradient(self, t_gradient: float, hold: float | None = None) -> Gradient:
        """The shared gradient at one gradient time, and optionally a different hold."""
        return Gradient(
            phi0=phi_from_percent_b(self.percent_b_start),
            phif=phi_from_percent_b(self.percent_b_end),
            t_gradient=t_gradient,
            t_init=self.hold if hold is None else hold,
        )

    def runs(self) -> tuple[Run, Run]:
        """The two scouting runs, named by their gradient time as v0.1 named them."""
        return (
            Run(self.gradient(self.t_gradient1), name=f"tG{self.t_gradient1:g}"),
            Run(self.gradient(self.t_gradient2), name=f"tG{self.t_gradient2:g}"),
        )

    @classmethod
    def from_runs(cls, run1: Run, run2: Run) -> ScoutingEntry:
        """The table's values back from a restored pair (the display side of the turn)."""
        shared = run1.gradient
        return cls(
            percent_b_start=percent_b_from_phi(shared.phi0),
            percent_b_end=percent_b_from_phi(shared.phif),
            hold=shared.t_init,
            t_gradient1=run1.gradient.t_gradient,
            t_gradient2=run2.gradient.t_gradient,
        )


@dataclass(frozen=True)
class ProgrammePoint:
    """One row of the candidate table as typed: a time and a %B, either still blank."""

    t_min: float | None
    percent_b: float | None

    @property
    def is_typed(self) -> bool:
        return self.t_min is not None and self.percent_b is not None


@dataclass(frozen=True)
class ProgrammeRead:
    """What the candidate table came to: the programme, or why there is none yet.

    ``points`` are the rows as they should read — the first row's time put back to
    0, everything else as typed — so the screen can show the put-back and nothing
    more. ``notes`` name the rows that were left out and why; ``blocked`` is the one
    case with nothing to predict, worded for the rail.
    """

    programme: Programme | None
    points: tuple[ProgrammePoint, ...]
    notes: tuple[str, ...] = ()
    blocked: str | None = None


_NO_RAMP = (
    "**The candidate needs a ramp.** Row 1 is where the run starts; add a row with a "
    "later time and the %B it ramps to before anything can be predicted."
)


def programme_from_points(points: Sequence[ProgrammePoint]) -> ProgrammeRead:
    """The candidate table read as a :class:`~hplcsim.model.Programme` (SPEC §3, §7).

    Row 1 is the start of the run: its %B is φ0 and its time is 0 whatever was typed.
    Row 2 at the same %B is the end of the initial hold — the hold row, always shown,
    so a candidate with no hold carries it at t = 0. Every later row ends a segment at
    its time and its %B; a repeated %B is a hold segment, a lower one descends (SPEC
    §3, #58). A row still being typed is skipped without a word; a row that does not
    move forward in time is skipped and named — the rest of the programme stands
    (CLAUDE.md's warnings-over-blocks). With no segment at all there is nothing to
    predict, and that is the one thing said as a block.
    """
    typed = [
        (row, point.t_min, point.percent_b)
        for row, point in enumerate(points, start=1)
        if point.t_min is not None and point.percent_b is not None
    ]
    if not typed:
        return ProgrammeRead(None, tuple(points), blocked=_NO_RAMP)

    first_row, _, start = typed[0]
    shown = list(points)
    shown[first_row - 1] = replace(shown[first_row - 1], t_min=0.0)

    t_init = 0.0
    segments: list[Segment] = []
    notes: list[str] = []
    previous_t, previous_b = 0.0, start
    for position, (row, t_min, percent_b) in enumerate(typed[1:], start=2):
        duration = round(t_min - previous_t, _TABLE_DECIMALS)
        flat = percent_b == previous_b
        if duration < 0.0:
            notes.append(
                f"Row {row} is at {t_min:g} min, before the row above it at "
                f"{previous_t:g} min — a programme only moves forward, so the row is "
                "left out until its time is later."
            )
            continue
        if duration == 0.0:
            if position == 2 and flat:
                continue  # the hold row, holding for nothing
            notes.append(
                f"Row {row} repeats the time above it ({t_min:g} min) — a step needs a "
                "duration, however short (the instrument's own is 0.1 min), so the row "
                "is left out until it has one."
            )
            continue
        if position == 2 and flat:
            t_init = duration
        else:
            segments.append(Segment(duration=duration, phif=phi_from_percent_b(percent_b)))
        previous_t, previous_b = t_min, percent_b

    if not segments:
        return ProgrammeRead(None, tuple(shown), tuple(notes), blocked=_NO_RAMP)
    programme = Programme(phi0=phi_from_percent_b(start), segments=tuple(segments), t_init=t_init)
    return ProgrammeRead(programme, tuple(shown), tuple(notes))


def points_from_programme(programme: Programme) -> tuple[ProgrammePoint, ...]:
    """A programme as the rows the candidate table shows — the inverse of the read.

    The hold row is always written, at t = 0 when there is no hold, so the table a
    user sees has the same shape as the scouting table above it and the same shape
    every time. Cumulative times are summed exactly and rounded at the table's own
    precision, so what is shown reads back as the programme that was saved.
    """
    start = percent_b_from_phi(programme.phi0)
    rows = [ProgrammePoint(0.0, start), ProgrammePoint(_at_table(programme.t_init), start)]
    elapsed = [programme.t_init]
    for segment in programme.segments:
        elapsed.append(segment.duration)
        rows.append(ProgrammePoint(_at_table(math.fsum(elapsed)), percent_b_from_phi(segment.phif)))
    return tuple(rows)


def _at_table(minutes: float) -> float:
    return round(minutes, _TABLE_DECIMALS)


def programme_summary(target: Target) -> str:
    """The candidate in one line, as the rail's caption and the status bar read it."""
    programme = as_programme(target)
    count = len(programme.segments)
    return (
        f"{percent_b_from_phi(programme.phi0):g} → {percent_b_from_phi(programme.phif):g} %B · "
        f"tG {programme.t_gradient:g} min · hold {programme.t_init:g} min · "
        f"{count} segment{'' if count == 1 else 's'}"
    )
