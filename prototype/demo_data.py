"""THROWAWAY demo sessions, ticket #31.

Two datasets, because the pane has to survive both:

* **Lab** — `validation/`, the real three-peak scouting pair. Its pairs sit at Rs
  30–116 (SPEC §10), so its map is a flat, uneventful ceiling: the boring case, which
  is exactly the layout stress no synthetic dataset would apply.
* **Eight-peak** — invented compounds, honest physics. Their (ln k0, S_e) are made up;
  every tR and W½ below is then *forward-computed by `hplcsim`* at tG 15 and 45 and
  handed to the app as scouting entries, so the app fits them the way it fits real
  ones and the sweep is a genuine LSS map with genuine order flips.
"""

from __future__ import annotations

from hplcsim.model import Gradient, Method, Peak, RetentionParams, Run
from hplcsim.retention import predict_retention
from hplcsim.session import Session
from hplcsim.width import peak_width

METHOD = Method(
    t0=0.525,
    t_dwell=0.9375,
    flow=0.4,
    column_length_mm=100.0,
    column_id_mm=2.1,
    particle_um=1.6,
    temperature_c=45.0,
    t0_is_measured=True,
)
HOLD = 0.5
PHI0, PHIF = 0.05, 0.95
TG1, TG2 = 15.0, 45.0

# name, ln k0 (at phi_ref 0), S_e — invented, chosen so the map has something to say.
INVENTED: list[tuple[str, float, float]] = [
    ("Impurity A", 6.2, 22.0),
    ("Impurity B", 7.6, 27.5),
    ("Main", 9.4, 30.0),
    ("Des-methyl", 10.264, 33.0),
    ("Isomer 1", 12.6, 38.0),
    ("Isomer 2", 13.27, 40.0),
    ("Dimer", 16.5, 45.0),
    ("Late unknown", 18.425, 50.0),
]


def _forward(ln_k0: float, s_e: float, t_gradient: float) -> tuple[float, float]:
    """(tR, W½) this compound would give at ``t_gradient`` — the engine's own numbers."""
    params = RetentionParams(ln_k0=ln_k0, s_e=s_e, phi_ref=0.0)
    gradient = Gradient(PHI0, PHIF, t_gradient, HOLD)
    retention = predict_retention(params, METHOD, gradient)
    width = peak_width(params, METHOD, gradient, plate_count=16000.0)
    return retention.t_r, width.w_half


def eight_peak() -> Session:
    peaks = []
    for name, ln_k0, s_e in INVENTED:
        tr1, w1 = _forward(ln_k0, s_e, TG1)
        tr2, w2 = _forward(ln_k0, s_e, TG2)
        peaks.append(
            Peak(
                name=name,
                t_r_run1=round(tr1, 3),
                t_r_run2=round(tr2, 3),
                w_half_run1=round(w1, 4),
                w_half_run2=round(w2, 4),
            )
        )
    return _session("PROTOTYPE #31 — eight peaks, invented", peaks)


def lab() -> Session:
    """`validation/run1.csv` + `run2.csv`, entered as they stand."""
    peaks = [
        Peak(9.855, 20.831, "Unknown-1", w_half_run1=0.033, w_half_run2=0.087),
        Peak(11.592, 25.932, "Unknown-2", w_half_run1=0.034, w_half_run2=0.093),
        Peak(16.159, 39.796, "Unknown-3", w_half_run1=0.025, w_half_run2=0.071),
    ]
    return _session("PROTOTYPE #31 — lab runs 1+2", peaks)


def _session(name: str, peaks: list[Peak]) -> Session:
    return Session(
        method=METHOD,
        runs=(
            Run(Gradient(PHI0, PHIF, TG1, HOLD), name="run 1"),
            Run(Gradient(PHI0, PHIF, TG2, HOLD), name="run 2"),
        ),
        candidate=Gradient(PHI0, PHIF, 25.0, HOLD),
        peaks=tuple(peaks),
        untracked=(),
        plate_count=None,
        session_name=name,
    )
