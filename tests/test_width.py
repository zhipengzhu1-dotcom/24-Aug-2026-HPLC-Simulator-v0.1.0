"""Peak width under gradient elution (SPEC §3; research doc §5)."""

from __future__ import annotations

import math

import pytest

from hplcsim.model import Gradient, Method, RetentionParams
from hplcsim.retention import predict_retention
from hplcsim.width import band_compression_factor, default_plate_count, peak_width


class TestDefaultPlateCount:
    """SPEC §4: N is a global knob with a column-based default."""

    def test_lab_column_gets_the_reduced_plate_height_estimate(self) -> None:
        # N = L / (h·dp) with h = 2: 100 mm / (2 × 0.0016 mm) = 31250 for the
        # validation/method.csv column (100 mm × 2.1 mm, 1.6 µm).
        method = Method(t0=0.6, t_dwell=0.9375, flow=0.4, column_length_mm=100.0, particle_um=1.6)
        assert default_plate_count(method) == pytest.approx(31250.0)

    def test_geometry_is_required_to_estimate_a_default(self) -> None:
        method = Method(t0=0.6, t_dwell=0.9375, flow=0.4)
        with pytest.raises(ValueError, match="column length and particle size"):
            default_plate_count(method)


class TestBandCompressionFactor:
    """Research doc §5.2: G(p) = √(1 + p + p²/3)/(1 + p), p = b_e·k0/(1 + k0)."""

    # §5.2's computed table, quoted for large k0 (so p → b_e). This is the
    # transcription that pins the log-base convention: reading b as base-10 would
    # move every row by ~10–15% — a 2.303-slipped G at b_e = 0.2 reads 0.847, which
    # is this table's b_e = 0.46 entry, so the table cannot be satisfied by accident.
    DOC_TABLE_LARGE_K0 = [(0.1, 0.955), (0.2, 0.918), (0.46, 0.847), (1.0, 0.764), (3.0, 0.661)]

    @pytest.mark.parametrize(("b_e", "expected_g"), DOC_TABLE_LARGE_K0)
    def test_matches_the_research_doc_table(self, b_e: float, expected_g: float) -> None:
        assert band_compression_factor(b_e, k0=1e6) == pytest.approx(expected_g, abs=5e-4)

    def test_no_gradient_means_no_compression(self) -> None:
        assert band_compression_factor(0.0, k0=1e6) == pytest.approx(1.0)

    def test_compression_increases_with_steepness(self) -> None:
        factors = [band_compression_factor(b_e, k0=1e6) for b_e in (0.1, 0.5, 1.0, 2.0, 5.0)]
        assert factors == sorted(factors, reverse=True)

    def test_weakly_retained_solutes_compress_less_than_strongly_retained(self) -> None:
        # p carries the k0/(1+k0) factor, so a solute barely retained at φ0 sees a
        # smaller effective steepness than one that is well retained.
        assert band_compression_factor(1.0, k0=0.5) > band_compression_factor(1.0, k0=1e6)


