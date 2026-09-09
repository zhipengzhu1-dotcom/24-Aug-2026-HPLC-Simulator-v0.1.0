"""Measuring peaks off a detector trace: retention time, area, width, resolution.

Pure functions over an :class:`~scripts.arw.Trace`; no file is read or written here.

Conventions, all settled with the driver on 2026-09-09 and none of them free choices:

* **Baseline and splitting** follow Empower's default so the cross-check against the
  instrument's own report is like-for-like: one straight baseline per *cluster* of
  peaks that never return to it, drawn between the cluster's outer limits, and a
  perpendicular drop at the valleys inside it.
* **The asserted resolution** is Rs = dt / (2(sigma1 + sigma2)) with sigma from the
  measured W-half — the same definition `hplcsim.resolution` predicts in, so a measured
  and a predicted Rs differ by the model and never by the definition.
* **USP resolution and USP tailing are recorded, never asserted.** They are built the
  way the pharmacopoeia builds them — tangents through the inflection points, extended
  to the baseline — so they are a real second measurement rather than a rescaling of
  the first. On a Gaussian peak the tangent width is 1.699 x W-half and the two
  resolutions agree; the gap between them on these peaks *is* the peak asymmetry, which
  the xlsx puts between 0.62 and 1.32.

Nothing here knows what a gradient is. A peak that elutes in the void is measured
exactly like any other and carries its k' so the caller can decline to use it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy.signal import find_peaks, peak_prominences, savgol_filter

from scripts.arw import Trace

# W-half = sqrt(8 ln 2) x sigma. The research doc (gradient-elution-math.md) section 6 is
# explicit that the exact constant is used and not the 1.178 or 2.355 roundings the
# literature quotes, which cost ~0.04% on every Rs. Same citation as hplcsim.resolution.
_W_HALF_PER_SIGMA = float(np.sqrt(8.0 * np.log(2.0)))

_TAILING_HEIGHT_FRACTION = 0.05


@dataclass(frozen=True)
class Settings:
    """Every threshold the integration depends on, so a run can be reproduced exactly."""

    # Detection. Both thresholds are in units of the trace's own noise, so one setting
    # serves traces that differ by three orders of magnitude in absorbance.
    min_prominence_noise: float = 12.0
    min_height_noise: float = 15.0
    # Smoothing is used for detection and for slopes only; every reported value is
    # measured on the unsmoothed trace.
    smooth_points: int = 11
    smooth_polyorder: int = 2
    # A peak's limits are walked out from its apex until the slope has fallen to this
    # fraction of that peak's own steepest slope -- scale-free, so a tall peak and a
    # small one are cut at the same point on their shoulders.
    limit_slope_fraction: float = 0.01
    # Peaks whose limits touch are one cluster and share one baseline.
    cluster_gap_points: int = 2
    # Ignore everything before this time (min): the injection disturbance is not a peak.
    ignore_before_min: float = 0.0
    # How far a flank may rise above its lowest point before that counts as a valley
    # rather than noise, in units of the trace's own noise.
    valley_rise_noise: float = 3.0


@dataclass(frozen=True)
class Peak:
    """One measured peak. Times in minutes, area and height in the trace's own units."""

    apex_index: int
    t_r: float
    area: float
    height: float
    w_half: float
    start_time: float
    end_time: float
    cluster: int
    w_tangent: float | None
    tailing: float | None
    # Which flank the value had to be mirrored from, when a neighbour cut one off.
    w_half_basis: Literal["both flanks", "leading flank", "trailing flank"]
    fused_left: bool
    fused_right: bool

    @property
    def sigma(self) -> float:
        return self.w_half / _W_HALF_PER_SIGMA


@dataclass(frozen=True)
class Pair:
    """Two peaks adjacent in elution order, with both resolutions."""

    earlier: Peak
    later: Peak
    rs: float
    usp_resolution: float | None


@dataclass(frozen=True)
class Measurement:
    """Everything one trace yielded, with the settings that yielded it."""

    peaks: tuple[Peak, ...]
    pairs: tuple[Pair, ...]
    noise: float
    settings: Settings = field(default_factory=Settings)


