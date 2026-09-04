"""The four tables the Cockpit shows, as DataFrames (SPEC §7).

Pandas lives here and in nothing else; the numbers arrive already computed by
:mod:`app.entry` and :mod:`app.pipeline`. This module's only real work is the
*display* boundary for the tables: the base-10 quantities a chromatographer reads
(log10 k0, S, %B) are made from the natural-log ones the engine holds, through
``model``'s converters and never by hand (CLAUDE.md's log-convention rule). The left
rail formats a few of those same quantities in ``streamlit_app.py``, calling the same
converters — the rule holds, but this is not the only file that crosses the boundary.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.diagnostics import CompositionWindow, Diagnostic, Diagnostics
from app.entry import ProgrammePoint, ScoutingEntry
from app.pipeline import Cockpit, PeakOutcome
from hplcsim.model import (
    PeakRow,
    log10_k0_from_ln_k0,
    percent_b_from_phi,
    s_base10_from_s_e,
)
from hplcsim.width import PlateCountSource

COMPOUND = "Compound"
TR_RUN1 = "tR run 1 (min)"
TR_RUN2 = "tR run 2 (min)"
AREA_RUN1 = "Area run 1"
AREA_RUN2 = "Area run 2"
W_HALF_RUN1 = "W½ run 1 (min)"
W_HALF_RUN2 = "W½ run 2 (min)"

# Every optional per-peak measurement of SPEC §4, as a display column against the
# :class:`~hplcsim.model.PeakRow` field it fills. One mapping rather than a column list
# beside a hand-written constructor: adding a measurement is then one line here.
_MEASUREMENT_FIELDS = {
    TR_RUN1: "t_r_run1",
    TR_RUN2: "t_r_run2",
    AREA_RUN1: "area_run1",
    AREA_RUN2: "area_run2",
    W_HALF_RUN1: "w_half_run1",
    W_HALF_RUN2: "w_half_run2",
}
PEAK_COLUMNS = (COMPOUND, *_MEASUREMENT_FIELDS)

# Blank rows offered under a restored table, so there is somewhere to keep typing.
_SPARE_ROWS = 3

N_RATIO = "N run 1 / run 2"
FIT_COLUMNS = (COMPOUND, "log10 k0", "S", "N", "N from", N_RATIO, "Note")
FLAGS = "Flags"
PREDICTION_COLUMNS = (COMPOUND, "tR (min)", "W½ (min)", "k at elution", FLAGS)

# SPEC §6's per-peak badges (diagnostics 2 and 4) as a table cell. The full sentence is
# rendered beside the selected peak; a table needs a word, and one the eye can scan down
# a column. Keyed by ``Diagnostic.code`` so re-wording a diagnostic cannot silently
# empty this column.
_BADGE_LABEL = {
    "early_eluter": "early eluter",
    "prediction_crossing": "crossing",
    "low_k0": "low k0",
    "wash_eluted": "wash-eluted",
}


def badge_labels(badges: Sequence[Diagnostic]) -> str:
    """The short forms of one peak's badges, for the table's Flags cell."""
    return "; ".join(_BADGE_LABEL.get(badge.code, badge.code) for badge in badges)


GRADE = "Rs grade"
RESOLUTION_COLUMNS = ("Pair", "ΔtR (min)", "Rs", GRADE)

# SPEC §6's per-peak composition-window readout, on the fit-parameters tab: the per-peak
# fact behind diagnostic 1, whose own tier is method-level. Each peak's calibrated
# window is the two elution compositions the fit was actually shown, its width is
# ln β / S_e, and the last two columns say where the candidate puts this peak against
# them — which is the whole question diagnostic 1 answers as one number for the method.
# Headers are terse because the rail leaves the main view about 1000 px and six columns
# do not fit at conversational widths — the last one clipped in the browser at
# 1440 × 900, which is the defect #73 shipped a first screenshot of. The caption
# beneath the table carries the sentence the headers no longer can.
WINDOW_LOW = "From (%B)"
WINDOW_HIGH = "To (%B)"
WINDOW_WIDTH = "Width (%B)"
WINDOW_CANDIDATE = "Elutes at (%B)"
WINDOW_POSITION = "Position"
WINDOW_COLUMNS = (
    COMPOUND,
    WINDOW_LOW,
    WINDOW_HIGH,
    WINDOW_WIDTH,
    WINDOW_CANDIDATE,
    WINDOW_POSITION,
)

# What a stamped Rs pair is called in the resolution table's own column. The sentence
# is painted once above the table (SPEC §6's stamp); a cell needs a word.
_INDICATIVE_CELL = "indicative"

# What SPEC §6 diagnostic 5 and the fitted-N badge say when they fire, in the words
# ticket #19 owns. Wiring the remaining five diagnostics is ticket #20's.
_PLATE_COUNT_LABEL: dict[PlateCountSource, str] = {
    "fitted": "fitted from W½",
    "supplied": "global knob",
    "default": "column estimate",
}
_UNTRACKED = "untracked — not fitted"
_POST_GRADIENT_N = "N from a post-gradient width — treat as indicative"
_LOW_CONFIDENCE_FIT = "low-confidence fit"


def plate_count_label(source: PlateCountSource) -> str:
    """How a plate count's provenance is worded on screen — one wording, two panels."""
    return _PLATE_COUNT_LABEL[source]


