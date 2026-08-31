"""The guided empty state: SPEC §7's numbered 1→4 worksheet (ticket #21).

The Cockpit is a good screen to *work* in and a poor one to arrive at. Opening it with
nothing entered gives four empty tabs, a blank chromatogram and a rail of dashes, none
of which say what to do first. SPEC §7 carries the prototype's answer forward — the
bench worksheet's four numbered steps, which are the actual order of the job:

1. the method and the instrument, 2. the two scouting runs and the peaks they gave,
3. the fit those peaks produce, 4. the candidate gradient predicted from the fit.

Each step reports whether it is done, so the list is a place in the work rather than a
paragraph of instructions.

**It retires when the prediction arrives, not when the first row is typed.** The
cockpit's empty state is not "nobody has typed anything" — it is "there is nothing to
show yet", and the results surfaces stay empty right up until a peak is fitted and
predicted. Retiring on the first keystroke would have made steps 2, 3 and 4 unreachable:
each ticks on evidence that only exists once rows are entered, so the list would have
read ✅⬜⬜⬜ forever and said nothing about a screen that is stuck. Retiring on the
prediction is what makes "a screen that is stuck says which step is stuck" true — two
scouting runs at one tG, or a pair the engine refuses, both leave the list on screen
naming the step that has not happened.

Every one of those judgements is computed here and only *placed* by ``streamlit_app``,
following what ticket #20 established for :mod:`app.diagnostics`. The wording is here
too — including the block's own title and lead — because a step's sentence and the
condition that ticks it are the same decision, and splitting them across two files is
how they come to disagree.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.pipeline import Cockpit, CockpitInputs

TITLE = "Start here"
LEAD = "Four steps, in the order the job runs. The screen fills in as you go."


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


def needs_guidance(cockpit: Cockpit) -> bool:
    """There is still nothing to show — SPEC §7's empty state, and so the worksheet.

    The condition is the absence of a *prediction*, which is exactly what the resolution
    map, the fit table, the resolution table and the chromatogram are all waiting for.
    While it holds, every results surface on the cockpit is empty and the guidance has
    something to say; the moment it lifts, the screen has filled and the guidance goes.
    """
    return cockpit.resolution is None


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
