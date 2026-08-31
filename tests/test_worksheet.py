"""The guided empty state of SPEC §7 (ticket #21).

What is being pinned is not the prose but the *conditions*: which step ticks, and when
the worksheet gives way to the cockpit. Those are the judgements, and #20's rule puts
them in the logic layer precisely so they can be asserted here rather than looked at.
"""

from __future__ import annotations

from dataclasses import replace

from app.pipeline import CockpitInputs, PeakRow, run_cockpit
from app.worksheet import is_empty, worksheet_steps
from hplcsim.model import Gradient, Method, Run

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


def test_an_untouched_screen_is_the_empty_state() -> None:
    assert is_empty(run_cockpit(EMPTY))


def test_a_table_of_nothing_but_the_editors_spares_is_still_empty() -> None:
    """The worksheet must not vanish on the first keystroke in a blank spare row."""
    spares = replace(EMPTY, rows=(PeakRow(), PeakRow(), PeakRow()))
    assert is_empty(run_cockpit(spares))


def test_one_tracked_peak_hands_the_screen_to_the_cockpit() -> None:
    assert not is_empty(run_cockpit(replace(EMPTY, rows=(TRACKED,))))


def test_a_half_typed_peak_also_hands_over_rather_than_hiding_the_table() -> None:
    """Pulling the worksheet back over a row being typed would hide the row."""
    half = replace(EMPTY, rows=(PeakRow(name="P1", t_r_run1=9.855),))
    assert not is_empty(run_cockpit(half))


# --- which step is done --------------------------------------------------------------


def test_reaching_this_screen_at_all_means_step_one_is_done() -> None:
    """The dwell is the required constant, and nothing renders until it is entered."""
    assert _steps(EMPTY)[1]


def test_an_empty_screen_has_only_step_one_done() -> None:
    assert _steps(EMPTY) == {1: True, 2: False, 3: False, 4: False}


def test_one_fitted_peak_completes_every_step() -> None:
    assert _steps(replace(EMPTY, rows=(TRACKED,))) == {1: True, 2: True, 3: True, 4: True}


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
