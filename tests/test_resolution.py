"""Adjacent-pair resolution and the critical pair (SPEC §3; research doc §6)."""

from __future__ import annotations

import math

import pytest

from hplcsim.model import (
    Gradient,
    Method,
    RetentionParams,
    ln_k0_from_log10_k0,
    s_e_from_s_base10,
)
from hplcsim.resolution import resolution_table
from hplcsim.width import FittedPlateCount

METHOD = Method(t0=0.6, t_dwell=0.9375, flow=0.4, column_length_mm=100.0, particle_um=1.6)


def _gradient(t_gradient: float) -> Gradient:
    return Gradient(phi0=0.05, phif=0.95, t_gradient=t_gradient, t_init=0.5)


def _peak(log10_k0: float, s: float) -> RetentionParams:
    """A peak quoted the way a chromatographer reads it, converted at the boundary."""
    return RetentionParams(
        ln_k0=ln_k0_from_log10_k0(log10_k0), s_e=s_e_from_s_base10(s), phi_ref=0.05
    )


# A pair whose elution order reverses between a steep and a shallow gradient
# (research doc §7.4): at tG = 5 they nearly coelute with SLOW first, at tG = 60
# they are baseline-separated with FAST first.
FAST = _peak(log10_k0=2.5, s=4.0)
SLOW = _peak(log10_k0=3.5, s=6.0)

THREE_PEAKS = [_peak(2.76, 5.08), _peak(3.24, 4.99), _peak(4.76, 5.18)]


class TestResolutionFormula:
    """§6: Rs = Δt/(2(σ1+σ2)) = 2Δt/(W1+W2) = √(8 ln 2)/2 · Δt/(W½1+W½2)."""

    def test_matches_the_three_equivalent_published_forms(self) -> None:
        table = resolution_table(THREE_PEAKS, METHOD, _gradient(20.0))

        for pair in table.pairs:
            delta_t = pair.later.retention.t_r - pair.earlier.retention.t_r
            sigma_form = delta_t / (2.0 * (pair.earlier.width.sigma + pair.later.width.sigma))
            base_form = 2.0 * delta_t / (pair.earlier.width.w_base + pair.later.width.w_base)
            half_form = (
                math.sqrt(8.0 * math.log(2.0))
                / 2.0
                * delta_t
                / (pair.earlier.width.w_half + pair.later.width.w_half)
            )
            assert pair.rs == pytest.approx(sigma_form, rel=1e-12)
            assert pair.rs == pytest.approx(base_form, rel=1e-12)
            assert pair.rs == pytest.approx(half_form, rel=1e-12)

    def test_uses_the_exact_gaussian_constant_not_the_rounded_1178(self) -> None:
        # §6: "Use the exact constant, not 1.178 — the rounded value costs ~0.04% on
        # every Rs." Asserted as a real difference so the exactness cannot rot.
        table = resolution_table(THREE_PEAKS, METHOD, _gradient(20.0))
        pair = table.pairs[0]
        delta_t = pair.later.retention.t_r - pair.earlier.retention.t_r
        half_widths = pair.earlier.width.w_half + pair.later.width.w_half

        rounded = 1.178 * delta_t / half_widths

        assert pair.rs != pytest.approx(rounded, rel=1e-5)
        assert pair.rs == pytest.approx(rounded, rel=1e-3)

    def test_coeluting_peaks_are_unresolved(self) -> None:
        table = resolution_table([THREE_PEAKS[0], THREE_PEAKS[0]], METHOD, _gradient(20.0))

        assert table.pairs[0].rs == 0.0
        assert table.critical_pair is not None
        assert table.critical_pair.rs == 0.0


class TestTableShape:
    def test_n_peaks_give_n_minus_one_adjacent_pairs(self) -> None:
        table = resolution_table(THREE_PEAKS, METHOD, _gradient(20.0))

        assert len(table.peaks) == 3
        assert len(table.pairs) == 2

    def test_a_lone_peak_has_no_pair_to_resolve_against(self) -> None:
        table = resolution_table([THREE_PEAKS[0]], METHOD, _gradient(20.0))

        assert table.pairs == ()
        assert table.critical_pair is None

    def test_no_peaks_is_an_empty_table(self) -> None:
        table = resolution_table([], METHOD, _gradient(20.0))

        assert table.peaks == ()
        assert table.pairs == ()
        assert table.critical_pair is None

    def test_peaks_are_named_p1_through_pn_by_default(self) -> None:
        # SPEC §5: "one row per compound ... name (auto P1…Pn)".
        table = resolution_table(THREE_PEAKS, METHOD, _gradient(20.0))

        assert [peak.name for peak in table.peaks] == ["P1", "P2", "P3"]

    def test_supplied_names_travel_with_their_peak_through_the_sort(self) -> None:
        table = resolution_table(
            [SLOW, FAST], METHOD, _gradient(60.0), names=["late-at-60", "early-at-60"]
        )

        assert [peak.name for peak in table.peaks] == ["early-at-60", "late-at-60"]

    def test_a_name_per_peak_is_required_when_names_are_supplied(self) -> None:
        with pytest.raises(ValueError, match="one name per peak"):
            resolution_table(THREE_PEAKS, METHOD, _gradient(20.0), names=["only-one"])


