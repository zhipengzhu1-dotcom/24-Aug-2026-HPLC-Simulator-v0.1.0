"""The Validation_2 four-peak dataset as test fixtures (method, scouting runs, peaks).

A *different sample* from the one `lab_data.py` carries, injected on the same
instrument and column. It is kept in its own module rather than added to the `LAB_*`
constants for two reasons: those constants are keyed by gradient time across four runs
that share one sample, and `test_reality.py`'s G-convention calibration iterates them
as a closed set (a new key there silently changes §5.4's answer).

Why the sample exists: SPEC §10's `Rs ± 0.3` criterion was unmet for want of a near-
critical pair, not for want of a better model — the `validation/` sample's pairs sit at
Rs 30–116, where ±0.3 is a 0.3–1% tolerance no width model meets and no method decision
needs. These four compounds elute inside a 0.5 min window with a critical pair at
Rs ≈ 1.75, which is where the bar was written to bite.

Runs are keyed by file name, not by tG. Runs 3 and 4 are *both* tG = 20 and differ only
in φ0, so gradient time stopped identifying a run the moment run 4 arrived — the same
reason `lab_data.py` keys campaign #27 by name.
"""

from __future__ import annotations

from hplcsim.model import Gradient, Method, Peak, Programme, Run, Segment

# No method.csv of its own: the driver confirmed 2026-09-02 that the column, instrument,
# t0 and dwell are the parent `validation/method.csv` set. Restated here rather than
# imported from `lab_data` so the two datasets stay independently editable; the
# restatement is pinned against LAB_METHOD by a test, so it cannot drift unnoticed.
VALIDATION2_METHOD = Method(
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

# 4peaks_run1.csv / 4peaks_run2.csv: the scouting pair, 5 → 95 %B. β = 40/15 = 2.67 —
# above the protocol's 2.5 floor, below its preferred 3.0, so `classify_spacing` returns
# "ok" and the fits are not flagged low-confidence.
VALIDATION2_RUN1 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=15.0, t_init=0.5), name="run1")
VALIDATION2_RUN2 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=40.0, t_init=0.5), name="run2")

# 4peaks_run3.csv: tG = 20 in the same 5 → 95 %B window — interpolation inside the
# scouting bracket, held out of the fit.
VALIDATION2_RUN3 = Run(Gradient(phi0=0.05, phif=0.95, t_gradient=20.0, t_init=0.5), name="run3")

# 4peaks_run4.csv: tG = 20 again, but starting at 15 %B. Not a second point on the same
# axis — and not a clean φ0 change either. Pinning φf while raising φ0 also moves Δφ
# (0.90 → 0.80) and therefore s* = t0·Δφ/tG (0.0270 → 0.0240), so three things move
# together and no difference between run3 and run4 may be attributed to φ0 alone.
#
# It does not extrapolate the fit. composition-extrapolation.md §7.2 shows the candidate
# gradient enters the elution composition only through s*, and 0.0240 is inside the
# scouting bracket [0.0135, 0.0360]; the bands duly elute at 68.5–70.7 %B, inside the
# 63.5–74.3 %B the scouting runs covered. So run4 is a change of *programme* that leaves
# the composition interpolated — which is why it is scored on the same bar as run3.
#
# #49 records the injection that would separate the three: 5 → 85 %B at tG 20 shares φ0
# with run3 and Δφ, tG and s* with run4.
VALIDATION2_RUN4 = Run(Gradient(phi0=0.15, phif=0.95, t_gradient=20.0, t_init=0.5), name="run4")

# --- the 2026-09-03 bench session (#53, scored on #46) ---
#
# Three more programmes and two replicates, all keyed by file name like runs 3 and 4.
# Every one was pre-registered under validation/run-sheets/ before injection; the sheet
# each measured file answers is named in validation/run-sheets/README.md.

# 4peaks_run5.csv — run P, the trap case: 15 → 55 %B at tG 25 with a 19.5 min hold at
# 55 %B, then a 95 %B wash. tG is inside the scouting bracket but s* = 0.0096 is 0.35
# window-widths below it, and the engine puts all four peaks *after* the ramp, in the
# hold, flagged low-confidence — which is what happened. The engine sees only the single
# ramp; the hold and the wash are what the programme table records and v0.1 cannot model.
VALIDATION2_RUN5 = Run(Gradient(phi0=0.15, phif=0.55, t_gradient=25.0, t_init=0.5), name="run5")

