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
| four-peak 8 | `Validation_2/4peaks_run8.csv` | +70 %B | 0.005250 | **0.827** window-widths below |
| three-peak 8 | `run8.csv` | +45 %B | 0.011813 | inside (0.0105–0.0315) |
| ~~three-peak 9~~ | ~~`run9.csv`~~ | ~~+70 %B~~ | ~~0.005250~~ | **withdrawn 2026-09-09 — see #154** |

Window-widths are SPEC §6 item 1's measure, log_β(s\*_edge / s\*_cand), taken from the
engine's own `app.diagnostics.window_widths_outside` — not a linear ratio of the bracket,
which is a different and smaller number.

> **Withdrawal, 2026-09-09 (#154).** The three-peak 75 %B run was never collected. The
> instrument's own report for the day, `08Sep2026 Results.xlsx`, carries three result
> blocks — cannabinoid at 50 and 75 %B, nitrosamine at 50 %B — and no fourth. `run9.csv`
> was built from `Export Data Points23054_75% Nitroso.arw`, whose identity came from its
> filename alone: the `.arw` format carries no sample name, no method and no gradient
> table. The row above is struck rather than deleted because this sheet is a record of
> what was claimed. It fed no residual — its own note read "contributes no retention
> residual" — so nothing below changes except that **only one +70 %B run exists**, on the
> four-peak sample.

Diagnostic 7 is strong on all four (it is strong from +10 %B), so every number is stamped
indicative. The 75 %B runs carry diagnostic 1 as well, and at its **strong** tier: they
move the start *and* leave the steepness bracket, so neither isolates φ0 and neither can
be read as a clean φ0 point.

### These are the first real data on diagnostic 1's strong tier

SPEC §6 item 1 says of the 0.6 window-width boundary:

> **The strong tier is untested by real data** and stays so until a run beyond 0.6
> window-widths elutes on the ramp.

The four-peak 75 %B run is beyond 0.6 — 0.827 — and the engine predicts a peak eluting on
the ramp segment there (Unknown-4), so diagnostic 1 is not silent under #58's rule. That
sentence in SPEC is therefore falsified, by **one** run rather than the two originally
claimed here: the three-peak 75 %B run was withdrawn (#154).

What the runs say about the tier is a weaker thing than it looks, and is **not** proposed
as a SPEC amendment here. The four-peak run misses the retention bar at 4.44 % mean
|ΔtR| — consistent with a strong warning — but it is confounded twice over: φ0 moves +70 %B
at the same time, and every peak elutes at k′ 0.6–1.1, where the residual is reporting the
void rather than the model. So the tier now has data — one run of it — and that run cannot
separate the steepness overshoot from the two other things wrong with it. Raised as its own
ticket (#151) rather than settled here.

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
5.101 min and the trace is flat there; the compound did not appear.

There is **no 75 %B run on this sample** — the one recorded here was withdrawn (#154). What
survives is a statement about the engine alone, which needs no measurement: asked for a
75 %B start on this fit, it puts Unknown-1 at 0.638 and Unknown-2 at 0.909 min, both
*before* the void at t0 + t_D = 1.4625 min. That is not a wrong prediction but an impossible
one, and it is a property of the fit rather than evidence from a run.

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