class TestPeakWidth:
    """Research doc §5.1: σ_t = G·t0·(1 + k_e)/√N, W = 4σ, W½ = √(8 ln 2)·σ."""

    METHOD = Method(t0=0.6, t_dwell=0.0, flow=0.4, column_length_mm=100.0, particle_um=1.6)

    # A deliberately extreme synthetic solute: k0 = 1e8 with an S_e steep enough
    # to still elute it during the ramp. The Guillarme cross-check below is an
    # identity in the large-k0 limit (k_e → 1/b_e), so the fixture has to sit in
    # that limit — these are not meant as physically typical parameters.
    @staticmethod
    def _well_retained(s_e: float = 45.0) -> RetentionParams:
        return RetentionParams(ln_k0=math.log(1e8), s_e=s_e, phi_ref=0.0)

    def test_matches_guillarme_eq_13_once_compression_is_divided_out(self) -> None:
        # §5.1 cross-check: Guillarme et al. (2022) Eq. 13 gives the no-compression
        # width as w = (4·t0/√N)·(1 + 2.3b)/(2.3b), where 2.3b is this engine's b_e.
        # A well-retained solute has k_e → 1/b_e, so the two forms must agree
        # exactly apart from G. This is the equation stated by a different paper
        # than the one §5.1's form comes from, so it is a real cross-check.
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)
        params = self._well_retained()
        n = 20000.0
        b_e = self.METHOD.t0 * gradient.delta_phi * params.s_e / gradient.t_gradient
        guillarme_w = (4.0 * self.METHOD.t0 / math.sqrt(n)) * (1.0 + b_e) / b_e

        width = peak_width(params, self.METHOD, gradient, plate_count=n)

        assert width.w_base / width.g == pytest.approx(guillarme_w, rel=1e-6)

    def test_the_three_width_measures_use_the_published_gaussian_constants(self) -> None:
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)
        width = peak_width(self._well_retained(), self.METHOD, gradient, plate_count=20000.0)

        assert width.w_base == pytest.approx(4.0 * width.sigma)
        # §6 insists on the exact √(8 ln 2) = 2.3548, not the rounded 2.355/2.35.
        assert width.w_half == pytest.approx(math.sqrt(8.0 * math.log(2.0)) * width.sigma)

    def test_width_scales_as_one_over_root_n(self) -> None:
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)
        params = self._well_retained()
        narrow = peak_width(params, self.METHOD, gradient, plate_count=80000.0)
        wide = peak_width(params, self.METHOD, gradient, plate_count=20000.0)

        assert wide.sigma == pytest.approx(2.0 * narrow.sigma)

    def test_the_plate_count_knob_defaults_to_the_column_estimate(self) -> None:
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)
        width = peak_width(self._well_retained(), self.METHOD, gradient)

        assert width.plate_count == pytest.approx(default_plate_count(self.METHOD))

    def test_post_gradient_eluters_are_not_compressed(self) -> None:
        # §5.3: "Do not silently apply G to peaks in the post-gradient regime —
        # they are not compressed; use G = 1 there." A solute still on-column when
        # the ramp ends finishes isocratically and sees no compression.
        gradient = Gradient(phi0=0.0, phif=0.2, t_gradient=2.0)
        params = RetentionParams(ln_k0=math.log(500.0), s_e=5.0, phi_ref=0.0)
        assert predict_retention(params, self.METHOD, gradient).regime == "post_gradient"

        width = peak_width(params, self.METHOD, gradient)

        assert width.g == 1.0

    def test_a_band_that_leaves_before_the_gradient_arrives_is_not_compressed(self) -> None:
        # §4.1 isocratic-hold regime: same argument as the post-gradient case.
        method = Method(t0=0.6, t_dwell=5.0, flow=0.4, column_length_mm=100.0, particle_um=1.6)
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)
        params = RetentionParams(ln_k0=math.log(2.0), s_e=5.0, phi_ref=0.0)
        assert predict_retention(params, method, gradient).regime == "isocratic_hold"

        width = peak_width(params, method, gradient)

        assert width.g == 1.0

    def test_gradient_eluters_are_compressed(self) -> None:
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)
        width = peak_width(self._well_retained(), self.METHOD, gradient)

        assert width.g < 1.0
        assert width.w_half < math.sqrt(8.0 * math.log(2.0)) * self.METHOD.t0 * (
            1.0 + width.k_e
        ) / math.sqrt(width.plate_count)

    def test_a_defaulted_plate_count_is_stamped_as_an_estimate(self) -> None:
        # SPEC §4 takes this posture on an estimated t0 — "labeled fallback that
        # stamps predictions lower-confidence". A defaulted N earns the same stamp:
        # it is column geometry, not the column's measured efficiency, and against
        # the lab data it is the larger of the two error sources in a width.
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)

        assert peak_width(self._well_retained(), self.METHOD, gradient).plate_count_is_default

    def test_a_supplied_plate_count_is_not_stamped(self) -> None:
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)
        width = peak_width(self._well_retained(), self.METHOD, gradient, plate_count=20000.0)

        assert not width.plate_count_is_default

    def test_supplying_the_default_value_explicitly_still_counts_as_supplied(self) -> None:
        # The stamp records provenance, not the number: a user who types in the
        # geometry estimate has made a choice the engine should not overwrite.
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)
        width = peak_width(
            self._well_retained(),
            self.METHOD,
            gradient,
            plate_count=default_plate_count(self.METHOD),
        )

        assert not width.plate_count_is_default

    def test_a_non_positive_plate_count_is_refused(self) -> None:
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)
        with pytest.raises(ValueError, match="plate count"):
            peak_width(self._well_retained(), self.METHOD, gradient, plate_count=0.0)