# The same file's full programme table: the ramp above, the 19.5 min hold at 55 %B, the
# step to the 95 %B wash and 2.9 min there, the step down and 3.9 min at 25 %B. Every
# peak leaves in the first hold, ~10 min before the wash arrives — which is what makes
# this run SPEC §10 item 4(c)'s inertness case: the wash changes nothing.
VALIDATION2_RUN5_PROGRAMME = Programme(
    phi0=0.15,
    t_init=0.5,
    segments=(
        Segment(25.0, 0.55),
        Segment(19.5, 0.55),
        Segment(0.1, 0.95),
        Segment(2.9, 0.95),
        Segment(0.1, 0.25),
        Segment(3.9, 0.25),
    ),
)

# 4peaks_run6.csv — raised start: 25 → 95 %B at tG 25. Δφ 0.70 and s* = 0.0168, inside
# the scouting bracket, so this run moves φ0 by 20 %B with the composition interpolated.
# log10 k0 at 25 %B is 2.7–2.8 on every peak, above the low-k0 floor, as pre-registered.
VALIDATION2_RUN6 = Run(Gradient(phi0=0.25, phif=0.95, t_gradient=25.0, t_init=0.5), name="run6")

# E1.csv — the axis test (research #52 §5.2): 5 → 85 %B at tG 20 shares φ0 with run3 and
# Δφ, tG and s* (0.0240) with run4. Its residual therefore says which of the two moved
# run4's residual off run3's: it landed at +0.026 min, two fifths of the way from run3's
# +0.019 to run4's +0.036 at t0 = 0.525 (one third at the former 0.6: +0.017 between
# +0.012 and +0.028) — predominantly φ0 (#46 resolution, item 10). Asserted below
# as a measurement, never as that reading.
VALIDATION2_E1 = Run(Gradient(phi0=0.05, phif=0.85, t_gradient=20.0, t_init=0.5), name="E1")

# E4_Run3.csv — run3's programme injected twice more in one sequence, both blocks in one
# file. With the original that is three determinations of one condition: the sample's
# repeatability floor, which is what every pinned residual below is allowed to drift by.
VALIDATION2_RUN3_REP2 = Run(VALIDATION2_RUN3.gradient, name="run3_rep2")
VALIDATION2_RUN3_REP3 = Run(VALIDATION2_RUN3.gradient, name="run3_rep3")

# Per-peak measured tR and W½ from the scouting pair. All four peaks fit cleanly:
# residual ~0, log10 k0 3.71–3.80, S 4.92–4.95, fitted N 29k–34k with the two scouting
# widths agreeing to within 2–11%.
VALIDATION2_PEAKS = [
    Peak(t_r_run1=13.219, t_r_run2=28.036, name="Unknown-1", w_half_run1=0.025, w_half_run2=0.056),
    Peak(t_r_run1=13.317, t_r_run2=28.296, name="Unknown-2", w_half_run1=0.023, w_half_run2=0.054),
    Peak(t_r_run1=13.517, t_r_run2=28.805, name="Unknown-3", w_half_run1=0.025, w_half_run2=0.057),
    Peak(t_r_run1=13.584, t_r_run2=28.984, name="Unknown-4", w_half_run1=0.023, w_half_run2=0.053),
]

# The held-out runs, keyed by compound rather than positioned so a fixture edit cannot
# silently transpose peaks. All four compounds elute in both.
VALIDATION2_MEASURED_TR = {
    "run3": {
        "Unknown-1": 16.373,
        "Unknown-2": 16.504,
        "Unknown-3": 16.768,
        "Unknown-4": 16.857,
    },
    "run4": {
        "Unknown-1": 15.393,
        "Unknown-2": 15.541,
        "Unknown-3": 15.837,
        "Unknown-4": 15.938,
    },
    "run5": {
        "Unknown-1": 32.202,
        "Unknown-2": 32.955,
        "Unknown-3": 34.565,
        "Unknown-4": 35.202,
    },
    "run6": {
        "Unknown-1": 16.448,
        "Unknown-2": 16.658,
        "Unknown-3": 17.074,
        "Unknown-4": 17.218,
    },
    "E1": {
        "Unknown-1": 17.904,
        "Unknown-2": 18.051,
        "Unknown-3": 18.345,
        "Unknown-4": 18.446,
    },
    "run3_rep2": {
        "Unknown-1": 16.372,
        "Unknown-2": 16.503,
        "Unknown-3": 16.767,
        "Unknown-4": 16.857,
    },
    "run3_rep3": {
        "Unknown-1": 16.371,
        "Unknown-2": 16.502,
        "Unknown-3": 16.766,
        "Unknown-4": 16.856,
    },
}

