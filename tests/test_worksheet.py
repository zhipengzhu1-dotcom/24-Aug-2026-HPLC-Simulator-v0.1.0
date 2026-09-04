"""The guided empty state of SPEC §7 (ticket #21).

What is being pinned is not the prose but the *conditions*: which step ticks, and when
the worksheet gives way to the cockpit. Those are the judgements, and #20's rule puts
them in the logic layer precisely so they can be asserted here rather than looked at.
"""

from __future__ import annotations

from dataclasses import replace

from app.pipeline import CockpitInputs, run_cockpit
from app.worksheet import needs_guidance, worksheet_steps
from hplcsim.model import Gradient, Method, PeakRow, Run

_SHARED = Gradient(phi0=0.05, phif=0.95, t_gradient=0.0, t_init=0.5)

EMPTY = CockpitInputs(
    method=Method(t0=0.6, t_dwell=0.9375, flow=0.4, column_length_mm=100.0, particle_um=1.6),
    run1=Run(replace(_SHARED, t_gradient=15.0)),
    run2=Run(replace(_SHARED, t_gradient=45.0)),
    candidate=replace(_SHARED, t_gradient=25.0),
)
# The lab pair used throughout the suite: fittable at these two scouting gradients.
TRACKED = PeakRow(name="Acetanilide", t_r_run1=9.855, t_r_run2=20.831)


def _steps(inputs: CockpitInputs) -> dict[int, bool]:
    return {step.number: step.done for step in worksheet_steps(inputs, run_cockpit(inputs))}


# --- when the worksheet is on screen at all ------------------------------------------
#
# The retirement condition is the arrival of a *prediction*, not the first keystroke.
# Retiring on the first row would leave steps 2, 3 and 4 unreachable — each ticks on
# evidence that only exists once rows are entered — so the list would read ✅⬜⬜⬜
# forever and never say which step a stuck screen is stuck on.


def test_an_untouched_screen_is_the_empty_state() -> None:
    assert needs_guidance(run_cockpit(EMPTY))


def test_a_table_of_nothing_but_the_editors_spares_is_still_empty() -> None:
    spares = replace(EMPTY, rows=(PeakRow(), PeakRow(), PeakRow()))
    assert needs_guidance(run_cockpit(spares))


def test_a_prediction_retires_the_guidance() -> None:
    """The screen has filled: SPEC §7's "cockpit layout thereafter"."""
    assert not needs_guidance(run_cockpit(replace(EMPTY, rows=(TRACKED,))))


def test_a_half_typed_peak_leaves_the_guidance_up_because_nothing_is_predicted_yet() -> None:
    half = replace(EMPTY, rows=(PeakRow(name="P1", t_r_run1=9.855),))
    assert needs_guidance(run_cockpit(half))


def test_a_screen_that_is_stuck_keeps_the_guidance_that_names_the_stuck_step() -> None:
    """The case the retirement condition exists for: rows typed, nothing predicted."""
    same = replace(EMPTY, run2=Run(replace(_SHARED, t_gradient=15.0)), rows=(TRACKED,))
    cockpit = run_cockpit(same)

    assert needs_guidance(cockpit)
    steps = {step.number: step.done for step in worksheet_steps(same, cockpit)}
    assert steps[2] is False


# --- which step is done --------------------------------------------------------------


def test_reaching_this_screen_at_all_means_step_one_is_done() -> None:
    """The dwell is the required constant, and nothing renders until it is entered."""
    assert _steps(EMPTY)[1]


def test_an_empty_screen_has_only_step_one_done() -> None:
    assert _steps(EMPTY) == {1: True, 2: False, 3: False, 4: False}


def test_one_fitted_peak_completes_every_step() -> None:
    assert _steps(replace(EMPTY, rows=(TRACKED,))) == {1: True, 2: True, 3: True, 4: True}


def test_only_the_first_two_ticks_can_ever_appear_while_the_guidance_is_on_screen() -> None:
    """The ceiling is ✅✅⬜⬜, and it is the design rather than an accident.

    A prediction exists exactly when at least one peak is fitted, so a screen still
    showing this worksheet has `cockpit.fitted` empty by construction. Steps 3 and 4
    therefore cannot tick here — step 4 completing *is* the worksheet disappearing.
    Pinned so that a future change to the retirement condition has to face it: the
    earlier version of this test was named for a ✅ it then asserted was absent.
    """
    refused = replace(EMPTY, rows=(PeakRow(name="P1", t_r_run1=20.831, t_r_run2=9.855),))
    cockpit = run_cockpit(refused)

    assert needs_guidance(cockpit)
    assert _steps(refused) == {1: True, 2: True, 3: False, 4: False}


def test_a_pair_the_engine_refuses_is_named_at_step_three() -> None:
    """The second of the two stuck states. Without it, step 3 sends a chromatographer
    to a tab that is empty and says nothing about why."""
    refused = replace(EMPTY, rows=(PeakRow(name="P1", t_r_run1=20.831, t_r_run2=9.855),))
    (step,) = [s for s in worksheet_steps(refused, run_cockpit(refused)) if s.number == 3]

    assert "refused by the fit" in step.detail


def test_step_three_gives_plain_directions_when_nothing_has_been_entered_yet() -> None:
    """Nothing is refused on an empty table, so the refusal wording must not appear."""
    (step,) = [s for s in worksheet_steps(EMPTY, run_cockpit(EMPTY)) if s.number == 3]

    assert "refused" not in step.detail
    assert "Fit parameters" in step.detail


def test_two_scouting_runs_at_one_gradient_time_hold_step_two_back() -> None:
    """SPEC §4's one hard failure: the peaks are typed but nothing can be fitted."""
    same = replace(EMPTY, run2=Run(replace(_SHARED, t_gradient=15.0)), rows=(TRACKED,))
    assert _steps(same)[2] is False


def test_step_two_says_which_thing_is_missing() -> None:
    """A stuck screen has to name the step that is stuck, not just fail to tick."""
    same = replace(EMPTY, run2=Run(replace(_SHARED, t_gradient=15.0)))
    (step,) = [s for s in worksheet_steps(same, run_cockpit(same)) if s.number == 2]
    assert "different gradient times" in step.detail


def test_a_peak_the_engine_refuses_leaves_the_fit_step_undone() -> None:
    """Step 3 reads the fit itself, so a row that cannot be fitted does not tick it."""
    # tR falling as tG rises is the transposition `fit` refuses outright (3faa5ed).
    refused = replace(EMPTY, rows=(PeakRow(name="P1", t_r_run1=20.831, t_r_run2=9.855),))
    steps = _steps(refused)
    assert steps[2] is True
    assert steps[3] is False
    assert steps[4] is False


def test_every_step_is_numbered_once_and_in_order() -> None:
    assert [step.number for step in worksheet_steps(EMPTY, run_cockpit(EMPTY))] == [1, 2, 3, 4]


def test_a_done_step_and_an_undone_one_are_marked_differently() -> None:
    done, undone = worksheet_steps(EMPTY, run_cockpit(EMPTY))[:2]
    assert done.marker != undone.marker
