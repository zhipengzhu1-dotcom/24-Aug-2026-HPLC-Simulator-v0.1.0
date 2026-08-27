# Handoff — ticket #14 (Retention core) complete → back to the main context

**Repo**: `/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0` · **Remote**: https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0 · **Written**: 2026-08-27 · **Prior handoff**: `docs/handoffs/2026-08-27-tdd-engine-14-17.md` (the per-ticket workflow; still authoritative).

## Status: #14 DONE

- Issue #14 closed with a completion comment; branch `build/14-retention-core` merged `--no-ff` into `main` as `3f10e94`, pushed to origin.
- Commits: `e5a045b` (TDD build) → `347c7bb` (code-review fixes) → `3f10e94` (merge). Read them with `git show` — this doc does not repeat the diff.
- All gates green on main: `uv run pytest` (20 passed), `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` (strict).
- `/code-review` (Standards vs CLAUDE.md, Spec vs #14/SPEC §3–4/§10) was run and findings addressed before merge.

## What exists now (for the next tickets)

- `src/hplcsim/model.py` — `Method`, `Gradient`, `Run`, `Peak`, `RetentionParams` (+ `RetentionParams.k_at(phi)`), boundary converters `phi_from_percent_b` / `percent_b_from_phi`, `s_e_from_s_base10` / `s_base10_from_s_e`, `ln_k0_from_log10_k0` / `log10_k0_from_ln_k0`. The ln(10) factor lives only in `_to_base10` / `_from_base10`.
- `src/hplcsim/retention.py` — `predict_retention(params, method, gradient) -> RetentionResult(t_r, k_e, regime, low_confidence)`; regimes `"isocratic_hold" | "gradient" | "post_gradient"`.
- `tests/test_retention.py` — contains `_integrate_fundamental_equation(...)`, a scipy-based independent solver of the §2.1 fundamental equation. **Reuse it** for #15's round-trip checks and #16; consider promoting it to `tests/conftest.py` or a `tests/numerics.py` helper when a second test file needs it.
- `tests/test_retention.py::LAB_METHOD` / `LAB_PEAKS` — the lab method and pre-build fitted parameters as fixtures.

## Decisions made in this session (not derivable from the diff)

- Δφ = 0 is treated as the isocratic branch (`regime="isocratic_hold"`) rather than an error — warnings-over-blocks.
- `low_confidence` = `regime != "gradient" or k_e < 1 or t'_R < t0`, with t'_R = tR − t0 − τ per the research doc's **symbol table** (a reviewer assumed t'_R = tR − t0; that reading was rejected).
- Deliberately deferred to the diagnostics/UI tickets: the `k_e > 20` warning (§8.2) and consuming `Method.t0_is_measured` to stamp predictions lower-confidence. Both are noted in the #14 close comment.
- `Peak` keeps `t_r_run1` / `t_r_run2` side by side (SPEC §5 entry shape); `Run` is a thin `Gradient` + name wrapper. #15 may reshape these if the fit API wants it.

## Next steps (from the chain)

1. **#15 Two-run fit** — fresh `/tdd` session, branch `build/15-two-run-fit`. Seed = closed form (research doc §3.2), then Brent root-find on the run-2 residual (§3.3), round-trip ≤ 1e-8 (SPEC §10 layer 1). The seed is never the answer (CLAUDE.md).
2. **#18 session file** — now unblocked; `/implement`, lighter parallel option.
3. Then #16, #17 per the prior handoff.

Untracked `teach/` folder is the user's learning material — leave it alone.

## Suggested skills

- `tdd` — for #15/#16/#17.
- `code-review` — mandatory before each merge (CLAUDE.md Process).
- `codebase-design` — if the fit API shape (per-peak vs batch, where `Run`/`Peak` sit) needs a seam decision.
