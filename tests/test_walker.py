"""The piecewise walker: retention under a programme of two or more segments (#70).

Seams are SPEC §10 item 4, taken as pre-agreed: (a) a one-segment programme pushed
through the walker agrees with the closed form to 1e-12; (b) two or more segments agree
with numerical integration of the fundamental gradient equation (research doc §2.1) to
1e-10, a descending segment and a mid-programme hold included; (c) a segment that starts
after a peak has eluted changes that peak by exactly zero; (d) one reality point,
three-peak run 6's Unknown-3 under the programme it was actually run with.
"""

import math
from pathlib import Path

import pytest

from hplcsim.fit import fit_peaks
from hplcsim.model import Gradient, Method, Programme, RetentionParams, Segment, as_programme
from hplcsim.resolution import resolution_table
from hplcsim.retention import predict_retention, segment_steepness, walk_programme
from hplcsim.width import band_compression_factor, peak_width
from lab_data import (
    LAB_CAMPAIGN27_TR,
    LAB_CAMPAIGN27_WASH_ELUTED,
    LAB_CAMPAIGN27_WASH_PREREGISTERED,
    LAB_CAMPAIGN27_WASH_TR,
    LAB_METHOD,
    LAB_PEAKS,
    LAB_RUN6,
    LAB_RUN6_PROGRAMME,
)
from numerics import integrate_fundamental_equation
from programme_cases import FIXTURE_CASES
from validation2_data import (
    VALIDATION2_METHOD,
    VALIDATION2_PEAKS,
    VALIDATION2_RUN1,
    VALIDATION2_RUN2,
    VALIDATION2_RUN5,
    VALIDATION2_RUN5_PROGRAMME,
)

# --- SPEC §10 item 4(a), second half: the walker reproduces the closed form on one segment ---


@pytest.mark.parametrize(
    ("method", "peaks", "gradient", "label"),
    FIXTURE_CASES,
    ids=[label for _, _, _, label in FIXTURE_CASES],
)
def test_one_segment_walked_matches_the_closed_form(method, peaks, gradient, label) -> None:
    """Walking one segment piece by piece is the same algebra as §2.2, arranged differently.

    Not bitwise — that identity belongs to the conversion (#69). The walker forms
    1 + b·k0·(1 − x) where the closed form has b·(k0 − τ/t0) + 1, so the last bits may
    differ; 1e-12 min is the bar SPEC §10 item 4(a) sets for the walk itself.
    """
    programme = Programme.from_gradient(gradient)
    for params in peaks:
        closed_form = predict_retention(params, method, gradient)
        walked = walk_programme(params, method, programme)
        assert walked.t_r == pytest.approx(closed_form.t_r, abs=1e-12)
        assert walked.k_e == pytest.approx(closed_form.k_e, rel=1e-12)
        assert walked.regime == closed_form.regime
        assert walked.low_confidence == closed_form.low_confidence


# --- SPEC §10 item 4(b): two or more segments against the fundamental equation ---


# A ramp too fast for Unknown-3 to leave on (x ≈ 0.23 at its end), so the band is still
# on-column when the composition turns round: it leaves during the *descending* leg.
_DESCENDING = Programme(phi0=0.05, segments=(Segment(2.0, 0.95), Segment(10.0, 0.45)), t_init=0.5)
# A ramp, a hold at 45 %B, a second ramp: the three lab peaks land one in each place
# depending on how far the first ramp carries them.
_RAMP_HOLD_RAMP = Programme(
    phi0=0.05, segments=(Segment(10.0, 0.45), Segment(10.0, 0.45), Segment(10.0, 0.95)), t_init=0.5
)
_TWO_RAMPS = Programme(phi0=0.05, segments=(Segment(8.0, 0.35), Segment(20.0, 0.95)), t_init=0.5)
# Ends on a hold the band never leaves during: the post-programme branch.
_ENDS_ON_COLUMN = Programme(phi0=0.05, segments=(Segment(3.0, 0.30), Segment(2.0, 0.30)))
# A flat first segment at φ0 before the ramp: a band leaving during it has never seen a
# ramp, so it is the early-eluter's regime (§4.1), not diagnostic 9's later hold.
_FLAT_FIRST = Programme(phi0=0.05, segments=(Segment(5.0, 0.05), Segment(20.0, 0.95)), t_init=0.5)
# Survives τ (x ≈ 0.46) and leaves inside the 5 min flat leg (x would reach ≈ 2.0).
_FLAT_FIRST_PARAMS = RetentionParams(ln_k0=math.log(6.0), s_e=10.0, phi_ref=0.05)