def blank_peak_frame(rows: int = 6) -> pd.DataFrame:
    """An empty peak table with the right dtypes, so the editor offers number fields."""
    return pd.DataFrame(
        {
            COMPOUND: pd.Series([""] * rows, dtype="string"),
            **{column: pd.Series([pd.NA] * rows, dtype="Float64") for column in PEAK_COLUMNS[1:]},
        }
    )


def peak_frame_from_rows(rows: Sequence[PeakRow]) -> pd.DataFrame:
    """A restored peak table as the editor's frame — the inverse of the read below.

    Keeps :func:`blank_peak_frame`'s dtypes exactly, so a loaded session gets the same
    number fields as a fresh one; ``pd.NA`` rather than ``None`` is what makes the
    Float64 columns stay Float64 when a measurement is missing. A few empty rows ride
    along underneath, because a session is reopened to be added to and the editor's
    dynamic row only appears once there is somewhere to put the cursor.
    """
    if not rows:
        return blank_peak_frame()
    names = [row.name for row in rows] + [""] * _SPARE_ROWS
    return pd.DataFrame(
        {
            COMPOUND: pd.Series(names, dtype="string"),
            **{
                column: pd.Series(
                    [_na(getattr(row, field)) for row in rows] + [pd.NA] * _SPARE_ROWS,
                    dtype="Float64",
                )
                for column, field in _MEASUREMENT_FIELDS.items()
            },
        }
    )


def _na(value: float | None) -> Any:
    return pd.NA if value is None else value


def peak_rows_from_frame(frame: pd.DataFrame) -> list[PeakRow]:
    """The edited table back as :class:`~hplcsim.model.PeakRow`, blanks and all.

    Nothing is dropped or validated here — :func:`~app.entry.split_rows` decides what
    counts as a row and what counts as tracked, so that judgement stays in one place.
    """
    return [
        PeakRow(
            name=_text(record.get(COMPOUND)),
            **{field: _number(record.get(column)) for column, field in _MEASUREMENT_FIELDS.items()},
        )
        for record in frame.to_dict("records")
    ]


def fit_frame(cockpit: Cockpit) -> pd.DataFrame:
    """The promoted fit-parameter table (SPEC §7) — every non-blank row, in entry order.

    Peaks that could not be fitted and rows that are not yet paired stay in the table
    rather than vanishing from it: the count SPEC §5 asks for is only useful next to
    the rows it counts. The plate count and its provenance ride along, because a
    width and every Rs downstream of it rest on them (SPEC §4, §6 diagnostic 5).
    """
    widths = cockpit.predicted_by_name
    rows: list[dict[str, Any]] = []
    for outcome in cockpit.outcomes:
        fit = outcome.fit
        predicted = widths.get(outcome.peak.name)
        source = predicted.width.plate_count_source if predicted else None
        rows.append(
            {
                COMPOUND: outcome.peak.name,
                "log10 k0": None if fit is None else log10_k0_from_ln_k0(fit.params.ln_k0),
                "S": None if fit is None else s_base10_from_s_e(fit.params.s_e),
                "N": None if predicted is None else predicted.width.plate_count,
                "N from": None if source is None else _PLATE_COUNT_LABEL[source],
                N_RATIO: None if fit is None or fit.plate_count is None else fit.plate_count.ratio,
                "Note": _fit_note(outcome),
            }
        )
    rows.extend({COMPOUND: row.name, "Note": _UNTRACKED} for row in cockpit.entry.untracked)
    return pd.DataFrame(rows, columns=FIT_COLUMNS)


def _fit_note(outcome: PeakOutcome) -> str:
    """Why a row is worth a second look — the engine's own refusal, or its own caveat."""
    if outcome.error is not None:
        return outcome.error
    if outcome.fit is None:
        return ""
    notes = []
    if outcome.fit.low_confidence:
        notes.append(_LOW_CONFIDENCE_FIT)
    if outcome.fit.plate_count is not None and outcome.fit.plate_count.low_confidence:
        notes.append(_POST_GRADIENT_N)
    return "; ".join(notes)