def estimate_noise(signal: NDArray[np.float64], window_points: int = 1200) -> float:
    """Noise as the quietest window's residual about its own straight line.

    A gradient trace drifts and holds large peaks, so a global standard deviation is
    the drift, not the noise. The quietest minute is the honest estimate.
    """
    if signal.size < window_points * 2:
        window_points = max(16, signal.size // 4)
    steps = np.arange(window_points, dtype=np.float64)
    best = np.inf
    for start in range(0, signal.size - window_points, window_points // 2):
        block = signal[start : start + window_points]
        slope, intercept = np.polyfit(steps, block, 1)
        residual = float(np.std(block - (slope * steps + intercept)))
        best = min(best, residual)
    # A perfectly flat synthetic trace has no noise; keep the thresholds finite.
    return max(best, float(np.finfo(np.float64).eps))


def _limits(
    smoothed: NDArray[np.float64],
    slope: NDArray[np.float64],
    apex: int,
    left_bound: int,
    right_bound: int,
    fraction: float,
    rise_tolerance: float,
) -> tuple[int, int]:
    """Walk out from an apex to where its own flanks have flattened.

    A flank ends where the trace turns back up, but "turns up" cannot be read from one
    point against the next. On a broad, low peak the fall between adjacent samples is
    smaller than the noise on them -- a 0.1 min-wide peak at 20 Hz descends about 1 nAU
    per point through 6 nAU of noise -- so a point-to-point test calls the first noisy
    sample a valley and cuts the peak off at its own apex. The turn is measured against
    the lowest value the walk has reached instead, and must clear ``rise_tolerance``.
    """
    span = slice(left_bound, right_bound + 1)
    threshold = fraction * float(np.max(np.abs(slope[span]))) if right_bound > left_bound else 0.0

    # The slope is zero *at* the apex, so a walk that stops the moment the trace is flat
    # never leaves it. Each flank is followed down until it has been steep and then
    # flattened again -- or until the trace turns back up, which is a neighbouring peak
    # rather than baseline.
    left, steep, floor = apex, False, smoothed[apex]
    while left > left_bound:
        if smoothed[left - 1] > floor + rise_tolerance:
            break
        left -= 1
        floor = min(floor, smoothed[left])
        if abs(slope[left]) > threshold:
            steep = True
        elif steep:
            break

    right, steep, floor = apex, False, smoothed[apex]
    while right < right_bound:
        if smoothed[right + 1] > floor + rise_tolerance:
            break
        right += 1
        floor = min(floor, smoothed[right])
        if abs(slope[right]) > threshold:
            steep = True
        elif steep:
            break
    return left, right


def _baseline(
    times: NDArray[np.float64],
    signal: NDArray[np.float64],
    start: int,
    end: int,
) -> NDArray[np.float64]:
    """A straight line between the cluster's two outer limits."""
    t0, t1 = times[start], times[end]
    y0, y1 = signal[start], signal[end]
    if t1 == t0:
        return np.full(end - start + 1, y0, dtype=np.float64)
    slope = (y1 - y0) / (t1 - t0)
    line: NDArray[np.float64] = y0 + slope * (times[start : end + 1] - t0)
    return line


def _cross(
    times: NDArray[np.float64],
    values: NDArray[np.float64],
    level: float,
    apex: int,
    side: int,
    limit: int,
) -> float | None:
    """Time at which ``values`` crosses ``level`` walking ``side`` from ``apex``.

    The first crossing is taken, and a point that ticks back up on the way down is
    stepped over rather than treated as the end of the flank: on a real trace one noisy
    sample rises, and aborting there would mirror a width that was measurable. When the
    flank reaches ``limit`` without ever falling to ``level`` there is no crossing --
    a neighbour is holding the valley up -- and ``None`` is the answer. ``limit`` is the
    peak's own drop boundary, never the end of the trace: a fused peak's width is not
    allowed to be measured across the neighbour that fused with it.
    """
    index = apex
    while index != limit:
        nxt = index + side
        if values[nxt] <= level:
            span = values[index] - values[nxt]
            if span <= 0.0:
                return float(times[nxt])
            weight = (values[index] - level) / span
            return float(times[index] + weight * (times[nxt] - times[index]))
        index = nxt
    return None


def _width_at(
    times: NDArray[np.float64],
    corrected: NDArray[np.float64],
    apex: int,
    fraction: float,
    low: int,
    high: int,
) -> tuple[float | None, float | None]:
    """Times where the peak crosses ``fraction`` of its height, leading then trailing."""
    level = corrected[apex] * fraction
    return (
        _cross(times, corrected, level, apex, -1, low),
        _cross(times, corrected, level, apex, +1, high),
    )


def _tangent_width(
    times: NDArray[np.float64],
    corrected: NDArray[np.float64],
    slope: NDArray[np.float64],
    apex: int,
    start: int,
    end: int,
) -> float | None:
    """The USP tangent width: inflection tangents extended to the baseline."""
    if apex <= start or apex >= end:
        return None
    rise = int(np.argmax(slope[start:apex])) + start
    fall = int(np.argmin(slope[apex : end + 1])) + apex
    if slope[rise] <= 0.0 or slope[fall] >= 0.0:
        return None
    lead = times[rise] - corrected[rise] / slope[rise]
    trail = times[fall] - corrected[fall] / slope[fall]
    width = float(trail - lead)
    return width if width > 0.0 else None


def measure(trace: Trace, settings: Settings | None = None) -> Measurement:
    """Detect, integrate and pair every peak on one trace."""
    settings = settings or Settings()
    times, signal = trace.times, trace.signal
    noise = estimate_noise(signal)

    window = min(settings.smooth_points, (signal.size // 2) * 2 - 1)
    smoothed = savgol_filter(signal, window, settings.smooth_polyorder)
    step = float(np.median(np.diff(times)))
    slope = savgol_filter(signal, window, settings.smooth_polyorder, deriv=1, delta=step)

    apices, _ = find_peaks(smoothed, prominence=settings.min_prominence_noise * noise)
    apices = apices[times[apices] >= settings.ignore_before_min]
    if apices.size == 0:
        return Measurement(peaks=(), pairs=(), noise=noise, settings=settings)

    left_bases, right_bases = peak_prominences(smoothed, apices)[1:]
    rise_tolerance = settings.valley_rise_noise * noise
    bounds = [
        _limits(
            smoothed,
            slope,
            int(apex),
            int(low),
            int(high),
            settings.limit_slope_fraction,
            rise_tolerance,
        )
        for apex, low, high in zip(apices, left_bases, right_bases, strict=True)
    ]

    # Peaks whose limits touch share one baseline; the drop at the valley between them
    # is where one peak's area ends and the next begins.
    clusters: list[list[int]] = [[0]]
    for position in range(1, len(bounds)):
        if bounds[position][0] - bounds[position - 1][1] <= settings.cluster_gap_points:
            clusters[-1].append(position)
        else:
            clusters.append([position])

    peaks: list[Peak] = []
    for cluster_id, members in enumerate(clusters):
        start = bounds[members[0]][0]
        end = bounds[members[-1]][1]
        baseline = _baseline(times, signal, start, end)
        corrected = signal[start : end + 1] - baseline
        local_times = times[start : end + 1]
        local_slope = slope[start : end + 1]

        # Perpendicular drop: interior boundaries are the valleys between apices.
        edges = [0]
        for left, right in zip(members, members[1:], strict=False):
            valley = int(np.argmin(smoothed[apices[left] : apices[right] + 1])) + apices[left]
            edges.append(valley - start)
        edges.append(end - start)

        for position, member in enumerate(members):
            apex = int(apices[member]) - start
            low, high = edges[position], edges[position + 1]
            height = float(corrected[apex])
            if height < settings.min_height_noise * noise:
                continue
            area = float(np.trapezoid(corrected[low : high + 1], local_times[low : high + 1]))
            if area <= 0.0:
                # The baseline sits above the trace across the integration range: a
                # wobble on a drifting baseline, not a peak. Drift late in a gradient
                # run raises these regularly and none of them is a compound.
                continue

            lead, trail = _width_at(local_times, corrected, apex, 0.5, low, high)
            apex_time = float(local_times[apex])
            if lead is not None and trail is not None:
                w_half, basis = trail - lead, "both flanks"
            elif lead is not None:
                w_half, basis = 2.0 * (apex_time - lead), "leading flank"
            elif trail is not None:
                w_half, basis = 2.0 * (trail - apex_time), "trailing flank"
            else:
                continue  # neither flank reaches half height: not a measurable peak

            w_tangent = _tangent_width(local_times, corrected, local_slope, apex, low, high)
            tail_lead, tail_trail = _width_at(
                local_times, corrected, apex, _TAILING_HEIGHT_FRACTION, low, high
            )
            tailing: float | None = None
            if tail_lead is not None and tail_trail is not None:
                front = apex_time - tail_lead
                if front > 0.0:
                    tailing = float((tail_trail - tail_lead) / (2.0 * front))

            peaks.append(
                Peak(
                    apex_index=int(apices[member]),
                    t_r=apex_time,
                    area=area,
                    height=height,
                    w_half=float(w_half),
                    start_time=float(local_times[low]),
                    end_time=float(local_times[high]),
                    cluster=cluster_id,
                    w_tangent=w_tangent,
                    tailing=tailing,
                    w_half_basis=basis,  # type: ignore[arg-type]
                    fused_left=position > 0,
                    fused_right=position < len(members) - 1,
                )
            )

    peaks.sort(key=lambda peak: peak.t_r)
    pairs = tuple(
        Pair(
            earlier=earlier,
            later=later,
            rs=(later.t_r - earlier.t_r) / (2.0 * (earlier.sigma + later.sigma)),
            usp_resolution=(
                2.0 * (later.t_r - earlier.t_r) / (earlier.w_tangent + later.w_tangent)
                if earlier.w_tangent and later.w_tangent
                else None
            ),
        )
        for earlier, later in zip(peaks, peaks[1:], strict=False)
    )
    return Measurement(peaks=tuple(peaks), pairs=pairs, noise=noise, settings=settings)


def capacity_factor(t_r: float, t0: float, t_dwell: float) -> float:
    """k' against the void, counting the dwell the gradient had to travel first."""
    return (t_r - t0 - t_dwell) / t0
