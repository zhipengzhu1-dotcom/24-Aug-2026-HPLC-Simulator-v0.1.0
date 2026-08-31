"""The four tables the Cockpit shows, as DataFrames (SPEC §7).

Pandas lives here and in nothing else; the numbers arrive already computed by
:mod:`app.pipeline`. This module's only real work is the *display* boundary for
the tables: the base-10 quantities a chromatographer reads (log10 k0, S, %B) are
made from the natural-log ones the engine holds, through ``model``'s converters
and never by hand (CLAUDE.md's log-convention rule). The left rail formats a few
of those same quantities in ``streamlit_app.py``, calling the same converters —
the rule holds, but this is not the only file that crosses the boundary.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from app.diagnostics import Diagnostic
from app.pipeline import Cockpit, PeakOutcome, PeakRow
from hplcsim.model import log10_k0_from_ln_k0, s_base10_from_s_e
from hplcsim.width import PlateCountSource

COMPOUND = "Compound"
TR_RUN1 = "tR run 1 (min)"
TR_RUN2 = "tR run 2 (min)"
AREA_RUN1 = "Area run 1"
AREA_RUN2 = "Area run 2"
W_HALF_RUN1 = "W½ run 1 (min)"
W_HALF_RUN2 = "W½ run 2 (min)"

# Every optional per-peak measurement of SPEC §4, as a display column against the
# :class:`~app.pipeline.PeakRow` field it fills. One mapping rather than a column list
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
}


def badge_labels(badges: Sequence[Diagnostic]) -> str:
    """The short forms of one peak's badges, for the table's Flags cell."""
    return "; ".join(_BADGE_LABEL.get(badge.code, badge.code) for badge in badges)


RESOLUTION_COLUMNS = ("Pair", "ΔtR (min)", "Rs")

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


def peak_frame_from_rows(rows: Sequence[PeakRow], spare: int = 3) -> pd.DataFrame:
    """A restored peak table as the editor's frame — the inverse of the read below.

    Keeps :func:`blank_peak_frame`'s dtypes exactly, so a loaded session gets the same
    number fields as a fresh one; ``pd.NA`` rather than ``None`` is what makes the
    Float64 columns stay Float64 when a measurement is missing. ``spare`` empty rows
    ride along underneath, because a session is reopened to be added to and the
    editor's dynamic row only appears once there is somewhere to put the cursor.
    """
    if not rows:
        return blank_peak_frame()
    names = [row.name for row in rows] + [""] * spare
    return pd.DataFrame(
        {
            COMPOUND: pd.Series(names, dtype="string"),
            **{
                column: pd.Series(
                    [_na(getattr(row, field)) for row in rows] + [pd.NA] * spare,
                    dtype="Float64",
                )
                for column, field in _MEASUREMENT_FIELDS.items()
            },
        }
    )


def _na(value: float | None) -> Any:
    return pd.NA if value is None else value


def peak_rows_from_frame(frame: pd.DataFrame) -> list[PeakRow]:
    """The edited table back as :class:`~app.pipeline.PeakRow`, blanks and all.

    Nothing is dropped or validated here — :func:`~app.pipeline.split_rows` decides what
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


def resolution_frame(cockpit: Cockpit) -> pd.DataFrame:
    """Adjacent-pair resolution at the candidate gradient (SPEC §3)."""
    if cockpit.resolution is None:
        return pd.DataFrame(columns=RESOLUTION_COLUMNS)
    return pd.DataFrame(
        [
            {
                "Pair": f"{pair.earlier.name} / {pair.later.name}",
                "ΔtR (min)": pair.later.retention.t_r - pair.earlier.retention.t_r,
                "Rs": pair.rs,
            }
            for pair in cockpit.resolution.pairs
        ]
    )


def _text(value: Any) -> str:
    return "" if pd.isna(value) else str(value).strip()


def _number(value: Any) -> float | None:
    """A cell as a float, with every way the editor spells "empty" mapped to ``None``."""
    if value is None or pd.isna(value):
        return None
    return float(value)
