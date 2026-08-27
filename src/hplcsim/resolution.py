"""Adjacent-pair resolution and the critical pair (SPEC §3; research doc §6).

Resolution is computed from the widths the engine already predicts exactly, not
from the ¼(α−1)√N·k/(1+k) master form: that form assumes equal widths and is an
approximation, and the gradient variant of it could not be verified against a
primary source (research doc §10 item 8).

Elution order is a property of the *condition*, not of the input list — peaks are
re-sorted by predicted tR before pairing, because order reverses between gradients
(research doc §7.4).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from hplcsim.model import Gradient, Method, RetentionParams
from hplcsim.retention import RetentionResult, predict_retention
from hplcsim.width import PeakWidth, peak_width


@dataclass(frozen=True)
class PredictedPeak:
    """One peak as predicted at one condition: where it elutes and how wide it is."""

    name: str
    retention: RetentionResult
    width: PeakWidth


@dataclass(frozen=True)
class AdjacentPair:
    """Two peaks neighbouring in elution order, and the resolution between them."""

    earlier: PredictedPeak
    later: PredictedPeak
    rs: float


@dataclass(frozen=True)
class ResolutionTable:
    """Every adjacent pair at one condition, with the worst of them called out."""

    peaks: tuple[PredictedPeak, ...]
    pairs: tuple[AdjacentPair, ...]

    @property
    def critical_pair(self) -> AdjacentPair | None:
        """The worst-resolved adjacent pair — ``None`` when there is nothing to pair."""
        return min(self.pairs, key=lambda pair: pair.rs) if self.pairs else None


def resolution_table(
    params: Sequence[RetentionParams],
    method: Method,
    gradient: Gradient,
    *,
    names: Sequence[str] | None = None,
    plate_count: float | None = None,
) -> ResolutionTable:
    """Predict every peak under ``gradient`` and resolve the adjacent pairs.

    ``names`` defaults to P1…Pn (SPEC §5); when supplied it must carry one name per
    peak, and each name travels with its peak through the re-sort.
    """
    if names is None:
        names = [f"P{index}" for index in range(1, len(params) + 1)]
    elif len(names) != len(params):
        raise ValueError(f"one name per peak is required; got {len(names)} for {len(params)} peaks")

    predicted = [
        PredictedPeak(
            name=name,
            retention=predict_retention(peak_params, method, gradient),
            width=peak_width(peak_params, method, gradient, plate_count=plate_count),
        )
        for name, peak_params in zip(names, params, strict=True)
    ]
    predicted.sort(key=lambda peak: peak.retention.t_r)

    pairs = tuple(
        AdjacentPair(earlier=earlier, later=later, rs=_resolution(earlier, later))
        for earlier, later in zip(predicted, predicted[1:], strict=False)
    )
    return ResolutionTable(peaks=tuple(predicted), pairs=pairs)


def _resolution(earlier: PredictedPeak, later: PredictedPeak) -> float:
    """Rs = (tR₂ − tR₁)/(2(σ₁ + σ₂)) — research doc §6."""
    separation = later.retention.t_r - earlier.retention.t_r
    return separation / (2.0 * (earlier.width.sigma + later.width.sigma))
