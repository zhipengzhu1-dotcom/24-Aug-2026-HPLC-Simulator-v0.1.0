"""The v0.2 gradient programme: the type, its validation, and the one-segment identity.

Ticket #69 — the expand half of an expand–contract. What is asserted here is that the
new type *is* the old one when it has a single segment (SPEC §10 item 4a, first half),
and that its validation matches SPEC §4's posture. Two or more segments predict through
the piecewise walker (#70, ``tests/test_walker.py``); only the one-segment door refuses.
"""

import math

import pytest

from hplcsim.model import (
    Gradient,
    MultiSegmentNotSupportedError,
    Programme,
    RetentionParams,
    Segment,
)
from hplcsim.resolution import resolution_table
from hplcsim.retention import gradient_end_time, predict_retention
from hplcsim.width import peak_width
from lab_data import LAB_METHOD, LAB_PEAKS
from programme_cases import FIXTURE_CASES

# A supplied N, so the identity test exercises the width path itself rather than
# whichever fixture happens to carry column geometry.
_PLATE_COUNT = 20_000.0


def test_the_fixture_sweep_covers_every_run_of_both_samples() -> None:
    """Seven three-peak runs and nine four-peak runs: a fixture added later must widen this."""
    assert len(FIXTURE_CASES) == 16
    assert sum(label.startswith("three-peak") for _, _, _, label in FIXTURE_CASES) == 7
    assert sum(label.startswith("four-peak") for _, _, _, label in FIXTURE_CASES) == 9


# --- SPEC §10 item 4a: one segment is bitwise identical to the gradient it is ---


@pytest.mark.parametrize(
    ("method", "peaks", "gradient", "label"),
    FIXTURE_CASES,
    ids=[label for _, _, _, label in FIXTURE_CASES],
)
def test_one_segment_programme_predicts_bitwise_like_its_gradient(
    method, peaks, gradient, label
) -> None:
    programme = Programme.from_gradient(gradient)
    for params in peaks:
        # Equality, not approx: a one-segment programme does not *reproduce* the v0.1
        # path, it takes it, so any difference at all would mean the conversion lied.
        assert predict_retention(params, method, programme) == predict_retention(
            params, method, gradient
        )
        assert peak_width(params, method, programme, plate_count=_PLATE_COUNT) == peak_width(
            params, method, gradient, plate_count=_PLATE_COUNT
        )


@pytest.mark.parametrize(
    ("method", "peaks", "gradient", "label"),
    FIXTURE_CASES,
    ids=[label for _, _, _, label in FIXTURE_CASES],
)
def test_one_segment_programme_resolves_bitwise_like_its_gradient(
    method, peaks, gradient, label
) -> None:
    programme = Programme.from_gradient(gradient)
    assert resolution_table(peaks, method, programme, plate_count=_PLATE_COUNT) == (
        resolution_table(peaks, method, gradient, plate_count=_PLATE_COUNT)
    )


@pytest.mark.parametrize(
    ("method", "peaks", "gradient", "label"),
    FIXTURE_CASES,
    ids=[label for _, _, _, label in FIXTURE_CASES],
)
def test_gradient_end_time_matches_for_a_one_segment_programme(
    method, peaks, gradient, label
) -> None:
    assert gradient_end_time(method, Programme.from_gradient(gradient)) == gradient_end_time(
        method, gradient
    )


# --- the conversion, which lives in exactly one place ---


@pytest.mark.parametrize(
    ("method", "peaks", "gradient", "label"),
    FIXTURE_CASES,
    ids=[label for _, _, _, label in FIXTURE_CASES],
)
def test_gradient_round_trips_through_a_programme(method, peaks, gradient, label) -> None:
    assert Programme.from_gradient(gradient).as_gradient() == gradient


def test_as_gradient_is_none_for_two_or_more_segments() -> None:
    programme = Programme(
        phi0=0.05, segments=(Segment(10.0, 0.45), Segment(10.0, 0.95)), t_init=0.5
    )
    assert programme.as_gradient() is None


# --- SPEC §4 validation posture ---


@pytest.mark.parametrize("duration", [0.0, -1.0])
def test_a_segment_duration_must_be_positive(duration: float) -> None:
    with pytest.raises(ValueError, match="duration must be positive"):
        Segment(duration=duration, phif=0.95)


def test_a_programme_needs_at_least_one_segment() -> None:
    with pytest.raises(ValueError, match="at least one segment"):
        Programme(phi0=0.05, segments=())


def test_an_initial_hold_may_not_be_negative() -> None:
    with pytest.raises(ValueError, match="t_init must be non-negative"):
        Programme(phi0=0.05, segments=(Segment(10.0, 0.95),), t_init=-0.1)


