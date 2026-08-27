# Handoff — /implement session for ticket #18 (Session file: inputs-only JSON schema v1)

**Repo**: this working directory · **Remote**: https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0 · **Written**: 2026-08-27, after #15 merged (`65d2afc`; 45 tests green on main). Prior handoffs in this folder: `2026-08-27-tdd-engine-14-17.md` (workflow), `2026-08-27-ticket-14-complete.md`, `2026-08-27-ticket-15-complete.md` (what the engine looks like now).

## The session's job

`/implement` on **[#18 Session file](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/18)**, branch `build/18-session-file`, one ticket only. `gh issue view 18` — the acceptance criteria are the definition of done:

- Round-trip equality on all inputs, including t0 source and per-run optional fields
- `schema_version` and `app_version` present; unknown schema rejected with a clear message
- Field validation produces actionable errors (bad units, missing mandatory fields)

This is the parallel track: a `/tdd` session on #16 (reality bar) may run concurrently — see "Parallel etiquette" below.

## Read first

1. `CLAUDE.md` (auto-loads) — **inputs-only persistence** (fitted results are never serialized; the fit recomputes on load) and the log-convention/units rule: φ and natural-log live inside the engine; the *file* speaks user units (%B 0–100, mL, min) like every other boundary.
2. `SPEC.md` §8 — the schema sketch (normative intent) — and §4 for the field list, units, and optionality.
3. `src/hplcsim/model.py` — the dataclasses being serialized (`Method`, `Gradient`, `Run`, `Peak`) and the **only** boundary converters (`phi_from_percent_b` etc.). Reuse them; do not add a second conversion site.

## One real design question to settle (flagged, with a recommendation)

SPEC §8's sketch nests `peaks` inside each run (`runs: [{tg_min, peaks: [...]}]`), but the in-memory `Peak` — per the peak-tracking decision (#5) and SPEC §5 — is **row-per-compound with `t_r_run1`/`t_r_run2` side by side**, and peak *names are optional* (auto P1…Pn). Storing peaks per-run would force name-based re-matching on load, which the tracking decision deliberately avoided.

**Recommendation: store the peak table once, row-per-compound (both tR and both areas on the row), diverging from the sketch's nesting; keep `runs` for per-run scalars (tG).** If adopted: treat SPEC §8's sketch as illustrative, note the divergence in the completion handoff, and amend SPEC §8's sketch in the same branch so the spec stays truthful (precedent: #15 amended research §7.2 when normative sources disagreed). Invoke `codebase-design` only if this grows into a real seam debate.

## Implementation notes

- Location: `src/hplcsim/session.py` (SPEC §9 layout). Stdlib `json` only — the engine stays UI-free; no pandas.
- `app_version` from `hplcsim.__version__`; `schema_version = 1`; `session_name` stored in-file (it later seeds the download filename, SPEC §8).
- Rejection semantics: a malformed or unknown-schema *file* is a hard, clearly-worded error — CLAUDE.md's warnings-over-blocks governs user *entry*, not corrupt inputs; missing mandatory fields and un-parseable values are errors that name the field.
- `Method.t0_is_measured` maps to the sketch's `t0_source: "measured" | "estimated"`.
- The `candidate` block (tG + hold of the current what-if) round-trips too — it is an input.
- Even under `/implement`, the round-trip property is a natural TDD seam: `load(save(session)) == session`, plus one failing-schema test per rejection rule. Write those first.

## Parallel etiquette (if #16 runs at the same time)

#18 owns `src/hplcsim/session.py` + `tests/test_session.py` (+ the SPEC §8 sketch amendment). Do **not** touch `fit.py`, `retention.py`, `tests/lab_data.py`, `tests/numerics.py`, or the reality-bar tests — those are #16's ground. Before merging: `git fetch && git merge origin/main` (or rebase) so whichever branch lands second integrates cleanly.

## Wrap-up (same loop as #13–#15)

Gates green (`uv run pytest`, `ruff check`, `ruff format --check`, `mypy`) → `/code-review` vs `main` → fix findings → `merge --no-ff` → push → close #18 with a completion comment → append a `ticket-18-complete` handoff in `docs/handoffs/` (include the resolved schema decision) → stop. Untracked `teach/` stays untouched.

## Suggested skills

- **`tdd`** — for the round-trip and rejection seams, even inside `/implement`.
- **`code-review`** — mandatory before merge (CLAUDE.md Process).
- `codebase-design` — only if the peak-table schema question above needs a deeper seam decision.
