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
predicted.

**Steps 1 and 2 are the chromatographer's; steps 3 and 4 are the app's.** That asymmetry
is the design, not an oversight, and it bounds what the list can ever show. A prediction
exists exactly when at least one peak is fitted, so while this worksheet is on screen
``cockpit.fitted`` is empty by construction — steps 3 and 4 cannot be ticked *here*, and
the list reads ✅✅⬜⬜ at best. Step 4 completing *is* the worksheet disappearing.

So the guidance that a stuck screen owes the reader lives in the step **details**, not in
the ticks. There are two ways to be stuck, and each names itself: two scouting runs at
one tG (step 2), and rows that are paired but that the engine refuses to fit (step 3).

:func:`worksheet_steps` is a pure function and reports all four honestly, including the
all-done state the screen never displays — that state is what the callers' tests assert
against, and computing it here rather than special-casing keeps the four steps one shape.

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
    stuck says *which* step is stuck. See the module docstring for why only the first
    two of those ticks can ever appear while the worksheet is being shown.
    """
    scouting_ready = inputs.run1.gradient.t_gradient != inputs.run2.gradient.t_gradient
    # Rows are paired and the runs differ, yet nothing came back fitted: the engine
    # refused every pair. This is the second of the two stuck states, and without it
    # step 3 would offer a chromatographer directions to a tab that is empty.
    all_refused = bool(cockpit.entry.tracked) and scouting_ready and not cockpit.fitted
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
                "Every pair you have entered was refused by the fit. **Fit parameters** "
                "carries the reason against each row — most often two retention times "
                "that do not move the way a gradient makes them move."
                if all_refused
                else "log10 k0 and S per peak, under **Fit parameters** — one pair of "
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
