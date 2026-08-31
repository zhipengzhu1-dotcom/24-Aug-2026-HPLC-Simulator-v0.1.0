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
# Where the trace starts and stops relative to the outermost peaks.
_MARGIN_SIGMAS = 5.0

_ROOT_TWO_PI = math.sqrt(2.0 * math.pi)


@dataclass(frozen=True)
class PeakLabel:
    """Where to write one peak's name: its apex, in the trace's own units."""

    name: str
    t_r: float
    height: float


@dataclass(frozen=True)
class Chromatogram:
    """The rendered trace and the labels that go on it."""

    time: NDArray[np.float64]
    signal: NDArray[np.float64]
    labels: tuple[PeakLabel, ...]
    scaled_by_area: bool


def chromatogram(
    peaks: Sequence[PredictedPeak], shares: Mapping[str, float] | None = None
) -> Chromatogram:
    """Sum the predicted peaks into one trace over a time axis that fits them all."""
    if not peaks:
        raise ValueError("a chromatogram needs at least one predicted peak")

    sigmas = [peak.width.sigma for peak in peaks]
    times = [peak.retention.t_r for peak in peaks]
    start = max(0.0, min(times) - _MARGIN_SIGMAS * max(sigmas))
    stop = max(times) + _MARGIN_SIGMAS * max(sigmas)
    time = np.linspace(start, stop, _grid_points(start, stop, min(sigmas)))

    heights = _apex_heights(peaks, sigmas, shares)
    signal = np.zeros_like(time)
    labels = []
    for peak, sigma, height in zip(peaks, sigmas, heights, strict=True):
        signal += height * np.exp(-0.5 * ((time - peak.retention.t_r) / sigma) ** 2)
        labels.append(PeakLabel(name=peak.name, t_r=peak.retention.t_r, height=height))

    return Chromatogram(
        time=time, signal=signal, labels=tuple(labels), scaled_by_area=shares is not None
    )


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


def figure(trace: Chromatogram, *, height: int = CHROMATOGRAM_HEIGHT) -> Any:
    """The Plotly figure for a rendered trace — the hero of SPEC §7's Cockpit."""
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
    fig.update_layout(
        height=height,
        # The subheader above the plot already names the condition, so the top margin
        # only has to clear the tallest peak label — every pixel here is pinned screen.
        margin={"l": 10, "r": 10, "t": 28, "b": 10},
        showlegend=False,
        xaxis_title="time (min)",
        yaxis_title="response (relative)" if trace.scaled_by_area else "response (equal heights)",
    )
    return fig


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