WALKER_INTEGRATION_CASES = [
    ("descending-leg", LAB_PEAKS[2], LAB_METHOD, _DESCENDING),
    ("descending-leg-peak-1", LAB_PEAKS[0], LAB_METHOD, _DESCENDING),
    ("ramp-hold-ramp-peak-1", LAB_PEAKS[0], LAB_METHOD, _RAMP_HOLD_RAMP),
    ("ramp-hold-ramp-peak-2", LAB_PEAKS[1], LAB_METHOD, _RAMP_HOLD_RAMP),
    ("ramp-hold-ramp-peak-3", LAB_PEAKS[2], LAB_METHOD, _RAMP_HOLD_RAMP),
    ("two-ramps-peak-3", LAB_PEAKS[2], LAB_METHOD, _TWO_RAMPS),
    (
        "still-on-column-after-the-end",
        RetentionParams(ln_k0=math.log(60.0), s_e=6.0, phi_ref=0.05),
        Method(t0=1.0, t_dwell=0.5, flow=1.0),
        _ENDS_ON_COLUMN,
    ),
    (
        "elutes-in-the-initial-hold",
        RetentionParams(ln_k0=math.log(2.0), s_e=10.0, phi_ref=0.05),
        LAB_METHOD,
        _TWO_RAMPS,
    ),
    ("elutes-in-a-flat-first-segment", _FLAT_FIRST_PARAMS, LAB_METHOD, _FLAT_FIRST),
]


@pytest.mark.parametrize(
    ("params", "method", "programme"),
    [case[1:] for case in WALKER_INTEGRATION_CASES],
    ids=[case[0] for case in WALKER_INTEGRATION_CASES],
)
def test_walker_matches_numerical_integration(params, method, programme) -> None:
    expected = integrate_fundamental_equation(params, method, programme)
    assert predict_retention(params, method, programme).t_r == pytest.approx(expected, abs=1e-10)


def test_the_cases_cover_every_place_a_band_can_leave() -> None:
    """The regimes the cases above claim to exercise, so a fixture edit cannot hollow them out."""
    regimes = {
        label: predict_retention(params, method, programme).regime
        for label, params, method, programme in WALKER_INTEGRATION_CASES
    }
    assert regimes["descending-leg"] == "gradient"
    assert predict_retention(*WALKER_INTEGRATION_CASES[0][1:]).eluting_segment == 1
    assert regimes["ramp-hold-ramp-peak-1"] == "post_gradient"  # leaves in the mid hold
    assert predict_retention(*WALKER_INTEGRATION_CASES[2][1:]).eluting_segment == 1
    assert regimes["ramp-hold-ramp-peak-3"] == "gradient"  # leaves on the second ramp
    assert predict_retention(*WALKER_INTEGRATION_CASES[4][1:]).eluting_segment == 2
    assert regimes["still-on-column-after-the-end"] == "post_gradient"
    assert predict_retention(*WALKER_INTEGRATION_CASES[6][1:]).eluting_segment is None
    assert regimes["elutes-in-the-initial-hold"] == "isocratic_hold"
    assert regimes["elutes-in-a-flat-first-segment"] == "isocratic_hold"


