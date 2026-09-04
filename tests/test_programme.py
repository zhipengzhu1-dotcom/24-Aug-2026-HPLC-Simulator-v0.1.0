"""The v0.2 gradient programme (SPEC §3, §4; ticket #69).

The expand step of an expand–contract: :class:`~hplcsim.model.Programme` lands beside
:class:`~hplcsim.model.Gradient`, the scouting runs and the two-run fit are untouched,
and a one-segment programme *is* a v0.1 candidate — bitwise, not approximately, which is
the half of SPEC §10 item 4(a) this ticket owns. Two or more segments are accepted by the
type and refused by prediction until the walker of #70 lands.
"""

from __future__ import annotations

import pytest

from den_uijl_data import SET_X, SET_Y, ScanningGradientSet
from hplcsim.fit import fit_peaks
from hplcsim.model import (
    Gradient,
    Method,
    MultiSegmentProgrammeError,
    Programme,
    RetentionParams,
    Run,
    Segment,
    gradient_from_programme,
    programme_from_gradient,
)
from hplcsim.retention import (
    RetentionResult,
    gradient_steepness,
    predict_retention,
    predict_retention_programme,
    segment_steepness,
)
from hplcsim.width import (
    PeakWidth,
    band_compression_factor,
    peak_width,
    peak_width_programme,
    programme_band_compression_factor,
)
from lab_data import (
    LAB_METHOD,
    LAB_PEAKS,
    LAB_RUN1,
    LAB_RUN2,
    LAB_RUN3,
    LAB_RUN4,
    LAB_RUN5,
    LAB_RUN6,
    LAB_RUN7,
)
from validation2_data import (
    VALIDATION2_METHOD,
    VALIDATION2_PEAKS,
    VALIDATION2_RUN1,
    VALIDATION2_RUN2,
    VALIDATION2_RUNS_BY_NAME,
)

# A supplied N, so the sweep can include the den Uijl methods — they carry no column
# geometry, and the width's plate count is not what these tests are about.
_SUPPLIED_N = 10000.0


class TestSegmentAndProgramme:
    """SPEC §3: φ0, an initial hold, and an ordered list of duration/end-composition legs."""

    def test_a_segment_carries_a_duration_and_an_end_composition(self) -> None:
        programme = Programme(phi0=0.05, segments=(Segment(duration=15.0, phi_end=0.95),))
        assert programme.segments[0].duration == 15.0
        assert programme.segments[0].phi_end == 0.95
        assert programme.t_init == 0.0

    def test_a_segment_entry_composition_is_the_previous_end(self) -> None:
        programme = Programme(
            phi0=0.05,
            segments=(
                Segment(duration=10.0, phi_end=0.50),
                Segment(duration=5.0, phi_end=0.50),
                Segment(duration=8.0, phi_end=0.95),
            ),
        )
        assert programme.phi_at_entry(0) == 0.05
        assert programme.phi_at_entry(1) == 0.50
        assert programme.phi_at_entry(2) == 0.50
        assert programme.delta_phi(0) == pytest.approx(0.45)
        assert programme.delta_phi(2) == pytest.approx(0.45)

    def test_a_repeated_end_composition_is_a_hold(self) -> None:
        programme = Programme(
            phi0=0.05,
            segments=(Segment(duration=10.0, phi_end=0.50), Segment(duration=5.0, phi_end=0.50)),
        )
        assert not programme.is_hold(0)
        assert programme.is_hold(1)
        assert programme.delta_phi(1) == 0.0

    def test_a_first_segment_flat_at_phi0_is_a_hold(self) -> None:
        programme = Programme(phi0=0.30, segments=(Segment(duration=4.0, phi_end=0.30),))
        assert programme.is_hold(0)

    def test_a_descending_segment_is_allowed(self) -> None:
        programme = Programme(
            phi0=0.05,
            segments=(Segment(duration=10.0, phi_end=0.90), Segment(duration=3.0, phi_end=0.40)),
        )
        assert programme.delta_phi(1) == pytest.approx(-0.50)
        assert not programme.is_hold(1)

    @pytest.mark.parametrize("duration", [0.0, -1.0])
    def test_every_segment_duration_must_be_positive(self, duration: float) -> None:
        with pytest.raises(ValueError, match="segment duration must be positive"):
            Programme(
                phi0=0.05,
                segments=(
                    Segment(duration=10.0, phi_end=0.50),
                    Segment(duration=duration, phi_end=0.95),
                ),
            )

    def test_the_failing_segment_is_named(self) -> None:
        with pytest.raises(ValueError, match="segment 2"):
            Programme(
                phi0=0.05,
                segments=(
                    Segment(duration=10.0, phi_end=0.50),
                    Segment(duration=0.0, phi_end=0.95),
                ),
            )

    def test_a_programme_needs_at_least_one_segment(self) -> None:
        with pytest.raises(ValueError, match="at least one segment"):
            Programme(phi0=0.05, segments=())

    def test_the_initial_hold_may_not_be_negative(self) -> None:
        with pytest.raises(ValueError, match="initial hold"):
            Programme(phi0=0.05, segments=(Segment(duration=10.0, phi_end=0.95),), t_init=-0.5)


