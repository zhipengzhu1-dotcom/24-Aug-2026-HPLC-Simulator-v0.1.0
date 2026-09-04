"""SPEC §6's v0.2 diagnostics, without a browser (ticket #72).

Diagnostic 1 re-expressed on s\\*, the composition-window sentence on 3, the φ0-departure
guard 7, the low-k0 and wash-eluted badges 8 and 9, the *indicative, not decision-grade*
stamp, and the per-peak composition-window readout — the objects, thresholds and wording,
placed on screen by #74. The seams are the ticket's acceptance criteria, read through
:func:`app.diagnostics.diagnose` on the two bench samples' own fixtures.
"""

from __future__ import annotations

import math
import pathlib

import pytest

import spec10_item2
from app.diagnostics import (
    STRONG_WINDOW_WIDTHS,
    Diagnostic,
    Diagnostics,
    diagnose,
    steepness_bracket,
    window_widths_outside,
)
from app.pipeline import CockpitInputs
from hplcsim.model import Gradient, PeakRow, Programme, Run, Segment, Target
from hplcsim.retention import predict_retention
from lab_data import (
    LAB_MEASURED_PEAKS,
    LAB_METHOD,
    LAB_PEAKS,
    LAB_RUN1,
    LAB_RUN2,
    LAB_RUN4,
    LAB_RUN6,
    LAB_RUN6_PROGRAMME,
    LAB_STAMPED,
    LAB_UNSTAMPED,
)
from validation2_data import (
    VALIDATION2_STAMPED,
    VALIDATION2_UNSTAMPED,
)

# The rows a sample's peaks make and the door a programme goes in by are shared with
# `test_overlay` through `spec10_item2`, so both files drive the Cockpit the same way.
_rows = spec10_item2.rows
_inputs = spec10_item2.cockpit_inputs


def _lab(candidate: Target) -> Diagnostics:
    return diagnose(_inputs(LAB_METHOD, LAB_RUN1, LAB_RUN2, candidate, _rows(LAB_MEASURED_PEAKS)))


def _scouting(t_gradient: float) -> Gradient:
    return Gradient(phi0=0.05, phif=0.95, t_gradient=t_gradient, t_init=0.5)


def _steepness(diagnostics: Diagnostics) -> list[Diagnostic]:
    return [d for d in diagnostics.candidate if d.code == "steepness_extrapolation"]


# --- diagnostic 1 on s*: the bracket and the window-widths measure ----------------------


def test_the_scouting_bracket_is_the_pairs_steepness_shortest_run_steepest() -> None:
    """s* = t0·Δφ/tG: 0.525 × 0.9 / 45 and / 15 on the three-peak pair."""
    lo, hi = steepness_bracket(LAB_METHOD, LAB_RUN1, LAB_RUN2)
    assert lo == pytest.approx(0.0105)
    assert hi == pytest.approx(0.0315)


def test_run_4_sits_the_research_docs_0_26_window_widths_below_the_bracket() -> None:
    """composition-extrapolation.md §7.3's worked number: log₃(0.0120 / 0.0090) = 0.26."""
    (leg,) = Programme.from_gradient(LAB_RUN4.gradient).legs()
    widths = window_widths_outside(LAB_METHOD, leg, LAB_RUN1, LAB_RUN2)
    assert widths == pytest.approx(0.262, abs=0.001)


def test_inside_the_bracket_and_on_its_edges_the_distance_is_zero() -> None:
    for t_gradient in (15.0, 25.0, 45.0):
        (leg,) = Programme.from_gradient(_scouting(t_gradient)).legs()
        assert window_widths_outside(LAB_METHOD, leg, LAB_RUN1, LAB_RUN2) == 0.0


def test_a_hold_has_no_position_in_a_steepness_bracket() -> None:
    (leg,) = Programme(phi0=0.05, segments=(Segment(10.0, 0.05),)).legs()
    assert window_widths_outside(LAB_METHOD, leg, LAB_RUN1, LAB_RUN2) == 0.0


def test_a_flat_candidate_is_silent_though_it_now_reports_a_segment() -> None:
    """#94: correcting the eluting segment hands diagnostic 1 segment 0 of a hold.

    SPEC §6 item 1: *flat segments are holds and are never bracketed (s\\* = 0 has no
    position in a steepness bracket)*. That rule lives one level down, inside
    :func:`window_widths_outside`, so the segment the fix newly attributes measures 0.0
    and the diagnostic stays silent — which is what it did before the fix, by having no
    segment to read at all.
    """
    flat = Programme.from_gradient(Gradient(phi0=0.70, phif=0.70, t_gradient=25.0, t_init=0.5))
    assert any(predict_retention(p, LAB_METHOD, flat).eluting_segment == 0 for p in LAB_PEAKS), (
        "the peaks must actually leave inside the hold, or this asserts nothing"
    )

    assert _steepness(_lab(flat)) == []


