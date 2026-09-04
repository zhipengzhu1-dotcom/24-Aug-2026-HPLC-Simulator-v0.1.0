"""The screen and the session file, each read as the other (SPEC §8, ticket #21).

:class:`~hplcsim.session.Session` and :class:`~app.pipeline.CockpitInputs` describe the
same experiment and disagree about almost every detail of how: the runs are a pair
there and two fields here, N is a whole count there and a widget's float here, the peak
table is split in two there and one list of :class:`~hplcsim.model.PeakRow` here. Both
shapes are right for where they live, so the disagreement is translated in one place
rather than negotiated at each call site.

No Streamlit here — this is the logic layer ticket #20 asked #21 to keep using. What
this module deliberately does not do is *widget identity*: taking a restored session and
writing it into the screen under the keys the widgets answer to. That half belongs to
:mod:`app.screen_state`, which is the one module in ``app/`` that reaches Streamlit's
per-session store, and which calls :func:`inputs_from_session` here to cross the shapes
before it writes (#93).

**The peak table comes back re-ordered**, tracked rows first. The file stores the two
halves as two tables (SPEC §5's split, which is what lets a half-paired row be saved at
all) and nothing records where an untracked row sat among the tracked ones. Names are
stored, though — including the automatic P1…Pn, which :func:`session_from_inputs` fills
in before saving — so every row comes back under the name it was shown with, and it is
only the order that moves. An unfinished row surfacing at the foot of the table is a
fair place for it.
"""

from __future__ import annotations

import re

from app.entry import split_rows
from app.pipeline import CockpitInputs
from hplcsim.model import Peak, PeakRow, as_programme
from hplcsim.session import Session

_FILENAME_FALLBACK = "hplcsim-session"
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_STEM = 80


class Restore:
    """Restored values squeezed into the ranges the widgets can actually show.

    The file and the widgets disagree about what is possible. ``load_session`` refuses
    an impossible number — a negative t0, a flow of zero — but it has no opinion about
    a column length of 5 m, which is past the end of a number box that stops at 1000 mm.
    Writing that straight into the widget's state does not warn: Streamlit raises on
    the next run, and the whole page becomes a traceback.

    So a restored value is squeezed into the widget's range and the squeeze is
    *reported*, never silent — CLAUDE.md's warnings-over-blocks, applied to a file that
    is valid but does not fit the screen. The caller paints :attr:`adjusted` beside the
    uploader, so the one number that changed is named while the file is still to hand.

    The candidate is not squeezed at all since #73: the rail's programme table holds any
    programme the file can (SPEC §7, §8), so the crossing is exact in both directions.
    """

    def __init__(self) -> None:
        self.adjusted: list[str] = []

    def within(self, label: str, value: float, low: float, high: float) -> float:
        """``value``, or the nearer end of [low, high] with ``label`` recorded."""
        squeezed = min(max(value, low), high)
        if squeezed != value:
            self.adjusted.append(f"{label} {value:g} → {squeezed:g}")
        return squeezed

    @property
    def note(self) -> str | None:
        """What to tell the user about the file, or ``None`` when all of it is on screen."""
        if not self.adjusted:
            return None
        return (
            "**Some values in that file are outside what this screen can show**, and "
            "have been brought to the nearest limit: " + "; ".join(self.adjusted) + ". "
            "The file itself is unchanged — saving from here would write these values."
        )


def session_from_inputs(inputs: CockpitInputs, *, session_name: str = "") -> Session:
    """The screen as the file holds it, ready for :func:`~hplcsim.session.save_session`.

    Saves what :func:`~app.entry.split_rows` made of the table, not the raw table:
    the editor's spare blank rows are not worth writing down, and the automatic P1…Pn
    the user reads beside a row is the name that should come back. Splitting here is
    also what puts each row in the list the file requires it to be in — a row with one
    retention time cannot go in ``peaks``, and a row with both cannot go anywhere else.
    """
    entry = split_rows(inputs.rows)
    return Session(
        method=inputs.method,
        runs=(inputs.run1, inputs.run2),
        peaks=entry.tracked,
        untracked=entry.untracked,
        candidate=as_programme(inputs.target),
        session_name=session_name,
        plate_count=_whole(inputs.plate_count),
    )


def inputs_from_session(session: Session) -> CockpitInputs:
    """A restored session as the values the widgets hold.

    The candidate crosses as the programme it is (SPEC §8's rows are the rail's rows,
    #73); the peak table comes back re-ordered, tracked first, as the module docstring
    says. Nothing here squeezes — the number boxes' ranges are the entry point's.
    """
    return CockpitInputs.with_programme(
        method=session.method,
        run1=session.runs[0],
        run2=session.runs[1],
        programme=session.candidate,
        rows=peak_rows_from_session(session),
        plate_count=None if session.plate_count is None else float(session.plate_count),
    )


def peak_rows_from_session(session: Session) -> tuple[PeakRow, ...]:
    """Both of the file's peak tables back as the one table the editor shows."""
    return tuple(_as_row(peak) for peak in session.peaks) + session.untracked


def session_filename(session_name: str) -> str:
    """The download's suggested filename, from the name the user gave the session.

    A session name is free text a chromatographer types — "Impurity screen 2026-08-27",
    or a compound with a slash in it — and it lands in a filename the browser will
    write to disk. Anything a path could read as structure is replaced rather than
    dropped, so two different names cannot collapse into one file, and a name that
    survives none of that falls back to a fixed stem rather than to ``.json`` alone.
    """
    stem = _UNSAFE.sub("-", session_name).strip("-.")[:_MAX_STEM].strip("-.")
    return f"{stem or _FILENAME_FALLBACK}.json"


# The six measurements are copied field by field rather than by `getattr` over a list of
# names. The loop reads shorter, but it types as `Any`, and this function is exactly
# where a field silently going to the wrong slot would cost a measurement — spelled out,
# mypy checks every one of them (CLAUDE.md: strict on `app/`).


def _as_row(peak: Peak) -> PeakRow:
    return PeakRow(
        name=peak.name,
        t_r_run1=peak.t_r_run1,
        t_r_run2=peak.t_r_run2,
        area_run1=peak.area_run1,
        area_run2=peak.area_run2,
        w_half_run1=peak.w_half_run1,
        w_half_run2=peak.w_half_run2,
    )


def _whole(plate_count: float | None) -> int | None:
    """N as the file's whole count. The knob offers a float; a plate count is a number
    of plates, and the file says so (SPEC §8). Rounding a typed 12345.5 to 12346 loses
    nothing a chromatographer meant, and CLAUDE.md's warnings-over-blocks says round
    rather than refuse to save over it."""
    return None if plate_count is None else int(round(plate_count))