class TestGradientConversion:
    """The one place a one-segment programme and a v0.1 gradient become each other."""

    def test_a_gradient_becomes_its_one_segment_programme(self) -> None:
        gradient = Gradient(phi0=0.05, phif=0.95, t_gradient=15.0, t_init=0.5)
        programme = programme_from_gradient(gradient)
        assert programme == Programme(
            phi0=0.05, segments=(Segment(duration=15.0, phi_end=0.95),), t_init=0.5
        )

    def test_the_round_trip_is_exact(self) -> None:
        gradient = Gradient(phi0=0.15, phif=0.55, t_gradient=22.2, t_init=0.5)
        recovered = gradient_from_programme(programme_from_gradient(gradient))
        assert recovered == gradient
        assert recovered.phi0 == gradient.phi0
        assert recovered.phif == gradient.phif
        assert recovered.t_gradient == gradient.t_gradient
        assert recovered.t_init == gradient.t_init

    def test_two_segments_cannot_become_a_gradient(self) -> None:
        programme = Programme(
            phi0=0.05,
            segments=(Segment(duration=10.0, phi_end=0.50), Segment(duration=5.0, phi_end=0.95)),
        )
        with pytest.raises(MultiSegmentProgrammeError):
            gradient_from_programme(programme)


class TestMultiSegmentRefusal:
    """SPEC §3: the walker is entered only for ≥ 2 segments — and it does not exist yet."""

    _TWO_SEGMENTS = Programme(
        phi0=0.05,
        segments=(Segment(duration=10.0, phi_end=0.50), Segment(duration=5.0, phi_end=0.95)),
    )

    def test_prediction_refuses_two_segments(self) -> None:
        with pytest.raises(MultiSegmentProgrammeError) as excinfo:
            predict_retention_programme(LAB_PEAKS[0], LAB_METHOD, self._TWO_SEGMENTS)
        assert "#70" in str(excinfo.value)
        assert "2 segments" in str(excinfo.value)

    def test_the_refusal_is_a_not_implemented_error(self) -> None:
        # Typed as "not yet", not as "bad input": the programme is valid, the engine is
        # incomplete. Callers that catch NotImplementedError see it without importing us.
        assert issubclass(MultiSegmentProgrammeError, NotImplementedError)

    def test_width_refuses_two_segments_too(self) -> None:
        with pytest.raises(MultiSegmentProgrammeError):
            peak_width_programme(
                LAB_PEAKS[0], LAB_METHOD, self._TWO_SEGMENTS, plate_count=_SUPPLIED_N
            )

    def test_a_three_segment_programme_names_its_count(self) -> None:
        programme = Programme(
            phi0=0.05,
            segments=(
                Segment(duration=10.0, phi_end=0.50),
                Segment(duration=5.0, phi_end=0.50),
                Segment(duration=5.0, phi_end=0.95),
            ),
        )
        with pytest.raises(MultiSegmentProgrammeError, match="3 segments"):
            predict_retention_programme(LAB_PEAKS[0], LAB_METHOD, programme)


class TestSegmentSteepness:
    """b_e for one segment — signed, and the same expression the v0.1 gradient uses."""

    def test_one_segment_matches_the_gradient_steepness_bitwise(self) -> None:
        gradient = LAB_RUN1.gradient
        programme = programme_from_gradient(gradient)
        s_e = LAB_PEAKS[0].s_e
        assert segment_steepness(LAB_METHOD, programme, 0, s_e) == gradient_steepness(
            LAB_METHOD, gradient, s_e
        )

    def test_a_descending_segment_has_a_negative_steepness(self) -> None:
        programme = Programme(
            phi0=0.05,
            segments=(Segment(duration=10.0, phi_end=0.90), Segment(duration=3.0, phi_end=0.40)),
        )
        assert segment_steepness(LAB_METHOD, programme, 1, LAB_PEAKS[0].s_e) < 0.0

    def test_a_hold_has_zero_steepness(self) -> None:
        programme = Programme(
            phi0=0.05,
            segments=(Segment(duration=10.0, phi_end=0.50), Segment(duration=5.0, phi_end=0.50)),
        )
        assert segment_steepness(LAB_METHOD, programme, 1, LAB_PEAKS[0].s_e) == 0.0