# The widths that turn a retention comparison into a *resolution* comparison at the
# held-out conditions — the measurement SPEC §10's Rs bar has always needed.
VALIDATION2_MEASURED_W_HALF = {
    "run1": {"Unknown-1": 0.025, "Unknown-2": 0.023, "Unknown-3": 0.025, "Unknown-4": 0.023},
    "run2": {"Unknown-1": 0.056, "Unknown-2": 0.054, "Unknown-3": 0.057, "Unknown-4": 0.053},
    "run3": {"Unknown-1": 0.031, "Unknown-2": 0.029, "Unknown-3": 0.031, "Unknown-4": 0.029},
    "run4": {"Unknown-1": 0.034, "Unknown-2": 0.032, "Unknown-3": 0.035, "Unknown-4": 0.032},
    # run5's peaks leave in the hold, 4–6× broader than on any ramp; Unknown-2's 0.16 is
    # a dropped trailing zero, not a two-decimal reading (the export is three-decimal).
    "run5": {"Unknown-1": 0.158, "Unknown-2": 0.160, "Unknown-3": 0.198, "Unknown-4": 0.186},
    "run6": {"Unknown-1": 0.046, "Unknown-2": 0.044, "Unknown-3": 0.047, "Unknown-4": 0.043},
    "E1": {"Unknown-1": 0.034, "Unknown-2": 0.032, "Unknown-3": 0.035, "Unknown-4": 0.032},
    "run3_rep2": {"Unknown-1": 0.031, "Unknown-2": 0.029, "Unknown-3": 0.031, "Unknown-4": 0.029},
    "run3_rep3": {"Unknown-1": 0.031, "Unknown-2": 0.029, "Unknown-3": 0.032, "Unknown-4": 0.029},
}

# All four runs export three decimals, so every width carries the same half-ULP. On
# these narrow peaks that is a ±1.6–2.2% band — tight enough to resolve a ±0.3 miss at
# Rs 1.75 (which would be ±17%) many times over, which is precisely why this sample can
# settle a question the Rs 30–116 sample could not.
VALIDATION2_W_HALF_ULP = 0.0005

# tR is exported to 0.001 min; differences between predicted and measured inherit it.
VALIDATION2_TR_GRANULARITY = 0.001

# Not consumed by the engine (SPEC §5's area-share tracking is a later ticket), carried
# so the fixture can be checked cell-by-cell against the source CSVs. These are ~100×
# the `validation/` set's areas — a different sample at a different concentration or
# detector scaling, which is the one thing about this dataset known *not* to match.
VALIDATION2_MEASURED_AREA = {
    "run1": {
        "Unknown-1": 1161691.0,
        "Unknown-2": 793319.0,
        "Unknown-3": 565688.0,
        "Unknown-4": 477065.0,
    },
    "run2": {
        "Unknown-1": 635387.0,
        "Unknown-2": 454123.0,
        "Unknown-3": 756191.0,
        "Unknown-4": 618829.0,
    },
    "run3": {
        "Unknown-1": 630510.0,
        "Unknown-2": 421702.0,
        "Unknown-3": 779640.0,
        "Unknown-4": 623821.0,
    },
    "run4": {
        "Unknown-1": 630642.0,
        "Unknown-2": 428954.0,
        "Unknown-3": 782671.0,
        "Unknown-4": 626879.0,
    },
    "run5": {
        "Unknown-1": 683768.0,
        "Unknown-2": 496847.0,
        "Unknown-3": 768642.0,
        "Unknown-4": 643506.0,
    },
    "run6": {
        "Unknown-1": 640394.0,
        "Unknown-2": 448902.0,
        "Unknown-3": 778697.0,
        "Unknown-4": 629720.0,
    },
    "E1": {
        "Unknown-1": 634507.0,
        "Unknown-2": 429622.0,
        "Unknown-3": 794099.0,
        "Unknown-4": 630082.0,
    },
    "run3_rep2": {
        "Unknown-1": 635888.0,
        "Unknown-2": 423345.0,
        "Unknown-3": 789737.0,
        "Unknown-4": 628829.0,
    },
    "run3_rep3": {
        "Unknown-1": 635779.0,
        "Unknown-2": 422724.0,
        "Unknown-3": 790949.0,
        "Unknown-4": 627788.0,
    },
}

