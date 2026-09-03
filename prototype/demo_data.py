"""THROWAWAY demo sessions for ticket #45 — both real datasets, per the #31 lesson.

`?data=lab` — `validation/` runs 1+2 (three peaks, 5→95 %B, tG 15/45).
`?data=v2`  — `validation/Validation_2` runs 1+2 (four peaks in 0.5 min, tG 15/40).
`?data=own` — whatever is typed in.

The fixtures under `tests/` are the source of truth for both, so this imports them
rather than copying numbers.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from lab_data import LAB_MEASURED_PEAKS, LAB_METHOD, LAB_RUN1, LAB_RUN2  # noqa: E402
from validation2_data import (  # noqa: E402
    VALIDATION2_METHOD,
    VALIDATION2_PEAKS,
    VALIDATION2_RUN1,
    VALIDATION2_RUN2,
)

from hplcsim.model import Gradient  # noqa: E402
from hplcsim.session import Session  # noqa: E402

CANDIDATE_TG = 25.0


def lab() -> Session:
    g = LAB_RUN1.gradient
    return Session(
        method=LAB_METHOD,
        runs=(LAB_RUN1, LAB_RUN2),
        peaks=tuple(LAB_MEASURED_PEAKS),
        candidate=Gradient(g.phi0, g.phif, CANDIDATE_TG, g.t_init),
        session_name="PROTOTYPE #45 — validation/ runs 1+2",
    )


def v2() -> Session:
    g = VALIDATION2_RUN1.gradient
    return Session(
        method=VALIDATION2_METHOD,
        runs=(VALIDATION2_RUN1, VALIDATION2_RUN2),
        peaks=tuple(VALIDATION2_PEAKS),
        candidate=Gradient(g.phi0, g.phif, 20.0, g.t_init),
        session_name="PROTOTYPE #45 — Validation_2 runs 1+2",
    )
