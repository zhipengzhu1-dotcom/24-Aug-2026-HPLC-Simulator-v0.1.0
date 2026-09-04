"""t0 from column geometry, and the check a measured t0 gets (SPEC §4, ticket #24).

Layer 1 pins the arithmetic and the constants against the research docs; the reality
section pins what a t0 error actually costs on the lab dataset — the two regimes of
`dead-time-from-geometry.md` §6, forty times apart, which is the whole reason the
estimate is cheap to autofill and the fitted parameters are what the stamp warns about.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import replace

import pytest

from hplcsim.dead_time import (
    EXTRA_COLUMN_VOLUME_RETAINED_ML,
    EXTRA_COLUMN_VOLUME_TYPICAL_ML,
    POROSITY,
    POROSITY_PLAUSIBLE,
    check_measured_t0,
    classify_marker,
    column_volume_ml,
    estimate_t0,
)
from hplcsim.fit import FitResult, fit_peaks
from hplcsim.model import Method
from hplcsim.retention import predict_retention
from lab_data import (
    LAB_MEASURED_PEAKS,
    LAB_METHOD,
    LAB_RUN1,
    LAB_RUN2,
    LAB_RUN3,
    LAB_RUN4,
)

# The driver's column as method.csv records it (t0 0.525, core–shell declared) — the
# fixture itself since the 2026-09-03 re-baseline.
LAB_COLUMN = LAB_METHOD


# --- the estimator (research doc §7.1–§7.2) --------------------------------------------


class TestColumnVolume:
    def test_the_lab_column_is_0_34636_ml(self) -> None:
        # (π/4) · 2.1² · 100 · 1e-3 — research doc §4.1, pinned to five figures.
        assert column_volume_ml(LAB_COLUMN) == pytest.approx(0.34636, abs=5e-6)

    def test_the_constant_is_exact_not_the_rounded_literal(self) -> None:
        # §7.1: never 0.000785. The rounded literal is 0.05% out, and this is the check.
        unit = Method(t0=1.0, t_dwell=0.0, flow=1.0, column_length_mm=1.0, column_id_mm=1.0)
        assert column_volume_ml(unit) == pytest.approx(math.pi / 4.0 / 1000.0, rel=1e-15)
        assert column_volume_ml(unit) != pytest.approx(0.000785, rel=1e-6)

    @pytest.mark.parametrize(
        ("missing", "field"),
        [
            ({"column_id_mm": None}, "column_id_mm"),
            ({"column_length_mm": None}, "column_length_mm"),
        ],
    )
    def test_a_missing_dimension_is_refused_by_name(
        self, missing: dict[str, None], field: str
    ) -> None:
        with pytest.raises(ValueError, match=field):
            column_volume_ml(replace(LAB_COLUMN, **missing))


class TestEstimate:
    def test_the_constants_are_the_porosity_docs_defaults(self) -> None:
        # porosity-for-t0-geometry.md §5.1 — not Waters' 0.66 / 0.49 (WKB28079).
        assert (POROSITY["fully_porous"].value, POROSITY["fully_porous"].band) == (
            0.62,
            (0.52, 0.70),
        )
        assert (POROSITY["core_shell"].value, POROSITY["core_shell"].band) == (0.52, (0.45, 0.60))

    def test_the_lab_column_estimates_0_450_min_at_core_shell(self) -> None:
        # §5.1's worked default: V_M = 180 µL, t0 = 0.450 min at 0.4 mL/min, band 0.39–0.52.
        estimate = estimate_t0(LAB_COLUMN)
        assert estimate.t0 == pytest.approx(0.4503, abs=5e-5)
        assert estimate.v_m_ml == pytest.approx(0.1801, abs=5e-5)
        assert estimate.t0_band == pytest.approx((0.3897, 0.5195), abs=5e-5)
        assert estimate.porosity.label == "core–shell"

    def test_fully_porous_puts_the_same_column_at_0_537_min(self) -> None:
        estimate = estimate_t0(replace(LAB_COLUMN, particle_is_solid_core=False))
        assert estimate.t0 == pytest.approx(0.5369, abs=5e-5)
        assert estimate.porosity.label == "fully porous"

    def test_a_published_geometry_reproduces_its_measured_porosity(self) -> None:
        # Research doc §3.2 / ref. 2: Zorbax SB-C18 4.6 × 250 mm measured ε_T = 0.526 with
        # uracil, from ε_T = F·t0/V_col. Run the relation forwards at that porosity and the
        # marker time comes back — the estimator is that equation, and nothing else.
        zorbax = Method(
            t0=1.0,
            t_dwell=0.0,
            flow=1.0,
            column_length_mm=250.0,
            column_id_mm=4.6,
            particle_um=5.0,
            particle_is_solid_core=False,
        )
        assert column_volume_ml(zorbax) == pytest.approx(4.1548, abs=5e-5)
        measured = replace(zorbax, t0=0.526 * column_volume_ml(zorbax) / zorbax.flow)
        assert check_measured_t0(measured).implied_porosity == pytest.approx(0.526, rel=1e-12)

    def test_an_undeclared_architecture_is_refused_by_name_not_defaulted(self) -> None:
        # #34, decision 2 — overriding both research docs' original "default to fully
        # porous". At the corrected t0 that default would put geometry *above* the marker.
        with pytest.raises(ValueError, match="particle_is_solid_core"):
            estimate_t0(replace(LAB_COLUMN, particle_is_solid_core=None))

    def test_a_missing_column_id_is_refused_by_name_like_the_plate_count_default(self) -> None:
        with pytest.raises(ValueError, match="column_id_mm"):
            estimate_t0(replace(LAB_COLUMN, column_id_mm=None))

    def test_the_estimate_scales_with_geometry_and_inversely_with_flow(self) -> None:
        base = estimate_t0(LAB_COLUMN).t0
        assert estimate_t0(replace(LAB_COLUMN, column_id_mm=4.2)).t0 == pytest.approx(4.0 * base)
        assert estimate_t0(replace(LAB_COLUMN, column_length_mm=50.0)).t0 == pytest.approx(
            base / 2.0
        )
        assert estimate_t0(replace(LAB_COLUMN, flow=0.8)).t0 == pytest.approx(base / 2.0)


# --- the reverse check (research doc §7.5, decided on #34) ------------------------------


class TestReverseCheck:
    def test_the_lab_columns_measured_t0_implies_0_606_and_30_ul_of_plumbing(self) -> None:
        """The driver's own dataset, at the corrected t0 — unremarkable, and it must stay so.

        The superseded 0.6 min implied ε_total = 0.693; the ticket was written around that
        anomaly. At 0.525 the column sits 0.075 min above its core–shell estimate, which is
        29.9 µL of extra-column volume, inside Handlovic's 26–78 µL. No tier fires.
        """
        check = check_measured_t0(LAB_COLUMN)
        assert check.implied_porosity == pytest.approx(0.6063, abs=5e-5)
        assert check.extra_column_volume_ml == pytest.approx(0.0299, abs=0.00005)
        assert check.finding == "plausible"
        assert check.geometry is not None and check.geometry.t0 == pytest.approx(0.4503, abs=5e-5)

    def test_the_fully_porous_inversion_that_forbids_a_default(self) -> None:
        # §4.2's inversion (test (e) of §7.9): at the lab geometry and 0.525, fully porous
        # puts the geometry estimate above the marker, an impossible −4.7 µL of plumbing.
        check = check_measured_t0(replace(LAB_COLUMN, particle_is_solid_core=False))
        assert check.extra_column_volume_ml == pytest.approx(-0.0047, abs=0.00005)
        assert check.finding == "below_geometry"

    @pytest.mark.parametrize("porosity", [0.62, 0.66])
    def test_every_fully_porous_constant_puts_geometry_above_the_marker(
        self, porosity: float
    ) -> None:
        # §7.9(e) in full: the porosity doc's 0.62 and Waters' 0.66 both imply V_ec < 0
        # at the lab geometry and 0.525 — −4.7 and −18.6 µL (#34's table).
        geometry_t0 = porosity * column_volume_ml(LAB_COLUMN) / LAB_COLUMN.flow
        v_ec_ul = LAB_COLUMN.flow * (LAB_COLUMN.t0 - geometry_t0) * 1000.0
        assert v_ec_ul < 0.0
        assert v_ec_ul == pytest.approx({0.62: -4.7, 0.66: -18.6}[porosity], abs=0.05)

    def test_the_superseded_0_6_min_no_longer_fires_anything(self) -> None:
        # The "~15% above the constant" tier of the first draft was dropped on #34: at
        # 0.6 the column implies 0.693 and 60 µL, and both are inside the bounds kept.
        check = check_measured_t0(replace(LAB_COLUMN, t0=0.6))
        assert check.implied_porosity == pytest.approx(0.693, abs=5e-4)
        assert check.finding == "plausible"

    def test_undeclared_architecture_keeps_the_porosity_bounds_and_loses_the_rest(self) -> None:
        # The accepted cost of refusing to guess, on the record in #34.
        check = check_measured_t0(replace(LAB_COLUMN, particle_is_solid_core=None))
        assert check.implied_porosity == pytest.approx(0.6063, abs=5e-5)
        assert check.geometry is None
        assert check.extra_column_volume_ml is None
        assert check.finding == "plausible"

    def test_more_mobile_phase_than_an_empty_tube_is_impossible(self) -> None:
        # ε_total > 1: t0 = 0.9 min at 0.4 mL/min is 0.36 mL through a 0.346 mL tube.
        assert check_measured_t0(replace(LAB_COLUMN, t0=0.9)).finding == "impossible_porosity"

    @pytest.mark.parametrize("t0", [0.25, 0.75])
    def test_a_porosity_no_packed_column_has_is_implausible(self, t0: float) -> None:
        lo, hi = POROSITY_PLAUSIBLE
        check = check_measured_t0(replace(LAB_COLUMN, t0=t0))
        assert not lo <= check.implied_porosity <= hi
        assert check.finding == "implausible_porosity"

    def test_the_impossible_tier_outranks_the_implausible_one(self) -> None:
        assert check_measured_t0(replace(LAB_COLUMN, t0=2.0)).finding == "impossible_porosity"

    def test_a_gap_too_large_to_be_plumbing_means_a_retained_marker(self) -> None:
        # 80 µL is 0.2 min at 0.4 mL/min above the 0.4503 estimate; still ε_total = 0.75.
        t0 = 0.4503 + EXTRA_COLUMN_VOLUME_RETAINED_ML / LAB_COLUMN.flow + 1e-3
        check = check_measured_t0(replace(LAB_COLUMN, t0=t0))
        assert check.extra_column_volume_ml is not None
        assert check.extra_column_volume_ml > EXTRA_COLUMN_VOLUME_TYPICAL_ML[1]
        assert check.finding == "marker_retained"

    def test_the_bounds_are_the_ones_the_map_decided(self) -> None:
        assert POROSITY_PLAUSIBLE == (0.35, 0.80)
        # 26–78 µL and 80 µL, held in the engine's mL.
        assert EXTRA_COLUMN_VOLUME_TYPICAL_ML == (0.026, 0.078)
        assert EXTRA_COLUMN_VOLUME_RETAINED_ML == 0.080

    def test_the_check_needs_only_the_geometry_not_the_architecture(self) -> None:
        with pytest.raises(ValueError, match="column_id_mm"):
            check_measured_t0(replace(LAB_COLUMN, column_id_mm=None))


# --- the marker (research doc §5.2, §7.6) ---------------------------------------------


@pytest.mark.parametrize(
    ("marker", "kind"),
    [
        (None, "absent"),
        ("", "absent"),
        ("   ", "absent"),
        ("uracil, apex", "compound"),
        ("thiourea", "compound"),
        ("acetone (first rise)", "compound"),
        ("solvent front", "solvent_disturbance"),
        ("first baseline disturbance of the injection", "solvent_disturbance"),
        ("system peak", "solvent_disturbance"),
        ("sodium nitrate", "inorganic_salt"),
        ("KNO3", "inorganic_salt"),
        ("KI", "inorganic_salt"),
        ("potassium bromide, apex", "inorganic_salt"),
        # Whole words only: "KI" must not fire inside a column name, and ordinary
        # injection vocabulary around a compound is not a disturbance.
        ("uracil on Kinetex", "compound"),
        ("uracil, 1 µL injection, apex", "compound"),
        ("injection peak", "solvent_disturbance"),
    ],
)
def test_marker_classification(marker: str | None, kind: str) -> None:
    assert classify_marker(marker) == kind


# --- reality: what a t0 error costs (research doc §6) -----------------------------------
#
# Both computed on the lab dataset at the fixture t0 (0.525 since the re-baseline;
# §6.2's tables were computed at the former 0.6 — see the provenance note there). The
# regimes are the point, not the baseline: the ratio between them is what is pinned.


def _held_out(method: Method, fits: Sequence[FitResult] | None = None) -> dict[str, list[float]]:
    """Run 3 and run 4 predicted from a fit at ``method`` (or from ``fits`` at it)."""
    fitted = fits if fits is not None else fit_peaks(LAB_MEASURED_PEAKS, method, LAB_RUN1, LAB_RUN2)
    return {
        run.name: [predict_retention(fit.params, method, run.gradient).t_r for fit in fitted]
        for run in (LAB_RUN3, LAB_RUN4)
    }


def _percent(changed: list[float], base: list[float]) -> list[float]:
    return [100.0 * (c - b) / b for c, b in zip(changed, base, strict=True)]


def test_case_a_a_30_percent_t0_error_moves_every_held_out_prediction_under_0_3_percent() -> None:
    """§6.2's insensitivity band: fit and predict with the *same* wrong t0.

    t0 vanishes from the prefactor (§6.1), the two-run fit absorbs the rest into k0, and
    the prediction barely moves — which is what makes an autofilled estimate cheap.
    """
    base = _held_out(LAB_METHOD)
    wrong = _held_out(replace(LAB_METHOD, t0=0.7 * LAB_METHOD.t0))
    for run_name in ("tG25", "tG60"):
        shifts = _percent(wrong[run_name], base[run_name])
        assert all(abs(shift) < 0.3 for shift in shifts), (run_name, shifts)


def test_case_b_the_same_error_at_prediction_time_only_is_forty_times_larger() -> None:
    """§6.3: parameters fitted under one t0 and used under another.

    Pinned as the *large* number so the two regimes cannot be confused, and so a future
    feature that carries fitted parameters across a change of t0 fails here.
    """
    fits = fit_peaks(LAB_MEASURED_PEAKS, LAB_METHOD, LAB_RUN1, LAB_RUN2)
    base = _held_out(LAB_METHOD, fits)["tG25"]
    mismatched = _held_out(replace(LAB_METHOD, t0=0.7 * LAB_METHOD.t0), fits)["tG25"]
    shifts = _percent(mismatched, base)
    assert all(shift < -3.0 for shift in shifts), shifts
    # Elasticity d ln tR / d ln t0 ≈ 0.12–0.25 here against ≲ 0.008 in case A.
    elasticities = [shift / -30.0 for shift in shifts]
    assert all(0.1 < e < 0.3 for e in elasticities), elasticities


def test_the_two_regimes_are_a_factor_of_forty_apart() -> None:
    consistent = _held_out(replace(LAB_METHOD, t0=0.7 * LAB_METHOD.t0))["tG25"]
    fits = fit_peaks(LAB_MEASURED_PEAKS, LAB_METHOD, LAB_RUN1, LAB_RUN2)
    mismatched = _held_out(replace(LAB_METHOD, t0=0.7 * LAB_METHOD.t0), fits)["tG25"]
    base = _held_out(LAB_METHOD)["tG25"]
    worst_a = max(abs(s) for s in _percent(consistent, base))
    worst_b = max(abs(s) for s in _percent(mismatched, base))
    assert worst_b / worst_a > 20.0, (worst_a, worst_b)