def test_a_v01_session_outside_the_bracket_names_the_distance_in_window_widths() -> None:
    (flag,) = _lab(_scouting(60.0)).candidate
    assert flag.code == "steepness_extrapolation"
    assert flag.severity == "info"
    assert "0.26 window-widths" in flag.message
    assert "1.33×" in flag.message  # the v0.1 reading of the same distance, kept


def test_the_strong_tier_starts_at_0_6_window_widths_not_at_a_tg_multiple() -> None:
    """SPEC §6 item 1 (#55): gentle to ~0.6 window-widths, strong beyond."""
    assert STRONG_WINDOW_WIDTHS == 0.6
    edge = 45.0 * 3.0**STRONG_WINDOW_WIDTHS  # β = 3 on this pair
    assert _lab(_scouting(edge - 0.1)).candidate[0].severity == "info"
    assert _lab(_scouting(edge + 0.1)).candidate[0].severity == "strong"


def test_a_trailing_wash_no_peak_elutes_in_cannot_fire_the_bracket() -> None:
    """Three-peak run 6 as run: the ramp is 0.20 window-widths out and every peak that
    leaves on a ramp leaves on it; the 0.1 min steps to 95 and 25 %B are far outside the
    bracket and inert (#58)."""
    (flag,) = _steepness(_lab(LAB_RUN6_PROGRAMME))
    assert flag.severity == "info"
    assert "0.20 window-widths" in flag.message
    (as_ramp_only,) = _steepness(_lab(LAB_RUN6.gradient))
    assert as_ramp_only.severity == "info"


def test_silent_when_every_peak_leaves_in_a_hold_or_after_the_end() -> None:
    """A ramp too short for anything to leave on, then a long hold: no segment that
    elutes a peak is a ramp, so there is nothing to bracket (#58)."""
    programme = Programme(phi0=0.05, segments=(Segment(1.0, 0.30), Segment(60.0, 0.30)), t_init=0.5)
    assert _lab(programme).candidate == ()


def test_the_tier_is_the_worst_ramp_that_elutes_a_peak() -> None:
    """Two ramps: a first far too steep (strong on its own) that nothing leaves on, then
    an in-bracket second ramp every peak leaves on — silent; swap the roles and it fires."""
    steep_then_fine = Programme(
        phi0=0.05, segments=(Segment(0.5, 0.20), Segment(25.0, 0.95)), t_init=0.5
    )
    assert _lab(steep_then_fine).candidate == ()
    fine_then_shallow = Programme(
        phi0=0.05, segments=(Segment(1.0, 0.08), Segment(120.0, 0.95)), t_init=0.5
    )
    (flag,) = _lab(fine_then_shallow).candidate
    assert flag.severity == "strong"
    assert "segment 2" in flag.message


# --- diagnostic 3: the composition-window sentence -----------------------------------------


def test_a_narrow_beta_also_says_it_narrows_every_peaks_composition_window() -> None:
    """SPEC §6 item 3's one added sentence: ln β / S_e, ~10 %B per peak, disjoint."""
    inputs = CockpitInputs(
        method=LAB_METHOD,
        run1=LAB_RUN1,
        run2=Run(_scouting(30.0), name="tG30"),  # β = 2, under the 2.5 warning tier
        candidate=_scouting(20.0),
        rows=_rows(LAB_MEASURED_PEAKS),
    )
    (notice,) = diagnose(inputs).fit
    assert notice.code == "beta_spacing"
    assert "composition window" in notice.message
    assert "ln β / S_e" in notice.message
    assert "disjoint" in notice.message


# --- diagnostic 7: the φ0 departure --------------------------------------------------------


def _departure(start_percent_b: float, *, phif: float = 0.95, t_gradient: float = 25.0):
    """A one-segment candidate whose start departs from the 5 %B scouting start."""
    candidate = Gradient(phi0=start_percent_b / 100.0, phif=phif, t_gradient=t_gradient, t_init=0.5)
    return [d for d in _lab(candidate).candidate if d.code == "phi0_departure"]


