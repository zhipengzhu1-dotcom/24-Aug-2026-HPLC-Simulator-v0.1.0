# Handoff — ticket #15 (Two-run fit) complete → back to the main context

**Repo**: `/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0` · **Remote**: https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0 · **Written**: 2026-08-27 · **Prior handoffs**: `2026-08-27-tdd-engine-14-17.md` (the per-ticket workflow; still authoritative), `2026-08-27-ticket-14-complete.md`.

## Status: #15 DONE

- Issue #15 closed with a completion comment; branch `build/15-two-run-fit` merged `--no-ff` into `main` as `65d2afc`, pushed to origin.
- Commits: `109c293` (TDD build) → `5a25196` (code-review fixes) → `65d2afc` (merge). Read them with `git show` — this doc does not repeat the diff.
- All gates green on main: `uv run pytest` (45 passed), `uv run ruff check`, `uv run ruff format --check`, `uv run mypy` (strict).
- `/code-review` was run (Standards vs CLAUDE.md/SPEC, Spec vs #15/SPEC §3/§10/research §3/§7.2) and every finding was addressed or answered before merge.

## What exists now (for #16 and #17)

- `src/hplcsim/fit.py` — `fit_peak(peak, method, run1, run2) -> FitResult`, `fit_peaks(...) -> list[FitResult]`. Run argument order is not significant; the fit orients the pair internally and reports φ_e in the order the runs were passed.
- `FitResult` fields: `params: RetentionParams`, `beta`, `beta_spacing: "ok" | "warning" | "strong"`, `phi_e_run1`, `phi_e_run2`, `delta_phi_e` (property), `seed_s_e`, `max_residual`, `low_k0`, `low_confidence`.
- **Test helpers now shared** — `tests/numerics.py` (`integrate_fundamental_equation`, the scipy oracle promoted out of `test_retention.py`) and `tests/lab_data.py` (`LAB_METHOD`, `LAB_RUN1`, `LAB_RUN2`, `LAB_MEASURED_PEAKS`, `LAB_PEAKS`). Import them bare (`from lab_data import ...`) — there is no `tests/__init__.py`, pytest puts `tests/` on the path.
- `scipy-stubs` is in the dev group so mypy stays strict over code that imports `scipy.optimize`.

## Decisions made in this session (not derivable from the diff)

- **β spacing warns, never blocks.** The research doc §7.2 said "refuse β < 2"; SPEC §4 is normative and says "warning < 2.5, strong < 1.2, **never a hard block**", which CLAUDE.md's warnings-over-blocks rule seconds. Implemented as `beta_spacing`'s two tiers, and **§7.2 of the research doc was amended** to stop contradicting the spec.
- **Four refusals, all genuine impossibilities**: equal gradient times; runs differing in anything but tG (breaks the §3.3 elimination); φ_e1 ≤ φ_e2 (no LSS root — the peak-tracking failure); no solution below S_e = 200.
- **The early-eluter refusal is deliberately narrow** — it fires only when the band leaves the column before the gradient reaches it, so both runs are the same isocratic measurement and carry no information about S. SPEC §6's early-eluter *badge* is a different case (elutes soon after, still fits) and is not implemented here.
- **The Guillarme reference spreadsheet hard-codes `2.303` where ln 10 belongs** — verified this session. Its *predicted* tR reproduce to ~1e-16 only if that rounding is copied; with exact ln 10 the gap is 0.9–4.0e-5 min. A correct engine cannot match that table to 1e-6 and must not be bent to. Layer 2 therefore asserts against the spreadsheet's *fitted intermediates*, which carry no such rounding. **Recorded in `docs/research/validation-datasets.md` §3.**
- The seed's uselessness is now an executable assertion, not a comment: at log10 k0 = 0.9 it returns S = 7.77 against a true 4.0 while the root-find is exact to 1e-8.

## Deferred (candidates for the diagnostics ticket, not #16)

- **Δφ_e thresholding** — the number is exposed but does not feed `low_confidence`. Research §7.2 wants "smaller than a few times the composition-equivalent of retention-time noise"; that needs a noise constant no spec supplies, and SPEC §6's six v0.1 diagnostics do not list it.
- Still open from #14: the `k_e > 20` warning (§8.2), and consuming `Method.t0_is_measured` to stamp predictions lower-confidence.

## Next: #16 Reality bar

Blocked-by is now clear. `gh issue view 16` for the criteria — den Uijl Sets X and Y (median |ΔtR| ≤ 0.5%, worst ≤ 2%, mean signed ≤ 0.2%), the lab tG = 25 confirmation (avg ≤ 2%, worst ≤ 5%, order correct), and the tG = 60 extrapolation case.

Three things that shorten that session:

1. **The whole pipeline exists now.** #16 is `fit_peaks` on the scouting pair → `predict_retention` at the target condition → compare against measured. No new engine math is required unless the bar fails.
2. **`tests/lab_data.py` already holds the lab half** of the fixture, and `tests/test_fit.py::test_fitting_the_lab_scouting_pair_reproduces_the_pre_build_parameters` already asserts the tG = 25 predictions per peak. #16 widens this to the stated percentage bars, adds tG = 60, and adds den Uijl. Extend `lab_data.py`; do not re-transcribe.
3. **den Uijl Set X has a corrected cell** — the issue says so explicitly. Take the numbers from `docs/research/validation-datasets.md` Example 1, including that correction, and cite the table row in each fixture comment.

Watch for: den Uijl's t_init = 0.25 min and t0 = 0.262 min are small relative to τ, so peaks land near the early-eluter boundary more often than in the lab set — expect `low_confidence` to be set on some of them, and treat that as information rather than a failure.

Untracked `teach/` folder is the user's learning material — left untouched, as instructed.

## Suggested skills

- `tdd` — for #16 and #17.
- `code-review` — mandatory before each merge (CLAUDE.md Process).
