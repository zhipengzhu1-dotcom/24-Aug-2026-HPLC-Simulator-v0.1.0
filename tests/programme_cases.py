"""Every fixture run of both bench samples, as (method, peaks, gradient, label) cases.

The three-peak sample's scouting pair, its held-out tG runs and campaign #27's φ-range
arm, and the four-peak sample's whole set. "Every fixture on both samples" in #69's and
#70's acceptance criteria is this list; a guard test pins its size.
"""

from __future__ import annotations

from hplcsim.fit import fit_peaks
from lab_data import (
    LAB_METHOD,
    LAB_PEAKS,
    LAB_RUN1,
    LAB_RUN2,
    LAB_RUN3,
    LAB_RUN4,
    LAB_RUN5,
    LAB_RUN6,
    LAB_RUN7,
)
from validation2_data import (
    VALIDATION2_METHOD,
    VALIDATION2_PEAKS,
    VALIDATION2_RUN1,
    VALIDATION2_RUN2,
    VALIDATION2_RUNS_BY_NAME,
)

# The four-peak sample is fixtured as measurements, not parameters; its LSS fit is the
# same two-run fit the reality layer uses.
VALIDATION2_PARAMS = [
    fit.params
    for fit in fit_peaks(VALIDATION2_PEAKS, VALIDATION2_METHOD, VALIDATION2_RUN1, VALIDATION2_RUN2)
]

# Both samples, every run either carries: the three-peak sample's scouting pair, its
# held-out tG runs and campaign #27's φ-range arm, and the four-peak sample's whole set.
# "Every fixture on both samples" in the ticket's first acceptance criterion is this.
_LAB_CASES = [
    (LAB_METHOD, LAB_PEAKS, run.gradient, f"three-peak {run.name}")
    for run in (LAB_RUN1, LAB_RUN2, LAB_RUN3, LAB_RUN4, LAB_RUN5, LAB_RUN6, LAB_RUN7)
]
_V2_CASES = [
    (VALIDATION2_METHOD, VALIDATION2_PARAMS, run.gradient, f"four-peak {name}")
    for name, run in VALIDATION2_RUNS_BY_NAME.items()
]
FIXTURE_CASES = _LAB_CASES + _V2_CASES