def test_a_flat_first_segment_is_the_initial_hold_by_another_name() -> None:
    """Leaving during a flat first segment at φ0 is isocratic elution at k0, segment 0."""
    result = predict_retention(_FLAT_FIRST_PARAMS, LAB_METHOD, _FLAT_FIRST)
    assert result.regime == "isocratic_hold"
    assert result.eluting_segment == 0
    assert result.t_r == pytest.approx(LAB_METHOD.t0 * (1.0 + 6.0), abs=1e-12)


# --- #94: a flat one-segment candidate is a hold, and holds are somebody's segment ----

# What a chromatographer makes by typing the same %B into both ends of a one-segment
# candidate table. One segment never reaches the walker (`predict_retention` sends only
# two or more), so the closed form has to arrive at the walker's answer on its own.
_FLAT_INSIDE = Programme.from_gradient(Gradient(phi0=0.70, phif=0.70, t_gradient=25.0, t_init=0.5))
# The same flat candidate at a composition Unknown-3 outlives: still on-column when the
# programme ends, which is after the last leg and so no segment's.
_FLAT_OUTLIVED = Programme.from_gradient(
    Gradient(phi0=0.50, phif=0.50, t_gradient=25.0, t_init=0.5)
)


@pytest.mark.parametrize("programme", [_FLAT_INSIDE, _FLAT_OUTLIVED])
def test_a_flat_one_segment_candidate_lands_where_the_walker_lands_it(
    programme: Programme,
) -> None:
    """#94: the same physical band was given two different places by the two paths.

    Both sides of the boundary, because getting one right by always answering 0 would
    mirror the fault rather than fix it.
    """
    closed = predict_retention(LAB_PEAKS[2], LAB_METHOD, programme)
    walked = walk_programme(LAB_PEAKS[2], LAB_METHOD, programme)

    assert closed.eluting_segment == walked.eluting_segment
    assert closed.b_e_seg == walked.b_e_seg
    assert closed.k_seg_entry == walked.k_seg_entry
    assert closed.t_r == pytest.approx(walked.t_r, rel=1e-12)


def test_the_flat_candidate_has_both_of_the_walkers_answers_to_give() -> None:
    """So the agreement above cannot pass by both paths saying ``None`` every time."""
    k0 = LAB_PEAKS[2].k_at(0.70)
    inside = predict_retention(LAB_PEAKS[2], LAB_METHOD, _FLAT_INSIDE)
    assert inside.eluting_segment == 0
    assert inside.b_e_seg == 0.0  # a hold has Δφ = 0
    assert inside.k_seg_entry == pytest.approx(k0)
    # SPEC §10 item 4a: the closed form still returns v0.1's number for the flat case.
    assert inside.t_r == pytest.approx(LAB_METHOD.t0 * (1.0 + k0), abs=1e-12)

    outlived = predict_retention(LAB_PEAKS[2], LAB_METHOD, _FLAT_OUTLIVED)
    assert outlived.eluting_segment is None
    assert outlived.b_e_seg is None
    assert outlived.k_seg_entry is None


def test_the_outlived_flat_candidates_regime_still_differs_pinned_by_100() -> None:
    """#100, deliberately not fixed here: the two paths still disagree about the *regime*.

    Pinned rather than asserted equal so the divergence cannot drift unremarked, and so
    the fix, when it comes, fails this test and replaces it. Which regime is right —
    diagnostic 2's or diagnostic 9's — is a SPEC §6 ruling, not a code choice.
    """
    closed = predict_retention(LAB_PEAKS[2], LAB_METHOD, _FLAT_OUTLIVED)
    walked = walk_programme(LAB_PEAKS[2], LAB_METHOD, _FLAT_OUTLIVED)
    assert closed.regime == "isocratic_hold"
    assert walked.regime == "post_gradient"


# --- SPEC §10 item 4(c): a segment that starts after a peak has eluted is inert ---


