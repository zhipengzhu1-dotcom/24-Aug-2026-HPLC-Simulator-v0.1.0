"""Session file round-trip and rejection rules (SPEC §8).

The property that matters is ``load_session(save_session(s)) == s`` for every input
the user can type; everything else here is a rejection rule, each one asserting that
the message names the field a chromatographer would go and fix.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from typing import Any

import pytest

import hplcsim
from hplcsim.model import Gradient, Method, Peak, Run, phi_from_percent_b
from hplcsim.session import (
    SCHEMA_VERSION,
    Session,
    SessionFileError,
    UntrackedPeak,
    load_session,
    save_session,
)

FULL_SESSION = Session(
    session_name="Impurity screen 2026-08-27",
    method=Method(
        t0=0.6,
        t_dwell=0.9375,
        flow=0.4,
        column_length_mm=100.0,
        column_id_mm=2.1,
        particle_um=1.6,
        temperature_c=45.0,
        t0_is_measured=True,
    ),
    runs=(
        Run(Gradient(phi0=0.05, phif=0.95, t_gradient=15.0, t_init=0.5), name="tG15"),
        Run(Gradient(phi0=0.05, phif=0.95, t_gradient=45.0, t_init=0.5), name="tG45"),
    ),
    peaks=(
        Peak(
            t_r_run1=9.855,
            t_r_run2=20.831,
            name="Unknown-1",
            area_run1=13352.0,
            area_run2=13401.0,
            w_half_run1=0.033,
            w_half_run2=0.061,
        ),
        Peak(t_r_run1=11.592, t_r_run2=25.932, name="Unknown-2"),
    ),
    candidate=Gradient(phi0=0.05, phif=0.95, t_gradient=25.0, t_init=0.5),
    plate_count=12000,
)

# Nothing optional filled in: no column geometry, no names, no areas or widths, no N.
MINIMAL_SESSION = Session(
    method=Method(t0=0.6, t_dwell=0.9375, flow=0.4),
    runs=(
        Run(Gradient(phi0=0.05, phif=0.95, t_gradient=15.0)),
        Run(Gradient(phi0=0.05, phif=0.95, t_gradient=45.0)),
    ),
    peaks=(Peak(t_r_run1=9.855, t_r_run2=20.831),),
    candidate=Gradient(phi0=0.05, phif=0.95, t_gradient=25.0),
)

# Mid-entry: four peaks paired, one still half-tracked. This is the shape the file
# could not carry before ticket #21, and the moment a chromatographer most often saves.
HALF_TRACKED_SESSION = Session(
    method=MINIMAL_SESSION.method,
    runs=MINIMAL_SESSION.runs,
    peaks=FULL_SESSION.peaks,
    untracked=(
        UntrackedPeak(name="P3", t_r_run1=13.204, area_run1=8801.0),
        UntrackedPeak(name="P4", t_r_run2=31.006),
        UntrackedPeak(name="P5"),
    ),
    candidate=MINIMAL_SESSION.candidate,
)


def _file_of(session: Session) -> dict[str, Any]:
    """The saved session as parsed JSON, for tests that inspect the file itself."""
    parsed: dict[str, Any] = json.loads(save_session(session))
    return parsed


def _mutated(session: Session, mutate: Callable[[dict[str, Any]], object]) -> str:
    """Save ``session``, then apply ``mutate`` to the parsed file and re-serialize."""
    parsed = _file_of(session)
    mutate(parsed)
    return json.dumps(parsed)


# --- round trip -------------------------------------------------------------------


@pytest.mark.parametrize("session", [FULL_SESSION, MINIMAL_SESSION, HALF_TRACKED_SESSION])
def test_round_trip_is_equality(session: Session) -> None:
    assert load_session(save_session(session)) == session


def test_round_trip_preserves_estimated_t0_source() -> None:
    estimated = Session(
        method=Method(t0=0.55, t_dwell=0.9375, flow=0.4, t0_is_measured=False),
        runs=MINIMAL_SESSION.runs,
        peaks=MINIMAL_SESSION.peaks,
        candidate=MINIMAL_SESSION.candidate,
    )
    assert _file_of(estimated)["method"]["t0_source"] == "estimated"
    assert load_session(save_session(estimated)) == estimated


def test_round_trip_accepts_bytes_as_uploaded() -> None:
    uploaded = save_session(FULL_SESSION).encode("utf-8")
    assert load_session(uploaded) == FULL_SESSION


def test_empty_peak_table_round_trips() -> None:
    partial = Session(
        method=MINIMAL_SESSION.method,
        runs=MINIMAL_SESSION.runs,
        peaks=(),
        candidate=MINIMAL_SESSION.candidate,
    )
    assert load_session(save_session(partial)) == partial


# --- what the file looks like ------------------------------------------------------


def test_file_stamps_schema_and_app_version() -> None:
    parsed = _file_of(FULL_SESSION)
    assert parsed["schema_version"] == SCHEMA_VERSION
    assert parsed["app_version"] == hplcsim.__version__


def test_file_speaks_user_units_not_engine_units() -> None:
    method = _file_of(FULL_SESSION)["method"]
    assert method["pct_b_start"] == pytest.approx(5.0)
    assert method["pct_b_end"] == pytest.approx(95.0)
    assert method["t0_source"] == "measured"
    assert "phi0" not in method


def test_file_holds_no_fitted_results() -> None:
    text = save_session(FULL_SESSION)
    for fitted in ("s_e", "ln_k0", "log10_k0", "phi_ref", "beta", "residual", "implied_run"):
        assert fitted not in text


def test_peaks_are_stored_once_row_per_compound() -> None:
    # The tracking decision (SPEC §5) pairs peaks at entry; nesting them per run would
    # force name-based re-matching on load, and names are optional.
    parsed = _file_of(FULL_SESSION)
    peaks = parsed["peaks"]
    assert peaks[0]["tr_run1_min"] == pytest.approx(9.855)
    assert peaks[0]["tr_run2_min"] == pytest.approx(20.831)
    assert all("peaks" not in run for run in parsed["runs"])


def test_unset_optional_fields_are_omitted_not_null() -> None:
    parsed = _file_of(MINIMAL_SESSION)
    assert "session_name" not in parsed
    assert "column_length_mm" not in parsed["method"]
    assert "plate_count" not in parsed["method"]
    assert "area_run1" not in parsed["peaks"][0]
    assert "name" not in parsed["peaks"][0]


# --- half-paired rows (SPEC §5, ticket #21) -----------------------------------------
#
# Before this the file had nowhere to put a row missing one tR, so a chromatographer who
# had paired four peaks of five, saved, and reloaded got four rows back and no word about
# the fifth. These pin the shape that ended that: a second top-level table, absent when
# there is nothing in it, holding rows that are the same shape as a peak minus the
# guarantee of a pair.


def test_a_half_paired_row_survives_the_round_trip() -> None:
    """AC-1's unmet corner from #18: saving mid-entry must lose nothing."""
    restored = load_session(save_session(HALF_TRACKED_SESSION))
    assert restored.untracked == HALF_TRACKED_SESSION.untracked
    assert restored == HALF_TRACKED_SESSION


