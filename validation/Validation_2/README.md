# Validation_2 — the four-peak sample

A **different sample** from the one in the parent `validation/` folder, injected on the
**same instrument, column, flow, temperature, injection volume and diluent**, with the
same t0 and dwell — driver-confirmed 2026-09-02, so this folder carries no `method.csv`
of its own; `../method.csv` applies. Four compounds elute inside a 0.5 min window with a
critical pair at Rs ≈ 1.75, which is what SPEC §10's `Rs ± 0.3` bar always needed
(issue #49).

| file | condition | role |
|---|---|---|
| `4peaks_run1.csv` | tG 15, 5 → 95 %B | scouting |
| `4peaks_run2.csv` | tG 40, 5 → 95 %B | scouting |
| `4peaks_run3.csv` | tG 20, 5 → 95 %B | held out |
| `4peaks_run4.csv` | tG 20, 15 → 95 %B | held out — raised φ0 |
| `4peaks_run5.csv` | tG 25, 15 → 55 %B, 20 min hold at 55 | held out — the trap run: s* 0.35 window-widths below the scouting bracket, all four peaks in the hold (pre-registered as `../run-sheets/4peaks_run5-predicted.csv`) |
| `4peaks_run6.csv` | tG 25, 25 → 95 %B | held out — raised φ0 by 20 %B, in-bracket on s* (pre-registered as `../run-sheets/4peaks_run6-predicted.csv`; re-equilibrated 3.4 min, 5.7 CV) |
| `E1.csv` | tG 20, 5 → 85 %B | held out — the axis test (#52 §5.2): shares φ0 with run3 and Δφ / tG / s* with run4 (pre-registered as `../run-sheets/4peaks_E1-predicted.csv`; re-equilibrated 4.0 min, 6.7 CV, not the sheet's 6.4 min, and without its 95 %B wash step) |
| `4peaks_run7.csv` | tG 20, 50 → 95 %B | held out — φ0 raised to 50 %B, s\* 0.0118 on the shallow bracket edge (#134; **not** pre-registered) |
| `4peaks_run8.csv` | tG 20, 75 → 95 %B | held out — φ0 raised to 75 %B; every peak at k′ 0.6–1.1, i.e. in the void, and s\* 0.00525 is 0.33 window-widths below the bracket, so it varies start and steepness together (#134; **not** pre-registered) |
| `E4_Run3.csv` | tG 20, 5 → 95 %B, two replicates of run3 in one file | repeatability — tR spread 0.002 min (0.012 %), W½ within one tick, at 4.0 min / 6.7 CV re-equilibration (#46, #55) |
| `sticky-check.json` | scouting pair as a session file | loads the set into the app |

Runs 7 and 8 are the first files here that were **measured before anything was
predicted**, and the first that carry no pre-registration at all: the injections were
made on 2026-09-08 without the run sheets #134's checklist asks for. They are recorded
as post-hoc evidence and are never cited as a blind test. Their numbers come from
`scripts/measure_runs.py` rather than from Empower's on-screen report, and each file
carries the provenance of the raw export it was read from; the signal itself is in
`../traces/`.

Pre-registered predictions for runs not yet made live in `../run-sheets/`, never here.
Fixtures: `tests/validation2_data.py` — runs 1–4 on SPEC §10's v0.1 bar; runs 5, 6, E1 and the E4 replicates (`run3_rep2`, `run3_rep3`) on #46's bar (`tests/test_reality.py`, last section).