def test_a_candidate_starting_at_the_scouting_start_draws_no_departure() -> None:
    assert _departure(5.0) == []


def test_any_departure_above_the_scouting_start_is_gentle_below_plus_10() -> None:
    """SPEC §6 item 7: gentle for any non-zero Δφ0; untested below +10, and it says so."""
    (flag,) = _departure(7.0)
    assert flag.severity == "info"
    assert "+2 %B" in flag.message
    assert "departure from the scouting start" in flag.message


def test_strong_from_plus_10_percent_b_departure() -> None:
    """The smallest departure measured, where the retention error doubled on both samples."""
    (at_ten,) = _departure(15.0)
    assert at_ten.severity == "strong"
    assert "+10 %B" in at_ten.message
    (just_under,) = _departure(14.9)
    assert just_under.severity == "info"


def test_the_departure_is_a_departure_not_an_absolute_start() -> None:
    """A method scouted at 20 %B is silent until its candidate starts above 20 %B."""
    scouted_high = Run(Gradient(phi0=0.20, phif=0.95, t_gradient=15.0, t_init=0.5), name="r1")
    scouted_high2 = Run(Gradient(phi0=0.20, phif=0.95, t_gradient=45.0, t_init=0.5), name="r2")
    rows = tuple(
        PeakRow(name=name, t_r_run1=t1, t_r_run2=t2)
        for name, t1, t2 in (("A", 6.0, 12.0), ("B", 8.0, 17.0))
    )
    at_start = CockpitInputs(
        method=LAB_METHOD,
        run1=scouted_high,
        run2=scouted_high2,
        candidate=Gradient(phi0=0.20, phif=0.95, t_gradient=25.0, t_init=0.5),
        rows=rows,
    )
    assert [d for d in diagnose(at_start).candidate if d.code == "phi0_departure"] == []
    raised = CockpitInputs(
        method=LAB_METHOD,
        run1=scouted_high,
        run2=scouted_high2,
        candidate=Gradient(phi0=0.32, phif=0.95, t_gradient=25.0, t_init=0.5),
        rows=rows,
    )
    (flag,) = [d for d in diagnose(raised).candidate if d.code == "phi0_departure"]
    assert flag.severity == "strong"
    assert "+12 %B" in flag.message


def test_lowering_the_start_is_gentle_at_any_amount_with_no_data_either_way() -> None:
    (flag,) = _departure(2.0)
    assert flag.severity == "info"
    assert "−3 %B" in flag.message
    assert "no data either way" in flag.message
    (far,) = _departure(0.0)
    assert far.severity == "info"


def test_the_message_quotes_both_ladders_as_observations_and_evaluates_no_multiplier() -> None:
    """SPEC §6 item 7 as merged: what was observed from 5 %B starts, never a rule."""
    (flag,) = _departure(25.0)
    for observed in ("0.42", "0.82", "0.11", "0.23", "1.67", "0.26"):
        assert observed in flag.message
    assert "5 %B" in flag.message  # the starts the ladders were measured from
    assert "No correction" in flag.message
    assert "×" not in flag.message.split("**", 2)[2]  # no evaluated multiplier after the head
    assert "roughly doubled" in flag.message


def test_a_later_segment_that_steps_above_the_scouting_start_earns_no_term() -> None:
    """#58: Δφ0 is the candidate's *start* against the scouting start only."""
    later_step = Programme(
        phi0=0.05, segments=(Segment(5.0, 0.05), Segment(20.0, 0.95)), t_init=0.5
    )
    assert [d for d in _lab(later_step).candidate if d.code == "phi0_departure"] == []


# --- diagnostics 8 and 9: the per-peak badges --------------------------------------------

LAB_RUN7_START = 0.25  # three-peak run 7: 25 → 95 %B, where Unknown-1 sits at log₁₀ k0 = 1.74


def _badges(diagnostics: Diagnostics, code: str) -> dict[str, Diagnostic]:
    return {
        name: badge
        for name, badges in diagnostics.badges.items()
        for badge in badges
        if badge.code == code
    }


