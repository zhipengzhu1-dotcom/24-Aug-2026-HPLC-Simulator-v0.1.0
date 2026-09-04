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

from app.diagnostics import CompositionWindow
from hplcsim.model import Method, Run, Target, as_programme, percent_b_from_phi
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
Y_HEADROOM = 1.08
# How far along the x axis the gradient-end marker may sit before its caption, which
# hangs to the right, would run off the plot and has to hang to the left instead.
_CAPTION_FLIPS_AT = 0.85


@dataclass(frozen=True)
class PeakLabel:
    """Where to write one peak's name: its apex, in the trace's own units."""

    name: str
    t_r: float
    height: float


@dataclass(frozen=True)
class AxisRequest:
    """Where the reader asked each axis to begin and end; ``None`` means the whole run.

    One object rather than four loose floats, so the app's widgets, its session keys and
    :func:`axis_view` all name the same quartet once.
    """

    x_start: float | None = None
    x_end: float | None = None
    y_start: float | None = None
    y_end: float | None = None


@dataclass(frozen=True)
class AxisView:
    """What the plot actually shows, and anything the reader should be told about it.

    The trace is the run; this is the window onto it. They are kept apart on purpose —
    cropping the view must never be mistaken for a different prediction, so nothing here
    touches the sampled signal and every value drawn stays drawn.

    ``run_x`` / ``run_y`` are the whole-run extents the ranges default to, kept so the
    controls that seed from them read the same numbers this view was built from.
    """

    x_range: tuple[float, float]
    y_range: tuple[float, float]
    run_x: tuple[float, float]
    run_y: tuple[float, float]
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
    Where the ramp outlasts the peaks the axis is stretched past it by the same margin a
    peak gets, so the marker is never the one thing cropped off the picture it is there
    to explain — nor drawn on the frame, where a line is easy to miss.

    ``extend_to`` is a reader asking the x axis to end later than the run does. It is
    taken here rather than in :func:`axis_view` because a window wider than the data
    would stop the drawn baseline in mid-air partway across the plot — the trace has to
    grow with the window, not just be looked at through a larger one.
    """
    if not peaks:
        raise ValueError("a chromatogram needs at least one predicted peak")

    sigmas = [peak.width.sigma for peak in peaks]
    times = [peak.retention.t_r for peak in peaks]
    margin = _MARGIN_SIGMAS * max(sigmas)
    window_start = max(0.0, min(times) - margin)
    window_stop = max(times) + margin
    reaches = [window_stop]
    if gradient_end is not None:
        reaches.append(gradient_end + margin)
    if extend_to is not None:
        reaches.append(extend_to)
    stop = max(reaches)
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


def axis_view(trace: Chromatogram, request: AxisRequest | None = None) -> AxisView:
    """The drawn window, defaulting to the whole run from injection and from zero.

    An end at or below its own start is a typo, not an instruction: it would blank that
    axis and leave nothing on screen to explain why. Per CLAUDE.md the entry is kept,
    the axis falls back to the whole run, and the reader is told — warn, do not block.

    A window that leaves a peak off-screen is honoured — the reader may well want the
    crop — but it is named, so a plot with fewer peaks than the table is never read as
    a prediction with fewer peaks.
    """
    asked = request if request is not None else AxisRequest()
    run_x = (float(trace.time[0]), float(trace.time[-1]))
    run_y = (0.0, float(trace.signal.max()) * Y_HEADROOM)

    x_range, x_note = _span(run_x, asked.x_start, asked.x_end, "x-axis", "{:g} min")
    y_range, y_note = _span(run_y, asked.y_start, asked.y_end, "y-axis", "{:.4g}")
    notes = [n for n in (x_note, y_note, _cropped(trace, x_range, y_range)) if n]
    return AxisView(x_range=x_range, y_range=y_range, run_x=run_x, run_y=run_y, notes=tuple(notes))


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


def _cropped(
    trace: Chromatogram, x_range: tuple[float, float], y_range: tuple[float, float]
) -> str | None:
    """Which peaks the window leaves out, if any — by apex, since the label sits there."""
    off_x = [lb.name for lb in trace.labels if not x_range[0] <= lb.t_r <= x_range[1]]
    off_y = [lb.name for lb in trace.labels if lb.height > y_range[1]]
    parts = []
    if off_x:
        parts.append(f"{', '.join(off_x)} outside the x range")
    if off_y:
        parts.append(f"{', '.join(off_y)} taller than the y range")
    if not parts:
        return None
    return "This window leaves " + " and ".join(parts) + " — the prediction still has them."


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


# --- the programme overlay (SPEC §7, v0.2, #45/#74) -----------------------------------
#
# Both programmes on a right-hand %B axis — the candidate solid, the scouting pair
# dashed — with each peak marked at its elution composition and its calibrated
# composition window drawn as the whisker. Always on, never behind a toggle: the
# strong-tier states of SPEC §6 are exactly when it must be seen.
#
# **The time base is the detector's, not the pump's.** A programme is typed against the
# pump, but this plot's x axis is time from injection *at the detector*, which is what
# the trace beneath it is drawn on. So every point is delayed by t_dwell + t0 — the same
# expression `hplcsim.retention.gradient_end_time` uses, which is why the "gradient ends"
# marker lands exactly where the candidate curve reaches φf. What that buys is the
# property the whole overlay rests on: a peak's marker sits *on* the candidate curve
# whenever it elutes on a ramp, because the composition the band left the column in is
# the composition arriving at the detector at that instant. `tests/test_overlay.py` pins
# it to float precision on one segment, on several, on a descending leg and in a hold.

# The overlay's palette, chosen against the trace rather than for itself. The candidate
# was drawn in the app's instrument blue first and had to be moved: on screen it reads
# as *signal* beside a periwinkle chromatogram, and being the tallest solid line on the
# plot it took the eye the trace is meant to have. A muted green is the nearest colour
# that is neither the signal's family nor one of the panel's status colours. The
# scouting pair keeps the grey of the gradient-end marker, which is what "as run,
# already known" reads as everywhere else on this plot, and the peak markers are the one
# saturated thing in the picture because they are the point of it.
_CANDIDATE_COLOUR = "#5b8c5a"
_SCOUTING_COLOUR = "#9aa7b6"
_WINDOW_COLOUR = "#b0399a"

# Air above and below the compositions actually drawn, and the narrowest %B span the
# axis is allowed to have: a candidate that moves 4 %B should not be magnified into a
# full-height ramp by an axis fitted tightly to it.
_OVERLAY_PAD_PERCENT_B = 4.0
_MIN_OVERLAY_SPAN_PERCENT_B = 10.0

# Room on the right for the %B axis' ticks and its title. The left margin is 10; this
# one has an axis in it, and at 10 the tick labels are drawn outside the paper and
# clipped. Measured in a browser at 1440 × 900.
_OVERLAY_RIGHT_MARGIN = 46


@dataclass(frozen=True)
class ProgrammeCurve:
    """One programme as the overlay draws it: %B against time at the detector."""

    label: str
    times: tuple[float, ...]
    percent_b: tuple[float, ...]
    dashed: bool


@dataclass(frozen=True)
class WindowMarker:
    """One peak on the %B axis: where the candidate elutes it, inside what window.

    ``percent_b`` is the elution composition; ``percent_b_low`` / ``percent_b_high`` are
    the calibrated composition window [φ_e,run2, φ_e,run1] the fit was actually shown,
    drawn as the whisker. All three come from the one
    :class:`~app.diagnostics.CompositionWindow` the fit tab's readout is built from, so
    the whisker on the plot and the row in the table can never disagree.
    """

    name: str
    t_r: float
    percent_b: float
    percent_b_low: float
    percent_b_high: float


@dataclass(frozen=True)
class Overlay:
    """Everything drawn on the right-hand %B axis for one rendering."""

    candidate: ProgrammeCurve
    scouting: tuple[ProgrammeCurve, ...]
    peaks: tuple[WindowMarker, ...]

    @property
    def curves(self) -> tuple[ProgrammeCurve, ...]:
        return (*self.scouting, self.candidate)

    @property
    def percent_b_range(self) -> tuple[float, float]:
        """The %B axis, padded around everything drawn and kept inside 0–100.

        Clamping is one-sided on purpose: 0 and 100 %B are the ends of the axis a
        chromatographer reads, but a value that somehow lands outside them is still
        drawn rather than cropped to make the axis tidy.
        """
        values = [b for curve in self.curves for b in curve.percent_b]
        values += [
            b
            for peak in self.peaks
            for b in (peak.percent_b, peak.percent_b_low, peak.percent_b_high)
        ]
        drawn_low, drawn_high = min(values), max(values)
        low = drawn_low - _OVERLAY_PAD_PERCENT_B
        high = drawn_high + _OVERLAY_PAD_PERCENT_B
        if high - low < _MIN_OVERLAY_SPAN_PERCENT_B:
            middle = (drawn_low + drawn_high) / 2.0
            low = middle - _MIN_OVERLAY_SPAN_PERCENT_B / 2.0
            high = middle + _MIN_OVERLAY_SPAN_PERCENT_B / 2.0
        # The clamp comes last, after the widening: widening a near-100 %B hold and
        # then clamping in the other order left the axis running to 103 %B, which is a
        # composition no pump makes. Whatever is drawn is still inside the range —
        # cropping a value to keep the axis tidy is the one thing this must not do.
        return (min(drawn_low, max(0.0, low)), max(drawn_high, min(100.0, high)))


def programme_curve(
    method: Method,
    target: Target,
    *,
    label: str,
    dashed: bool,
    extend_to: float | None = None,
) -> ProgrammeCurve:
    """One programme as the composition arriving at the detector, minute by minute.

    Row 1 is injection at φ0; the ramp begins one dwell plus one t0 after the pump
    starts it, and every later point is the end of a segment at the same delay. A
    programme that finishes before ``extend_to`` is carried flat out to it, so the
    curve spans the plot instead of stopping in mid-air part-way across it.
    """
    programme = as_programme(target)
    delay = method.t_dwell + method.t0
    elapsed = [delay, programme.t_init]
    times = [0.0, math.fsum(elapsed)]
    percent_b = [percent_b_from_phi(programme.phi0)] * 2
    for segment in programme.segments:
        elapsed.append(segment.duration)
        times.append(math.fsum(elapsed))
        percent_b.append(percent_b_from_phi(segment.phif))
    if extend_to is not None and extend_to > times[-1]:
        times.append(float(extend_to))
        percent_b.append(percent_b[-1])
    return ProgrammeCurve(
        label=label, times=tuple(times), percent_b=tuple(percent_b), dashed=dashed
    )


def programme_overlay(
    method: Method,
    target: Target,
    scouting: Sequence[Run],
    windows: Sequence[CompositionWindow],
    predicted: Mapping[str, PredictedPeak],
    *,
    extend_to: float | None = None,
) -> Overlay:
    """SPEC §7's programme overlay for one rendering — the candidate, the pair, the peaks.

    ``windows`` is :attr:`~app.diagnostics.Diagnostics.windows` and ``predicted`` is
    :attr:`~app.pipeline.Cockpit.predicted_by_name`; a peak with a window but no
    prediction has no time to be drawn at and is left out rather than guessed at.
    """
    return Overlay(
        candidate=programme_curve(
            method, target, label="candidate", dashed=False, extend_to=extend_to
        ),
        scouting=tuple(
            programme_curve(
                method,
                run.gradient,
                label=run.name or f"scouting {index}",
                dashed=True,
                extend_to=extend_to,
            )
            for index, run in enumerate(scouting, start=1)
        ),
        peaks=tuple(
            WindowMarker(
                name=window.name,
                t_r=predicted[window.name].retention.t_r,
                percent_b=percent_b_from_phi(window.candidate_phi_e),
                percent_b_low=percent_b_from_phi(window.phi_low),
                percent_b_high=percent_b_from_phi(window.phi_high),
            )
            for window in windows
            if window.name in predicted
        ),
    )


# SPEC §7 pins the chromatogram beneath the tabs, "always visible". A pinned block is
# screen the reader cannot scroll out of the way, so its height is not a free choice:
# ticket #19 drew it at 380 px in normal flow, which pinned would take over half a
# laptop viewport and cover the tabs it sits beneath. 250 px still shows the peak shapes
# and the baseline between them, which is what the trace is read for — 50 px less than
# the 300 it was, which is what the always-open axis strip beneath the block costs out
# of the same pinned budget (#62).
CHROMATOGRAM_HEIGHT = 250


def figure(
    trace: Chromatogram,
    *,
    height: int = CHROMATOGRAM_HEIGHT,
    view: AxisView | None = None,
    overlay: Overlay | None = None,
) -> Any:
    """The Plotly figure for a rendered trace — the hero of SPEC §7's Cockpit.

    ``overlay`` is SPEC §7's always-on programme overlay. It is drawn first, so the two
    programmes sit *behind* the trace they explain and the trace stays the hero; the
    peak markers go on last, because a whisker under a Gaussian cannot be read.
    """
    if view is None:
        view = axis_view(trace)
    fig = go.Figure()
    if overlay is not None:
        _draw_programmes(fig, overlay)
    fig.add_trace(
        go.Scatter(
            x=trace.time,
            y=trace.signal,
            mode="lines",
            # The colour is pinned rather than left to Plotly's cycle. The overlay's
            # curves are added to the figure before this one so that they sit behind it,
            # and an unset colour takes the *next* entry of the colorway — so the trace
            # silently turned red the moment the overlay went in. This is the first
            # entry of that colorway, which is the blue v0.1 drew it in.
            line={"width": 1.4, "color": "#636efa"},
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
            if _room_on_the_right(trace.gradient_end, view.x_range)
            else "bottom left",
        )
    if overlay is not None:
        _draw_peak_windows(fig, overlay)
    fig.update_layout(
        height=height,
        # The top margin is what the tallest peak's label hangs in. Labels are rotated
        # -55° at 10 px with an 8 px shift, so a ten-character name projects ~50 px
        # upward — trimming this to save pinned screen clips the name off the tallest
        # peak, usually the one being asked about. CHROMATOGRAM_HEIGHT is where the
        # pinned block was made to fit; this is not.
        margin={
            "l": 10,
            "r": 10 if overlay is None else _OVERLAY_RIGHT_MARGIN,
            "t": 44,
            "b": 10,
        },
        showlegend=False,
        # Both axes are pinned rather than autoranged: Plotly pads an autoranged axis by
        # a few percent of the span, which on a trace that deliberately starts at
        # injection would put visible negative time on screen — and a pinned axis is
        # also what lets the reader move the start without the plot arguing back.
        xaxis={"title": "time (min)", "range": list(view.x_range)},
        yaxis={
            "title": "response (relative)" if trace.scaled_by_area else "response (equal heights)",
            "range": list(view.y_range),
        },
        # SPEC §7's right-hand %B axis. Its own range, not the reader's: the axis strip
        # (#62) sets the window onto the *trace*, and a composition axis cropped by a
        # box meant for the signal would move the programmes without saying so.
        **(
            {}
            if overlay is None
            else {
                "yaxis2": {
                    "title": "%B",
                    "overlaying": "y",
                    "side": "right",
                    "range": list(overlay.percent_b_range),
                    "showgrid": False,
                    "zeroline": False,
                    "tickfont": {"size": 9},
                    "title_font": {"size": 10},
                    "title_standoff": 4,
                }
            }
        ),
    )
    return fig


def _draw_programmes(fig: Any, overlay: Overlay) -> None:
    """The scouting pair dashed and the candidate solid, on the right-hand %B axis.

    Dashed against solid is SPEC §7's own distinction — "as run" against "predicted" —
    and it is carried by the line style rather than by a legend: the block is pinned
    screen, and a legend would cost it the room the tallest peak's label hangs in. Each
    curve names itself on hover instead, and the caption beneath the plot says which is
    which.
    """
    for curve in overlay.curves:
        fig.add_trace(
            go.Scatter(
                x=list(curve.times),
                y=list(curve.percent_b),
                yaxis="y2",
                mode="lines",
                name=curve.label,
                line={
                    "width": 1.1 if curve.dashed else 1.4,
                    "color": _SCOUTING_COLOUR if curve.dashed else _CANDIDATE_COLOUR,
                    "dash": "dash" if curve.dashed else "solid",
                },
                hovertemplate=(
                    f"<b>{curve.label}</b><br>%{{x:.2f}} min · %{{y:.1f}} %B<extra></extra>"
                ),
            )
        )


def _draw_peak_windows(fig: Any, overlay: Overlay) -> None:
    """Each peak at its elution composition, its calibrated window as the whisker.

    The marker lands on the candidate curve whenever the peak elutes on a ramp — that
    is the arithmetic, not a drawing choice — so what the whisker shows is the only
    thing worth showing beside it: how far the fit's own two compositions reach, and
    whether this peak is being predicted inside them or outside.
    """
    if not overlay.peaks:
        return
    peaks = overlay.peaks
    fig.add_trace(
        go.Scatter(
            x=[peak.t_r for peak in peaks],
            y=[peak.percent_b for peak in peaks],
            yaxis="y2",
            mode="markers",
            name="elution %B",
            marker={
                "size": 7,
                "symbol": "diamond",
                "color": _WINDOW_COLOUR,
                "line": {"width": 1, "color": "#ffffff"},
            },
            error_y={
                "type": "data",
                "symmetric": False,
                "array": [peak.percent_b_high - peak.percent_b for peak in peaks],
                "arrayminus": [peak.percent_b - peak.percent_b_low for peak in peaks],
                "color": _WINDOW_COLOUR,
                "thickness": 1.2,
                "width": 4,
            },
            customdata=[[peak.name, peak.percent_b_low, peak.percent_b_high] for peak in peaks],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>elutes at %{y:.1f} %B<br>"
                "calibrated window %{customdata[1]:.1f}–%{customdata[2]:.1f} %B<extra></extra>"
            ),
        )
    )


def _room_on_the_right(gradient_end: float, x_range: tuple[float, float]) -> bool:
    """Whether the marker's caption fits to its right, or has to hang on its left."""
    span = x_range[1] - x_range[0]
    return span > 0.0 and (gradient_end - x_range[0]) / span < _CAPTION_FLIPS_AT


def resolution_map_placeholder(
    *,
    t_gradient_range: tuple[float, float],
    hold_range: tuple[float, float],
    candidate: tuple[float, float],
    height: int = 430,
) -> Any:
    """The frame of the v0.2 resolution map, with nothing drawn inside it.

    SPEC §11 puts the map — "max-of-minimum Rs over swept tG/hold" — in v0.7. The
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
            "<b>Resolution map — not built yet</b><br>"
            "<span style='font-size:12px'>Minimum Rs swept over gradient time and "
            "initial hold.<br>Planned for v0.7 with the optimiser (SPEC §11).<br>"
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
