"""The screen and the session file, each read as the other (SPEC §8, ticket #21).

:class:`~hplcsim.session.Session` and :class:`~app.pipeline.CockpitInputs` describe the
same experiment and disagree about almost every detail of how: the runs are a pair
there and two fields here, N is a whole count there and a widget's float here, the peak
table is split in two there and one list of :class:`~app.pipeline.PeakRow` here. Both
shapes are right for where they live, so the disagreement is translated in one place
rather than negotiated at each call site.

No Streamlit here — this is the logic layer ticket #20 asked #21 to keep using. What
the entry point still owns is *widget identity*: taking a restored session and writing
it into ``st.session_state`` under the keys the widgets answer to.

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
from dataclasses import fields

from app.pipeline import CockpitInputs, PeakRow, split_rows
from hplcsim.model import Peak
from hplcsim.session import Session, UntrackedPeak

# What a row holds beyond its name: the six optional measurements of SPEC §4. PeakRow,
# Peak and UntrackedPeak all spell them the same way, which is what lets the three
# translations below be field copies rather than seven hand-written arguments apiece —
# and what makes adding a seventh measurement a change in one place.
_MEASUREMENTS = tuple(field.name for field in fields(UntrackedPeak) if field.name != "name")

_FILENAME_FALLBACK = "hplcsim-session"
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_STEM = 80


def session_from_inputs(inputs: CockpitInputs, *, session_name: str = "") -> Session:
    """The screen as the file holds it, ready for :func:`~hplcsim.session.save_session`.

    Saves what :func:`~app.pipeline.split_rows` made of the table, not the raw table:
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
        untracked=tuple(_as_untracked(row) for row in entry.untracked),
        candidate=inputs.candidate,
        session_name=session_name,
        plate_count=_whole(inputs.plate_count),
    )


def inputs_from_session(session: Session) -> CockpitInputs:
    """A restored session as the values the widgets hold."""
    return CockpitInputs(
        method=session.method,
        run1=session.runs[0],
        run2=session.runs[1],
        candidate=session.candidate,
        rows=peak_rows_from_session(session),
        plate_count=None if session.plate_count is None else float(session.plate_count),
    )


def peak_rows_from_session(session: Session) -> tuple[PeakRow, ...]:
    """Both of the file's peak tables back as the one table the editor shows."""
    tracked: tuple[Peak | UntrackedPeak, ...] = session.peaks
    return tuple(_as_row(peak) for peak in (*tracked, *session.untracked))


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


def _as_untracked(row: PeakRow) -> UntrackedPeak:
    return UntrackedPeak(name=row.name, **{name: getattr(row, name) for name in _MEASUREMENTS})


def _as_row(peak: Peak | UntrackedPeak) -> PeakRow:
    return PeakRow(name=peak.name, **{name: getattr(peak, name) for name in _MEASUREMENTS})


def _whole(plate_count: float | None) -> int | None:
    """N as the file's whole count. The knob offers a float; a plate count is a number
    of plates, and the file says so (SPEC §8). Rounding a typed 12345.5 to 12346 loses
    nothing a chromatographer meant, and CLAUDE.md's warnings-over-blocks says round
    rather than refuse to save over it."""
    return None if plate_count is None else int(round(plate_count))