def test_the_low_k0_badge_fires_on_run_7_unknown_1_and_nowhere_else() -> None:
    """SPEC §6 item 8: log₁₀ k0 at the candidate's φ0 below 2.1 — one peak on file."""
    run7 = Gradient(phi0=LAB_RUN7_START, phif=0.95, t_gradient=25.0, t_init=0.5)
    low = _badges(_lab(run7), "low_k0")
    assert list(low) == ["Unknown-1"]
    assert low["Unknown-1"].severity == "warning"
    # 1.79 at t0 = 0.525; SPEC §6 item 8 and §10 item 2 quote 1.74, the 0.6-era fit.
    assert "1.79" in low["Unknown-1"].message
    assert "2.1" in low["Unknown-1"].message
    assert _badges(_lab(_scouting(25.0)), "low_k0") == {}


def test_the_low_k0_badge_reads_the_candidates_start_not_the_scouting_start() -> None:
    """A later segment above the start changes nothing: k0 is at φ0 (#58's rule for 7,
    and 8 sits beside 2 as the same physics from the other side)."""
    stepped = Programme(
        phi0=0.05, segments=(Segment(0.1, LAB_RUN7_START), Segment(25.0, 0.95)), t_init=0.5
    )
    assert _badges(_lab(stepped), "low_k0") == {}


def test_the_wash_eluted_badge_fires_on_run_6_unknown_3_and_nowhere_else() -> None:
    """SPEC §6 item 9: a peak leaving in a *later* hold or after the last segment."""
    washed = _badges(_lab(LAB_RUN6_PROGRAMME), "wash_eluted")
    assert list(washed) == ["Unknown-3"]
    assert washed["Unknown-3"].severity == "warning"
    assert "95 %B" in washed["Unknown-3"].message
    assert "46.8" in washed["Unknown-3"].message  # the one measured case, both ways


def test_a_peak_still_on_column_after_the_last_segment_is_wash_eluted_too() -> None:
    """v0.1's post-gradient branch — run 6 as a single ramp puts Unknown-3 at ~110 min."""
    washed = _badges(_lab(LAB_RUN6.gradient), "wash_eluted")
    assert list(washed) == ["Unknown-3"]
    assert "after the programme ends" in washed["Unknown-3"].message


def test_the_initial_hold_is_diagnostic_2s_not_diagnostic_9s() -> None:
    """A band that never meets the gradient is early, not wash-eluted."""
    long_hold = Gradient(phi0=0.60, phif=0.95, t_gradient=25.0, t_init=30.0)
    diagnostics = _lab(long_hold)
    assert _badges(diagnostics, "wash_eluted") == {}
    assert _badges(diagnostics, "early_eluter")


# --- the indicative stamp and what it downgrades --------------------------------------------


def test_inside_the_bracket_at_the_scouting_start_nothing_is_stamped() -> None:
    diagnostics = _lab(_scouting(25.0))
    assert diagnostics.indicative is None
    assert diagnostics.pair_is_indicative(("Unknown-1", "Unknown-2")) is False


def test_gentle_on_1_or_7_leaves_the_numbers_unstamped() -> None:
    assert _lab(_scouting(60.0)).indicative is None  # 0.26 window-widths
    assert _lab(Gradient(0.07, 0.95, 25.0, 0.5)).indicative is None  # +2 %B


def test_strong_on_7_stamps_rs_and_the_critical_pair_indicative() -> None:
    stamp = _lab(Gradient(0.15, 0.95, 25.0, 0.5)).indicative
    assert stamp is not None
    assert stamp.code == "indicative"
    assert stamp.severity == "strong"
    assert "indicative, not decision-grade" in stamp.message
    assert "never pinned" in stamp.message


def test_strong_on_1_stamps_too_and_the_ladder_is_the_worse_of_the_two() -> None:
    diagnostics = _lab(_scouting(120.0))  # 0.89 window-widths, φ0 unchanged
    assert diagnostics.indicative is not None
    assert "steepness" in diagnostics.indicative.message
    assert diagnostics.pair_is_indicative(("Unknown-1", "Unknown-2")) is True


def test_a_badge_downgrades_only_the_pairs_involving_that_peak() -> None:
    diagnostics = _lab(LAB_RUN6_PROGRAMME)  # Unknown-3 wash-eluted; run 6 is also strong on 7
    assert diagnostics.pair_is_indicative(("Unknown-2", "Unknown-3")) is True
    unstamped = _lab(Gradient(0.05, 0.55, 25.0, 0.5))  # same ramp from the scouting start
    assert unstamped.indicative is None
    assert list(_badges(unstamped, "wash_eluted")) == ["Unknown-3"]
    assert unstamped.pair_is_indicative(("Unknown-2", "Unknown-3")) is True
    assert unstamped.pair_is_indicative(("Unknown-1", "Unknown-2")) is False


