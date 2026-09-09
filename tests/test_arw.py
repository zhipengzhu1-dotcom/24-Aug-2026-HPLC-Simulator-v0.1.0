"""The integrator against traces whose answers are known exactly.

`scripts/` has no other gate. The measurements it produces become validation evidence,
and a wrong area or width does not look wrong — it looks like a number. So every
quantity is asserted against a synthetic peak whose true retention time, area, width
and resolution are arithmetic rather than opinion.

The Gaussian is the case where the two resolution conventions must *coincide*: its
inflection tangents meet the baseline at ±2σ, so the USP tangent width is exactly 4σ
and USP Rs reduces to Δt/(2(σ₁+σ₂)). Any gap between the two on a synthetic Gaussian
is a bug in one of them; the gap on a real peak is that peak's asymmetry.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from scripts.arw import Channel, Trace, nearest_channel, read_channel, read_spectra
from scripts.assign import Fingerprint, fingerprints, similarity_matrix
from scripts.integrate import Settings, capacity_factor, estimate_noise, measure

_STEP_MIN = 1.0 / (20.0 * 60.0)  # the instrument's 20 Hz
_W_HALF_PER_SIGMA = math.sqrt(8.0 * math.log(2.0))

# A uniform stand-in axis for the file tests. The instrument's own axis is close to
# 210.0668 nm with a 0.6093 nm step but is not exactly regular, so the channels it
# actually offers are asserted separately, against real values.
_AXIS = np.array([210.0668 + 0.6093 * n for n in range(120)], dtype=np.float64)

# Verbatim from the exports: the channels bracketing each nominal wavelength.
_REAL_NEAR_220 = np.array([219.2079, 219.8182, 220.4275], dtype=np.float64)
_REAL_NEAR_254 = np.array([253.4681, 254.0824, 254.6957], dtype=np.float64)


def _times(run_time_min: float) -> NDArray[np.float64]:
    return np.arange(0.0, run_time_min, _STEP_MIN, dtype=np.float64)


def _gaussian(
    times: NDArray[np.float64], t_r: float, height: float, sigma: float
) -> NDArray[np.float64]:
    return height * np.exp(-((times - t_r) ** 2) / (2.0 * sigma**2))


def _trace(times: NDArray[np.float64], signal: NDArray[np.float64]) -> Trace:
    return Trace(
        times=times,
        signal=signal,
        channel=Channel(index=16, nm=219.8182),
        source=Path("synthetic.arw"),
        sha256="0" * 64,
        wavelengths=_AXIS,
    )


def _write_arw(path: Path, times: NDArray[np.float64], matrix: NDArray[np.float64]) -> None:
    """An .arw as Empower writes one: CR line endings, tabs, a bare `Time` row."""
    rows = ["Wavelength\t" + "\t".join(f"{nm:.4f}" for nm in _AXIS), "Time"]
    rows += [
        f"{time:.7f}\t" + "\t".join(f"{value:.7g}" for value in row)
        for time, row in zip(times, matrix, strict=True)
    ]
    path.write_bytes(("\r".join(rows) + "\r").encode("ascii"))


class TestReader:
    def test_the_nominal_wavelengths_are_not_on_the_grid(self) -> None:
        """220 and 254 nm do not exist; the nearest channel is named by what it holds.

        Both nominal values fall between real channels, and the nearer one is not the
        lower one in both cases — 219.8182 is 0.18 nm below 220 while 220.4275 is 0.43
        above, and 254.0824 is 0.08 above 254 while 253.4681 is 0.53 below.
        """
        assert nearest_channel(_REAL_NEAR_220, 220.0) == Channel(index=1, nm=219.8182)
        assert nearest_channel(_REAL_NEAR_254, 254.0) == Channel(index=1, nm=254.0824)

    def test_a_channel_is_chosen_and_never_interpolated(self) -> None:
        """The returned nm is always a value the axis actually holds."""
        for axis, target in ((_REAL_NEAR_220, 220.0), (_REAL_NEAR_254, 254.0)):
            channel = nearest_channel(axis, target)
            assert channel.nm in set(axis.tolist())
            assert channel.nm != target

    def test_a_channel_round_trips_through_the_file(self, tmp_path: Path) -> None:
        times = _times(0.5)
        matrix = np.outer(_gaussian(times, 0.25, 1.0, 0.02), np.arange(1.0, len(_AXIS) + 1.0))
        path = tmp_path / "run.arw"
        _write_arw(path, times, matrix)

        trace = read_channel(path, 220.0)

        assert trace.channel.nm == pytest.approx(_AXIS[16])
        assert trace.times == pytest.approx(times, abs=1e-6)
        # Channel 16 is the 17th column, scaled by 17 in the synthetic matrix.
        assert trace.signal == pytest.approx(matrix[:, 16], rel=1e-5)
        # The export writes times to seven decimals, so the rate it implies is 20 Hz
        # only to about 0.04% — the real files read 20.008 for the same reason.
        assert trace.sampling_hz == pytest.approx(20.0, rel=1e-3)
        assert len(trace.sha256) == 64

    def test_a_file_that_is_not_an_export_is_refused_by_name(self, tmp_path: Path) -> None:
        path = tmp_path / "not-an-export.arw"
        path.write_bytes(b"Absorbance\t1\t2\rTime\r0\t1\t2\r")
        with pytest.raises(ValueError, match="expected a 'Wavelength' row 0"):
            read_channel(path, 220.0)

    def test_spectra_come_back_in_the_order_asked_for(self, tmp_path: Path) -> None:
        times = _times(0.2)
        matrix = np.outer(np.arange(1.0, len(times) + 1.0), np.arange(1.0, len(_AXIS) + 1.0))
        path = tmp_path / "run.arw"
        _write_arw(path, times, matrix)

        spectra = read_spectra(path, np.array([5, 1], dtype=np.int64))

        assert spectra.shape == (2, len(_AXIS))
        assert spectra[0] == pytest.approx(matrix[5], rel=1e-6)
        assert spectra[1] == pytest.approx(matrix[1], rel=1e-6)

    def test_a_row_index_past_the_end_is_an_error_and_not_a_silent_gap(
        self, tmp_path: Path
    ) -> None:
        times = _times(0.05)
        path = tmp_path / "run.arw"
        _write_arw(path, times, np.zeros((len(times), len(_AXIS))))
        with pytest.raises(ValueError, match="no data row at index"):
            read_spectra(path, np.array([10_000], dtype=np.int64))


class TestOnePeak:
    """A single Gaussian, where every quantity has a closed form."""

    T_R = 5.0
    HEIGHT = 0.2
    SIGMA = 0.02

    @pytest.fixture
    def trace(self) -> Trace:
        times = _times(10.0)
        rng = np.random.default_rng(1)
        noise = rng.normal(0.0, 1e-5, times.size)
        return _trace(times, _gaussian(times, self.T_R, self.HEIGHT, self.SIGMA) + noise)

    def test_retention_time_area_height_and_width_are_all_recovered(self, trace: Trace) -> None:
        peaks = measure(trace).peaks
        assert len(peaks) == 1
        peak = peaks[0]

        assert peak.t_r == pytest.approx(self.T_R, abs=2e-3)
        assert peak.height == pytest.approx(self.HEIGHT, rel=0.02)
        assert peak.w_half == pytest.approx(_W_HALF_PER_SIGMA * self.SIGMA, rel=0.02)
        # Area under a Gaussian is h·σ·√(2π); integration limits clip the far tails,
        # so the measured value is a little under and never over.
        analytic = self.HEIGHT * self.SIGMA * math.sqrt(2.0 * math.pi)
        assert peak.area == pytest.approx(analytic, rel=0.05)
        assert peak.area < analytic

    def test_sigma_is_the_width_in_the_conventions_exact_constant(self, trace: Trace) -> None:
        peak = measure(trace).peaks[0]
        assert peak.sigma == pytest.approx(self.SIGMA, rel=0.02)
        assert peak.w_half / peak.sigma == pytest.approx(math.sqrt(8.0 * math.log(2.0)))

    def test_the_tangent_width_of_a_gaussian_is_four_sigma(self, trace: Trace) -> None:
        peak = measure(trace).peaks[0]
        assert peak.w_tangent is not None
        assert peak.w_tangent == pytest.approx(4.0 * self.SIGMA, rel=0.05)

    def test_a_symmetric_peak_is_not_tailing(self, trace: Trace) -> None:
        peak = measure(trace).peaks[0]
        assert peak.tailing is not None
        assert peak.tailing == pytest.approx(1.0, abs=0.05)

    def test_a_sloping_baseline_does_not_reach_the_area(self, trace: Trace) -> None:
        """The baseline is drawn under the peak, so drift is subtracted, not integrated."""
        drifting = _trace(trace.times, trace.signal + 0.01 * trace.times)
        flat = measure(trace).peaks[0]
        tilted = measure(drifting).peaks[0]

        assert tilted.area == pytest.approx(flat.area, rel=0.03)
        assert tilted.height == pytest.approx(flat.height, rel=0.03)
        assert tilted.t_r == pytest.approx(flat.t_r, abs=2e-3)


class TestTwoPeaks:
    def test_both_resolutions_agree_on_gaussians_and_match_the_closed_form(self) -> None:
        """The one case where the asserted Rs and the recorded USP Rs must coincide."""
        times = _times(10.0)
        sigma = 0.02
        signal = _gaussian(times, 5.0, 0.2, sigma) + _gaussian(times, 5.15, 0.15, sigma)
        rng = np.random.default_rng(2)

        result = measure(_trace(times, signal + rng.normal(0.0, 1e-5, times.size)))

        assert len(result.peaks) == 2
        expected = 0.15 / (2.0 * (sigma + sigma))
        pair = result.pairs[0]
        assert pair.rs == pytest.approx(expected, rel=0.03)
        assert pair.usp_resolution is not None
        assert pair.usp_resolution == pytest.approx(pair.rs, rel=0.03)

    def test_a_fused_pair_is_split_at_the_valley_and_keeps_the_total_area(self) -> None:
        """Peaks that never return to baseline share one baseline and one drop."""
        times = _times(10.0)
        sigma = 0.02
        first = _gaussian(times, 5.0, 0.2, sigma)
        second = _gaussian(times, 5.05, 0.2, sigma)
        rng = np.random.default_rng(3)

        result = measure(_trace(times, first + second + rng.normal(0.0, 1e-5, times.size)))

        assert len(result.peaks) == 2
        assert result.peaks[0].fused_right and result.peaks[1].fused_left
        assert result.peaks[0].cluster == result.peaks[1].cluster
        total = sum(peak.area for peak in result.peaks)
        analytic = 2.0 * 0.2 * sigma * math.sqrt(2.0 * math.pi)
        assert total == pytest.approx(analytic, rel=0.05)

    def test_a_shoulder_that_never_falls_to_half_height_mirrors_its_open_flank(self) -> None:
        times = _times(10.0)
        sigma = 0.02
        signal = _gaussian(times, 5.0, 0.30, sigma) + _gaussian(times, 5.05, 0.28, sigma)
        rng = np.random.default_rng(4)

        peaks = measure(_trace(times, signal + rng.normal(0.0, 1e-5, times.size))).peaks

        assert len(peaks) == 2
        # The valley between them never falls to half height, so the inner flank of
        # each is unmeasurable and its width comes from the flank that is open.
        assert peaks[0].w_half_basis == "leading flank"
        assert peaks[1].w_half_basis == "trailing flank"
        for peak in peaks:
            assert peak.w_half == pytest.approx(_W_HALF_PER_SIGMA * sigma, rel=0.20)


class TestWhatIsNotAPeak:
    def test_a_wobble_on_a_drifting_baseline_is_not_reported(self) -> None:
        """Late-gradient drift raises these constantly and none of them is a compound."""
        times = _times(10.0)
        drift = -0.4 * (times / times[-1]) ** 3
        rng = np.random.default_rng(5)
        signal = drift + _gaussian(times, 5.0, 0.2, 0.02) + rng.normal(0.0, 1e-5, times.size)

        peaks = measure(_trace(times, signal)).peaks

        assert [round(peak.t_r, 1) for peak in peaks] == [5.0]
        assert all(peak.area > 0.0 for peak in peaks)

    def test_noise_is_the_quietest_window_and_not_the_drift(self) -> None:
        times = _times(10.0)
        rng = np.random.default_rng(6)
        quiet = rng.normal(0.0, 1e-5, times.size)
        assert estimate_noise(quiet) == pytest.approx(1e-5, rel=0.2)
        # The same noise on a baseline that falls 0.4 AU must read the same.
        assert estimate_noise(quiet - 0.4 * times / times[-1]) == pytest.approx(1e-5, rel=0.2)

    def test_nothing_above_the_threshold_is_no_peaks_rather_than_an_error(self) -> None:
        times = _times(1.0)
        rng = np.random.default_rng(7)
        result = measure(_trace(times, rng.normal(0.0, 1e-5, times.size)))
        assert result.peaks == ()
        assert result.pairs == ()

    def test_everything_before_the_cutoff_is_ignored_when_one_is_set(self) -> None:
        times = _times(10.0)
        signal = _gaussian(times, 0.6, 0.2, 0.02) + _gaussian(times, 5.0, 0.2, 0.02)
        trace = _trace(times, signal)

        assert len(measure(trace).peaks) == 2
        assert len(measure(trace, Settings(ignore_before_min=1.5)).peaks) == 1


class TestBroadAndLow:
    """The case that a point-to-point valley test gets wrong.

    A three-peak run at 254 nm puts a real 0.1 min-wide peak of 520 nAU on 6 nAU of
    noise. Between adjacent samples such a peak falls about 1 nAU — less than the noise
    on either of them — so "the next point is higher" fires on the first noisy sample
    and cuts the peak off at its own apex, which is how a peak Empower reported at
    15.95 min came back with an area of −35 µAU·s.
    """

    def test_a_peak_that_falls_more_slowly_than_its_noise_is_still_measured(self) -> None:
        times = _times(20.0)
        sigma = 0.042
        height = 5.2e-4
        rng = np.random.default_rng(11)
        signal = _gaussian(times, 15.95, height, sigma) + rng.normal(0.0, 6e-6, times.size)

        peaks = measure(_trace(times, signal)).peaks

        assert len(peaks) == 1
        peak = peaks[0]
        assert peak.t_r == pytest.approx(15.95, abs=0.01)
        assert peak.area > 0.0
        assert peak.height == pytest.approx(height, rel=0.10)
        assert peak.w_half == pytest.approx(_W_HALF_PER_SIGMA * sigma, rel=0.10)

    def test_a_step_in_the_baseline_is_not_a_peak(self) -> None:
        """The four-peak 75 %B run ends with the gradient returning to its start.

        The trace rises 0.42 AU over about half a minute and stays there to the end of
        the run. Empower reported that step as a peak carrying 94.8 % of the run's area;
        it is the mobile phase changing, and it never comes back down.
        """
        times = _times(28.0)
        rng = np.random.default_rng(12)
        step = -0.200 + 0.422 / (1.0 + np.exp(-(times - 25.2) / 0.08))
        signal = step + _gaussian(times, 2.0, 0.3, 0.011) + rng.normal(0.0, 5.7e-5, times.size)

        peaks = measure(_trace(times, signal)).peaks

        assert [round(peak.t_r, 1) for peak in peaks] == [2.0]


class TestTailing:
    def test_an_exponentially_modified_peak_reads_above_one(self) -> None:
        """USP tailing is the measurement that tells a real peak from the Gaussian."""
        times = _times(10.0)
        sigma, tau = 0.015, 0.03
        # An EMG built by convolving the Gaussian with a decaying exponential.
        kernel_t = np.arange(0.0, 10.0 * tau, _STEP_MIN)
        kernel = np.exp(-kernel_t / tau)
        emg = np.convolve(_gaussian(times, 5.0, 0.2, sigma), kernel / kernel.sum(), mode="same")

        peak = measure(_trace(times, emg)).peaks[0]

        assert peak.tailing is not None
        assert peak.tailing > 1.2
        # A tailing peak's tangent width exceeds the Gaussian relation to its W½.
        assert peak.w_tangent is not None
        assert peak.w_tangent > 1.699 * peak.w_half


class TestSpectralFingerprints:
    """What a spectrum can and cannot settle about a peak's identity.

    The PDA baseline climbs steeply through a gradient — the mobile phase absorbs — so a
    raw apex spectrum is the compound *plus* wherever in the gradient it happened to
    elute. Subtracting the spectrum at the foot of the same peak is what makes two runs
    comparable, and it is the step that a check on the raw apex would not notice was
    missing.
    """

    def _run(self, tmp_path: Path, shapes: list[NDArray[np.float64]]) -> tuple[Path, Trace]:
        """One synthetic run: each peak given its own spectral shape, on a rising eluent."""
        times = _times(10.0)
        matrix = np.zeros((times.size, len(_AXIS)), dtype=np.float64)
        # An eluent background that climbs through the run and is not any compound.
        matrix += np.outer(0.5 * times / times[-1], np.linspace(1.0, 3.0, len(_AXIS)))
        for index, shape in enumerate(shapes):
            matrix += np.outer(_gaussian(times, 2.0 + 2.0 * index, 0.2, 0.02), shape)
        path = tmp_path / f"run{len(shapes)}.arw"
        _write_arw(path, times, matrix)
        return path, read_channel(path, 220.0)

    def test_the_eluent_background_is_subtracted_and_not_fingerprinted(
        self, tmp_path: Path
    ) -> None:
        """Two runs, same compounds, different gradient positions: same fingerprints."""
        shape = np.linspace(3.0, 1.0, len(_AXIS))
        first, trace = self._run(tmp_path, [shape])
        peaks = measure(trace).peaks
        prints = fingerprints(first, peaks, trace.times)

        assert len(prints) == 1
        assert prints[0].spectrum == pytest.approx(shape / np.linalg.norm(shape), abs=0.02)
        assert float(np.linalg.norm(prints[0].spectrum)) == pytest.approx(1.0, abs=1e-9)

    def test_a_compound_matches_itself_and_not_a_different_one(self, tmp_path: Path) -> None:
        same = np.linspace(3.0, 1.0, len(_AXIS))
        other = np.linspace(1.0, 3.0, len(_AXIS))
        path, trace = self._run(tmp_path, [same, other])
        prints = fingerprints(path, measure(trace).peaks, trace.times)

        scores = similarity_matrix(prints, prints)

        assert scores[0][0] == pytest.approx(1.0, abs=1e-9)
        assert scores[1][1] == pytest.approx(1.0, abs=1e-9)
        assert scores[0][1] < 0.95
        assert scores[0][1] == pytest.approx(scores[1][0])

    def test_axes_of_different_length_compare_on_the_shared_channels(self) -> None:
        """The exports carry 115, 148 and 309 channels of one grid; the short one wins."""
        long = Fingerprint(t_r=1.0, spectrum=np.linspace(1.0, 2.0, 309))
        short = Fingerprint(t_r=1.0, spectrum=np.linspace(1.0, 2.0, 309)[:115])

        assert similarity_matrix([long], [short])[0][0] == pytest.approx(1.0, abs=1e-9)

    def test_nothing_to_compare_is_an_empty_matrix_rather_than_an_error(self) -> None:
        one = Fingerprint(t_r=1.0, spectrum=np.ones(115))
        assert similarity_matrix([], [one]).shape == (0, 1)
        assert similarity_matrix([one], []).shape == (1, 0)

    def test_no_peaks_yields_no_fingerprints_without_reading_the_file(self) -> None:
        assert fingerprints(Path("does-not-exist.arw"), [], _times(1.0)) == ()


def test_capacity_factor_counts_the_dwell_the_gradient_had_to_travel() -> None:
    """k′ on the lab instrument: t0 = 0.525 min, V_D 0.375 mL at 0.4 mL/min."""
    assert capacity_factor(t_r=1.9, t0=0.525, t_dwell=0.9375) == pytest.approx(0.833, abs=1e-3)
    # A peak sitting exactly at the void plus the dwell is unretained.
    assert capacity_factor(t_r=1.4625, t0=0.525, t_dwell=0.9375) == pytest.approx(0.0, abs=1e-9)
