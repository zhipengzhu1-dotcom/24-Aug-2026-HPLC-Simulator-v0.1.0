# hplcsim — repo standards

The approved spec is `SPEC.md` (normative). Science detail: `docs/research/gradient-elution-math.md`; validation datasets: `docs/research/validation-datasets.md`; real instrument data: `validation/`.

## Architecture rules

- The engine (`src/hplcsim`) is a **pure library**: it imports no UI code (no streamlit/pandas/plotly). The app (`app/` plus the root `streamlit_app.py` entry point) depends on the engine, never the reverse.
- **Log-convention rule**: retention math runs in the natural-log convention internally (S_e, b_e). Base-10 values (S, log10 k0) appear only at display boundaries, and the conversion lives in exactly one function.
- **Session-state rule**: `st.session_state` is read and written in exactly one module, `app/screen_state.py`; a test asserts by grep that no other file in `app/`, `scripts/` or `streamlit_app.py` names it. Restoring a session file writes widget state, and state written after a widget is created for that run is state the widget never sees — so `restore()` refuses to run after a read.
- **Units**: minutes, mL, mm, µm, °C. φ is a fraction 0–1 internally; %B 0–100 exists only at entry/display boundaries.
- **Session persistence is inputs-only** (SPEC §8): fitted results are never serialized; the fit recomputes on load.
- **Warnings over blocks**: user-facing validation warns and annotates; it hard-fails only on impossibilities (e.g. equal scouting gradient times).
- The closed-form fit expression is a **seed only**, never the returned answer (SPEC §3).

## Tooling

- Python ≥ 3.12, uv-managed. Run everything through uv: `uv run pytest`, `uv run ruff check`, `uv run mypy`.
- ruff lints and formats; mypy runs strict on `src/hplcsim`, `app/` and `scripts/` (only the root `streamlit_app.py` is excluded); pytest owns `tests/`.
- **The screen has a second gate, and it is not pytest.** `AppTest` has no frontend and no scroll, so anything about layout, stickiness or a browser-held widget value is invisible to it — #57 and #79 both shipped green. `scripts/check_sticky_rows.py` measures SPEC §7's three pinned rows in a real browser; run it after any change to `app/panels.py`'s stylesheet or to where the pinned rows are placed:

  ```bash
  uv run --extra app streamlit run streamlit_app.py --server.headless true --server.port 8767
  uv run --with playwright python scripts/check_sticky_rows.py --port 8767
  ```
- Engine correctness is defined by the three-layer test bar (SPEC §10); changes to scientific code must keep every layer green.

## Process

- One build ticket per branch (`build/NN-slug`); run `/code-review` before merging to main.
- Parallel ticket sessions get separate `git worktree`s from the start — never share one checkout (learned the hard way during #16/#18).
- **A resolution is the record; a research doc is the authority.** Any number a later
  prediction, warning or SPEC line will rest on lands in `docs/research/` (or `SPEC.md`)
  in the **same session that establishes it** — the issue comment carries the story, the
  doc carries the number. A resolution that supersedes a figure already in a research doc
  amends that doc in the same pass, in place, dated and ticket-stamped, with the
  superseded reading kept beneath rather than deleted. The failure this prevents is two
  authorities disagreeing: `run-sheets/4peaks_run6-predicted.csv` and
  `Validation_2/4peaks_run6.csv` carried opposite claims about the re-equilibration
  end-point for five days, and only a later bench run settled which was true.