def test_the_stamp_never_claims_curvature_corrected_accuracy() -> None:
    stamp = _lab(Gradient(0.25, 0.95, 25.0, 0.5)).indicative
    assert stamp is not None
    assert "curvature" not in stamp.message.lower() or "cannot see curvature" in stamp.message


# --- the per-peak composition-window readout -------------------------------------------------


def test_every_fitted_peak_has_a_window_and_it_is_the_fits_own_elution_compositions() -> None:
    """[φ_e,run2, φ_e,run1] per peak, width ln β / S_e — research doc §2.2's ~9 %B."""
    windows = {window.name: window for window in _lab(_scouting(25.0)).windows}
    assert set(windows) == {"Unknown-1", "Unknown-2", "Unknown-3"}
    for window in windows.values():
        assert window.phi_low < window.phi_high
        assert window.width == pytest.approx(window.phi_high - window.phi_low, rel=1e-9)
        assert 0.08 < window.width < 0.10  # ~9 %B per peak on the 5 → 95 %B scouting pair
    lows = sorted(window.phi_low for window in windows.values())
    highs = sorted(window.phi_high for window in windows.values())
    assert all(high < low for high, low in zip(highs, lows[1:], strict=False))  # disjoint


def test_the_readout_says_where_the_candidate_puts_each_peak() -> None:
    inside = {w.name: w for w in _lab(_scouting(25.0)).windows}
    assert all(w.position == "inside" for w in inside.values())
    for window in inside.values():
        assert window.phi_low <= window.candidate_phi_e <= window.phi_high
    below = {w.name: w for w in _lab(_scouting(60.0)).windows}
    assert all(w.position == "below" for w in below.values())
    # 0.260–0.262 per peak against the research doc's 0.262: the exact LSS elution
    # composition against the large-k0 law the doc's number was worked with.
    assert all(w.distance_in_widths == pytest.approx(0.262, abs=0.003) for w in below.values())
    above = {w.name: w for w in _lab(_scouting(7.0)).windows}
    assert all(w.position == "above" for w in above.values())


def test_a_peak_leaving_in_a_hold_reports_the_holds_composition() -> None:
    windows = {w.name: w for w in _lab(LAB_RUN6_PROGRAMME).windows}
    assert windows["Unknown-3"].candidate_phi_e == pytest.approx(0.95)
    assert windows["Unknown-3"].position == "above"


# --- SPEC §10 item 2: fire / silent on named runs, both samples ---------------------------
#
# Every held-out run of both samples as the Cockpit would hold it — the fixture's own
# programme where the instrument ran one (three-peak run 6, four-peak run 5), the
# gradient otherwise — diagnosed through the same call the app makes. The expected
# table is SPEC §10 item 2's, transcribed; nothing here is recomputed from the code.

_THREE_PEAK = spec10_item2.THREE_PEAK
_FOUR_PEAK = spec10_item2.FOUR_PEAK
_TABLE = spec10_item2.TABLE


def _diagnose(sample: str, run: str) -> Diagnostics:
    return diagnose(spec10_item2.inputs_for(sample, run))


def _tier(diagnostics: Diagnostics, code: str) -> str | None:
    found = [d for d in diagnostics.candidate if d.code == code]
    return found[0].severity if found else None


@pytest.mark.parametrize(("sample", "run"), list(_TABLE), ids=spec10_item2.IDS)
def test_the_fire_silent_table_of_spec_10_item_2(sample: str, run: str) -> None:
    diagnostics = _diagnose(sample, run)
    tier_1, tier_7, low_k0, wash = _TABLE[(sample, run)]
    assert _tier(diagnostics, "steepness_extrapolation") == tier_1, "diagnostic 1"
    assert _tier(diagnostics, "phi0_departure") == tier_7, "diagnostic 7"
    assert tuple(_badges(diagnostics, "low_k0")) == low_k0, "diagnostic 8"
    assert tuple(_badges(diagnostics, "wash_eluted")) == wash, "diagnostic 9"


def test_the_table_covers_every_held_out_run_the_spec_names() -> None:
    assert {r for s, r in _TABLE if s == "three-peak"} == set(_THREE_PEAK)
    assert {r for s, r in _TABLE if s == "four-peak"} == set(_FOUR_PEAK)


