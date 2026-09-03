"""THROWAWAY: a piecewise-linear gradient programme and its retention (ticket #45).

Not the v0.2 engine. No tests, no home in ``src/``. It exists so the segment list on the
rail is *live* — drag a second segment and the peaks move — rather than a dead table.

The arithmetic is the v0.1 closed form's own assumptions, extended piece by piece: the
band migrates as dx/dt = 1/(t0·k(φ_inlet(t))), φ_inlet is the pump programme delayed by
the dwell, and elution is one t0 after x reaches 1. Every linear piece has a closed
form, so a one-segment programme reproduces ``hplcsim.retention.predict_retention`` to
floating point (asserted by ``check_single_segment_matches_engine``). Multi-segment
numbers are therefore the same simplification the engine already makes — not den Uijl
Eq. 7–8, which is #46/#47's business.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hplcsim.model import Gradient, Method, RetentionParams
from hplcsim.retention import Regime, RetentionResult, predict_retention
from hplcsim.width import FittedPlateCount, PeakWidth, band_compression_factor, default_plate_count


@dataclass(frozen=True)
class Segment:
    duration: float  # min
    phi_end: float  # fraction


@dataclass(frozen=True)
class Programme:
    """φ0, an initial hold, then one or more linear segments. Pump time throughout."""

    phi0: float
    t_init: float
    segments: tuple[Segment, ...]

    # --- shape -------------------------------------------------------------------

    @property
    def is_single(self) -> bool:
        return len(self.segments) == 1

    @property
    def phif(self) -> float:
        return self.segments[-1].phi_end

    @property
    def t_ramp(self) -> float:
        return sum(s.duration for s in self.segments)

    @property
    def t_end(self) -> float:
        """Pump time at which the last segment finishes."""
        return self.t_init + self.t_ramp

    def as_gradient(self) -> Gradient:
        """Exact for one segment; the overall envelope φ0 → φf over Σ durations otherwise."""
        return Gradient(self.phi0, self.phif, self.t_ramp, self.t_init)

    @staticmethod
    def from_gradient(gradient: Gradient) -> Programme:
        return Programme(
            gradient.phi0, gradient.t_init, (Segment(gradient.t_gradient, gradient.phif),)
        )

    def breakpoints(self) -> list[tuple[float, float]]:
        """(pump time, φ) at every corner — what a No./Time/%B table lists."""
        points = [(0.0, self.phi0)]
        if self.t_init > 0:
            points.append((self.t_init, self.phi0))
        t, phi = self.t_init, self.phi0
        for s in self.segments:
            t += s.duration
            phi = s.phi_end
            points.append((t, phi))
        return points

    def phi_at_pump(self, t: float) -> float:
        points = self.breakpoints()
        if t <= 0:
            return self.phi0
        for (t_a, p_a), (t_b, p_b) in zip(points, points[1:], strict=False):
            if t <= t_b:
                if t_b == t_a:
                    return p_b
                return p_a + (p_b - p_a) * (t - t_a) / (t_b - t_a)
        return points[-1][1]

    def phi_at_detector(self, t: float, method: Method) -> float:
        """φ seen at the detector at time ``t`` after injection (pump + dwell + t0)."""
        return self.phi_at_pump(t - method.t_dwell - method.t0)

    def describe(self) -> str:
        """One line for a status bar / caption: '5 → 35 %B in 20 min, then → 95 in 5 min'."""
        parts = []
        phi = self.phi0
        for i, s in enumerate(self.segments):
            if i == 0:
                parts.append(
                    f"{phi * 100:g} → {s.phi_end * 100:g} %B in {s.duration:g} min"
                )
            elif s.phi_end == phi:
                parts.append(f"then hold {s.duration:g} min")
            else:
                parts.append(f"then → {s.phi_end * 100:g} in {s.duration:g} min")
            phi = s.phi_end
        hold = f"; hold {self.t_init:g} min" if self.t_init else ""
        return ", ".join(parts) + hold

    def steepness_per_segment(self, method: Method) -> list[float]:
        """s* = t0·|Δφ|/duration for each segment (dimensionless, Guillarme Eq. 8)."""
        out = []
        phi = self.phi0
        for s in self.segments:
            out.append(method.t0 * abs(s.phi_end - phi) / s.duration)
            phi = s.phi_end
        return out


def steepness(method: Method, gradient: Gradient) -> float:
    return method.t0 * gradient.delta_phi / gradient.t_gradient


# --- retention -------------------------------------------------------------------------


@dataclass(frozen=True)
class Elution:
    retention: RetentionResult
    phi_e: float  # inlet composition when the band leaves
    segment: int | None  # which segment it left during; None = hold / after the end
    k_start: float  # k at the start of that segment (for the compression factor)
    b_local: float  # natural-log steepness of that segment


def elute(params: RetentionParams, method: Method, programme: Programme) -> Elution:
    """Where and when one peak leaves the column under ``programme``."""
    t0 = method.t0
    tau = method.t_dwell + programme.t_init

    # Pieces in *inlet* time: (start, end or None, phi_start, slope per min, segment index)
    pieces: list[tuple[float, float | None, float, float, int | None]] = [
        (0.0, tau, programme.phi0, 0.0, None)
    ]
    t, phi = tau, programme.phi0
    for i, s in enumerate(programme.segments):
        pieces.append((t, t + s.duration, phi, (s.phi_end - phi) / s.duration, i))
        t, phi = t + s.duration, s.phi_end
    pieces.append((t, None, phi, 0.0, None))

    x = 0.0
    for start, end, phi_start, slope, index in pieces:
        k_a = params.k_at(phi_start)
        c = params.s_e * slope  # ln k falls at rate c per minute along this piece
        remaining = 1.0 - x
        if c == 0.0:
            dt_exit = remaining * t0 * k_a
            length = None if end is None else end - start
            if length is None or dt_exit <= length:
                t_exit = start + dt_exit
                regime: Regime = "isocratic_hold" if index is None and end is not None else (
                    "post_gradient" if index is None else "gradient"
                )
                return _finish(
                    t_exit, k_a, phi_start, regime, index, k_a, 0.0, t0, tau, method
                )
            x += length / (t0 * k_a)
            continue
        assert end is not None
        length = end - start
        arg = 1.0 + remaining * t0 * k_a * c
        if arg > 0.0:
            dt_exit = math.log(arg) / c
            if dt_exit <= length:
                t_exit = start + dt_exit
                phi_e = phi_start + slope * dt_exit
                return _finish(
                    t_exit, params.k_at(phi_e), phi_e, "gradient", index, k_a,
                    t0 * slope * params.s_e, t0, tau, method,
                )
        x += (math.exp(c * length) - 1.0) / (t0 * k_a * c)
    raise AssertionError("unreachable: the final flat piece always elutes")


def _finish(
    t_exit: float,
    k_e: float,
    phi_e: float,
    regime: Regime,
    segment: int | None,
    k_start: float,
    b_local: float,
    t0: float,
    tau: float,
    method: Method,
) -> Elution:
    t_r = t_exit + t0
    t_r_prime = t_r - t0 - tau
    low = regime != "gradient" or k_e < 1.0 or t_r_prime < t0
    return Elution(
        RetentionResult(t_r=t_r, k_e=k_e, regime=regime, low_confidence=low),
        phi_e=phi_e,
        segment=segment,
        k_start=k_start,
        b_local=b_local,
    )


def width(
    params: RetentionParams,
    method: Method,
    programme: Programme,
    plate_count: float | FittedPlateCount | None,
) -> PeakWidth:
    """Prototype width: the engine's σ = G·t0·(1+k_e)/√N with G from the exit segment.

    For a one-segment programme this is exactly ``hplcsim.width.peak_width``. For more,
    G is taken from the segment the band left during, with k at that segment's start —
    an approximation, flagged as such in the README.
    """
    if plate_count is None:
        n, source = default_plate_count(method), "default"
    elif isinstance(plate_count, FittedPlateCount):
        n, source = plate_count.plate_count, "fitted"
    else:
        n, source = float(plate_count), "supplied"
    e = elute(params, method, programme)
    g = (
        band_compression_factor(e.b_local, k0=e.k_start)
        if e.retention.regime == "gradient"
        else 1.0
    )
    sigma = g * method.t0 * (1.0 + e.retention.k_e) / math.sqrt(n)
    return PeakWidth(
        sigma=sigma,
        w_half=math.sqrt(8.0 * math.log(2.0)) * sigma,
        w_base=4.0 * sigma,
        g=g,
        plate_count=n,
        k_e=e.retention.k_e,
        plate_count_source=source,  # type: ignore[arg-type]
    )


def check_single_segment_matches_engine(
    params: RetentionParams, method: Method, gradient: Gradient
) -> float:
    """|tR(prototype) − tR(engine)| for a one-segment programme; should be ~1e-12."""
    ours = elute(params, method, Programme.from_gradient(gradient)).retention.t_r
    theirs = predict_retention(params, method, gradient).t_r
    return abs(ours - theirs)
