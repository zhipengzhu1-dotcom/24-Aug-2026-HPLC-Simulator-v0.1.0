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

from hplcsim.model import Gradient, Method, Peak, Run

# No method.csv of its own: the driver confirmed 2026-09-02 that the column, instrument,
# t0 and dwell are the parent `validation/method.csv` set. Restated here rather than
# imported from `lab_data` so the two datasets stay independently editable; the
# restatement is pinned against LAB_METHOD by a test, so it cannot drift unnoticed.
VALIDATION2_METHOD = Method(
    t0=0.6,
    t_dwell=0.9375,
    flow=0.4,
    column_length_mm=100.0,
    column_id_mm=2.1,
    particle_um=1.6,
    temperature_c=45.0,
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
# axis — it moves φ0, which is the axis the scouting pair holds fixed and therefore
# cannot constrain. The bands still elute at 68.5–70.7 %B, inside the 63.5–74.3 %B the
# scouting runs covered, so it extrapolates in the *programme* while interpolating in
# the composition the LSS fit is actually anchored on (research doc §7, ticket #44).
VALIDATION2_RUN4 = Run(Gradient(phi0=0.15, phif=0.95, t_gradient=20.0, t_init=0.5), name="run4")

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
}

# The widths that turn a retention comparison into a *resolution* comparison at the
# held-out conditions — the measurement SPEC §10's Rs bar has always needed.
VALIDATION2_MEASURED_W_HALF = {
    "run1": {"Unknown-1": 0.025, "Unknown-2": 0.023, "Unknown-3": 0.025, "Unknown-4": 0.023},
    "run2": {"Unknown-1": 0.056, "Unknown-2": 0.054, "Unknown-3": 0.057, "Unknown-4": 0.053},
    "run3": {"Unknown-1": 0.031, "Unknown-2": 0.029, "Unknown-3": 0.031, "Unknown-4": 0.029},
    "run4": {"Unknown-1": 0.034, "Unknown-2": 0.032, "Unknown-3": 0.035, "Unknown-4": 0.032},
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
}

VALIDATION2_RUNS_BY_NAME = {
    "run1": VALIDATION2_RUN1,
    "run2": VALIDATION2_RUN2,
    "run3": VALIDATION2_RUN3,
    "run4": VALIDATION2_RUN4,
}

# The two conditions the fit never saw, and what each one is evidence about.
VALIDATION2_HELD_OUT = ("run3", "run4")
