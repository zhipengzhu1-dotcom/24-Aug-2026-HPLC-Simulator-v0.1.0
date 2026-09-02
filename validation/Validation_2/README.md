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
| `sticky-check.json` | scouting pair as a session file | loads the set into the app |

Pre-registered predictions for runs not yet made live in `../run-sheets/`, never here.
Fixtures: `tests/validation2_data.py`.