_V2_PARAMS = {
    peak.name: fit.params
    for peak, fit in zip(
        VALIDATION2_PEAKS,
        fit_peaks(VALIDATION2_PEAKS, VALIDATION2_METHOD, VALIDATION2_RUN1, VALIDATION2_RUN2),
        strict=True,
    )
}
_LAB_PARAMS = {f"Unknown-{i}": params for i, params in enumerate(LAB_PEAKS, start=1)}
_PLATE_COUNT = 20_000.0


def _before_the_wash(programme: Programme) -> Programme:
    """The same programme cut after its first hold — before the 95 %B wash starts."""
    return Programme(phi0=programme.phi0, t_init=programme.t_init, segments=programme.segments[:2])


@pytest.mark.parametrize("name", ["Unknown-1", "Unknown-2", "Unknown-3", "Unknown-4"])
def test_four_peak_run5_is_unchanged_by_the_wash_that_follows_its_hold(name: str) -> None:
    """Every four-peak run 5 peak leaves in the 55 %B hold; the wash after it changes nothing.

    Exactly zero, so ``==`` on the whole result: the walker returns from the leg the band
    leaves in and never reads a later one, which is the property the assertion pins.
    """
    params = _V2_PARAMS[name]
    with_wash = predict_retention(params, VALIDATION2_METHOD, VALIDATION2_RUN5_PROGRAMME)
    without = predict_retention(
        params, VALIDATION2_METHOD, _before_the_wash(VALIDATION2_RUN5_PROGRAMME)
    )
    assert with_wash == without
    assert with_wash.regime == "post_gradient"
    assert with_wash.eluting_segment == 1
    # And the number the reality layer already pins for this run — v0.1's single ramp
    # with its post-gradient branch — is the same number to 1e-12 (not bitwise: the hold
    # is a leg here and an isocratic tail there).
    single_ramp = predict_retention(params, VALIDATION2_METHOD, VALIDATION2_RUN5.gradient)
    assert with_wash.t_r == pytest.approx(single_ramp.t_r, abs=1e-12)


@pytest.mark.parametrize("name", ["Unknown-1", "Unknown-2"])
def test_three_peak_run6_ramp_peaks_are_unchanged_by_the_wash(name: str) -> None:
    params = _LAB_PARAMS[name]
    with_wash = predict_retention(params, LAB_METHOD, LAB_RUN6_PROGRAMME)
    assert with_wash == predict_retention(params, LAB_METHOD, _before_the_wash(LAB_RUN6_PROGRAMME))
    assert with_wash.regime == "gradient"
    assert with_wash.eluting_segment == 0
    # These two are scored against the single-segment engine in the reality layer; the
    # programme must give that engine's number back, bitwise, because it *is* that path
    # up to the moment the band leaves.
    assert with_wash == predict_retention(params, LAB_METHOD, LAB_RUN6.gradient)


# --- SPEC §10 item 4(d): the one multi-segment reality point ---

# Computed by the walker at t0 = 0.525 on 2026-09-04 and pinned as a tripwire. The
# measured 46.8 is the driver's chromatogram reading; the pre-registered 47.0 was walked
# by hand before it. +0.32 min, +0.69 %: inside the coarse bar, and the first two-segment
# number this engine has ever been scored on. One peak, one sample — the whole of what
# multi-segment rests on (SPEC §10 item 4(d)); no Rs claim follows from it.
_RUN6_UNKNOWN3_WALKED = 47.122
_COARSE_BAR_MEAN = 0.02
_COARSE_BAR_WORST = 0.05  # one peak, so the mean is the worst; both halves written anyway


