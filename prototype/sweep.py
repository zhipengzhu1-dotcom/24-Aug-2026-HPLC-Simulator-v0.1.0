"""THROWAWAY sweep, ticket #31. Enough of #30's decisions to draw a real map.

Not the v0.2 engine — no tests, no edge handling, no home in `src/`. It exists so the
curves on the prototype are computed by `hplcsim` rather than drawn by hand: the
question this prototype answers is what the pane should look like, and a fake curve
would answer it wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scipy.optimize import brentq

from hplcsim.model import Gradient, Method, Peak, RetentionParams
from hplcsim.resolution import ResolutionTable, resolution_table
from hplcsim.width import FittedPlateCount

STEP = 0.5  # SPEC §7's candidate slider step — #30 makes it the sweep grid


@dataclass(frozen=True)
class Flip:
    """An order flip: the tG at which two named peaks exchange elution order (#30)."""

    t_gradient: float
    earlier: str
    later: str
    zone: tuple[float, float]  # co-elution zone: where this pair's Rs < target


@dataclass(frozen=True)
class Point:
    """One swept condition."""

    t_gradient: float
    table: ResolutionTable
    in_bracket: bool
    is_scouting: bool

    @property
    def critical_rs(self) -> float:
        pair = self.table.critical_pair
        return pair.rs if pair else float("inf")

    @property
    def critical_names(self) -> tuple[str, str]:
        pair = self.table.critical_pair
        return (pair.earlier.name, pair.later.name) if pair else ("", "")

    @property
    def run_time(self) -> float:
        return max(peak.retention.t_r for peak in self.table.peaks)


@dataclass
class Sweep:
    points: list[Point]
    bracket: tuple[float, float]
    bounds: tuple[float, float]
    clipped_low: bool = False
    clipped_high: bool = False
    flips: list[Flip] = field(default_factory=list)

    @property
    def grid(self) -> list[float]:
        return [point.t_gradient for point in self.points]

    def at(self, t_gradient: float) -> Point:
        return min(self.points, key=lambda point: abs(point.t_gradient - t_gradient))

    def pair_curve(self, names: frozenset[str]) -> list[tuple[float, float]]:
        """(tG, Rs) wherever this pair of names is adjacent — gaps where it is not."""
        out = []
        for point in self.points:
            for pair in point.table.pairs:
                if frozenset({pair.earlier.name, pair.later.name}) == names:
                    out.append((point.t_gradient, pair.rs))
        return out

    @property
    def pair_names(self) -> list[frozenset[str]]:
        seen: list[frozenset[str]] = []
        for point in self.points:
            for pair in point.table.pairs:
                names = frozenset({pair.earlier.name, pair.later.name})
                if names not in seen:
                    seen.append(names)
        return seen

    def goal_seek(self, target: float) -> Point | None:
        """Shortest run time whose critical Rs is at or above ``target`` (#29)."""
        meeting = [point for point in self.points if point.critical_rs >= target]
        return min(meeting, key=lambda point: point.run_time) if meeting else None

    @property
    def ceiling(self) -> Point:
        """The swept condition with the highest critical Rs (#29)."""
        return max(self.points, key=lambda point: point.critical_rs)


def bounds_for(
    tg1: float, tg2: float, *, slider: tuple[float, float]
) -> tuple[tuple[float, float], bool, bool]:
    """#30: tG1 ÷ 2 to tG2 × 2, clipped to the candidate slider."""
    low, high = min(tg1, tg2) / 2.0, max(tg1, tg2) * 2.0
    clipped_low, clipped_high = low < slider[0], high > slider[1]
    return (max(low, slider[0]), min(high, slider[1])), clipped_low, clipped_high


def run_sweep(
    fitted: list[tuple[Peak, RetentionParams, FittedPlateCount | None]],
    method: Method,
    *,
    tg1: float,
    tg2: float,
    candidate: Gradient,
    hold: float,
    plate_count: float | None,
    rs_target: float,
    slider: tuple[float, float],
) -> Sweep:
    (low, high), clipped_low, clipped_high = bounds_for(tg1, tg2, slider=slider)
    bracket = (min(tg1, tg2), max(tg1, tg2))

    grid = {round(low + index * STEP, 6) for index in range(int((high - low) / STEP) + 1)}
    grid |= {low, high}
    for extra in (tg1, tg2, candidate.t_gradient):
        if low <= extra <= high:
            grid.add(round(extra, 6))

    names = [peak.name for peak, _, _ in fitted]
    params = [param for _, param, _ in fitted]
    counts = [count for _, _, count in fitted]

    def table_at(t_gradient: float) -> ResolutionTable:
        return resolution_table(
            params,
            method,
            Gradient(candidate.phi0, candidate.phif, t_gradient, hold),
            names=names,
            plate_count=plate_count,
            plate_counts=counts,
        )

    points = [
        Point(
            t_gradient=t_gradient,
            table=table_at(t_gradient),
            in_bracket=bracket[0] <= t_gradient <= bracket[1],
            is_scouting=t_gradient in (tg1, tg2),
        )
        for t_gradient in sorted(grid)
    ]
    sweep = Sweep(points, bracket, (low, high), clipped_low, clipped_high)
    sweep.flips = _flips(sweep, table_at, names, rs_target)
    return sweep


def _flips(sweep: Sweep, table_at, names: list[str], rs_target: float) -> list[Flip]:
    """Locate each order flip exactly, then measure its co-elution zone (#30)."""
    by_name = {
        point.t_gradient: {peak.name: peak.retention.t_r for peak in point.table.peaks}
        for point in sweep.points
    }

    def gap(t_gradient: float, first: str, second: str) -> float:
        row = by_name.get(t_gradient)
        if row is None:
            row = {peak.name: peak.retention.t_r for peak in table_at(t_gradient).peaks}
        return row[first] - row[second]

    def rs_of(t_gradient: float, first: str, second: str) -> float:
        for pair in table_at(t_gradient).pairs:
            if {pair.earlier.name, pair.later.name} == {first, second}:
                return pair.rs
        return float("inf")

    flips: list[Flip] = []
    for index, first in enumerate(names):
        for second in names[index + 1 :]:
            for left, right in zip(sweep.grid, sweep.grid[1:], strict=False):
                if gap(left, first, second) * gap(right, first, second) >= 0:
                    continue
                at = brentq(lambda t, a=first, b=second: gap(t, a, b), left, right, xtol=1e-4)
                early, late = (first, second) if gap(right, first, second) > 0 else (second, first)
                flips.append(
                    Flip(at, early, late, _zone(at, first, second, rs_of, rs_target, sweep.bounds))
                )
    return sorted(flips, key=lambda flip: flip.t_gradient)


def _zone(at, first, second, rs_of, rs_target, bounds) -> tuple[float, float]:
    """The tG interval around a flip where the flipping pair sits below the target."""
    edges = []
    for direction in (-1, 1):
        edge, step = at, STEP / 4.0
        while bounds[0] <= edge + direction * step <= bounds[1]:
            edge += direction * step
            if rs_of(edge, first, second) >= rs_target:
                break
        edges.append(edge)
    return (edges[0], edges[1])
