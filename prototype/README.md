# PROTOTYPE — the resolution-map pane (wayfinder ticket #31)

Throwaway. **Never merges to main**; the decision is what carries forward (SPEC §12,
same posture as `prototype/main-screen`).

## Run it

```
uv run --extra app streamlit run streamlit_app.py
```

Then flip with the URL, or the switcher in the sidebar footer:

| | |
|---|---|
| `?variant=A` | **One instrument** — every pair on one dense chart, critical pair as the dark envelope, both recommendations annotated in place, readout as a caption below |
| `?variant=B` | **Answer first** — the goal-seek and the ceiling as cards at the top, the map beneath as evidence, split into an Rs strip and a run-time strip |
| `?variant=C` | **Trade-off** — Rs over run time as one two-panel figure with the feasible band spanning both; the recommendations leave the tab and live in the left rail |
| `?data=eight` | eight invented compounds, engine-computed (default) |
| `?data=lab` | `validation/` runs 1+2 — three peaks, Rs 30–116, the *boring* map |
| `?data=own` | whatever is typed in; no demo load |

## What is real and what is not

Real: every curve. The sweep calls `hplcsim.resolution.resolution_table` at each
gradient time, on parameters the app fitted from the entered scouting pair — the same
path the Cockpit already uses for a single candidate. Order flips are located with
Brent on the pair's ΔtR, per #30.

Not real: the eight compounds. Their `(ln k0, S_e)` are invented, then forward-run
through the engine to produce the tR and W½ that get typed in as scouting entries. The
lab dataset has three peaks at Rs 30–116 and its map is a flat line — true, and useless
for judging a layout. The invented set was chosen to put an order flip, a co-elution
zone, a goal-seek inside the bracket and a ceiling at the extrapolation edge all on one
screen.

`prototype/sweep.py` is *not* the v0.2 engine — no tests, no edge handling, no home in
`src/`. It exists so the picture is computed rather than drawn.

## Where it touches the real app

`streamlit_app.py`, four hunks, all commented `PROTOTYPE #31`: the import, the demo
restore + switcher in `main`, a rail slot for variant C, and the map tab calling
`proto.render` instead of `_resolution_map`. `app/chromatogram.py`'s
`resolution_map_placeholder` is untouched — main's v0.1 empty frame still stands.
