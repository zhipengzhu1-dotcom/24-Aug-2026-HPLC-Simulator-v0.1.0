# hplcsim — repo standards

The approved spec is `SPEC.md` (normative). Science detail: `docs/research/gradient-elution-math.md`; validation datasets: `docs/research/validation-datasets.md`; real instrument data: `validation/`.

## Architecture rules

- The engine (`src/hplcsim`) is a **pure library**: it imports no UI code (no streamlit/pandas/plotly). The Streamlit app (`app/`) depends on the engine, never the reverse.
- **Log-convention rule**: retention math runs in the natural-log convention internally (S_e, b_e). Base-10 values (S, log10 k0) appear only at display boundaries, and the conversion lives in exactly one function.
- **Units**: minutes, mL, mm, µm, °C. φ is a fraction 0–1 internally; %B 0–100 exists only at entry/display boundaries.
- **Session persistence is inputs-only** (SPEC §8): fitted results are never serialized; the fit recomputes on load.
- **Warnings over blocks**: user-facing validation warns and annotates; it hard-fails only on impossibilities (e.g. equal scouting gradient times).
- The closed-form fit expression is a **seed only**, never the returned answer (SPEC §3).

## Tooling

- Python ≥ 3.12, uv-managed. Run everything through uv: `uv run pytest`, `uv run ruff check`, `uv run mypy`.
- ruff lints and formats; mypy runs strict on `src/hplcsim`; pytest owns `tests/`.
- Engine correctness is defined by the three-layer test bar (SPEC §10); changes to scientific code must keep every layer green.

## Process

- One build ticket per branch (`build/NN-slug`); run `/code-review` before merging to main.
- Parallel ticket sessions get separate `git worktree`s from the start — never share one checkout (learned the hard way during #16/#18).
