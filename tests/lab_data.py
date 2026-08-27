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
# Column geometry (100 mm × 2.1 mm, 1.6 µm) is metadata for retention but is the
# basis of the plate-count default the width model needs (SPEC §4).
LAB_METHOD = Method(
    t0=0.6,
    t_dwell=0.9375,
    flow=0.4,
    column_length_mm=100.0,
    column_id_mm=2.1,
    particle_um=1.6,
    temperature_c=45.0,
)

# validation/run1.csv and run2.csv: the tG = 15 / 45 min scouting pair (β = 3).
LAB_RUN1 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=15.0, t_init=0.5), name="tG15")
LAB_RUN2 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=45.0, t_init=0.5), name="tG45")

# Per-peak measured retention times from the same two files, with the measured
# widths at half height (the W_half_min column) — the evidence the G convention is
# calibrated against (SPEC §3, research doc §5.4). Recorded to 0.001 min, which is
# a ±1.5–2.7% quantisation band on run 1's narrow peaks; that band is what limits
# how sharply these six numbers can discriminate a compression convention.
LAB_MEASURED_PEAKS = [
    Peak(t_r_run1=9.855, t_r_run2=20.831, name="Unknown-1", w_half_run1=0.033, w_half_run2=0.087),
    Peak(t_r_run1=11.592, t_r_run2=25.932, name="Unknown-2", w_half_run1=0.034, w_half_run2=0.093),
    Peak(t_r_run1=16.159, t_r_run2=39.796, name="Unknown-3", w_half_run1=0.025, w_half_run2=0.071),
]

# Measured W½ (min) for all four runs, keyed by run name then compound. run1/run2
# duplicate what LAB_MEASURED_PEAKS carries above (a consistency test pins them
# together); the held-out runs 3 and 4 are what turned the G calibration from
# "cannot separate the 2.303 factor" into a settled question — research doc §5.4.
LAB_MEASURED_W_HALF = {
    "tG15": {"Unknown-1": 0.033, "Unknown-2": 0.034, "Unknown-3": 0.025},
    "tG25": {"Unknown-1": 0.05, "Unknown-2": 0.05, "Unknown-3": 0.04},
    "tG45": {"Unknown-1": 0.087, "Unknown-2": 0.093, "Unknown-3": 0.071},
    "tG60": {"Unknown-1": 0.114, "Unknown-2": 0.103, "Unknown-3": 0.085},
}

# Half-ULP of the recorded W½, per run — the runs are NOT recorded alike. run3 carries
# two decimals, so its quantisation band is ±10% on a 0.05 min peak against ±1.5% for
# the three-decimal runs. That is why run3 carries almost no weight in §5.4.
LAB_W_HALF_ULP = {"tG15": 0.0005, "tG25": 0.005, "tG45": 0.0005, "tG60": 0.0005}

# Measured peak areas, same keying. Not yet consumed by the engine (SPEC §5's
# area-share tracking is a later ticket), but load-bearing in §5.4 as the
# outcome-independent evidence that Unknown-2 is an unreliable width measurement.
LAB_MEASURED_AREA = {
    "tG15": {"Unknown-1": 13352.0, "Unknown-2": 4829.0, "Unknown-3": 4013.0},
    "tG25": {"Unknown-1": 13648.0, "Unknown-2": 5642.0, "Unknown-3": 4441.0},
    "tG45": {"Unknown-1": 14299.0, "Unknown-2": 9437.0, "Unknown-3": 7057.0},
    "tG60": {"Unknown-1": 14412.0, "Unknown-2": 4872.0, "Unknown-3": 4573.0},
}

# Parameters fitted pre-build from that pair (handoff, 2026-08-27), quoted in the
# base-10 display convention and converted at the boundary.
LAB_PEAKS = [
    RetentionParams(ln_k0=ln_k0_from_log10_k0(2.76), s_e=s_e_from_s_base10(5.08), phi_ref=0.05),
    RetentionParams(ln_k0=ln_k0_from_log10_k0(3.24), s_e=s_e_from_s_base10(4.99), phi_ref=0.05),
    RetentionParams(ln_k0=ln_k0_from_log10_k0(4.76), s_e=s_e_from_s_base10(5.18), phi_ref=0.05),
]

# validation/run3.csv: the tG = 25 confirmation run, held out of the fit. Keyed by
# compound rather than positioned, so a fixture edit cannot silently transpose peaks.
LAB_RUN3 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=25.0, t_init=0.5), name="tG25")
LAB_MEASURED_TG25 = {
    "Unknown-1": 13.787,
    "Unknown-2": 16.658,
    "Unknown-3": 24.358,
}

# validation/run4.csv: tG = 60, outside the 15–45 scouting pair — the extrapolation case.
LAB_RUN4 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=60.0, t_init=0.5), name="tG60")
LAB_MEASURED_TG60 = {
    "Unknown-1": 25.587,
    "Unknown-2": 32.320,
    "Unknown-3": 50.821,
}
