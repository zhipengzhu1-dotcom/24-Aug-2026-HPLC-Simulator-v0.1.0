"""The chromatogram: a sum of Gaussians over the predicted peaks (SPEC §7).

Two decisions worth stating, because both are visible on screen:

*Size.* SPEC §7 asks for "heights scaled by area shares". A detector trace scales
peak *area*, not apex height, with how much of a compound came off — so a share is
spent as area (apex = share / σ√2π) and a broad peak is drawn correspondingly
shorter. Where no share exists the drawing claims nothing about amounts and every
peak is given the same apex height instead (:func:`~app.pipeline.area_shares`).

*Sampling.* A 1.6 µm column puts σ near 0.01 min inside a 30 min window, so a fixed
point count aliases the peaks into ragged triangles and makes a resolved pair look
merged. The grid is chosen from the narrowest σ present instead.

*Extent.* The axis runs from 0.00 min to the end of the run, not from the first peak to
the last. Framed on the peaks alone the trace reads as a full chromatogram at whatever
zoom the peaks happened to ask for — the screenshot that prompted this showed three
peaks filling a 3.7-5.1 min window of a run that starts at injection, which hides both
how early the first peak comes off and how much of the run is empty after the last. The
lead-in before the first peak is >5σ from every Gaussian and therefore flat, so it is
sampled coarsely and costs the peaks no resolution.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import plotly.graph_objects as go
from numpy.typing import NDArray

from hplcsim.resolution import PredictedPeak

# Points per σ of the narrowest peak. Five puts ~12 samples across a W½ and leaves the
# apex within 0.5% of the true one, which is well under any line width.
_POINTS_PER_SIGMA = 5.0
_MIN_POINTS = 2_000
# Cost ceiling: past this the browser, not the eye, is what notices.
_MAX_POINTS = 60_000
# How far past the outermost peaks the finely-sampled window reaches.
_MARGIN_SIGMAS = 5.0
# The flat stretches either side of that window: enough points to draw a baseline, and
# few enough that a long dead time or a ramp outlasting the peaks does not spend the
# peaks' sampling budget on nothing.
_FLAT_POINTS = 200

_ROOT_TWO_PI = math.sqrt(2.0 * math.pi)
# Headroom above the tallest apex once the y axis is pinned rather than autoranged.
# Plotly's own autorange leaves about this much, so cropping the axis from below does
# not silently change how much air the peak labels get.
_Y_HEADROOM = 1.08


@dataclass(frozen=True)
class PeakLabel:
    """Where to write one peak's name: its apex, in the trace's own units."""

    name: str
    t_r: float
    height: float


@dataclass(frozen=True)
class AxisView:
    """What the plot actually shows, and anything the reader should be told about it.

    The trace is the run; this is the window onto it. They are kept apart on purpose —
    cropping the view must never be mistaken for a different prediction, so nothing here
    touches the sampled signal and every value drawn stays drawn.
    """

    x_range: tuple[float, float]
    y_range: tuple[float, float]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Chromatogram:
    """The rendered trace and the labels that go on it."""

    time: NDArray[np.float64]
    signal: NDArray[np.float64]
    labels: tuple[PeakLabel, ...]
    scaled_by_area: bool
    gradient_end: float | None = None
    """When φf reaches the detector, if the caller knew the method (min from injection)."""


def chromatogram(
    peaks: Sequence[PredictedPeak],
    shares: Mapping[str, float] | None = None,
    *,
    gradient_end: float | None = None,
    extend_to: float | None = None,
) -> Chromatogram:
    """Sum the predicted peaks into one trace running from injection to the last peak.

    ``gradient_end`` is :func:`~hplcsim.retention.gradient_end_time` for the candidate.
    Where the ramp outlasts the peaks the axis is stretched to reach it, so the marker
    is never the one thing cropped off the picture it is there to explain.

    ``extend_to`` is a reader asking the x axis to end later than the run does. It is
    taken here rather than in :func:`axis_view` because a window wider than the data
    would stop the drawn baseline in mid-air partway across the plot — the trace has to
    grow with the window, not just be looked at through a larger one.
    """
    if not peaks:
        raise ValueError("a chromatogram needs at least one predicted peak")

    sigmas = [peak.width.sigma for peak in peaks]
    times = [peak.retention.t_r for peak in peaks]
    window_start = max(0.0, min(times) - _MARGIN_SIGMAS * max(sigmas))
    window_stop = max(times) + _MARGIN_SIGMAS * max(sigmas)
    stop = max([window_stop, *(e for e in (gradient_end, extend_to) if e is not None)])
    time = _time_grid(window_start, window_stop, stop, min(sigmas))

    heights = _apex_heights(peaks, sigmas, shares)
    signal = np.zeros_like(time)
    labels = []
    for peak, sigma, height in zip(peaks, sigmas, heights, strict=True):
        signal += height * np.exp(-0.5 * ((time - peak.retention.t_r) / sigma) ** 2)
        labels.append(PeakLabel(name=peak.name, t_r=peak.retention.t_r, height=height))

    return Chromatogram(
        time=time,
        signal=signal,
        labels=tuple(labels),
        scaled_by_area=shares is not None,
        gradient_end=gradient_end,
    )


def axis_view(
    trace: Chromatogram,
    *,
    x_start: float | None = None,
    x_end: float | None = None,
    y_start: float | None = None,
    y_end: float | None = None,
) -> AxisView:
    """The drawn window, defaulting to the whole run from injection and from zero.

    An end at or below its own start is a typo, not an instruction: it would blank that
    axis and leave nothing on screen to explain why. Per CLAUDE.md the entry is kept,
    the axis falls back to the whole run, and the reader is told — warn, do not block.
    """
    full_x = (float(trace.time[0]), float(trace.time[-1]))
    full_y = (0.0, float(trace.signal.max()) * _Y_HEADROOM)

    x_range, x_note = _span(full_x, x_start, x_end, "x-axis", "{:g} min")
    y_range, y_note = _span(full_y, y_start, y_end, "y-axis", "{:.4g}")
    return AxisView(x_range=x_range, y_range=y_range, notes=tuple(n for n in (x_note, y_note) if n))


def _span(
    full: tuple[float, float],
    start: float | None,
    end: float | None,
    axis: str,
    fmt: str,
) -> tuple[tuple[float, float], str | None]:
    """One axis's drawn range, or the whole of it plus the reason that was refused."""
    lo = full[0] if start is None else float(start)
    hi = full[1] if end is None else float(end)
    if lo >= hi:
        return full, (
            f"{axis} end {fmt.format(hi)} is at or below its start {fmt.format(lo)} — "
            f"showing the whole run instead."
        )
    return (lo, hi), None


