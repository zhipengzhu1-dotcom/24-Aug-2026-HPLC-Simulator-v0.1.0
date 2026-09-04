"""The lab dataset in `validation/` as test fixtures (method, scouting runs, peaks)."""

from __future__ import annotations

from hplcsim.model import (
    Gradient,
    Method,
    Peak,
    Programme,
    RetentionParams,
    Run,
    Segment,
    ln_k0_from_log10_k0,
    s_e_from_s_base10,
)

# validation/method.csv: t0 0.525 min (the driver's 2026-08-31 re-read of the solvent
# front's first disturbance; the 0.6 first entered was the wrong time point), dwell
# 0.375 mL @ 0.4 mL/min, 0.5 min hold. Re-baselined to 0.525 on 2026-09-03 (#24): every
# pinned fit, width, Rs and residual number in tests/test_reality.py was re-derived at it.
# Column geometry (100 mm × 2.1 mm, 1.6 µm) is metadata for retention but is the
# basis of the plate-count default the width model needs (SPEC §4) and, with the
# declared solid-core architecture (CORTECS), of the geometry t0 (0.450 min) the
# measured value is checked against — 29.9 µL of extra-column volume.
LAB_METHOD = Method(
    t0=0.525,
    t_dwell=0.9375,
    flow=0.4,
    column_length_mm=100.0,
    column_id_mm=2.1,
    particle_um=1.6,
    temperature_c=45.0,
    particle_is_solid_core=True,
    t0_marker="solvent front, first disturbance",
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

# Parameters fitted from that pair at t0 = 0.525 (re-baseline, 2026-09-03), quoted in
# the base-10 display convention and converted at the boundary. The pre-build handoff
# of 2026-08-27 fitted 2.76 / 5.08, 3.24 / 4.99, 4.76 / 5.18 at the superseded 0.6 —
# S ~3% higher, log10 k0 within 0.05 — which is what a t0 error does to the *fitted*
# parameters while barely moving the predictions (dead-time-from-geometry.md §6.2).
# These must never be used with a different Method.t0 (that doc's §6.3).
LAB_PEAKS = [
    RetentionParams(ln_k0=ln_k0_from_log10_k0(2.777), s_e=s_e_from_s_base10(4.919), phi_ref=0.05),
    RetentionParams(ln_k0=ln_k0_from_log10_k0(3.249), s_e=s_e_from_s_base10(4.836), phi_ref=0.05),
    RetentionParams(ln_k0=ln_k0_from_log10_k0(4.711), s_e=s_e_from_s_base10(5.016), phi_ref=0.05),
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

# --- campaign #27: the gradient-freedom runs (issue #27, run sheet 2026-09-02) ---
#
# Runs 1–4 all share the 5 → 95 %B window and differ only in tG, which is why the four
# are keyed by gradient time above. These three each carry their own composition window,
# so tG no longer identifies a run (6 and 7 are both tG = 25, as is run 3) — they are
# keyed by file name instead. Held out of the fit exactly as runs 3 and 4 are.
#
# Chosen on steepness s* = t0·Δφ/tG rather than on how different the windows look, since
# elution composition depends on the gradient only through s* (research doc §7):
#   run5 (A)  15 → 95 %B, tG 22.2  — s* matched to run 3; the falsification test
#   run6 (B)  15 → 55 %B, tG 25    — tG inside the scouting bracket, s* below it
#   run7 (C)  25 → 95 %B, tG 25    — raised φ0, in-bracket on s*
LAB_RUN5 = Run(Gradient(phi0=0.15, phif=0.95, t_gradient=22.2, t_init=0.5), name="run5")
LAB_RUN6 = Run(Gradient(phi0=0.15, phif=0.55, t_gradient=25.0, t_init=0.5), name="run6")
LAB_RUN7 = Run(Gradient(phi0=0.25, phif=0.95, t_gradient=25.0, t_init=0.5), name="run7")

LAB_CAMPAIGN27_RUNS = {"run5": LAB_RUN5, "run6": LAB_RUN6, "run7": LAB_RUN7}

# validation/run5.csv, run6.csv, run7.csv. Keyed by compound, so a fixture edit cannot
# silently transpose peaks. Unknown-3 has no run6 entry here on purpose: it left in the
# wash step, not the hold — see LAB_CAMPAIGN27_WASH_ELUTED. Consumers must not assume
# three peaks per run.
LAB_CAMPAIGN27_TR = {
    "run5": {"Unknown-1": 10.980, "Unknown-2": 13.843, "Unknown-3": 21.495},
    "run6": {"Unknown-1": 18.164, "Unknown-2": 24.471},
    "run7": {"Unknown-1": 9.235, "Unknown-2": 12.842, "Unknown-3": 22.770},
}

# Run 6 ends at 55 %B, where the engine puts Unknown-3 at ~110 min in the post-gradient
# hold and flags it low-confidence. It was brought off by the 45.1 min wash step instead,
# under a two-segment programme v0.1 cannot predict. run6.csv now records 46.8 min for
# it (driver-read from the chromatogram 2026-09-03, #46) — a v0.2 multi-segment reality
# point, not a v0.1 one — so it must never be scored against the single-segment engine.
# The engine did predict the non-elution in the hold correctly, which is itself testable.
LAB_CAMPAIGN27_WASH_ELUTED = {("run6", "Unknown-3")}

# validation/run6.csv's programme table, every row: the 15 → 55 %B ramp the `Gradient`
# above records, then the 19.5 min hold at 55, the 0.1 min step to the 95 %B wash, 3 min
# there, the step down to 25 %B and 4 min re-equilibrating. This is what the instrument
# ran, and what the walker (#70) predicts Unknown-3 under — SPEC §10 item 4(d)'s one
# multi-segment reality point. A test re-reads it from the CSV.
LAB_RUN6_PROGRAMME = Programme(
    phi0=0.15,
    t_init=0.5,
    segments=(
        Segment(25.0, 0.55),
        Segment(19.5, 0.55),
        Segment(0.1, 0.95),
        Segment(3.0, 0.95),
        Segment(0.1, 0.25),
        Segment(4.0, 0.25),
    ),
)

# The wash-eluted reading itself, driver-read from the chromatogram on 2026-09-03 (#46),
# with the hand-walked estimate pre-registered before the reading. Kept apart from
# LAB_CAMPAIGN27_TR on purpose: that table is what the single-segment engine is scored
# against, and this number must never reach it.
LAB_CAMPAIGN27_WASH_TR = {("run6", "Unknown-3"): 46.8}
LAB_CAMPAIGN27_WASH_PREREGISTERED = {("run6", "Unknown-3"): 47.0}

LAB_CAMPAIGN27_AREA = {
    "run5": {"Unknown-1": 13441.0, "Unknown-2": 14515.0, "Unknown-3": 7448.0},
    "run6": {"Unknown-1": 14983.0, "Unknown-2": 5707.0},
    "run7": {"Unknown-1": 14524.0, "Unknown-2": 3058.0, "Unknown-3": 8351.0},
}

# Half-height widths, the measurement that makes a held-out *resolution* comparison
# possible rather than a retention-only one (SPEC §10's still-unmet Rs bar). Unknown-2 is
# the broad one in runs 6 and 7 because both elute it more aqueous than any earlier run
# (50.9 and 55.3 %B, against 57.5 in run 5 and 62.3 in run 1) — driver-confirmed as real
# chromatography, not an integration artefact, unlike the tG = 45 area spike in §5.4.
LAB_CAMPAIGN27_W_HALF = {
    "run5": {"Unknown-1": 0.05, "Unknown-2": 0.045, "Unknown-3": 0.039},
    "run6": {"Unknown-1": 0.1, "Unknown-2": 0.132},
    "run7": {"Unknown-1": 0.071, "Unknown-2": 0.135, "Unknown-3": 0.053},
}

# These runs export three decimals; the 0.05 and 0.1 above are trailing zeros the export
# dropped, not two-decimal readings, so they carry run 1/2/4's quantisation rather than
# run 3's. That inference is worth stating because it is what lets these widths into the
# §5.4 discriminator at full weight — if it is wrong, run5 and run6 lose most of theirs.
LAB_CAMPAIGN27_W_HALF_ULP = {"run5": 0.0005, "run6": 0.0005, "run7": 0.0005}

# A property of these three runs worth knowing before a bar is pinned to them. The dwell
# is the instrument's own 0.375 mL (t_D = V_D / F = 0.9375 min) and stays that way by the
# driver's decision — see validation/method.csv. Against it, these runs carry a systematic
# over-prediction that grows with φ0: +0.42 / +0.82 / +1.67% mean at φ0 = 5 / 15 / 25 %B,
# worst peak 2.76% (at t0 = 0.525; +0.35 / +0.73 / +1.52%, worst 2.50%, at the former
# 0.6). Re-scoring at a larger dwell shrinks that (at 0.6, V_D ≈ 0.60 mL put every run
# inside ±0.6% and the worst peak at 0.64%), which is why the residual is
# recorded here as a known offset rather than read as curvature in log k vs φ — the
# φ0 ordering above is what a dwell term does, not what LSS error looks like. Substituting
# a data-tuned dwell to make it go away is not on the table; a tripwire on these runs
# should simply be set where the residual actually sits.

# Which held-out three-peak runs draw the *indicative, not decision-grade* stamp, by the
# two composition guards #44 decided and the tiers #55 re-pinned (SPEC §10 items 2–3).
# Runs 5, 6 and 7 all start ≥ 10 %B above the scouting pair's 5 %B — diagnostic 7,
# strong. Run 4 (s* 0.26 window-widths below the scouting bracket) and run 6 (0.20) are
# gentle on diagnostic 1, which does not stamp. Recorded here as a fixture fact, the way
# `VALIDATION2_STAMPED` is on the four-peak sample, so the reality layer can assert the
# stamp's honesty without importing the app; the app's own diagnostics are tested there.
LAB_STAMPED = ("run5", "run6", "run7")
LAB_UNSTAMPED = ("run3", "run4")
# SPEC §10 item 3(a) orders only runs strong on 7 whose s* is *inside* the scouting
# bracket [0.0105, 0.0315]. Run 6's s* (0.0084) is below it, and it is the run whose two
# biases cancel — a shallow s* pulls early (run 4: −0.106 min), a raised start pushes
# late (run 5: +0.115), and run 6 lands between at +0.039. So it is recorded, not ordered.
LAB_STAMPED_IN_BRACKET = ("run5", "run7")