def test_run6_unknown3_walks_off_in_the_wash_inside_the_coarse_bar() -> None:
    key = ("run6", "Unknown-3")
    assert key in LAB_CAMPAIGN27_WASH_ELUTED
    assert "Unknown-3" not in LAB_CAMPAIGN27_TR["run6"]  # never scored single-segment

    result = predict_retention(_LAB_PARAMS["Unknown-3"], LAB_METHOD, LAB_RUN6_PROGRAMME)
    measured = LAB_CAMPAIGN27_WASH_TR[key]

    assert result.regime == "post_gradient"  # left in the 95 %B hold: diagnostic 9's flag
    assert result.eluting_segment == 3
    assert abs(result.t_r - measured) / measured <= _COARSE_BAR_MEAN
    assert abs(result.t_r - measured) / measured <= _COARSE_BAR_WORST
    assert result.t_r == pytest.approx(_RUN6_UNKNOWN3_WALKED, abs=0.0005)
    # The pre-registered hand walk landed on the same side of the measurement and closer;
    # recorded, not asserted as a bound on the walker.
    assert LAB_CAMPAIGN27_WASH_PREREGISTERED[key] > measured


def test_run6_unknown3_never_leaves_the_55_percent_hold_without_the_wash() -> None:
    """What v0.1 said, and still says: in the hold alone it would take ~105 min."""
    without_wash = predict_retention(
        _LAB_PARAMS["Unknown-3"], LAB_METHOD, _before_the_wash(LAB_RUN6_PROGRAMME)
    )
    assert without_wash.regime == "post_gradient"
    assert without_wash.eluting_segment is None
    assert without_wash.t_r > 100.0


# --- the programme fixtures are the CSV tables, re-read ---

_VALIDATION_DIR = Path(__file__).resolve().parent.parent / "validation"


def _programme_from_csv(path: Path) -> Programme:
    """The `#, Time, Flow, %A, %B` table as a programme: a flat first pair is the hold."""
    rows = [
        line.strip().split(",")
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip(", ")
    ]
    table = [(float(r[1]), float(r[4]) / 100.0) for r in rows if r[0].isdigit()]
    (t_first, phi0), (t_second, phi_second) = table[0], table[1]
    assert t_first == 0.0
    t_init = t_second - t_first if phi_second == phi0 else 0.0
    start = 1 if t_init else 0
    segments = tuple(
        Segment(duration=table[i + 1][0] - table[i][0], phif=table[i + 1][1])
        for i in range(start, len(table) - 1)
    )
    return Programme(phi0=phi0, t_init=t_init, segments=segments)


@pytest.mark.parametrize(
    ("path", "fixture"),
    [
        (_VALIDATION_DIR / "run6.csv", LAB_RUN6_PROGRAMME),
        (_VALIDATION_DIR / "Validation_2" / "4peaks_run5.csv", VALIDATION2_RUN5_PROGRAMME),
    ],
    ids=["three-peak-run6", "four-peak-run5"],
)
def test_programme_fixtures_match_the_source_csvs(path: Path, fixture: Programme) -> None:
    from_csv = _programme_from_csv(path)
    assert from_csv.phi0 == fixture.phi0
    assert from_csv.t_init == fixture.t_init
    assert [s.phif for s in from_csv.segments] == pytest.approx([s.phif for s in fixture.segments])
    assert [s.duration for s in from_csv.segments] == pytest.approx(
        [s.duration for s in fixture.segments], abs=1e-9
    )


# --- band compression for a programme (SPEC §3): G from the eluting segment ---


def test_g_comes_from_the_segment_the_band_leaves_on() -> None:
    """Unknown-3 leaves _RAMP_HOLD_RAMP on its third leg (45 → 95 %B over 10 min).

    SPEC §3's rule, written out from the research doc's symbols rather than read back
    from the engine: p = b_e,seg·k/(1 + k) with b_e,seg = t0·Δφ_seg·S_e/duration and k
    the retention factor where the band *enters* that leg, 45 %B.
    """
    params = LAB_PEAKS[2]
    width = peak_width(params, LAB_METHOD, _RAMP_HOLD_RAMP, plate_count=_PLATE_COUNT)
    assert predict_retention(params, LAB_METHOD, _RAMP_HOLD_RAMP).eluting_segment == 2

    b_seg = LAB_METHOD.t0 * (0.95 - 0.45) * params.s_e / 10.0
    k_entry = params.k_at(0.45)
    p = b_seg * k_entry / (1.0 + k_entry)
    assert width.g == pytest.approx(math.sqrt(1.0 + p + p * p / 3.0) / (1.0 + p))
    assert width.g == pytest.approx(band_compression_factor(b_seg, k0=k_entry))
    assert width.g < 1.0