def _apex_heights(
    peaks: Sequence[PredictedPeak], sigmas: Sequence[float], shares: Mapping[str, float] | None
) -> list[float]:
    """Each Gaussian's apex, in whatever the y axis then means.

    A share is spent as *area*, so the apex carries a Gaussian's 1/σ√2π and a broad peak
    is drawn shorter for the same amount injected. With no shares to spend, every peak is
    given the same apex instead, which claims nothing about how much of anything there was.
    """
    if shares is None:
        return [1.0] * len(peaks)
    return [
        shares.get(peak.name, 0.0) / (sigma * _ROOT_TWO_PI)
        for peak, sigma in zip(peaks, sigmas, strict=True)
    ]


def _time_grid(
    window_start: float, window_stop: float, stop: float, narrowest_sigma: float
) -> NDArray[np.float64]:
    """0.00 min to the end of the run, sampled finely only where the peaks are.

    One uniform grid over the whole run would either blow past the cost ceiling or, once
    capped, spend on empty baseline the points the narrowest peak needs to be drawn as a
    peak — which is the aliasing this module already refuses. Both flat stretches — the
    lead-in from injection, and any tail where the ramp outlasts the last peak — sit
    >5σ from every Gaussian, so a coarse grid draws them exactly.
    """
    points = _grid_points(window_start, window_stop, narrowest_sigma)
    pieces = [np.linspace(window_start, window_stop, points)]
    if window_start > 0.0:
        pieces.insert(0, np.linspace(0.0, window_start, _FLAT_POINTS, endpoint=False))
    if stop > window_stop:
        pieces.append(np.linspace(window_stop, stop, _FLAT_POINTS + 1)[1:])
    return np.concatenate(pieces)


def _grid_points(start: float, stop: float, narrowest_sigma: float) -> int:
    """Enough samples that the narrowest peak is drawn as a peak, within a cost ceiling."""
    wanted = (stop - start) / narrowest_sigma * _POINTS_PER_SIGMA
    return int(min(max(wanted, _MIN_POINTS), _MAX_POINTS))


# SPEC §7 pins the chromatogram beneath the tabs, "always visible". A pinned block is
# screen the reader cannot scroll out of the way, so its height is not a free choice:
# ticket #19 drew it at 380 px in normal flow, which pinned would take over half a
# laptop viewport and cover the tabs it sits beneath. 300 px still shows the peak shapes
# and the baseline between them, which is what the trace is read for.
CHROMATOGRAM_HEIGHT = 300