class TestProgrammeBandCompression:
    """SPEC §3 "Band compression for a programme": the rule #70 fills in, declared here."""

    _PROGRAMME = Programme(
        phi0=0.05,
        segments=(
            Segment(duration=10.0, phi_end=0.50),
            Segment(duration=5.0, phi_end=0.50),
            Segment(duration=8.0, phi_end=0.95),
        ),
        t_init=0.5,
    )

    def test_g_comes_from_the_segment_the_band_elutes_in(self) -> None:
        s_e = LAB_PEAKS[0].s_e
        k_entry = 42.0
        for index in (0, 2):
            b_e_seg = segment_steepness(LAB_METHOD, self._PROGRAMME, index, s_e)
            assert programme_band_compression_factor(
                LAB_METHOD, self._PROGRAMME, s_e, eluting_segment=index, k_entry=k_entry
            ) == band_compression_factor(b_e_seg, k_entry)

    def test_a_descending_segment_is_refused_rather_than_guessed(self) -> None:
        # The type allows a descending segment; G(p) was derived for a *rising* one, so
        # the rule declines rather than inventing a dilation factor (#70's question).
        programme = Programme(
            phi0=0.05,
            segments=(Segment(duration=10.0, phi_end=0.90), Segment(duration=3.0, phi_end=0.40)),
        )
        with pytest.raises(ValueError, match="b_e must be non-negative"):
            programme_band_compression_factor(
                LAB_METHOD, programme, LAB_PEAKS[0].s_e, eluting_segment=1, k_entry=42.0
            )

    def test_a_band_leaving_in_a_hold_is_not_compressed(self) -> None:
        assert (
            programme_band_compression_factor(
                LAB_METHOD, self._PROGRAMME, LAB_PEAKS[0].s_e, eluting_segment=1, k_entry=42.0
            )
            == 1.0
        )

    def test_a_band_leaving_outside_every_segment_is_not_compressed(self) -> None:
        # None is both edges of the programme: the pre-gradient hold (§4.1) and after the
        # last segment ends (§4.2). v0.1 already sets G = 1 for both.
        assert (
            programme_band_compression_factor(
                LAB_METHOD, self._PROGRAMME, LAB_PEAKS[0].s_e, eluting_segment=None, k_entry=42.0
            )
            == 1.0
        )

    @pytest.mark.parametrize(
        "run", [LAB_RUN1, LAB_RUN2, LAB_RUN3, LAB_RUN4, LAB_RUN5, LAB_RUN6, LAB_RUN7]
    )
    def test_for_one_segment_the_rule_reproduces_what_the_width_applied(self, run: Run) -> None:
        # The declared rule, evaluated on the segment v0.1's regime branch says the band
        # left in, must be the G the v0.1 width actually used — bitwise, on every peak.
        for params in LAB_PEAKS:
            programme = programme_from_gradient(run.gradient)
            regime = predict_retention(params, LAB_METHOD, run.gradient).regime
            eluting_segment = 0 if regime == "gradient" else None
            declared = programme_band_compression_factor(
                LAB_METHOD,
                programme,
                params.s_e,
                eluting_segment=eluting_segment,
                k_entry=params.k_at(programme.phi_at_entry(0)),
            )
            applied = peak_width(params, LAB_METHOD, run.gradient, plate_count=_SUPPLIED_N).g
            assert declared == applied


# --- SPEC §10 item 4(a), first half: one segment is bitwise v0.1 ---------------------


_Case = tuple[str, RetentionParams, Method, Gradient]


def _den_uijl_cases(dataset: ScanningGradientSet) -> list[_Case]:
    """Every published gradient time of a den Uijl set, with params fitted from its ends."""
    steep, shallow = dataset.gradient_times[0], dataset.gradient_times[-1]
    peaks = [dataset.peak(compound, steep, shallow) for compound in dataset.fittable]
    fits = fit_peaks(peaks, dataset.method, dataset.run(steep), dataset.run(shallow))
    return [
        (
            f"{dataset.name}-{peak.name}-tG{t_gradient:g}",
            fit.params,
            dataset.method,
            dataset.run(t_gradient).gradient,
        )
        for peak, fit in zip(peaks, fits, strict=True)
        for t_gradient in dataset.gradient_times
    ]