def prediction_frame(
    cockpit: Cockpit, badges: Mapping[str, tuple[Diagnostic, ...]]
) -> pd.DataFrame:
    """What the candidate gradient is predicted to give, in elution order.

    ``badges`` is :attr:`~app.diagnostics.Diagnostics.badges` — SPEC §6's per-peak
    diagnostics 2 and 4, beside the rows they are about. Required rather than
    defaulted: the one caller that renders this table always has them, and a default
    would only exist to let a caller quietly ship a table with an empty Flags column.
    """
    if cockpit.resolution is None:
        return pd.DataFrame(columns=PREDICTION_COLUMNS)
    found = badges
    return pd.DataFrame(
        [
            {
                COMPOUND: peak.name,
                "tR (min)": peak.retention.t_r,
                "W½ (min)": peak.width.w_half,
                "k at elution": peak.retention.k_e,
                FLAGS: badge_labels(found.get(peak.name, ())),
            }
            for peak in cockpit.resolution.peaks
        ],
        columns=PREDICTION_COLUMNS,
    )


def resolution_frame(cockpit: Cockpit, diagnostics: Diagnostics) -> pd.DataFrame:
    """Adjacent-pair resolution at the candidate gradient (SPEC §3).

    ``diagnostics`` carries SPEC §6's *indicative, not decision-grade* stamp, which is
    what the last column reads. Required rather than defaulted, like
    :func:`prediction_frame`'s badges: a defaulted argument would exist only to let a
    caller ship a table of resolutions with nothing saying which of them were never
    pinned. The stamp downgrades every pair; a low-k0 or wash-eluted badge downgrades
    only the pairs its own peak is in, which is why this asks per pair.
    """
    if cockpit.resolution is None:
        return pd.DataFrame(columns=RESOLUTION_COLUMNS)
    return pd.DataFrame(
        [
            {
                "Pair": f"{pair.earlier.name} / {pair.later.name}",
                "ΔtR (min)": pair.later.retention.t_r - pair.earlier.retention.t_r,
                "Rs": pair.rs,
                GRADE: _INDICATIVE_CELL
                if diagnostics.pair_is_indicative((pair.earlier.name, pair.later.name))
                else "",
            }
            for pair in cockpit.resolution.pairs
        ],
        columns=RESOLUTION_COLUMNS,
    )


def window_position_label(window: CompositionWindow) -> str:
    """Where the candidate puts one peak against its own calibrated window.

    Inside is said as "inside", not as a distance of zero: a peak the fit was shown the
    composition of is the ordinary case, and a column of zeroes would read as a
    measurement rather than as the absence of an extrapolation.
    """
    if window.position == "inside":
        return "inside"
    return f"{window.distance_in_widths:.2f} widths {window.position}"


def composition_window_frame(windows: Sequence[CompositionWindow]) -> pd.DataFrame:
    """SPEC §6's per-peak composition-window readout, in %B (the display boundary).

    The engine holds every composition as a fraction; this is where they become the %B
    a chromatographer reads, through ``model``'s own converter and never by hand
    (CLAUDE.md's units rule). Nothing is computed here — the window, its width and the
    candidate's position in it are :class:`~app.diagnostics.CompositionWindow`'s, which
    is also what the chromatogram's whiskers are drawn from.
    """
    return pd.DataFrame(
        [
            {
                COMPOUND: window.name,
                WINDOW_LOW: percent_b_from_phi(window.phi_low),
                WINDOW_HIGH: percent_b_from_phi(window.phi_high),
                # A width is a *difference* of compositions; the same converter
                # carries it across, since 0–1 to 0–100 scales a span exactly as
                # it scales a position.
                WINDOW_WIDTH: percent_b_from_phi(window.width),
                WINDOW_CANDIDATE: percent_b_from_phi(window.candidate_phi_e),
                WINDOW_POSITION: window_position_label(window),
            }
            for window in windows
        ],
        columns=WINDOW_COLUMNS,
    )


def _text(value: Any) -> str:
    return "" if pd.isna(value) else str(value).strip()


def _number(value: Any) -> float | None:
    """A cell as a float, with every way the editor spells "empty" mapped to ``None``."""
    if value is None or pd.isna(value):
        return None
    return float(value)


# --- the rail's two programme tables (SPEC §7, v0.2, #73) ---------------------------------
#
# Both are typed like an instrument's gradient table: a row is a time from injection
# and the %B reached at it. The frames here are the editors' — what a table shows and
# what it reads back — and nothing more: the crossing from points to the engine's
# gradient or programme is `app.entry`'s (`ScoutingEntry`, `programme_from_points`).