def test_an_untracked_row_keeps_the_measurements_it_does_have() -> None:
    row = _file_of(HALF_TRACKED_SESSION)["untracked_peaks"][0]
    assert row["name"] == "P3"
    assert row["tr_run1_min"] == pytest.approx(13.204)
    assert row["area_run1"] == pytest.approx(8801.0)
    # The missing half is absent, not null — the same rule every other unset field follows.
    assert "tr_run2_min" not in row


def test_a_fully_paired_session_writes_no_untracked_table() -> None:
    """A finished session's file looks exactly as it did before the key existed."""
    assert "untracked_peaks" not in _file_of(FULL_SESSION)


def test_a_file_without_the_untracked_key_loads_as_no_untracked_rows() -> None:
    """Every session file saved before ticket #21 still opens."""
    text = _mutated(HALF_TRACKED_SESSION, lambda f: f.pop("untracked_peaks"))
    assert load_session(text).untracked == ()


def test_an_untracked_row_with_both_retention_times_is_refused_on_load() -> None:
    """It is a tracked peak filed in the wrong list, and the count would then lie."""
    text = _mutated(
        HALF_TRACKED_SESSION,
        lambda f: f["untracked_peaks"][0].__setitem__("tr_run2_min", 28.4),
    )
    with pytest.raises(SessionFileError, match=r"untracked_peaks\[0\].*belongs in peaks"):
        load_session(text)


