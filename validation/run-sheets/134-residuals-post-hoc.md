# #134 — the starting-composition extrapolation, measured and then predicted

**Post-hoc, not pre-registered.** The four injections were made on 2026-09-08 without the
run sheets #134's checklist step 1 asks for, so no prediction was on record before the
answer existed. What was done instead: the measured tables were integrated and committed
first (`8e6761b`), with no engine run and no prediction anywhere in that diff, and the
residuals below were computed only afterwards. That ordering makes the measurement
trustworthy. It does **not** make the residuals a blind test, and nothing here may be
cited as one.

This file lives under `run-sheets/` rather than in `validation/` because it contains
engine output, which that folder exists to keep separate from evidence.

## The programme (driver-supplied, both samples)

50 → 95 %B over tG 20 with a 0.5 min hold at 0.4 mL/min; wash 3 min at 95 %B; return and
re-equilibrate to 27 min. The 75 %B runs are the identical programme with the start moved.
All numbers at the measured t0 = 0.525 min and the instrument's dwell of 0.375 mL.

## Where each run sits

| run | file | φ0 departure | s\* | vs the scouting bracket |
|---|---|---|---|---|
| four-peak 7 | `Validation_2/4peaks_run7.csv` | +45 %B | 0.011813 | exactly the shallow edge (0.011813–0.0315) |
| four-peak 8 | `Validation_2/4peaks_run8.csv` | +70 %B | 0.005250 | 0.333 window-widths below |
| three-peak 8 | `run8.csv` | +45 %B | 0.011813 | inside (0.0105–0.0315) |
| three-peak 9 | `run9.csv` | +70 %B | 0.005250 | 0.250 window-widths below |

Diagnostic 7 is strong on all four (it is strong from +10 %B), so every number is stamped
indicative. The 75 %B runs carry diagnostic 1 as well: they move the start *and* leave the
steepness bracket, so neither isolates φ0 and neither can be read as a clean φ0 point.

## Retention

Four-peak sample, fitted on runs 1–2:

| | measured | predicted | Δ min | Δ % | k′ |
|---|---|---|---|---|---|
| **50 %B** Unknown-1 | 8.309 | 8.567 | +0.258 | +3.11 | 13.04 |
| Unknown-2 | 8.544 | 8.797 | +0.253 | +2.96 | 13.49 |
| Unknown-3 | 9.018 | 9.258 | +0.240 | +2.66 | 14.39 |
| Unknown-4 | 9.184 | 9.418 | +0.234 | +2.55 | 14.71 |
| | | | **mean 2.82 %** | worst 3.11 % | |
| **75 %B** Unknown-1 | 1.788 | 1.675 | −0.113 | −6.31 | 0.62 |
| Unknown-2 | 1.851 | 1.753 | −0.098 | −5.31 | 0.74 |
| Unknown-3 | 2.004 | 1.936 | −0.068 | −3.40 | 1.03 |
| Unknown-4 | 2.055 | 1.999 | −0.056 | −2.72 | 1.13 |
| | | | **mean 4.44 %** | worst 6.31 % | |

Three-peak sample, fitted on runs 1–2: at 50 %B, Unknown-1 measured 2.392 against 2.419
predicted, **+1.11 %** — the only assignable peak in the run. Unknown-2 is predicted at
5.101 min and the trace is flat there; the compound did not appear. At 75 %B nothing is
assignable, and the fit puts Unknown-1 at 0.638 and Unknown-2 at 0.909 min — both *before*
the void at t0 + t_D = 1.4625 min, which is not a wrong prediction but an impossible one.

## Resolution

Four-peak, measured Rs from the measured W½ against predicted, the SPEC §10 convention:

| pair | 50 %B measured | predicted | Δ | 75 %B measured | predicted | Δ |
|---|---|---|---|---|---|---|
| U1→U2 | 2.72 | 2.67 | −0.05 | 1.45 | 2.03 | +0.57 |
| U2→U3 | 5.46 | 5.31 | −0.15 | 3.26 | 4.43 | +1.17 |
| U3→U4 | 1.93 | 1.84 | −0.09 | 1.01 | 1.47 | +0.46 |

At +45 %B every pair is inside ± 0.3 with room to spare. At +70 %B none is — but predicted
W½ there runs 13–16 % narrow on peaks eluting at k′ 0.6–1.1, so the Rs miss is the void
being modelled as if it were retention. Under the k′ ≥ 1 floor, Unknown-1 and Unknown-2 are
excluded outright and the other two clear it only at 1.03 and 1.13.

## What #134 asked

> how far above the scouting start the two-run LSS line still meets SPEC §10's bar, and
> where it stops

**It stops between +20 and +45 %B.** The ladder on the four-peak sample, mean |ΔtR|:

| departure | +10 (run 4) | +20 (run 6) | **+45 (run 7)** | +70 (run 8) |
|---|---|---|---|---|
| | 0.23 % | 0.26 % | **2.82 %** | 4.44 % |

The three-peak sample reads 0.82 % at +10, 1.67 % at +20 and 1.11 % at +45, but its +45
figure rests on a single peak and cannot carry the conclusion.

The failure at +45 %B has a shape worth keeping. Every residual is positive and they are
nearly equal — +0.234 to +0.258 min across four compounds — so the cluster moves late as a
body and its spacing barely changes. That is why the retention bar fails while Rs ± 0.3
holds comfortably in the same run: **at a 45 %B departure the engine is still trustworthy
for resolution and no longer for retention time.** A ceiling stated as one number would
have hidden that.

## Recorded, not concluded

The engine puts three-peak Unknown-3 at 16.107 min in the 50 %B run, and there is an
unnamed measured peak at 15.951 — a residual of −0.97 %, inside the bar. Its spectral match
to the scouting Unknown-3 is only 0.753, and this prediction was computed after the
measurement was in hand, so the agreement confirms nothing. The peak stays unassigned
(driver, 2026-09-09) and contributes no residual. Settling it needs an injection, not an
argument.
