"""SPEC §10 item 2's fire/silent table, and the two samples' runs as the Cockpit holds them.

A data module beside `lab_data` and `validation2_data`, for the same reason those exist:
two test files now read the same transcription of SPEC §10 item 2 — `test_diagnostics_v2`
asserts the diagnostics fire on exactly these runs, and `test_overlay` asserts the
*surfaces* SPEC §6 places them on appear on exactly the same ones. One copy, so a run
cannot be re-tiered in one file and left alone in the other.

Nothing here is computed from the code: the expected tiers are the spec's own sentence,
at the measured t0 = 0.525.
"""

from __future__ import annotations

from app.pipeline import CockpitInputs
from hplcsim.model import Method, Peak, PeakRow, Programme, Run, Target
from lab_data import (
    LAB_MEASURED_PEAKS,
    LAB_METHOD,
    LAB_RUN1,
    LAB_RUN2,
    LAB_RUN3,
    LAB_RUN4,
    LAB_RUN5,
    LAB_RUN6_PROGRAMME,
    LAB_RUN7,
)
from validation2_data import (
    VALIDATION2_E1,
    VALIDATION2_METHOD,
    VALIDATION2_PEAKS,
    VALIDATION2_RUN1,
    VALIDATION2_RUN2,
    VALIDATION2_RUN3,
    VALIDATION2_RUN4,
    VALIDATION2_RUN5_PROGRAMME,
    VALIDATION2_RUN6,
)

THREE_PEAK: dict[str, Target] = {
    "run3": LAB_RUN3.gradient,
    "run4": LAB_RUN4.gradient,
    "run5": LAB_RUN5.gradient,
    "run6": LAB_RUN6_PROGRAMME,
    "run7": LAB_RUN7.gradient,
}
FOUR_PEAK: dict[str, Target] = {
    "run3": VALIDATION2_RUN3.gradient,
    "run4": VALIDATION2_RUN4.gradient,
    "run5": VALIDATION2_RUN5_PROGRAMME,
    "run6": VALIDATION2_RUN6.gradient,
    "E1": VALIDATION2_E1.gradient,
}

ALL_FOUR = ("Unknown-1", "Unknown-2", "Unknown-3", "Unknown-4")
SILENT = None

# (sample, run) -> diagnostic 1's tier, diagnostic 7's tier, the peaks 8 fires on, the
# peaks 9 fires on. SPEC §10 item 2, at t0 = 0.525.
TABLE: dict[tuple[str, str], tuple[str | None, str | None, tuple[str, ...], tuple[str, ...]]] = {
    ("three-peak", "run3"): (SILENT, SILENT, (), ()),
    ("three-peak", "run4"): ("info", SILENT, (), ()),
    ("three-peak", "run5"): (SILENT, "strong", (), ()),
    ("three-peak", "run6"): ("info", "strong", (), ("Unknown-3",)),
    ("three-peak", "run7"): (SILENT, "strong", ("Unknown-1",), ()),
    ("four-peak", "run3"): (SILENT, SILENT, (), ()),
    ("four-peak", "run4"): (SILENT, "strong", (), ()),
    ("four-peak", "run5"): (SILENT, "strong", (), ALL_FOUR),
    ("four-peak", "run6"): (SILENT, "strong", (), ()),
    ("four-peak", "E1"): (SILENT, SILENT, (), ()),
}

IDS = [f"{sample}-{run}" for sample, run in TABLE]


def rows(peaks: list[Peak]) -> tuple[PeakRow, ...]:
    """A sample's measured peaks as the Cockpit's own half-typeable rows."""
    return tuple(
        PeakRow(
            name=peak.name,
            t_r_run1=peak.t_r_run1,
            t_r_run2=peak.t_r_run2,
            w_half_run1=peak.w_half_run1,
            w_half_run2=peak.w_half_run2,
        )
        for peak in peaks
    )


def cockpit_inputs(
    method: Method, run1: Run, run2: Run, target: Target, entered: tuple[PeakRow, ...]
) -> CockpitInputs:
    """The cockpit inputs for ``target``, through the rail's door when it is a programme.

    Since #73 ``CockpitInputs.candidate`` is the one-segment reading and the engine
    predicts :attr:`CockpitInputs.target`; a programme goes in by ``with_programme`` so
    the reading is derived, never typed.
    """
    if isinstance(target, Programme):
        return CockpitInputs.with_programme(
            method=method, run1=run1, run2=run2, programme=target, rows=entered
        )
    return CockpitInputs(method=method, run1=run1, run2=run2, candidate=target, rows=entered)


def inputs_for(sample: str, run: str) -> CockpitInputs:
    """One named run of one named sample, as the Cockpit would hold it."""
    if sample == "three-peak":
        return cockpit_inputs(
            LAB_METHOD, LAB_RUN1, LAB_RUN2, THREE_PEAK[run], rows(LAB_MEASURED_PEAKS)
        )
    return cockpit_inputs(
        VALIDATION2_METHOD,
        VALIDATION2_RUN1,
        VALIDATION2_RUN2,
        FOUR_PEAK[run],
        rows(VALIDATION2_PEAKS),
    )
