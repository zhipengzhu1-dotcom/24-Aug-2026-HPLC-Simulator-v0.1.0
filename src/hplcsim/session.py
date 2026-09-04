"""The session file: save and load the user's inputs as one JSON document (SPEC §8).

**Inputs only.** Fitted parameters are never written, so a saved file cannot carry a
stale fit that contradicts the inputs it came from; the fit recomputes on load.

Like every other boundary in this engine the file speaks *user* units — %B on 0–100,
minutes, mL — while :class:`~hplcsim.model.Method`, :class:`~hplcsim.model.Gradient`
and friends keep φ on 0–1. The conversion is the one in ``model``; nothing here
converts by hand. That boundary is exactly reversible for compositions a user can
type, because a φ that arrived as ``percent / 100`` returns to that percent unchanged.

Two places diverge from the schema sketch in SPEC §8, which the spec now records:

* **Peaks are stored once, one row per compound**, with both retention times (and both
  optional areas and widths) on the row, rather than nested inside each run. That is
  the shape peak tracking produces (SPEC §5): the chromatographer pairs the peaks while
  typing, names are optional, and nesting would force name-based re-matching on load.
* **Dwell is stored in minutes** (``dwell_min``), the engine's own quantity, rather than
  as a volume that only becomes a time by dividing by the flow rate. V_D ÷ F is an
  entry-boundary conversion; keeping it out of the file makes the dwell independent of
  a later edit to the flow, and keeps the round trip exact.
* **Half-paired rows have their own list** (``untracked_peaks``), added by ticket #21.
  SPEC §5 keeps rows missing a tR visible as "untracked — not fitted" while insisting
  the engine sees only complete pairs, so :class:`~hplcsim.model.Peak` stays strict and
  :class:`~hplcsim.model.PeakRow` carries the unfinished ones. Mid-entry is exactly the
  moment someone saves; before this the unpaired row was dropped from the file in
  silence. What keeps the two lists meaning what they say is ``_check_untracked``, not
  the row type: a ``PeakRow`` with both retention times is refused from
  ``untracked_peaks`` on save and on load.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Final

from hplcsim import __version__
from hplcsim.dead_time import architecture_of
from hplcsim.model import (
    PERCENT_B_RANGE,
    Gradient,
    Method,
    Peak,
    PeakRow,
    Programme,
    Run,
    Segment,
    percent_b_from_phi,
    phi_from_percent_b,
)

# The version every file is written at. Version 1 (v0.1: a two-field candidate over the
# scouting range) is still read — see ``_read_candidate`` — so the rule on load is
# "a version this app knows", not an exact match (SPEC §8, #47).
SCHEMA_VERSION: Final = 2
KNOWN_SCHEMA_VERSIONS: Final = (1, 2)

# t0_source in the file <-> Method.t0_is_measured, which stamps SPEC §6 diagnostic 6.
_T0_SOURCES: Final = {"measured": True, "estimated": False}

# particle_architecture in the file <-> Method.particle_is_solid_core, the input the
# geometry estimate of t0 selects its porosity by (#24). The file's names are the
# engine's own ``Architecture`` literal (``dead_time.architecture_of`` writes them);
# absent when undeclared, like every other unset field — the estimator refuses on
# ``None`` rather than guessing.
_ARCHITECTURES: Final = {"fully_porous": False, "core_shell": True}

_TWO_RUNS: Final = "session file: runs must hold exactly two scouting runs"


class SessionFileError(ValueError):
    """A session file this app cannot read, or a session it cannot faithfully write.

    User *entry* warns rather than blocks (see CLAUDE.md), but a file that is corrupt,
    of an unknown schema, or missing a mandatory field has no usable reading — so this
    is a hard error, worded to name the field to go and fix.
    """


@dataclass(frozen=True)
class Session:
    """Everything the user entered: the unit that is saved and restored.

    The two scouting runs share every gradient setting but ``t_gradient`` (SPEC §4), and
    the file stores those shared settings once. ``candidate`` — the what-if programme on
    screen — is free of them since v0.2 (SPEC §4, #44): its own start, hold and segment
    rows, one segment being exactly v0.1's gradient (:meth:`Programme.as_gradient`).

    ``peaks`` and ``untracked`` are the peak table split in two: the pairs the engine
    may fit, and the rows still being typed. ``untracked`` defaults to empty, so every
    session built before ticket #21 still constructs.
    """

    method: Method
    runs: tuple[Run, Run]
    peaks: tuple[Peak, ...]
    candidate: Programme
    untracked: tuple[PeakRow, ...] = ()
    session_name: str = ""
    plate_count: int | None = None


def save_session(session: Session) -> str:
    """Serialize a session to the JSON text of SPEC §8, ready to hand to a download."""
    _check_inputs(session)
    shared = session.runs[0].gradient
    document = {
        "schema_version": SCHEMA_VERSION,
        "app_version": __version__,
        **_drop_unset({"session_name": session.session_name or None}),
        "method": _method_block(session, shared),
        "runs": [_run_row(run) for run in session.runs],
        "peaks": [_peak_row(peak) for peak in session.peaks],
        # Absent rather than empty when everything is paired, like every other unset
        # field — a finished session's file looks exactly as it did before ticket #21.
        **_drop_unset({"untracked_peaks": [_peak_row(row) for row in session.untracked] or None}),
        "candidate": _candidate_block(session.candidate),
    }
    return json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def load_session(text: str | bytes) -> Session:
    """Restore a session from file text, rejecting anything that cannot be read back."""
    document = _parse(text)
    version = _check_versions(document)

    method_block = document.block("method")
    candidate_block = document.block("candidate")
    shared = Gradient(
        phi0=phi_from_percent_b(method_block.number("pct_b_start")),
        phif=phi_from_percent_b(method_block.number("pct_b_end")),
        t_gradient=0.0,
        t_init=method_block.number_or("hold_min", 0.0),
    )
    session = Session(
        method=_read_method(method_block),
        runs=_read_runs(document.rows("runs"), shared),
        peaks=tuple(_read_peak(row) for row in document.rows("peaks")),
        untracked=tuple(_read_untracked(row) for row in document.optional_rows("untracked_peaks")),
        candidate=_read_candidate(candidate_block, shared, version),
        session_name=document.text("session_name", ""),
        plate_count=method_block.whole_number("plate_count"),
    )
    _check_inputs(session)
    return session


# --- writing ------------------------------------------------------------------------


def _method_block(session: Session, shared: Gradient) -> dict[str, Any]:
    """The method page as the file holds it: constants, the shared gradient, and N."""
    method = session.method
    return _drop_unset(
        {
            "column_length_mm": method.column_length_mm,
            "column_id_mm": method.column_id_mm,
            "particle_um": method.particle_um,
            "flow_ml_min": method.flow,
            "temperature_c": method.temperature_c,
            "t0_min": method.t0,
            "t0_source": "measured" if method.t0_is_measured else "estimated",
            "t0_marker": method.t0_marker or None,
            "particle_architecture": architecture_of(method),
            "dwell_min": method.t_dwell,
            "pct_b_start": percent_b_from_phi(shared.phi0),
            "pct_b_end": percent_b_from_phi(shared.phif),
            "hold_min": shared.t_init,
            "plate_count": session.plate_count,
        }
    )


def _candidate_block(candidate: Programme) -> dict[str, Any]:
    """The candidate as the rows the rail's table shows (SPEC §7, §8): start, hold, segments."""
    return {
        "pct_b_start": percent_b_from_phi(candidate.phi0),
        "hold_min": candidate.t_init,
        "segments": [
            {"tg_min": segment.duration, "pct_b_end": percent_b_from_phi(segment.phif)}
            for segment in candidate.segments
        ],
    }


def _run_row(run: Run) -> dict[str, Any]:
    return _drop_unset({"tg_min": run.gradient.t_gradient, "name": run.name or None})


def _peak_row(peak: Peak | PeakRow) -> dict[str, Any]:
    """One compound, both runs side by side — the row the peak table shows (SPEC §5).

    One writer for both lists. A ``Peak`` always fills in both retention times and a
    ``PeakRow`` in ``untracked`` never fills in more than one, so ``_drop_unset`` is
    what makes the two rows differ — the shape of the row itself is the same either way.
    """
    return _drop_unset(
        {
            "name": peak.name or None,
            "tr_run1_min": peak.t_r_run1,
            "tr_run2_min": peak.t_r_run2,
            "area_run1": peak.area_run1,
            "area_run2": peak.area_run2,
            "w_half_run1_min": peak.w_half_run1,
            "w_half_run2_min": peak.w_half_run2,
        }
    )


def _drop_unset(fields: Mapping[str, Any]) -> dict[str, Any]:
    """Leave what the user never filled in out of the file rather than writing nulls."""
    return {key: value for key, value in fields.items() if value is not None}


# --- reading ------------------------------------------------------------------------


@dataclass(frozen=True)
class _Fields:
    """One JSON object being read, carrying the dotted path that names it to the user."""

    data: Mapping[str, Any]
    path: str = ""

    def at(self, key: str) -> str:
        return f"{self.path}.{key}" if self.path else key

    def raw(self, key: str) -> Any:
        if key not in self.data:
            raise SessionFileError(f"session file: {self.at(key)} is required but missing")
        return self.data[key]

    def block(self, key: str) -> _Fields:
        value = self.raw(key)
        if not isinstance(value, Mapping):
            raise SessionFileError(f"session file: {self.at(key)} must be a JSON object")
        return _Fields(value, self.at(key))

    def rows(self, key: str) -> list[_Fields]:
        value = self.raw(key)
        if not isinstance(value, Sequence) or isinstance(value, str | bytes):
            raise SessionFileError(f"session file: {self.at(key)} must be a JSON list")
        rows = []
        for index, item in enumerate(value):
            path = f"{self.at(key)}[{index}]"
            if not isinstance(item, Mapping):
                raise SessionFileError(f"session file: {path} must be a JSON object")
            rows.append(_Fields(item, path))
        return rows

    def optional_rows(self, key: str) -> list[_Fields]:
        """A table that may simply be absent, read as empty — never as a missing field."""
        return [] if self.data.get(key) is None else self.rows(key)

    def number(self, key: str) -> float:
        return self._number(key, self.raw(key))

    def number_or(self, key: str, default: float) -> float:
        value = self.data.get(key)
        return default if value is None else self._number(key, value)

    def optional_number(self, key: str) -> float | None:
        value = self.data.get(key)
        return None if value is None else self._number(key, value)

    def whole_number(self, key: str) -> int | None:
        value = self.optional_number(key)
        if value is None:
            return None
        if value != int(value):
            raise SessionFileError(
                f"session file: {self.at(key)} must be a whole number, got {value:g}"
            )
        return int(value)

    def text(self, key: str, default: str) -> str:
        value = self.data.get(key, default)
        if not isinstance(value, str):
            raise SessionFileError(f"session file: {self.at(key)} must be text, got {value!r}")
        return value

    def optional_text(self, key: str) -> str | None:
        """Free text the user may not have entered — absent and blank both read as unset."""
        value = self.data.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise SessionFileError(f"session file: {self.at(key)} must be text, got {value!r}")
        return value.strip() or None

    def _number(self, key: str, value: Any) -> float:
        # bool is an int in Python, but `true` is never a measurement.
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise SessionFileError(f"session file: {self.at(key)} must be a number, got {value!r}")
        if not math.isfinite(value):
            raise SessionFileError(f"session file: {self.at(key)} must be a finite number")
        return float(value)


def _parse(text: str | bytes) -> _Fields:
    """Uploaded bytes or text -> the top-level object, or a hard error saying why not."""
    try:
        document = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SessionFileError(f"session file: not valid JSON ({error})") from error
    if not isinstance(document, Mapping):
        raise SessionFileError("session file: the top level must be a JSON object")
    return _Fields(document)


def _check_versions(document: _Fields) -> int:
    """The stamps that make a file readable: a schema this app knows, then provenance."""
    version = document.raw("schema_version")
    # bool is an int in Python, so `true` would otherwise read as version 1.
    if isinstance(version, bool) or version not in KNOWN_SCHEMA_VERSIONS:
        known = " or ".join(str(known) for known in KNOWN_SCHEMA_VERSIONS)
        raise SessionFileError(
            f"session file: schema_version {version!r} is not supported by this app, "
            f"which reads schema_version {known}"
        )
    stamp = document.raw("app_version")
    if not isinstance(stamp, str):
        raise SessionFileError(f"session file: app_version must be text, got {stamp!r}")
    return int(version)


def _read_method(block: _Fields) -> Method:
    return Method(
        t0=block.number("t0_min"),
        t_dwell=block.number("dwell_min"),
        flow=block.number("flow_ml_min"),
        column_length_mm=block.optional_number("column_length_mm"),
        column_id_mm=block.optional_number("column_id_mm"),
        particle_um=block.optional_number("particle_um"),
        temperature_c=block.optional_number("temperature_c"),
        t0_is_measured=_read_t0_source(block),
        particle_is_solid_core=_read_architecture(block),
        t0_marker=block.optional_text("t0_marker"),
    )


def _read_t0_source(block: _Fields) -> bool:
    source = block.text("t0_source", "measured")
    if source not in _T0_SOURCES:
        allowed = ", ".join(_T0_SOURCES)
        raise SessionFileError(
            f"session file: {block.at('t0_source')} must be one of {allowed}; got {source!r}"
        )
    return _T0_SOURCES[source]


def _read_architecture(block: _Fields) -> bool | None:
    name = block.optional_text("particle_architecture")
    if name is None:
        return None
    if name not in _ARCHITECTURES:
        allowed = ", ".join(_ARCHITECTURES)
        raise SessionFileError(
            f"session file: {block.at('particle_architecture')} must be one of {allowed}; "
            f"got {name!r}"
        )
    return _ARCHITECTURES[name]


def _read_runs(rows: list[_Fields], shared: Gradient) -> tuple[Run, Run]:
    """Each run is the shared gradient at its own tG — the only thing that differs."""
    if len(rows) != 2:
        raise SessionFileError(f"{_TWO_RUNS}, got {len(rows)}")
    first, second = (
        Run(replace(shared, t_gradient=row.number("tg_min")), name=row.text("name", ""))
        for row in rows
    )
    return first, second


def _read_candidate(block: _Fields, shared: Gradient, version: int) -> Programme:
    """The candidate's own start, hold and segment rows (SPEC §8, schema version 2).

    A version-1 file stored ``tg_min`` and ``hold_min`` only, because v0.1's candidate
    always spanned the scouting range: that is one segment from the method's start to
    its end — exactly what the file meant, so it is read as that and nothing is asked
    of the user.
    """
    if version == 1:
        return Programme(
            phi0=shared.phi0,
            t_init=block.number_or("hold_min", 0.0),
            segments=(_read_segment(block, shared.phif),),
        )
    rows = block.rows("segments")
    if not rows:
        raise SessionFileError(f"session file: {block.at('segments')} needs at least one segment")
    return Programme(
        phi0=phi_from_percent_b(block.number("pct_b_start")),
        t_init=block.number_or("hold_min", 0.0),
        segments=tuple(
            _read_segment(row, phi_from_percent_b(row.number("pct_b_end"))) for row in rows
        ),
    )


def _read_segment(row: _Fields, phif: float) -> Segment:
    """One row's duration, checked here because ``Segment`` itself refuses a non-positive
    one — and that refusal would not name the row in the file to go and fix."""
    duration = row.number("tg_min")
    _check_positive(row.at("tg_min"), duration)
    return Segment(duration=duration, phif=phif)


def _read_peak(row: _Fields) -> Peak:
    return Peak(
        t_r_run1=row.number("tr_run1_min"),
        t_r_run2=row.number("tr_run2_min"),
        name=row.text("name", ""),
        area_run1=row.optional_number("area_run1"),
        area_run2=row.optional_number("area_run2"),
        w_half_run1=row.optional_number("w_half_run1_min"),
        w_half_run2=row.optional_number("w_half_run2_min"),
    )


def _read_untracked(row: _Fields) -> PeakRow:
    """The same row with both retention times optional — the half-paired one of SPEC §5."""
    return PeakRow(
        t_r_run1=row.optional_number("tr_run1_min"),
        t_r_run2=row.optional_number("tr_run2_min"),
        name=row.text("name", ""),
        area_run1=row.optional_number("area_run1"),
        area_run2=row.optional_number("area_run2"),
        w_half_run1=row.optional_number("w_half_run1_min"),
        w_half_run2=row.optional_number("w_half_run2_min"),
    )


# --- what a session must hold to be worth writing down -------------------------------


def _check_inputs(session: Session) -> None:
    """Impossible values, and structure the flat file cannot carry — checked both ways.

    Saving applies the same rules as loading on purpose. Writing a value that ``load``
    would refuse hands the user a file that fails to open later, which is worse than an
    error naming the field while the value is still on screen and fixable.

    Two things are deliberately *not* checked. SPEC §4's judgement calls — spacing
    ratio, tR ≤ t0 — are warnings there and stay warnings. And two runs sharing a tG,
    which SPEC §4 and CLAUDE.md both make a hard failure, is refused by ``fit`` where
    the impossibility bites: a half-entered session is still worth saving, and refusing
    to *reopen* one would strand the work rather than protect it.
    """
    if len(session.runs) != 2:
        raise SessionFileError(f"{_TWO_RUNS}, got {len(session.runs)}")
    _check_method(session.method)
    _check_positive("method.plate_count", session.plate_count)
    _check_gradient(session.runs)
    _check_candidate(session.candidate)
    for index, peak in enumerate(session.peaks):
        _check_measurements(f"peaks[{index}]", peak)
    for index, row in enumerate(session.untracked):
        _check_untracked(f"untracked_peaks[{index}]", row)


def _check_method(method: Method) -> None:
    _check_positive("method.t0_min", method.t0)
    _check_positive("method.flow_ml_min", method.flow)
    _check_non_negative("method.dwell_min", method.t_dwell)
    _check_positive("method.column_length_mm", method.column_length_mm)
    _check_positive("method.column_id_mm", method.column_id_mm)
    _check_positive("method.particle_um", method.particle_um)
    _check_finite("method.temperature_c", method.temperature_c)


def _check_gradient(runs: tuple[Run, Run]) -> None:
    """The file stores the gradient once and a tG per run, so the runs must agree."""
    first, second = (run.gradient for run in runs)
    if (first.phi0, first.phif, first.t_init) != (second.phi0, second.phif, second.t_init):
        raise SessionFileError(
            "session file: the two scouting runs must differ only in gradient time — "
            "pct_b_start, pct_b_end and hold_min are stored once, for both runs"
        )
    _check_percent("method.pct_b_start", first.phi0)
    _check_percent("method.pct_b_end", first.phif)
    _check_non_negative("method.hold_min", first.t_init)
    for index, run in enumerate(runs):
        _check_positive(f"runs[{index}].tg_min", run.gradient.t_gradient)


def _check_candidate(candidate: Programme) -> None:
    """Impossible values on the candidate's own rows — and nothing about its range.

    Until v0.2 this refused a candidate whose %B range differed from the scouting
    runs'. It no longer does (SPEC §4, #44): leaving the fitted composition window is
    a warning the diagnostics deliver once the session is on screen, never a reason to
    refuse the file.
    """
    _check_percent("candidate.pct_b_start", candidate.phi0)
    _check_non_negative("candidate.hold_min", candidate.t_init)
    # A segment's duration is not checked here: ``Segment`` refuses a non-positive one
    # on construction, and ``_read_segment`` names the row before that can happen.
    for index, segment in enumerate(candidate.segments):
        _check_percent(f"candidate.segments[{index}].pct_b_end", segment.phif)


def _check_measurements(at: str, peak: Peak | PeakRow) -> None:
    """Every measurement on a row, whichever list the row is in.

    The checks are per-field and skip what is unset, so the same six lines serve a
    ``Peak`` (both tRs present, always checked) and an untracked ``PeakRow`` (at most
    one, the other skipped).
    """
    _check_positive(f"{at}.tr_run1_min", peak.t_r_run1)
    _check_positive(f"{at}.tr_run2_min", peak.t_r_run2)
    _check_non_negative(f"{at}.area_run1", peak.area_run1)
    _check_non_negative(f"{at}.area_run2", peak.area_run2)
    _check_positive(f"{at}.w_half_run1_min", peak.w_half_run1)
    _check_positive(f"{at}.w_half_run2_min", peak.w_half_run2)


def _check_untracked(at: str, row: PeakRow) -> None:
    """A half-paired row, and the one thing that makes it not a ``Peak``.

    ``PeakRow`` permits both retention times — it is the shape of any row a user can
    type — so this function, not the type, is what "untracked" means in the file.
    Checked on save as well as on load: a fully paired row written here would load back
    as untracked, so the count SPEC §5 shows would be wrong and the peak would never
    reach the fit — a silent loss of exactly the kind ``untracked_peaks`` exists to end.
    """
    if row.is_tracked:
        raise SessionFileError(
            f"session file: {at} has a retention time in both runs, so it is a tracked "
            "peak — it belongs in peaks, not in untracked_peaks"
        )
    _check_measurements(at, row)


def _check_positive(at: str, value: float | None) -> None:
    if value is not None and not value > 0.0:
        raise SessionFileError(f"session file: {at} must be greater than zero, got {value:g}")


def _check_non_negative(at: str, value: float | None) -> None:
    if value is not None and not value >= 0.0:
        raise SessionFileError(f"session file: {at} must not be negative, got {value:g}")


def _check_percent(at: str, phi: float) -> None:
    percent = percent_b_from_phi(phi)
    low, high = PERCENT_B_RANGE
    if not low <= percent <= high:
        raise SessionFileError(
            f"session file: {at} must be between {low:g} and {high:g}, got {percent:g}"
        )


def _check_finite(at: str, value: float | None) -> None:
    if value is not None and not math.isfinite(value):
        raise SessionFileError(f"session file: {at} must be a finite number")