def test_no_compression_for_a_band_leaving_in_a_later_hold_or_after_the_end() -> None:
    in_the_hold = peak_width(LAB_PEAKS[0], LAB_METHOD, _RAMP_HOLD_RAMP, plate_count=_PLATE_COUNT)
    assert predict_retention(LAB_PEAKS[0], LAB_METHOD, _RAMP_HOLD_RAMP).regime == "post_gradient"
    assert in_the_hold.g == 1.0

    wash = peak_width(
        _LAB_PARAMS["Unknown-3"], LAB_METHOD, LAB_RUN6_PROGRAMME, plate_count=_PLATE_COUNT
    )
    assert wash.g == 1.0
    assert wash.k_e == pytest.approx(1.5725, abs=5e-4)


def test_no_compression_claimed_for_a_band_leaving_on_a_descending_leg() -> None:
    """Poppe's G is derived for a rising composition; on a falling one it is not claimed."""
    width = peak_width(LAB_PEAKS[2], LAB_METHOD, _DESCENDING, plate_count=_PLATE_COUNT)
    assert predict_retention(LAB_PEAKS[2], LAB_METHOD, _DESCENDING).eluting_segment == 1
    assert width.g == 1.0


def test_the_carried_leg_agrees_with_the_legs_list() -> None:
    """The carried trio describes the leg the index names, exactly (#89).

    ``b_e_seg`` and ``k_seg_entry`` are values the walker already held, carried out
    rather than rebuilt, so equality here is exact and not ``approx``.
    """
    for _label, params, method, target in WALKER_INTEGRATION_CASES:
        result = predict_retention(params, method, target)
        if result.eluting_segment is None:
            assert result.b_e_seg is None
            assert result.k_seg_entry is None
            continue
        leg = as_programme(target).legs()[result.eluting_segment]
        assert result.b_e_seg == segment_steepness(method, leg, params.s_e)
        assert result.k_seg_entry == params.k_at(leg.phi_start)


def test_the_closed_form_carries_the_same_trio_as_its_one_leg() -> None:
    """SPEC §10 item 4a, for the carried trio: the v0.1 gradient path agrees with legs()[0].

    The closed form passes ``b_e`` and ``k0`` rather than reading a leg, on the argument
    that for one segment ``legs()[0].phi_start`` *is* ``phi0``. That argument is what
    keeps the bitwise identity, so it is pinned here rather than left to inspection.
    """
    params = LAB_PEAKS[2]
    ascending = Gradient(phi0=0.05, phif=0.95, t_gradient=20.0, t_init=0.5)
    descending = Gradient(phi0=0.95, phif=0.45, t_gradient=20.0, t_init=0.5)
    for gradient in (ascending, descending):
        result = predict_retention(params, LAB_METHOD, gradient)
        if result.eluting_segment is None:
            assert result.b_e_seg is None
            assert result.k_seg_entry is None
            continue
        leg = as_programme(gradient).legs()[result.eluting_segment]
        assert result.b_e_seg == segment_steepness(LAB_METHOD, leg, params.s_e)
        assert result.k_seg_entry == params.k_at(leg.phi_start)


def test_a_programme_resolves_through_the_same_table_as_a_gradient() -> None:
    table = resolution_table(LAB_PEAKS, LAB_METHOD, LAB_RUN6_PROGRAMME, plate_count=_PLATE_COUNT)
    assert [peak.retention.t_r for peak in table.peaks] == sorted(
        peak.retention.t_r for peak in table.peaks
    )
    assert len(table.pairs) == 2
    assert table.peaks[-1].retention.regime == "post_gradient"