def test_an_untracked_row_with_both_retention_times_is_refused_on_save_too() -> None:
    """Saving must not write a file this app would then refuse to open."""
    both = replace(
        HALF_TRACKED_SESSION,
        untracked=(UntrackedPeak(name="P3", t_r_run1=13.204, t_r_run2=28.4),),
    )
    with pytest.raises(SessionFileError, match="belongs in peaks"):
        save_session(both)


def test_a_negative_measurement_on_an_untracked_row_names_the_row() -> None:
    text = _mutated(
        HALF_TRACKED_SESSION,
        lambda f: f["untracked_peaks"][0].__setitem__("tr_run1_min", -1.0),
    )
    with pytest.raises(SessionFileError, match=r"untracked_peaks\[0\]\.tr_run1_min"):
        load_session(text)


def test_an_untracked_table_that_is_not_a_list_is_rejected() -> None:
    text = _mutated(HALF_TRACKED_SESSION, lambda f: f.__setitem__("untracked_peaks", 3))
    with pytest.raises(SessionFileError, match="untracked_peaks must be a JSON list"):
        load_session(text)


# --- schema rejection --------------------------------------------------------------


def test_unknown_schema_version_is_rejected_by_number() -> None:
    text = _mutated(FULL_SESSION, lambda f: f.__setitem__("schema_version", 2))
    with pytest.raises(SessionFileError, match="schema_version 2"):
        load_session(text)


def test_missing_schema_version_is_rejected() -> None:
    text = _mutated(FULL_SESSION, lambda f: f.pop("schema_version"))
    with pytest.raises(SessionFileError, match="schema_version"):
        load_session(text)


def test_missing_app_version_is_rejected() -> None:
    text = _mutated(FULL_SESSION, lambda f: f.pop("app_version"))
    with pytest.raises(SessionFileError, match="app_version"):
        load_session(text)


def test_non_text_app_version_is_rejected() -> None:
    text = _mutated(FULL_SESSION, lambda f: f.__setitem__("app_version", 0.1))
    with pytest.raises(SessionFileError, match="app_version"):
        load_session(text)


def test_unparseable_json_is_rejected() -> None:
    with pytest.raises(SessionFileError, match="not valid JSON"):
        load_session("{not json at all")


def test_non_object_top_level_is_rejected() -> None:
    with pytest.raises(SessionFileError, match="JSON object"):
        load_session("[1, 2, 3]")


# --- field validation --------------------------------------------------------------


def test_missing_mandatory_field_names_it() -> None:
    text = _mutated(FULL_SESSION, lambda f: f["method"].pop("t0_min"))
    with pytest.raises(SessionFileError, match="method.t0_min"):
        load_session(text)


def test_missing_mandatory_block_names_it() -> None:
    text = _mutated(FULL_SESSION, lambda f: f.pop("method"))
    with pytest.raises(SessionFileError, match="method"):
        load_session(text)


def test_non_numeric_value_names_the_field() -> None:
    text = _mutated(FULL_SESSION, lambda f: f["method"].__setitem__("flow_ml_min", "0.4 mL/min"))
    with pytest.raises(SessionFileError, match="method.flow_ml_min"):
        load_session(text)


def test_percent_b_outside_zero_to_hundred_is_rejected() -> None:
    # The classic bad-unit paste: %B entered as a 0–1 fraction, or over 100.
    text = _mutated(FULL_SESSION, lambda f: f["method"].__setitem__("pct_b_end", 120.0))
    with pytest.raises(SessionFileError, match="pct_b_end"):
        load_session(text)


