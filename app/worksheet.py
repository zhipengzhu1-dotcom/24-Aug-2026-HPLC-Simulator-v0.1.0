"""The guided empty state: SPEC §7's numbered 1→4 worksheet (ticket #21).

The Cockpit is a good screen to *work* in and a poor one to arrive at. Opening it with
nothing entered gives four empty tabs, a blank chromatogram and a rail of dashes, none
of which say what to do first. SPEC §7 carries the prototype's answer forward — the
bench worksheet's four numbered steps, which are the actual order of the job:

1. the method and the instrument, 2. the two scouting runs and the peaks they gave,
3. the fit those peaks produce, 4. the candidate gradient predicted from the fit.

Each step reports whether it is done, so the list is a place in the work rather than a
paragraph of instructions — and steps 3 and 4 stay visibly out of reach until the peaks
that feed them exist, which is the point being made.

Every one of those judgements is computed here and only *placed* by ``streamlit_app``,
following what ticket #20 established for :mod:`app.diagnostics`. The wording is here
too: a step's sentence and the condition that ticks it are the same decision, and
splitting them across two files is how they come to disagree.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.pipeline import Cockpit, CockpitInputs


@dataclass(frozen=True)
class Step:
    """One numbered step of the worksheet, and whether it has been done."""

    number: int
    title: str
    detail: str
    done: bool

    @property
    def marker(self) -> str:
        """The tick or the empty circle the step is drawn with."""
        return "✅" if self.done else "⬜"


def is_empty(cockpit: Cockpit) -> bool:
    """Nothing has been typed into the peak table yet — the guided state, SPEC §7.

    Blank rows do not count: :func:`~app.pipeline.split_rows` already drops the
    editor's spares, so the screen goes to the cockpit on the first real row and not
    on the first keystroke in a spare one. Untracked rows *do* count — a half-typed
    peak is work in progress, and pulling the worksheet back over it would hide the
    table it is being typed into.
    """
    return not cockpit.entry.tracked and not cockpit.entry.untracked


def worksheet_steps(inputs: CockpitInputs, cockpit: Cockpit) -> tuple[Step, ...]:
    """The four steps, each with the state the screen is actually in.

    Step 1 is ticked by the dwell: it is the one method constant SPEC §4 makes required
    with no silent default, and reaching this screen at all means it was entered. The
    rest tick on their own evidence rather than on the step before, so a screen that is
    stuck says *which* step is stuck.
    """
    scouting_ready = inputs.run1.gradient.t_gradient != inputs.run2.gradient.t_gradient
    return (
        Step(
            number=1,
            title="Method and instrument",
            detail=(
                "In the sidebar: column, flow, temperature, t0, and the dwell — "
                "the dwell is required, and a wrong one biases every prediction "
                "the same way."
            ),
            done=True,
        ),
        Step(
            number=2,
            title="Two scouting runs, and the peaks they gave",
            detail=(
                "Set both gradient times in the left rail — run 2 about 3× run 1 — "
                "then type the peaks into **Table of peaks**: one row per compound, "
                "tR from each run side by side. You pair the peaks as you type."
                if scouting_ready
                else "Give the two scouting runs different gradient times in the left "
                "rail — run 2 about 3× run 1. Two runs at one tG are one measurement, "
                "not two, and nothing can be fitted from them."
            ),
            done=bool(cockpit.entry.tracked) and scouting_ready,
        ),
        Step(
            number=3,
            title="Read the fit",
            detail=(
                "log10 k0 and S per peak, under **Fit parameters** — one pair of "
                "numbers per compound, fitted from its two retention times."
            ),
            done=bool(cockpit.fitted),
        ),
        Step(
            number=4,
            title="Predict a candidate gradient",
            detail=(
                "Move tG and the initial hold in the left rail and watch the "
                "chromatogram, the resolution table and the critical pair follow."
            ),
            done=cockpit.resolution is not None,
        ),
    )