def _bitwise_cases() -> list[_Case]:
    """Every fixture on both bench samples plus both den Uijl sets."""
    cases: list[_Case] = [
        (f"lab-peak{index + 1}-{run.name}", params, LAB_METHOD, run.gradient)
        for index, params in enumerate(LAB_PEAKS)
        for run in (LAB_RUN1, LAB_RUN2, LAB_RUN3, LAB_RUN4, LAB_RUN5, LAB_RUN6, LAB_RUN7)
    ]
    v2_fits = fit_peaks(VALIDATION2_PEAKS, VALIDATION2_METHOD, VALIDATION2_RUN1, VALIDATION2_RUN2)
    cases += [
        (f"4peaks-{peak.name}-{name}", fit.params, VALIDATION2_METHOD, run.gradient)
        for peak, fit in zip(VALIDATION2_PEAKS, v2_fits, strict=True)
        for name, run in VALIDATION2_RUNS_BY_NAME.items()
    ]
    cases += _den_uijl_cases(SET_X)
    cases += _den_uijl_cases(SET_Y)
    return cases


_BITWISE_CASES = _bitwise_cases()


@pytest.mark.parametrize(
    ("params", "method", "gradient"),
    [case[1:] for case in _BITWISE_CASES],
    ids=[case[0] for case in _BITWISE_CASES],
)
def test_one_segment_retention_is_bitwise_identical(
    params: RetentionParams, method: Method, gradient: Gradient
) -> None:
    from_gradient = predict_retention(params, method, gradient)
    from_programme = predict_retention_programme(params, method, programme_from_gradient(gradient))
    assert isinstance(from_programme, RetentionResult)
    assert from_programme.t_r == from_gradient.t_r
    assert from_programme.k_e == from_gradient.k_e
    assert from_programme.regime == from_gradient.regime
    assert from_programme.low_confidence == from_gradient.low_confidence


@pytest.mark.parametrize(
    ("params", "method", "gradient"),
    [case[1:] for case in _BITWISE_CASES],
    ids=[case[0] for case in _BITWISE_CASES],
)
def test_one_segment_width_is_bitwise_identical(
    params: RetentionParams, method: Method, gradient: Gradient
) -> None:
    from_gradient = peak_width(params, method, gradient, plate_count=_SUPPLIED_N)
    from_programme = peak_width_programme(
        params, method, programme_from_gradient(gradient), plate_count=_SUPPLIED_N
    )
    assert isinstance(from_programme, PeakWidth)
    assert from_programme.sigma == from_gradient.sigma
    assert from_programme.w_half == from_gradient.w_half
    assert from_programme.w_base == from_gradient.w_base
    assert from_programme.g == from_gradient.g
    assert from_programme.k_e == from_gradient.k_e
    assert from_programme.plate_count == from_gradient.plate_count
    assert from_programme.plate_count_source == from_gradient.plate_count_source


def test_the_bitwise_sweep_covers_every_fixture_run_on_both_samples() -> None:
    # A guard on the sweep itself: if a fixture run is added and not swept, the bitwise
    # claim quietly narrows. 3 lab peaks × 7 runs, 4 peaks × 9 runs, plus the two
    # den Uijl sets (their fittable compounds × their published gradient times).
    expected = (
        3 * 7
        + len(VALIDATION2_PEAKS) * len(VALIDATION2_RUNS_BY_NAME)
        + len(SET_X.fittable) * len(SET_X.gradient_times)
        + len(SET_Y.fittable) * len(SET_Y.gradient_times)
    )
    assert len(_BITWISE_CASES) == expected


def test_the_scouting_runs_still_take_a_gradient() -> None:
    # The expand step's contract: nothing about Run or the two-run fit moved (SPEC §4,
    # "Scouting gradient … Unchanged in v0.2"; #46 decision 9).
    fits = fit_peaks(VALIDATION2_PEAKS, VALIDATION2_METHOD, VALIDATION2_RUN1, VALIDATION2_RUN2)
    assert isinstance(VALIDATION2_RUN1.gradient, Gradient)
    assert len(fits) == len(VALIDATION2_PEAKS)
