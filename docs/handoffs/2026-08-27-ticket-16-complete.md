# Handoff — ticket #16 (Reality bar) complete → back to the orchestrator

**Repo**: `/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0` · **Remote**: https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0 · **Written**: 2026-08-27 · **Prior handoffs**: `docs/handoffs/2026-08-27-tdd-engine-14-17.md` (per-ticket workflow, still authoritative), `2026-08-27-ticket-15-complete.md` (the brief this session worked from).

## Status: #16 DONE

- Issue #16 closed with a completion comment (the numbers, the doc amendment and the review outcome live there — not repeated here).
- `main` = **`aa92097`**, local and origin in sync. Branch `build/16-reality-bar` merged `--no-ff`, deletable.
- Commits: `d91c04b` (TDD build) → `3921296` (review fixes) → `477c030` (merge main in) → `aa92097` (merge to main). Read them with `git show`.
- **94 tests pass on main**; `uv run ruff check`, `ruff format --check`, `mypy` (strict) all clean.
- `/code-review` run on both axes against `main`; every finding addressed or explicitly declined (see `3921296`'s message).

## The one-line result

**No engine change was needed.** The #14/#15 pipeline clears every acceptance bar as it stands, so #16 is fixtures and assertions only: `tests/den_uijl_data.py` (new), `tests/test_reality.py` (new), `tests/lab_data.py` (extended, not re-transcribed), and an amendment to `docs/research/validation-datasets.md` §1.2.

## Things a fresh agent should not re-derive

- **The mean-signed-error bar is the only one of SPEC §10's three that catches a dropped time term.** Dropping Set X's 0.25 min hold gives worst-case 1.889%, and Set Y's column-only t0 gives 0.893% — both *inside* the ±2% per-peak bar. `test_mean_signed_bar_is_what_catches_a_dropped_time_term` pins this so the bar cannot go vacuous. Do not loosen it.
- **Research doc §1.2 was amended** (same precedent as #15's §7.2 amendment). It claimed the engine "should refuse to fit" the four flat compounds; that overstates SPEC. Six of eight refuse; Set Y's Tyramine and Peptide 1 elute after t0 + τ and move with tG, so warnings-over-blocks makes them a low-confidence fit (log10 k0 ≈ −0.25). The split is pinned per compound so doc and test move together.
- **Set Y must use t0 = 0.229 min** (measured uracil), not the paper's stated 0.171 min column dead time. The bare value leaves a systematic +0.41% bias.
- **The corrected Set X cell is load-bearing** — Peptide 3 at tG = 4.5 is the worst-case prediction in the set.
- **`# fmt: off` does not take effect inside a dataclass call argument.** An E501 lint carve-out was added and then removed for this reason; the transcription is now guarded mechanically by `test_fixture_matches_the_transcription_of_record`, which re-parses both tables out of the research doc. Don't re-add the carve-out.
- Every new guard was **mutation-tested**, not trusted green: a digit changed in Set Y's unused tG = 18 column fails; dropping τ's hold from the engine fails 4 tests; the 2.303 slip fails 7.

## Repo state note the orchestrator may not have

**#18 (session file) landed from the parallel track mid-session**, taking `main` from `9e50a80` to `29e88c2` while #16 was in flight. It added `src/hplcsim/session.py` + `tests/test_session.py` and amended **SPEC §8** (schema: `peaks` is now a top-level table, dwell stored as `dwell_min`). No file overlap with #16, and §10 plus the section numbering are unchanged. Merged cleanly; gates were run on the combined state before `main` was touched.

## Next: #17 Peak widths, resolution, G-convention calibration

Frontier, now unblocked, 5 of 10. `gh issue view 17` for criteria. Two things that shorten that session:

1. **The G log-base hazard is the risky part.** Criterion 2 settles it *empirically* against the measured W½ values in `validation/run1.csv` and `run2.csv`. Those columns are already in the repo and nothing reads them yet; `Peak` already carries `w_half_run1` / `w_half_run2`, added by #14 as provenance for exactly this. CLAUDE.md names the 2.303 slip as the project's #1 hazard, so this is the most dangerous remaining engine work.
2. The outcome and evidence must be **recorded in `docs/research/gradient-elution-math.md`** — that is part of the acceptance criteria, not an afterthought.

Also still open from earlier tickets (candidates for a diagnostics ticket, explicitly *not* #17): Δφ_e thresholding into `low_confidence`, the `k_e > 20` warning (§8.2), consuming `Method.t0_is_measured`, and SPEC §6 diagnostic 1 (info flag when a candidate tG leaves the scouting bracket) — #16 asserts the bracket in tests but no engine code emits that flag.

Untracked `teach/` folder is the user's learning material — left untouched, as instructed.

## Suggested skills

- `tdd` — for #17, per the workflow handoff.
- `code-review` — mandatory before each merge (CLAUDE.md Process).
- `research` — optional, only if the G-convention calibration needs a primary source beyond the existing research docs.
