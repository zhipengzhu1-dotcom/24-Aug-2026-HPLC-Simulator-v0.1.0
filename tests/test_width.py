"""Peak width under gradient elution (SPEC §3; research doc §5)."""

from __future__ import annotations

import math

import pytest

from hplcsim.model import Gradient, Method, Peak, RetentionParams, Run
from hplcsim.retention import predict_retention
from hplcsim.width import (
    FittedPlateCount,
    band_compression_factor,
    default_plate_count,
    fit_plate_count,
    peak_width,
    plate_count_from_width,
)


class TestDefaultPlateCount:
    """SPEC §4: the column-based default — the last fallback behind a fitted N and the knob."""

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

        width = peak_width(self._well_retained(), self.METHOD, gradient)

        assert width.plate_count_source == "default"

    def test_a_supplied_plate_count_is_stamped_as_the_users(self) -> None:
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)
        width = peak_width(self._well_retained(), self.METHOD, gradient, plate_count=20000.0)

        assert width.plate_count_source == "supplied"

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

        assert width.plate_count_source == "supplied"

    def test_a_fitted_plate_count_is_used_and_stamped_as_fitted(self) -> None:
        # Measured-first (SPEC §4's t0 posture, extended to N): a plate count fitted
        # from the peak's own widths is the best information there is, and the stamp
        # lets SPEC §6 diagnostic 5 leave such a peak out of the defaulted-N caveat.
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)
        fitted = FittedPlateCount(
            plate_count=12345.0, implied_run1=12000.0, implied_run2=12700.0, low_confidence=False
        )

        width = peak_width(self._well_retained(), self.METHOD, gradient, plate_count=fitted)

        assert width.plate_count_source == "fitted"
        assert width.plate_count == 12345.0
        assert width.sigma == pytest.approx(
            peak_width(self._well_retained(), self.METHOD, gradient, plate_count=12345.0).sigma
        )

    def test_a_non_positive_plate_count_is_refused(self) -> None:
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)
        with pytest.raises(ValueError, match="plate count"):
            peak_width(self._well_retained(), self.METHOD, gradient, plate_count=0.0)


class TestPlateCountFromWidth:
    """The inverse of the width equation (research doc plate-count-from-widths.md §4.1).

    N = (√(8 ln 2)·G·t0·(1 + k_e)/W½)² — the same quantity §5.4 of the gradient-math
    doc used per run as its G-convention statistic, now a function.
    """

    # One case per retention regime (§4.1, §2.2, §4.2 of the gradient-math doc): the
    # inverse must share peak_width's regime branch, so G is applied — or not — the
    # same way in both directions.
    REGIME_CASES = [
        (
            "gradient",
            Method(t0=0.6, t_dwell=0.9375, flow=0.4),
            Gradient(phi0=0.05, phif=0.95, t_gradient=15.0, t_init=0.5),
            RetentionParams(ln_k0=math.log(500.0), s_e=11.0, phi_ref=0.05),
        ),
        (
            "post_gradient",
            Method(t0=0.6, t_dwell=0.0, flow=0.4),
            Gradient(phi0=0.0, phif=0.2, t_gradient=2.0),
            RetentionParams(ln_k0=math.log(500.0), s_e=5.0, phi_ref=0.0),
        ),
        (
            "isocratic_hold",
            Method(t0=0.6, t_dwell=5.0, flow=0.4),
            Gradient(phi0=0.0, phif=0.5, t_gradient=20.0),
            RetentionParams(ln_k0=math.log(2.0), s_e=5.0, phi_ref=0.0),
        ),
    ]

    @pytest.mark.parametrize(
        ("regime", "method", "gradient", "params"), REGIME_CASES, ids=[c[0] for c in REGIME_CASES]
    )
    def test_inverts_peak_width_exactly_in_every_regime(
        self, regime: str, method: Method, gradient: Gradient, params: RetentionParams
    ) -> None:
        assert predict_retention(params, method, gradient).regime == regime
        n = 17500.0
        w_half = peak_width(params, method, gradient, plate_count=n).w_half

        assert plate_count_from_width(params, method, gradient, w_half) == pytest.approx(
            n, rel=1e-12
        )

    def test_a_hold_regime_width_gives_the_pharmacopoeial_plate_number(self) -> None:
        # USP ⟨621⟩ defines N only from isocratic data, as N = 5.54·(tR/W½)² — 8 ln 2
        # to three figures. A band that leaves before the gradient arrives is exactly
        # that measurement, so the inverse must collapse to it (research doc §4.2), with
        # the exact constant (§3.4). An independent formula, not a re-statement of ours.
        method = Method(t0=0.6, t_dwell=5.0, flow=0.4)
        gradient = Gradient(phi0=0.0, phif=0.5, t_gradient=20.0)
        params = RetentionParams(ln_k0=math.log(2.0), s_e=5.0, phi_ref=0.0)
        retention = predict_retention(params, method, gradient)
        assert retention.regime == "isocratic_hold"
        w_half = 0.05

        usp_form = 8.0 * math.log(2.0) * (retention.t_r / w_half) ** 2

        assert plate_count_from_width(params, method, gradient, w_half) == pytest.approx(usp_form)

    def test_a_non_positive_width_is_refused(self) -> None:
        _, method, gradient, params = self.REGIME_CASES[0]
        with pytest.raises(ValueError, match="width"):
            plate_count_from_width(params, method, gradient, 0.0)