class TestElutionOrder:
    def test_peaks_come_back_sorted_by_predicted_retention(self) -> None:
        table = resolution_table(list(reversed(THREE_PEAKS)), METHOD, _gradient(20.0))

        times = [peak.retention.t_r for peak in table.peaks]
        assert times == sorted(times)

    def test_order_is_recomputed_at_every_condition(self) -> None:
        # §7.4: elution order is a property of the condition, not of the input list.
        # The same two peaks pair up in opposite directions at the two gradient times.
        steep = resolution_table([FAST, SLOW], METHOD, _gradient(5.0), names=["fast", "slow"])
        shallow = resolution_table([FAST, SLOW], METHOD, _gradient(60.0), names=["fast", "slow"])

        assert [peak.name for peak in steep.peaks] == ["slow", "fast"]
        assert [peak.name for peak in shallow.peaks] == ["fast", "slow"]

    def test_pairs_are_adjacent_in_elution_order(self) -> None:
        table = resolution_table(THREE_PEAKS, METHOD, _gradient(20.0))

        assert [(pair.earlier.name, pair.later.name) for pair in table.pairs] == [
            ("P1", "P2"),
            ("P2", "P3"),
        ]


class TestCriticalPair:
    def test_critical_pair_is_the_worst_resolved_adjacent_pair(self) -> None:
        table = resolution_table(THREE_PEAKS, METHOD, _gradient(20.0))

        assert table.critical_pair is not None
        assert table.critical_pair.rs == min(pair.rs for pair in table.pairs)

    def test_a_near_coelution_becomes_the_critical_pair(self) -> None:
        # At tG = 5 the crossing pair is almost on top of each other; a well-spaced
        # third peak must not be able to take the critical slot from them.
        table = resolution_table(
            [FAST, SLOW, _peak(4.76, 5.18)], METHOD, _gradient(5.0), names=["fast", "slow", "far"]
        )

        assert table.critical_pair is not None
        assert {table.critical_pair.earlier.name, table.critical_pair.later.name} == {
            "fast",
            "slow",
        }
        # And it dominates the metric: the far peak's pair is an order of magnitude
        # better resolved, which is the whole point of reporting a critical pair
        # rather than an average.
        other = next(pair for pair in table.pairs if pair is not table.critical_pair)
        assert other.rs > 10.0 * table.critical_pair.rs


def _fitted(plate_count: float) -> FittedPlateCount:
    return FittedPlateCount(
        plate_count=plate_count,
        implied_run1=plate_count,
        implied_run2=plate_count,
        low_confidence=False,
    )


class TestPlateCountPrecedence:
    """Measured-first: a peak's fitted N, else the global knob, else the column default.

    The same ordering SPEC §4 gives t0 (marker time primary, geometry estimate as a
    labelled fallback), extended to N by ticket #23.
    """

    def test_a_fitted_plate_count_overrides_the_global_knob_for_its_peak_only(self) -> None:
        table = resolution_table(
            THREE_PEAKS,
            METHOD,
            _gradient(20.0),
            plate_count=20000.0,
            plate_counts=[_fitted(12000.0), None, None],
        )

        assert [peak.width.plate_count for peak in table.peaks] == [12000.0, 20000.0, 20000.0]
        assert [peak.width.plate_count_source for peak in table.peaks] == [
            "fitted",
            "supplied",
            "supplied",
        ]

    def test_without_a_knob_the_unfitted_peaks_fall_through_to_the_default(self) -> None:
        table = resolution_table(
            THREE_PEAKS, METHOD, _gradient(20.0), plate_counts=[None, _fitted(12000.0), None]
        )

        assert [peak.width.plate_count_source for peak in table.peaks] == [
            "default",
            "fitted",
            "default",
        ]

    def test_no_per_peak_plate_counts_means_every_peak_uses_the_knob(self) -> None:
        table = resolution_table(THREE_PEAKS, METHOD, _gradient(20.0), plate_count=20000.0)

        assert all(peak.width.plate_count_source == "supplied" for peak in table.peaks)

    def test_a_plate_count_per_peak_is_required_when_they_are_supplied(self) -> None:
        with pytest.raises(ValueError, match="one plate count per peak"):
            resolution_table(THREE_PEAKS, METHOD, _gradient(20.0), plate_counts=[_fitted(1e4)])

    def test_fitted_plate_counts_travel_with_their_peak_through_the_sort(self) -> None:
        # Same guard as the names: at tG = 60 FAST elutes first although it is passed
        # second, and its own N — not SLOW's — must be the one its width rests on.
        table = resolution_table(
            [SLOW, FAST],
            METHOD,
            _gradient(60.0),
            names=["slow", "fast"],
            plate_counts=[_fitted(30000.0), _fitted(10000.0)],
        )

        assert [(peak.name, peak.width.plate_count) for peak in table.peaks] == [
            ("fast", 10000.0),
            ("slow", 30000.0),
        ]
