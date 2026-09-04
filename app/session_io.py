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

from app.pipeline import CockpitInputs, PeakRow, split_rows
from hplcsim.model import Gradient, Peak, Programme, percent_b_from_phi
from hplcsim.session import Session, UntrackedPeak

_FILENAME_FALLBACK = "hplcsim-session"
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_STEM = 80


class Restore:
    """Restored values squeezed into the ranges the widgets can actually show.

    The file and the widgets disagree about what is possible. ``load_session`` refuses
    an impossible number — a negative t0, a flow of zero — but it has no opinion about
    a candidate tG of 500 min, which is a perfectly good method and simply past the end
    of a slider that stops at 180. Writing that straight into the widget's state does
    not warn: Streamlit raises on the next run, and the whole page becomes a traceback.

    So a restored value is squeezed into the widget's range and the squeeze is
    *reported*, never silent — CLAUDE.md's warnings-over-blocks, applied to a file that
    is valid but does not fit the screen. The caller paints :attr:`adjusted` beside the
    uploader, so the one number that changed is named while the file is still to hand.

    The second way a file can outrun the screen is a control that does not exist yet.
    Since v0.2 the file holds the candidate as programme rows — its own %B range and any
    number of segments (SPEC §8) — while this screen still has v0.1's one segment over
    the scouting range, until the programme table of #73 lands. :meth:`single_segment`
    is that crossing: what the screen cannot hold is named in :attr:`not_shown`, and the
    note says so in different words from a squeeze, because no limit was hit.
    """

    def __init__(self) -> None:
        self.adjusted: list[str] = []
        self.not_shown: list[str] = []

    def within(self, label: str, value: float, low: float, high: float) -> float:
        """``value``, or the nearer end of [low, high] with ``label`` recorded."""
        squeezed = min(max(value, low), high)
        if squeezed != value:
            self.adjusted.append(f"{label} {value:g} → {squeezed:g}")
        return squeezed

    def single_segment(self, programme: Programme, scouting: Gradient) -> Gradient:
        """The one-segment gradient this screen shows for ``programme``, over ``scouting``'s range.

        Exact when the programme is one segment over the scouting range — the usual
        file, and every file v0.1 wrote. Otherwise the screen shows the programme's total
        ramp time and hold over the scouting range, and each thing it dropped is named:
        the segment count, and the candidate's own %B range.
        """
        if len(programme.segments) > 1:
            self.not_shown.append(
                f"the candidate programme has {len(programme.segments)} segments and this "
                f"screen has one segment, shown as the total ramp time {programme.t_gradient:g} min"
            )
        if (programme.phi0, programme.phif) != (scouting.phi0, scouting.phif):
            self.not_shown.append(
                f"the candidate's {_percent_range(programme.phi0, programme.phif)} range differs "
                f"from the scouting runs' {_percent_range(scouting.phi0, scouting.phif)}, and this "
                "screen predicts the candidate over the scouting range"
            )
        return Gradient(
            phi0=scouting.phi0,
            phif=scouting.phif,
            t_gradient=programme.t_gradient,
            t_init=programme.t_init,
        )

    @property
    def note(self) -> str | None:
        """What to tell the user about the file, or ``None`` when all of it is on screen."""
        parts = []
        if self.adjusted:
            parts.append(
                "**Some values in that file are outside what this screen can show**, and "
                "have been brought to the nearest limit: " + "; ".join(self.adjusted) + "."
            )
        if self.not_shown:
            parts.append(
                "**Some of that file's candidate programme has no control on this screen "
                "yet**: " + "; ".join(self.not_shown) + "."
            )
        if not parts:
            return None
        parts.append("The file itself is unchanged — saving from here would write these values.")
        return " ".join(parts)


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
        candidate=Programme.from_gradient(inputs.candidate),
        session_name=session_name,
        plate_count=_whole(inputs.plate_count),
    )


def inputs_from_session(session: Session, restore: Restore) -> CockpitInputs:
    """A restored session as the values the widgets hold.

    The candidate crosses through :meth:`Restore.single_segment`, so ``restore`` is
    required rather than optional: a programme this screen cannot hold is reported
    beside the uploader with everything else, and there is no way to ask for the
    inputs without also receiving what was not shown.
    """
    return CockpitInputs(
        method=session.method,
        run1=session.runs[0],
        run2=session.runs[1],
        candidate=restore.single_segment(session.candidate, session.runs[0].gradient),
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


# The six measurements are copied field by field rather than by `getattr` over a list of
# names. The loop reads shorter, but it types as `Any`, and these two functions are
# exactly where a field silently going to the wrong slot would cost a measurement —
# spelled out, mypy checks every one of them (CLAUDE.md: strict on `app/`).


def _as_untracked(row: PeakRow) -> UntrackedPeak:
    return UntrackedPeak(
        name=row.name,
        t_r_run1=row.t_r_run1,
        t_r_run2=row.t_r_run2,
        area_run1=row.area_run1,
        area_run2=row.area_run2,
        w_half_run1=row.w_half_run1,
        w_half_run2=row.w_half_run2,
    )


def _as_row(peak: Peak | UntrackedPeak) -> PeakRow:
    return PeakRow(
        name=peak.name,
        t_r_run1=peak.t_r_run1,
        t_r_run2=peak.t_r_run2,
        area_run1=peak.area_run1,
        area_run2=peak.area_run2,
        w_half_run1=peak.w_half_run1,
        w_half_run2=peak.w_half_run2,
    )


def _percent_range(phi0: float, phif: float) -> str:
    """A composition range as the user reads it: ``5 → 95 %B``."""
    return f"{percent_b_from_phi(phi0):g} → {percent_b_from_phi(phif):g} %B"


def _whole(plate_count: float | None) -> int | None:
    """N as the file's whole count. The knob offers a float; a plate count is a number
    of plates, and the file says so (SPEC §8). Rounding a typed 12345.5 to 12346 loses
    nothing a chromatographer meant, and CLAUDE.md's warnings-over-blocks says round
    rather than refuse to save over it."""
    return None if plate_count is None else int(round(plate_count))
