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
| `4peaks_run5-predicted.csv` | Validation_2 sample, tG 25, 15 → 55 %B | awaiting measurement |
