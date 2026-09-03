# PROTOTYPE — how the candidate's φ range enters the Cockpit (wayfinder ticket #45)

Throwaway. **Never merges to main**; the decision is what carries forward (SPEC §12,
same posture as `prototype/main-screen` and `prototype/resolution-map`).

## Run it

```
uv run --extra app streamlit run streamlit_app.py
```

Then flip with the URL, or the switcher at the foot of the sidebar:

| | |
|---|---|
| `?variant=A` | **Programme table** — the candidate *is* a No. / Time / %B table (the instrument's shape, and #56's); the scouting programme sits above it read-only in the same shape; what differs is named beneath. The sweep slider is gone. Rows 4–5 take a second segment and it is ignored with a warning. |
| `?variant=B` | **Knobs + profile overlay** — start %B, end %B, tG and hold as four slider+box pairs; the programme is *drawn* on the chromatogram against a right-hand %B axis (scouting runs dashed grey, candidate solid) with each peak's calibrated window as a bar at its apex and a diamond where the candidate puts it. No table; a segment list has nowhere to go. |
| `?variant=C` | **Departure rail** — "As run" is a pinned dense panel; the candidate is numbers; every departure from the scouting pair is a coloured panel row ("Start %B 15 (+10) · ×2.1 error", "s* 0.0096 · 0.20 ww out", "Rs standing: indicative") with the prose behind a "Why" expander. "+ Add a segment" is stubbed and refused. |
| absent | the v0.1 rail, untouched — which is why every test that drives the entry point stays green |
| `?data=lab` | `validation/sticky-check.json` — three peaks, Rs 30–116, windows that do not overlap |
| `?data=v2` | `validation/Validation_2/sticky-check.json` — four peaks in 0.5 min, critical pair Rs 1.75 |
| `?data=own` | whatever is typed in (default) |
| `&b0=15&b1=55&tg=25` | seed the candidate on a demo load — this is #44's trap case: tG inside [15, 45], s* outside |

Worth seeing, in this order:

1. `?variant=B&data=lab&b0=15&b1=55&tg=25` — the trap. Gentle on s* (0.20 window-widths), strong on φ0 (+10 %B, ×2.1), peak 3 pushed post-gradient and 25 %B below its window; Rs stamped indicative.
2. `?variant=A&data=lab&b0=25&b1=95&tg=25` — raise the start to 25 %B: Unknown-1 gets the low-k0 badge (log₁₀ k0 1.74 < 2.1) and only its pairs are downgraded.
3. `?variant=C&data=v2&b0=15&b1=95&tg=22.2` — Validation_2 at the s*-matched raised start: s* in bracket, φ0 strong, the 0.089 min critical pair stamped.
4. Any variant with `data=v2` and no seeds — nothing fires; the surfaces stay quiet.

## What is real and what is not

Real: every number. The candidate `Gradient` carries its own φ0/φf into `run_cockpit`
unchanged — the engine's `predict_retention` and `resolution_table` already take any
gradient. s\*, the bracket, the window-widths overshoot, each peak's window
`[φe,run2, φe,run1]` and where the candidate puts its elution composition are computed
in `prototype/composition.py` from `FitResult.phi_e_run1/2` and `RetentionParams`,
by the research's formulas (`composition-extrapolation.md` §7.2–7.3,
`phi0-dependent-retention-residual.md` §7.4). The thresholds are #44's resolution:
0.6 window-widths and 10 %B, both provisional there.

Not real, and not the v0.2 code: `prototype/composition.py` has no tests, breaks
`Diagnostic.code`'s Literal on purpose (three new codes), and stashes its analysis in
`session_state` so hooks later in the render order can read it. The four #44 surfaces
are wired the same way in every variant — the *form* of the two candidate-control
warnings is what varies (prose boxes in A and B, panel rows in C).

## Where it touches the real app

`streamlit_app.py`, nine hunks, all commented `PROTOTYPE #45`: the import; the demo
restore and switcher in `main`; the candidate block handed to the variant; `amend` after
`diagnose`; the candidate notices; two summary rows; the fit-tab columns and caption;
the chromatogram overlay hook; the status-bar cells. Nothing under `app/` or `src/`
changes.

## Observations recorded while building (for the #45 decision, not for this branch)

- **Both candidate-control warnings fall below the fold at 1440 × 900 in B and C.** Four
  slider+box pairs (B) or the "As run" panel plus two pairs (C) push diagnostics 1 and 7
  under the viewport; only A keeps the first warning visible. SPEC §6 puts them "at the
  candidate controls"; the rail's height budget is what decides whether that is true.
  This is #56's density question arriving early.
- **The trap case (15 → 55 %B, tG 25) throws Unknown-3 post-gradient to tR ≈ 108 min** —
  its window is 80–90 %B and the ramp stops at 55. Real under LSS, and the reason the
  research says to check φe < φf before committing a run. The x axis follows it.
- The per-peak window readout ran off the right of the fit table as extra columns; it is
  a second table beneath instead. #44 said "one readout row per peak" — a row in its own
  table reads fine, a fifth column past "Note" does not fit the tab.
- The Flags column prints a new badge's raw code unless `app/tables.py` learns the label
  — the build ticket adds `low_k0` to `_BADGE_LABEL` (the prototype reaches in).
- Peak-table spare rows render `None` (#25 item 4, still reproducible on a rendered page).

- **Saving refuses a candidate whose %B differs from the scouting runs'** — the sidebar
  shows "Not saveable yet — session file: the candidate gradient must span the same %B
  range". That is `session.py::_check_candidate`, which #44 already says becomes a
  warning path; SPEC §8's file needs `pct_b_start`/`pct_b_end` on the candidate too.
- `MethodEntry.gradient` is the one %B → φ turn; the variants build the candidate's
  `Gradient` through `phi_from_percent_b` themselves, which is a second turn. The build
  ticket should give `MethodEntry` a candidate-with-its-own-range constructor.
- The status bar already prints the candidate's %B range from the `Gradient`, so it
  distinguishes "predicted" from "run" for free once the candidate carries its own φ.