class TestFitPlateCount:
    """One N per peak from that peak's scouting widths (research doc §3, §6 item 1)."""

    METHOD = Method(t0=0.6, t_dwell=0.9375, flow=0.4, column_length_mm=100.0, particle_um=1.6)
    RUN1 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=15.0, t_init=0.5), name="steep")
    RUN2 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=45.0, t_init=0.5), name="shallow")
    PARAMS = RetentionParams(ln_k0=math.log(500.0), s_e=11.0, phi_ref=0.05)

    def _peak(self, n_run1: float | None, n_run2: float | None) -> Peak:
        """A peak whose recorded widths imply exactly ``n_run1`` and ``n_run2`` plates."""

        def width(run: Run, n: float | None) -> float | None:
            if n is None:
                return None
            return peak_width(self.PARAMS, self.METHOD, run.gradient, plate_count=n).w_half

        return Peak(
            t_r_run1=predict_retention(self.PARAMS, self.METHOD, self.RUN1.gradient).t_r,
            t_r_run2=predict_retention(self.PARAMS, self.METHOD, self.RUN2.gradient).t_r,
            w_half_run1=width(self.RUN1, n_run1),
            w_half_run2=width(self.RUN2, n_run2),
        )

    def test_two_widths_give_the_geometric_mean_of_the_plate_counts_they_imply(self) -> None:
        # Research doc §3.2(a): least squares in ln W — maximum likelihood when width
        # error scales with width — is the geometric mean of the implied N. The two
        # implied values are set 4× apart so the arithmetic mean (25000) is excluded.
        fitted = fit_plate_count(
            self._peak(10000.0, 40000.0), self.PARAMS, self.METHOD, self.RUN1, self.RUN2
        )

        assert fitted is not None
        assert fitted.plate_count == pytest.approx(20000.0, rel=1e-9)
        assert fitted.implied_run1 == pytest.approx(10000.0, rel=1e-9)
        assert fitted.implied_run2 == pytest.approx(40000.0, rel=1e-9)
        assert fitted.ratio == pytest.approx(0.25, rel=1e-9)
        assert not fitted.low_confidence

    def test_a_peak_without_widths_has_no_fitted_plate_count(self) -> None:
        # Sessions without widths keep the default, the knob and the stamp (#23
        # criterion 3): there is nothing to fit, and the caller falls through.
        assert (
            fit_plate_count(self._peak(None, None), self.PARAMS, self.METHOD, self.RUN1, self.RUN2)
            is None
        )

    @pytest.mark.parametrize(
        ("n_run1", "n_run2"), [(12000.0, None), (None, 12000.0)], ids=["run1-only", "run2-only"]
    )
    def test_one_width_is_enough(self, n_run1: float | None, n_run2: float | None) -> None:
        # Research doc §3.2's estimator is written for n widths; n = 1 is its degenerate
        # case, and the brief (design item 4) makes the call that one width still beats
        # a geometry estimate. With one value there is nothing to compare it against,
        # so the ratio is absent.
        fitted = fit_plate_count(
            self._peak(n_run1, n_run2), self.PARAMS, self.METHOD, self.RUN1, self.RUN2
        )

        assert fitted is not None
        assert fitted.plate_count == pytest.approx(12000.0, rel=1e-9)
        assert fitted.ratio is None
        assert (fitted.implied_run1 is None) is (n_run1 is None)
        assert (fitted.implied_run2 is None) is (n_run2 is None)

    # Research doc §4.3: a band still on-column when the ramp ends was compressed under
    # the ramp and then broadened isocratically, so its width is neither value and the
    # G = 1 inverse inherits an unquantified error. The steep run below elutes this
    # solute post-gradient and the shallow run in-gradient; each width is built at its
    # own N, so the fitted value shows which widths the fit rests on.
    POST_GRADIENT_METHOD = Method(t0=0.6, t_dwell=0.0, flow=0.4)
    STEEP = Run(Gradient(phi0=0.0, phif=0.2, t_gradient=2.0), name="steep")
    SHALLOW = Run(Gradient(phi0=0.0, phif=0.2, t_gradient=40.0), name="shallow")
    POST_GRADIENT_PARAMS = RetentionParams(ln_k0=math.log(500.0), s_e=20.0, phi_ref=0.0)

    def _regime_peak(self, n_steep: float | None, n_shallow: float | None) -> Peak:
        method, params = self.POST_GRADIENT_METHOD, self.POST_GRADIENT_PARAMS
        assert predict_retention(params, method, self.STEEP.gradient).regime == "post_gradient"
        assert predict_retention(params, method, self.SHALLOW.gradient).regime == "gradient"

        def width(run: Run, n: float | None) -> float | None:
            if n is None:
                return None
            return peak_width(params, method, run.gradient, plate_count=n).w_half

        return Peak(
            t_r_run1=predict_retention(params, method, self.STEEP.gradient).t_r,
            t_r_run2=predict_retention(params, method, self.SHALLOW.gradient).t_r,
            w_half_run1=width(self.STEEP, n_steep),
            w_half_run2=width(self.SHALLOW, n_shallow),
        )

    def test_a_post_gradient_width_is_left_out_when_the_other_run_has_a_usable_one(
        self,
    ) -> None:
        # Dropping a known-biased measurement is not a block: the fit rests on the
        # in-gradient width alone (9000 — not 6000, the geometric mean with the other),
        # while the post-gradient width's implied value is still reported, so the
        # ratio shows the disagreement.
        fitted = fit_plate_count(
            self._regime_peak(4000.0, 9000.0),
            self.POST_GRADIENT_PARAMS,
            self.POST_GRADIENT_METHOD,
            self.STEEP,
            self.SHALLOW,
        )

        assert fitted is not None
        assert fitted.plate_count == pytest.approx(9000.0, rel=1e-9)
        assert fitted.implied_run1 == pytest.approx(4000.0, rel=1e-9)
        assert fitted.ratio == pytest.approx(4000.0 / 9000.0, rel=1e-9)
        assert not fitted.low_confidence

    def test_a_lone_post_gradient_width_is_used_but_stamped_low_confidence(self) -> None:
        # Warnings over blocks: refusing the peak's only width would leave it on the
        # geometry default, which is worse. It is used, and the stamp says what it
        # rests on.
        fitted = fit_plate_count(
            self._regime_peak(4000.0, None),
            self.POST_GRADIENT_PARAMS,
            self.POST_GRADIENT_METHOD,
            self.STEEP,
            self.SHALLOW,
        )

        assert fitted is not None
        assert fitted.plate_count == pytest.approx(4000.0, rel=1e-9)
        assert fitted.low_confidence