def test_non_positive_flow_is_rejected() -> None:
    text = _mutated(FULL_SESSION, lambda f: f["method"].__setitem__("flow_ml_min", 0.0))
    with pytest.raises(SessionFileError, match="flow_ml_min"):
        load_session(text)


def test_negative_time_is_rejected() -> None:
    text = _mutated(FULL_SESSION, lambda f: f["method"].__setitem__("dwell_min", -0.5))
    with pytest.raises(SessionFileError, match="dwell_min"):
        load_session(text)


def test_unknown_t0_source_is_rejected_with_the_allowed_values() -> None:
    text = _mutated(FULL_SESSION, lambda f: f["method"].__setitem__("t0_source", "guessed"))
    with pytest.raises(SessionFileError, match="measured"):
        load_session(text)


def test_wrong_number_of_runs_is_rejected() -> None:
    text = _mutated(FULL_SESSION, lambda f: f["runs"].pop())
    with pytest.raises(SessionFileError, match="runs"):
        load_session(text)


def test_peak_missing_a_retention_time_names_the_row() -> None:
    text = _mutated(FULL_SESSION, lambda f: f["peaks"][1].pop("tr_run2_min"))
    with pytest.raises(SessionFileError, match=r"peaks\[1\].tr_run2_min"):
        load_session(text)


def test_non_integer_plate_count_is_rejected() -> None:
    text = _mutated(FULL_SESSION, lambda f: f["method"].__setitem__("plate_count", 12000.5))
    with pytest.raises(SessionFileError, match="plate_count"):
        load_session(text)


def test_boolean_is_not_accepted_as_a_number() -> None:
    text = _mutated(FULL_SESSION, lambda f: f["method"].__setitem__("t0_min", True))
    with pytest.raises(SessionFileError, match="t0_min"):
        load_session(text)


# --- save-side invariants the flat file layout depends on --------------------------


def test_saving_runs_that_differ_beyond_gradient_time_is_refused() -> None:
    diverged = Session(
        method=MINIMAL_SESSION.method,
        runs=(
            MINIMAL_SESSION.runs[0],
            Run(Gradient(phi0=0.10, phif=0.95, t_gradient=45.0)),
        ),
        peaks=MINIMAL_SESSION.peaks,
        candidate=MINIMAL_SESSION.candidate,
    )
    with pytest.raises(SessionFileError, match="gradient time"):
        save_session(diverged)


def test_saving_a_candidate_outside_the_scouting_range_is_refused() -> None:
    diverged = Session(
        method=MINIMAL_SESSION.method,
        runs=MINIMAL_SESSION.runs,
        peaks=MINIMAL_SESSION.peaks,
        candidate=Gradient(phi0=0.20, phif=0.80, t_gradient=25.0),
    )
    with pytest.raises(SessionFileError, match="candidate"):
        save_session(diverged)


def test_saving_out_of_range_input_is_refused_the_same_way_as_loading() -> None:
    bad = Session(
        method=Method(t0=0.6, t_dwell=0.9375, flow=-0.4),
        runs=MINIMAL_SESSION.runs,
        peaks=MINIMAL_SESSION.peaks,
        candidate=MINIMAL_SESSION.candidate,
    )
    with pytest.raises(SessionFileError, match="flow_ml_min"):
        save_session(bad)


def test_percent_b_survives_the_round_trip_across_the_whole_range() -> None:
    # The file speaks %B and the engine speaks phi, so the round trip is only equality
    # if that boundary is exactly reversible for compositions a user can actually type.
    for tenths in range(0, 1001):
        pct_b_start = tenths / 10.0
        session = Session(
            method=MINIMAL_SESSION.method,
            runs=(
                Run(Gradient(phi_from_percent_b(pct_b_start), 0.95, 15.0)),
                Run(Gradient(phi_from_percent_b(pct_b_start), 0.95, 45.0)),
            ),
            peaks=(),
            candidate=Gradient(phi_from_percent_b(pct_b_start), 0.95, 25.0),
        )
        assert load_session(save_session(session)) == session