def test_a_repeated_end_composition_is_a_hold() -> None:
    programme = Programme(
        phi0=0.05, segments=(Segment(10.0, 0.55), Segment(5.0, 0.55), Segment(10.0, 0.95))
    )
    assert [leg.is_hold for leg in programme.legs()] == [False, True, False]


def test_a_flat_first_segment_is_a_hold_against_phi0() -> None:
    programme = Programme(phi0=0.05, segments=(Segment(2.0, 0.05), Segment(10.0, 0.95)))
    assert programme.legs()[0].is_hold


def test_a_descending_segment_is_allowed_and_signed() -> None:
    # Signed steepness is the walker's (#70); the type does not refuse the shape.
    programme = Programme(phi0=0.05, segments=(Segment(10.0, 0.95), Segment(5.0, 0.35)))
    assert programme.legs()[1].delta_phi == pytest.approx(-0.60)


def test_legs_chain_entry_compositions_through_the_programme() -> None:
    programme = Programme(
        phi0=0.05, segments=(Segment(10.0, 0.40), Segment(5.0, 0.40), Segment(8.0, 0.95))
    )
    assert [(leg.phi_start, leg.phi_end) for leg in programme.legs()] == [
        (0.05, 0.40),
        (0.40, 0.40),
        (0.40, 0.95),
    ]
    assert programme.phif == 0.95
    assert programme.t_gradient == pytest.approx(23.0)


# --- two or more segments predict, through the walker; only the one-segment door refuses ---


def _two_segment_programme() -> Programme:
    return Programme(phi0=0.05, segments=(Segment(10.0, 0.45), Segment(10.0, 0.95)), t_init=0.5)


@pytest.mark.parametrize(
    ("name", "call"),
    [
        ("predict_retention", lambda p, m, t: predict_retention(p, m, t)),
        ("peak_width", lambda p, m, t: peak_width(p, m, t, plate_count=_PLATE_COUNT)),
        (
            "resolution_table",
            lambda p, m, t: resolution_table([p], m, t, plate_count=_PLATE_COUNT),
        ),
    ],
)
def test_two_segments_are_predicted_not_refused(name: str, call) -> None:
    """#69's refusal was a placeholder for the walker (#70); now every path predicts."""
    call(LAB_PEAKS[0], LAB_METHOD, _two_segment_programme())


def test_two_segments_are_not_the_first_segments_answer() -> None:
    """The failure mode #69's refusal existed to prevent: a plausible, wrong number.

    Truncating a two-segment programme to its first segment predicts perfectly happily.
    The walker's answer must be a different number — the second segment is a shallower
    continuation here, so the band leaves later than the truncation says.
    """
    programme = _two_segment_programme()
    truncated = Gradient(phi0=0.05, phif=0.45, t_gradient=10.0, t_init=0.5)

    truncated_answer = predict_retention(LAB_PEAKS[0], LAB_METHOD, truncated)
    walked = predict_retention(LAB_PEAKS[0], LAB_METHOD, programme)
    assert math.isfinite(walked.t_r)
    assert walked.t_r != truncated_answer.t_r


def test_the_single_gradient_door_still_refuses_two_segments() -> None:
    """The scouting-run paths only know one segment, and say so by type."""
    from hplcsim.model import as_single_gradient

    with pytest.raises(MultiSegmentNotSupportedError) as raised:
        as_single_gradient(_two_segment_programme())
    assert "2-segment" in str(raised.value)


def test_gradient_end_time_answers_a_multi_segment_programme() -> None:
    # Where the ramp finishes is arithmetic on the programme, not the walker's job.
    programme = Programme(
        phi0=0.05, segments=(Segment(10.0, 0.45), Segment(12.5, 0.95)), t_init=0.5
    )
    assert gradient_end_time(LAB_METHOD, programme) == pytest.approx(
        LAB_METHOD.t_dwell + 0.5 + 22.5 + LAB_METHOD.t0
    )


def test_a_gradient_still_predicts_unchanged() -> None:
    """No caller of the existing two-field gradient changes (the contract half)."""
    params = RetentionParams(ln_k0=math.log(500.0), s_e=10.0, phi_ref=0.05)
    gradient = Gradient(phi0=0.05, phif=0.95, t_gradient=20.0, t_init=0.5)
    assert predict_retention(params, LAB_METHOD, gradient).regime == "gradient"


def test_the_refusal_is_the_same_class_from_either_module() -> None:
    """The re-export is a convenience, not a second type.

    ``predict_retention`` raises it, so code that catches it will reach for it on
    :mod:`hplcsim.retention`; it is defined on :mod:`hplcsim.model` with the rest of the
    Gradient/Programme correspondence (SPEC §9). Two classes with one name would make
    an ``except`` silently miss.
    """
    from hplcsim import model, retention

    assert retention.MultiSegmentNotSupportedError is model.MultiSegmentNotSupportedError
    assert retention.as_single_gradient is model.as_single_gradient
    assert retention.Target is model.Target
