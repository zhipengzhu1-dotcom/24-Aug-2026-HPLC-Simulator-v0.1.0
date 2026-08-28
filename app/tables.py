"""The four tables the Cockpit shows, as DataFrames (SPEC §7).

Pandas lives here and in nothing else; the numbers arrive already computed by
:mod:`app.pipeline`. This module's only real work is the *display* boundary — the
one place the base-10 quantities a chromatographer reads (log10 k0, S, %B) are made
from the natural-log ones the engine holds, through ``model``'s converters and never
by hand (CLAUDE.md's log-convention rule).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

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
PREDICTION_COLUMNS = (COMPOUND, "tR (min)", "W½ (min)", "k at elution")
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


def peak_rows_from_frame(frame: pd.DataFrame) -> list[PeakRow]:
    """The edited table back as :class:`~app.pipeline.PeakRow`, blanks and all.

    Nothing is dropped or validated here — :func:`~app.pipeline.prepare` decides what
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


def prediction_frame(cockpit: Cockpit) -> pd.DataFrame:
    """What the candidate gradient is predicted to give, in elution order."""
    if cockpit.resolution is None:
        return pd.DataFrame(columns=PREDICTION_COLUMNS)
    return pd.DataFrame(
        [
            {
                COMPOUND: peak.name,
                "tR (min)": peak.retention.t_r,
                "W½ (min)": peak.width.w_half,
                "k at elution": peak.retention.k_e,
            }
            for peak in cockpit.resolution.peaks
        ]
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