NO = "#"
T1 = "t₁ (min)"
T2 = "t₂ (min)"
T_CANDIDATE = "t (min)"
PERCENT_B = "%B"
SCOUTING_COLUMNS = (NO, T1, T2, PERCENT_B)
CANDIDATE_COLUMNS = (T_CANDIDATE, PERCENT_B)

# A ramp has to take some time. When row 3 of the scouting table is typed before the
# hold ends, the run is put back to this rather than left with a gradient time the
# engine would divide by.
_MIN_GRADIENT_TIME = 0.1


@dataclass(frozen=True)
class ScoutingRead:
    """The scouting table read: its five values, the frame as it should show, and why.

    ``frame`` differs from what was typed only where a cell follows another — row 1's
    times are the start of the run, row 2's second time and %B follow its first and
    row 1's — or where a ramp was typed to end before the hold did; ``notes`` name the
    second kind. The caller shows ``frame`` back when it differs from what was typed.
    """

    entry: ScoutingEntry
    frame: pd.DataFrame
    notes: tuple[str, ...] = ()


def scouting_frame(entry: ScoutingEntry) -> pd.DataFrame:
    """One programme at two speeds as three rows: start, end of hold, end of each ramp."""
    hold = entry.hold
    return pd.DataFrame(
        {
            NO: pd.Series([1, 2, 3], dtype="Int64"),
            T1: pd.Series([0.0, hold, hold + entry.t_gradient1], dtype="Float64"),
            T2: pd.Series([0.0, hold, hold + entry.t_gradient2], dtype="Float64"),
            PERCENT_B: pd.Series(
                [entry.percent_b_start, entry.percent_b_start, entry.percent_b_end],
                dtype="Float64",
            ),
        }
    )


def scouting_read_from_frame(frame: pd.DataFrame) -> ScoutingRead:
    """The edited scouting table back as its five values, the following cells put back."""
    t1 = [_number(value) for value in frame[T1]]
    t2 = [_number(value) for value in frame[T2]]
    percent = [_number(value) for value in frame[PERCENT_B]]
    # A required cell cannot be committed blank in the editor; a blank that arrives
    # anyway (a frame built elsewhere) reads as the start of the run.
    start = _or_zero(percent[0])
    end = percent[2] if percent[2] is not None else start
    hold = max(_or_zero(t1[1]), 0.0)
    notes = []
    gradient_times = []
    for run, end_time in (("run 1", t1[2]), ("run 2", t2[2])):
        t_gradient = round(_or_zero(end_time) - hold, 6)
        if t_gradient <= 0.0:
            notes.append(
                f"**{run.capitalize()}'s ramp was typed to end before the hold does** — a "
                f"gradient has to take some time, so row 3 is put back to "
                f"{hold + _MIN_GRADIENT_TIME:g} min (tG {_MIN_GRADIENT_TIME:g} min); "
                "type the time the ramp really ends."
            )
            t_gradient = _MIN_GRADIENT_TIME
        gradient_times.append(t_gradient)
    entry = ScoutingEntry(
        percent_b_start=start,
        percent_b_end=end,
        hold=hold,
        t_gradient1=gradient_times[0],
        t_gradient2=gradient_times[1],
    )
    return ScoutingRead(entry=entry, frame=scouting_frame(entry), notes=tuple(notes))


def _or_zero(value: float | None) -> float:
    return 0.0 if value is None else value


def candidate_frame(points: Sequence[ProgrammePoint]) -> pd.DataFrame:
    """The candidate table's rows as the editor's frame, a blank cell as ``pd.NA``."""
    return pd.DataFrame(
        {
            T_CANDIDATE: pd.Series([_na(point.t_min) for point in points], dtype="Float64"),
            PERCENT_B: pd.Series([_na(point.percent_b) for point in points], dtype="Float64"),
        }
    )


def candidate_points_from_frame(frame: pd.DataFrame) -> tuple[ProgrammePoint, ...]:
    """The edited candidate table back as points, every way of spelling a blank as ``None``.

    Nothing is dropped or judged here — :func:`~app.entry.programme_from_points`
    decides which rows make the programme, so that judgement stays in one place.
    """
    return tuple(
        ProgrammePoint(
            t_min=_number(record.get(T_CANDIDATE)), percent_b=_number(record.get(PERCENT_B))
        )
        for record in frame.to_dict("records")
    )


def frames_agree(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    """Whether two table frames hold the same cells, dtype and blank spelling aside.

    The editor hands its frame back in whatever dtypes the browser's edits left it in,
    and ``DataFrame.equals`` is dtype-strict; what the rail needs to know is whether a
    cell *reads* differently — a put-back to make, a first edit to notice.
    """
    if list(left.columns) != list(right.columns) or len(left) != len(right):
        return False
    return all(
        [_number(a) for a in left[column]] == [_number(b) for b in right[column]]
        for column in left.columns
    )