def test_the_window_widths_are_the_specs_on_the_two_gentle_runs() -> None:
    """0.26 on three-peak run 4, 0.20 on run 6's ramp peaks (SPEC §10 item 2)."""
    (run4,) = _steepness(_diagnose("three-peak", "run4"))
    assert "0.26 window-widths" in run4.message
    (run6,) = _steepness(_diagnose("three-peak", "run6"))
    assert "0.20 window-widths" in run6.message


# --- SPEC §10 item 3: the stamped runs are the fixtures' own stamped sets -------------------


@pytest.mark.parametrize("run", LAB_STAMPED + LAB_UNSTAMPED)
def test_three_peak_runs_are_stamped_exactly_where_the_reality_layer_says(run: str) -> None:
    stamped = _diagnose("three-peak", run).indicative is not None
    assert stamped == (run in LAB_STAMPED), run


_FOUR_PEAK_CLASSIFIED = [r for r in VALIDATION2_STAMPED + VALIDATION2_UNSTAMPED if r in _FOUR_PEAK]


@pytest.mark.parametrize("run", _FOUR_PEAK_CLASSIFIED)
def test_four_peak_runs_are_stamped_exactly_where_the_reality_layer_says(run: str) -> None:
    stamped = _diagnose("four-peak", run).indicative is not None
    assert stamped == (run in VALIDATION2_STAMPED), run


# --- v0.1 continuity: one segment over the scouting range -----------------------------------


_TG_SWEEP = [5.0, 7.0, 10.0, 14.9, 15.0, 25.0, 45.0, 45.1, 60.0, 87.0, 91.0, 180.0]


@pytest.mark.parametrize("t_gradient", _TG_SWEEP)
def test_a_v01_session_fires_diagnostic_1_where_the_tg_bracket_did(t_gradient: float) -> None:
    """One segment over the scouting range: s* ∝ 1/tG, so the s* bracket *is* the tG
    bracket, and the distance in window-widths is log_β of the tG multiple."""
    lo, hi = 15.0, 45.0
    flags = _steepness(_lab(_scouting(t_gradient)))
    outside = t_gradient < lo or t_gradient > hi
    assert bool(flags) == outside
    if outside:
        factor = t_gradient / hi if t_gradient > hi else lo / t_gradient
        widths = math.log(factor, 3.0)
        assert f"{widths:.2f} window-widths" in flags[0].message
        assert flags[0].severity == ("strong" if widths > STRONG_WINDOW_WIDTHS else "info")


def test_where_the_0_6_tier_departs_from_v01s_2x_and_that_no_run_on_file_sits_there() -> None:
    """SPEC §6 item 1 keeps 0.6 as v0.1 continuity (log₃ 2 = 0.63). The two rules differ
    only for tG multiples between 3^0.6 = 1.93 and 2.0 at β = 3 — strong now, gentle in
    v0.1. Pinned here so the band is known, not discovered; no bench run sits in it."""
    departs_from, departs_to = 3.0**STRONG_WINDOW_WIDTHS, 2.0
    assert 1.93 < departs_from < 1.94
    assert _lab(_scouting(45.0 * 1.95)).candidate[0].severity == "strong"
    assert _lab(_scouting(45.0 * 1.90)).candidate[0].severity == "info"
    for target in (*_THREE_PEAK.values(), *_FOUR_PEAK.values()):
        single = target.as_gradient() if isinstance(target, Programme) else target
        if single is None or single.phi0 != 0.05 or single.phif != 0.95:
            continue
        factor = max(single.t_gradient / 45.0, 15.0 / single.t_gradient, 1.0)
        assert not departs_from < factor <= departs_to, single


def test_a_v01_session_draws_none_of_the_v02_diagnostics() -> None:
    """Over the scouting range at the scouting start, from the scouting compounds: no 7,
    no 8, no 9, no stamp — v0.1's screen, unchanged."""
    diagnostics = _lab(_scouting(25.0))
    assert _tier(diagnostics, "phi0_departure") is None
    assert _badges(diagnostics, "low_k0") == {}
    assert _badges(diagnostics, "wash_eluted") == {}
    assert diagnostics.indicative is None
    v02_codes = {"phi0_departure", "low_k0", "wash_eluted", "indicative"}
    assert not v02_codes & {d.code for d in diagnostics.all}


def test_the_diagnostics_module_is_streamlit_free() -> None:
    import app.diagnostics as module

    imports = [
        line
        for line in pathlib.Path(module.__file__).read_text().splitlines()
        if line.startswith(("import ", "from "))
    ]
    assert imports and not any("streamlit" in line for line in imports)