def figure(
    trace: Chromatogram, *, height: int = CHROMATOGRAM_HEIGHT, view: AxisView | None = None
) -> Any:
    """The Plotly figure for a rendered trace — the hero of SPEC §7's Cockpit."""
    window = view if view is not None else axis_view(trace)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=trace.time,
            y=trace.signal,
            mode="lines",
            line={"width": 1.4},
            hovertemplate="%{x:.3f} min · %{y:.4g}<extra></extra>",
        )
    )
    # SPEC §7 asks for "peak labels; hover values". The annotations are the labels; the
    # summed trace cannot say which peak a point belongs to, so an invisible marker at
    # each apex carries the name and the predicted time a reader would hover to find.
    fig.add_trace(
        go.Scatter(
            x=[label.t_r for label in trace.labels],
            y=[label.height for label in trace.labels],
            mode="markers",
            marker={"size": 12, "opacity": 0.0},
            customdata=[[label.name] for label in trace.labels],
            hovertemplate="<b>%{customdata[0]}</b><br>tR %{x:.3f} min<extra></extra>",
        )
    )
    for label in trace.labels:
        fig.add_annotation(
            x=label.t_r,
            y=label.height,
            yshift=8,
            text=label.name,
            textangle=-55,
            showarrow=False,
            font={"size": 10},
        )
    # Where the ramp finishes. The screenshot this came from showed every peak eluting
    # after it — three peaks that came off isocratically at φf, which the trace alone
    # cannot say and a chromatographer reading the method needs to know.
    if trace.gradient_end is not None:
        fig.add_vline(
            x=trace.gradient_end,
            line={"color": "#9aa7b6", "width": 1, "dash": "dot"},
            annotation={
                "text": "gradient ends",
                "font": {"size": 9, "color": "#6b7a8c"},
                "yanchor": "bottom",
            },
            annotation_position="bottom right"
            if _room_on_the_right(trace.gradient_end, window.x_range)
            else "bottom left",
        )
    fig.update_layout(
        height=height,
        # The top margin is what the tallest peak's label hangs in. Labels are rotated
        # -55° at 10 px with an 8 px shift, so a ten-character name projects ~50 px
        # upward — trimming this to save pinned screen clips the name off the tallest
        # peak, usually the one being asked about. CHROMATOGRAM_HEIGHT is where the
        # pinned block was made to fit; this is not.
        margin={"l": 10, "r": 10, "t": 44, "b": 10},
        showlegend=False,
        # Both axes are pinned rather than autoranged: Plotly pads an autoranged axis by
        # a few percent of the span, which on a trace that deliberately starts at
        # injection would put visible negative time on screen — and a pinned axis is
        # also what lets the reader move the start without the plot arguing back.
        xaxis={"title": "time (min)", "range": list(window.x_range)},
        yaxis={
            "title": "response (relative)" if trace.scaled_by_area else "response (equal heights)",
            "range": list(window.y_range),
        },
    )
    return fig


def _room_on_the_right(gradient_end: float, x_range: tuple[float, float]) -> bool:
    """Whether the marker's caption fits to its right, or has to hang on its left."""
    span = x_range[1] - x_range[0]
    return span > 0.0 and (gradient_end - x_range[0]) / span < 0.85


def resolution_map_placeholder(
    *,
    t_gradient_range: tuple[float, float],
    hold_range: tuple[float, float],
    candidate: tuple[float, float],
    height: int = 430,
) -> Any:
    """The frame of the v0.2 resolution map, with nothing drawn inside it.

    SPEC §11 puts the map — "max-of-minimum Rs over swept tG/hold" — in v0.2. The
    engine could already sweep it, which is exactly why this stays empty: a filled
    contour would be indistinguishable from the real thing on screen, and a plot that
    looks like data a chromatographer could pick a method from must be data. The axes
    and the current condition are real; the field is blank on purpose.
    """
    fig = go.Figure()
    fig.add_shape(
        type="rect",
        x0=t_gradient_range[0],
        x1=t_gradient_range[1],
        y0=hold_range[0],
        y1=hold_range[1],
        fillcolor="#eef2f7",
        line={"color": "#b9c6d6", "width": 1},
        layer="below",
    )
    fig.add_annotation(
        x=(t_gradient_range[0] + t_gradient_range[1]) / 2.0,
        y=(hold_range[0] + hold_range[1]) / 2.0,
        text=(
            "<b>Resolution map — not in v0.1</b><br>"
            "<span style='font-size:12px'>Minimum Rs swept over gradient time and "
            "initial hold.<br>Deferred to v0.2 with the optimiser (SPEC §11).<br>"
            "Left blank rather than mocked: a filled contour here would be<br>"
            "indistinguishable from a method you could choose from.</span>"
        ),
        showarrow=False,
        font={"size": 15, "color": "#5a6a7d"},
        align="center",
    )
    fig.add_trace(
        go.Scatter(
            x=[candidate[0]],
            y=[candidate[1]],
            mode="markers",
            marker={"size": 11, "symbol": "diamond-open", "color": "#1f4e79", "line": {"width": 2}},
            hovertemplate="candidate<br>tG %{x:.1f} min · hold %{y:.2f} min<extra></extra>",
        )
    )
    fig.update_layout(
        height=height,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        showlegend=False,
        xaxis={"title": "gradient time tG (min)", "range": list(t_gradient_range)},
        yaxis={"title": "initial hold (min)", "range": list(hold_range)},
        plot_bgcolor="#ffffff",
    )
    return fig