# Which file each run came from, for the transcription check. Runs 3 and 4 are CRLF with
# a UTF-8 BOM their siblings lack, and run 3's tG_min header arrived reading 40 (a stale
# copy from run 2, corrected by the driver to 20 on 2026-09-02) — the reason that check
# reads the embedded Gradient programme table and not just the header.
VALIDATION2_SOURCE_FILES = {
    "run1": "4peaks_run1.csv",
    "run2": "4peaks_run2.csv",
    "run3": "4peaks_run3.csv",
    "run4": "4peaks_run4.csv",
    "run5": "4peaks_run5.csv",
    "run6": "4peaks_run6.csv",
    "E1": "E1.csv",
    "run3_rep2": "E4_Run3.csv",
    "run3_rep3": "E4_Run3.csv",
}

# E4_Run3.csv holds two peak tables under `Replicate-1` / `Replicate-2` headings above
# one shared programme table; this names the block each replicate fixture was read from.
VALIDATION2_REPLICATE_BLOCK = {"run3_rep2": "Replicate-1", "run3_rep3": "Replicate-2"}

VALIDATION2_RUNS_BY_NAME = {
    "run1": VALIDATION2_RUN1,
    "run2": VALIDATION2_RUN2,
    "run3": VALIDATION2_RUN3,
    "run4": VALIDATION2_RUN4,
    "run5": VALIDATION2_RUN5,
    "run6": VALIDATION2_RUN6,
    "E1": VALIDATION2_E1,
    "run3_rep2": VALIDATION2_RUN3_REP2,
    "run3_rep3": VALIDATION2_RUN3_REP3,
}

# The two conditions the fit never saw, and what each one is evidence about. The v0.1
# bar (SPEC §10's Rs ± 0.3, the near-rigid residual, the dwell argument) is asserted on
# these two only; the 2026-09-03 runs are asserted on #46's bar below, not folded in.
VALIDATION2_HELD_OUT = ("run3", "run4")

# --- #46's bar on the 2026-09-03 runs ---

# Every condition on file that the fit never saw, including the replicates of run3.
# Order is the injection order of the sequence.
VALIDATION2_HELD_OUT_2026_09_03 = ("run5", "run6", "E1", "run3_rep2", "run3_rep3")

# The three determinations of run3's condition; their spread is the repeatability floor.
VALIDATION2_RUN3_DETERMINATIONS = ("run3", "run3_rep2", "run3_rep3")

# The floor itself, measured: the largest tR spread of any peak across the three
# determinations (0.002 min; Unknown-4 0.001) and the largest W½ spread (one export
# step). #46 item 10: E4's tR spread *replaces* the interim ± 0.10 % as the tolerance
# every pinned residual on this sample is allowed.
VALIDATION2_REPEATABILITY_TR = 0.002
VALIDATION2_REPEATABILITY_W_HALF = 0.001

# #46 items 4–5 (SPEC §10 items 2–3): which runs draw the *indicative, not decision-grade*
# stamp, by the two composition guards #44 decided — run4, run5 and run6 all start above
# 5 %B by ≥ 10 %B
# (diagnostic 7, strong). run5 also sits 0.35 window-widths below the s* bracket, but
# diagnostic 1 is silent there: every peak elutes in the hold and none on the ramp (#58),
# so 9 speaks instead. Recorded here as a fixture fact so the reality layer can assert
# the stamp's honesty without importing the app; the app's own diagnostics are tested
# there.
VALIDATION2_STAMPED = ("run4", "run5", "run6")
VALIDATION2_UNSTAMPED = ("run3", "E1", "run3_rep2", "run3_rep3")
# #55 (2026-09-03): the ordering claim in SPEC §10 item 3(a) is asserted only on runs
# strong on 7 *with s* inside the scouting bracket*. run5 is stamped but sits outside the
# bracket, so it is not ordered (its residual is the hold's, −0.51 min, in any case).
VALIDATION2_STAMPED_IN_BRACKET = ("run4", "run6")
