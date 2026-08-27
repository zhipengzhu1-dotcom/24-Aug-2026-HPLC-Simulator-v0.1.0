"""The lab dataset in `validation/` as test fixtures (method, scouting runs, peaks)."""

from __future__ import annotations

from hplcsim.model import (
    Gradient,
    Method,
    Peak,
    RetentionParams,
    Run,
    ln_k0_from_log10_k0,
    s_e_from_s_base10,
)

# validation/method.csv: t0 measured 0.6 min, dwell 0.375 mL @ 0.4 mL/min, 0.5 min hold.
LAB_METHOD = Method(t0=0.6, t_dwell=0.9375, flow=0.4)

# validation/run1.csv and run2.csv: the tG = 15 / 45 min scouting pair (β = 3).
LAB_RUN1 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=15.0, t_init=0.5), name="tG15")
LAB_RUN2 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=45.0, t_init=0.5), name="tG45")

# Per-peak measured retention times from the same two files.
LAB_MEASURED_PEAKS = [
    Peak(t_r_run1=9.855, t_r_run2=20.831, name="Unknown-1"),
    Peak(t_r_run1=11.592, t_r_run2=25.932, name="Unknown-2"),
    Peak(t_r_run1=16.159, t_r_run2=39.796, name="Unknown-3"),
]

# Parameters fitted pre-build from that pair (handoff, 2026-08-27), quoted in the
# base-10 display convention and converted at the boundary.
LAB_PEAKS = [
    RetentionParams(ln_k0=ln_k0_from_log10_k0(2.76), s_e=s_e_from_s_base10(5.08), phi_ref=0.05),
    RetentionParams(ln_k0=ln_k0_from_log10_k0(3.24), s_e=s_e_from_s_base10(4.99), phi_ref=0.05),
    RetentionParams(ln_k0=ln_k0_from_log10_k0(4.76), s_e=s_e_from_s_base10(5.18), phi_ref=0.05),
]
