# Run sheets

Predicted retention times for runs that have **not been made yet** — engine output, not
measurement. They live here rather than in `validation/`, which `CLAUDE.md` reserves for
real instrument data, so that nothing can mistake a prediction for evidence.

Each file carries a `PREDICTION` block naming the engine version, the runs the fit was
built from, the date, and a confidence note. Committing one timestamps the prediction
ahead of the run, which is the point: a prediction recorded after the fact is worthless.

When the run is made, put the measured file in `validation/` under its own name. Leave
the run sheet here unchanged — overwriting it destroys the pre-registration.

| file | condition | status |
|---|---|---|
| `4peaks_run5-predicted.csv` | Validation_2 sample, tG 25, 15 → 55 %B (run **P** on #53) | measured 2026-09-03 as `../Validation_2/4peaks_run5.csv` — mean −1.33 %, regime and order as predicted (#46) |
| `4peaks_run6-predicted.csv` | Validation_2 sample, tG 25, 25 → 95 %B (raised φ0 by 20 %B, in-bracket on s\*) | measured 2026-09-03 as `../Validation_2/4peaks_run6.csv` — mean +0.20 %, worst +0.23 %, order as predicted (#46, #53) |
| `4peaks_E1-predicted.csv` | Validation_2 sample, tG 20, 5 → 85 %B (**E1** on #53 — separates φ0 from Δφ) | measured 2026-09-03 as `../Validation_2/E1.csv` — mean Δ +0.017 min, predicted − measured (#46, #53) |
| `4peaks_E4-run3-predicted.csv` | Validation_2 sample, tG 20, 5 → 95 %B (**E4** replicates of run 3) | measured 2026-09-03 as `../Validation_2/E4_Run3.csv`, two replicates in one file (#53) |
| `4peaks_E4-run4-predicted.csv` | Validation_2 sample, tG 20, 15 → 95 %B (**E4** replicates of run 4) | awaiting measurement |
| `E5-run3-predicted.csv` | `validation/` sample, tG 25, 5 → 95 %B (**E5** repeat of run 3) | awaiting measurement |
| `E5-run5-predicted.csv` | `validation/` sample, tG 22.2, 15 → 95 %B (**E5** repeat of run 5) | awaiting measurement |

The injection order and the re-equilibration correction are in `sequence-2026-09-03.md`.
The measured files did **not** take the names that document planned, and the
re-equilibration ran shorter than it pre-registered; its dated addendum (§6) maps planned
to actual, and the table above is the authority for which sheet each measured file answers.
