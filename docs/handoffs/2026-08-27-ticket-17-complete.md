# Handoff — ticket #17 (Widths, resolution, G calibration) complete → back to the orchestrator

**Repo**: `/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0` · **Remote**: https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0 · **Written**: 2026-08-27 · **Prior handoffs**: `2026-08-27-tdd-engine-14-17.md` (per-ticket workflow, still authoritative), `2026-08-27-ticket-16-complete.md` (the brief this session worked from).

## Status: #17 DONE — and the engine is feature-complete for v0.1

- Issue #17 closed with a completion comment (the numbers live there — not repeated in full here).
- `main` = **`9c3e4da`**, local and origin in sync. Branch `build/17-widths-resolution` merged `--no-ff`, deletable.
- Commits: `0e0ec08` (TDD build) → `e09f07a` (review fixes) → `0a57565` (the calibration settled by new data) → `9c3e4da` (merge). Read them with `git show`.
- **143 tests pass on main** (94 before); `uv run ruff check`, `ruff format --check`, `mypy` (strict) all clean.
- `/code-review` run on both axes against `main`; every finding addressed or explicitly declined (see `e09f07a`'s message).

## The headline

**Research doc §10 item 5 — the log-base convention inside the band compression factor G — is RESOLVED**, empirically, on held-out data. It was the document's self-declared "highest-risk number".

Be precise about what this does *not* close. `CLAUDE.md`'s log-convention rule and SPEC §3's "the log-base trap is the #1 implementation hazard" are about the **retention** convention — S_e/b_e internal, base-10 only at display, conversion in exactly one function. That discipline is unchanged and still binding. What is settled is only the separate question of which convention G's `p` is written in.

## Things a fresh agent should not re-derive

- **The calibration statistic is N-constancy, not a width ratio.** N is a property of the column, not the run, so the N implied by each of a compound's measured widths must agree across every gradient time. That is N-free by construction and uses all four runs. The shipped natural-log convention holds Unknown-1's N to **0.92% across a fourfold steepness range** (15299 / 15126 / 15023 at tG = 15/45/60); every alternative scatters 5–13%. The *sign of the trend* is the tell — too little compression makes N fall with tG, too much makes it rise.
- **This was impossible until mid-session.** The scouting pair alone gives only a threefold lever and **cannot** separate the shipped convention from its ×ln10 mirror. The first pass shipped on the two primary sources and recorded that limit honestly. The user then filled in the empty `W_half_min` and `area_pct` columns of `run3.csv`/`run4.csv`. Run 4 against run 1 gives the fourfold lever. Do not re-open this question — but if you ever doubt it, a ×2.303 slip now fails five reality tests, where before those widths existed it failed none.
- **`run3.csv`'s W½ is recorded to two decimals** (0.05, 0.05, 0.04) — a ±10% band. It is a robustness check only, never part of the primary verdict. Runs 1, 2, 4 carry three decimals.
- **Only Unknown-1's areas are trustworthy.** Area is *expected* to grow with run time (the user's own correction — an earlier framing of mine was wrong), and all three compounds do: 1.08× / 1.01× / 1.14× end to end. The real fault is a **1.54–1.67× spike at run 2 only** for peaks 2 and 3, which no run-time trend can produce. SPEC §5 already named peaks 2–3. The verdict does not depend on this — it survives averaging over all three compounds, and that robustness is asserted as a test.
- **Extra-column dispersion was checked and does not rescue the mirror.** Shipped is best with no nuisance parameter at all (joint CV 6.70% at σ_ec = 0) and still beats the mirror after the mirror is given its own best-fit σ_ec (7.39% at 1.25 µL).
- **`b_e` now lives in exactly one function** — `retention.gradient_steepness`. It was written four times before review. Mutating it there fails 32 tests. Keep it that way; it is the natural-log convention's most exposed surface.
- Every new guard was **mutation-tested**: both 2.303 directions, dropping G, dropping √N, the rounded 2.355, applying G in every regime, not re-sorting by tR, a wrong Rs denominator, a µm/mm units slip, and the defaulted-N stamp. Each caught by ≥2 tests.

## SPEC was amended in three places (user-approved before applying)

Precedent: #15 amended research §7.2, #16 amended §1.2, #18 amended SPEC §8.

- **§3** — G hazard status Open → RESOLVED, pointing at research doc §5.4.
- **§6 diagnostic 5** — the Width/Rs caveat banner is *not* retired. It is re-based on the one thing still open: a defaulted N. The engine stamps this via `PeakWidth.plate_count_is_default`. **Wording is #19's call.** Absolute widths and Rs are caveated; the critical *pair* is not.
- **§10** — Rs ± 0.3 recorded as **unmet**, with the honest reason. My first attempt at this text blamed the wrong cause and the Spec reviewer caught it; read `e09f07a` before touching it.

## The one thing left open, and it is now the biggest

**Fit N instead of estimating it from geometry.** This is the highest-value remaining width work and it is not filed as a ticket yet.

- The shipped default is N = L/(h·dp) with h = 2 — textbook, documented, overridable, and *not* this column's real efficiency.
- Consequence: predicted widths run 0.67–0.91× measured, and Rs is **18–39% optimistic** at both held-out conditions. This is now the largest error in the width model, larger than anything G contributes.
- Fitting N per compound from the scouting pair alone drops held-out Rs error from 18–39% to 1.5–11.7 absolute Rs units.
- Research doc §5.1 notes DryLab took exactly this route ("measured peak widths as input data").
- `Peak.w_half_run1` / `w_half_run2` already carry the inputs. `tests/test_reality.py::test_resolution_is_uniformly_optimistic_with_a_defaulted_plate_count` is pinned as a one-sided band that **fails deliberately** the day N becomes fitted — that is the signal, not a regression.
- Note SPEC §4 currently specifies N as "global knob, column-based default", so this is a spec change, not just an implementation change.

## Next: #19 Streamlit Cockpit — entry to fit to prediction, live

Frontier, now unblocked, 7 of 10. `gh issue view 19` for criteria. #18 (session file) is already closed, so #21 unblocks as soon as #19 lands.

Things that shorten that session:

1. **The engine is complete and stable.** `model` / `retention` / `fit` / `width` / `resolution` / `session`. #19 is a pure UI ticket — the architecture rule holds: `app/` depends on the engine, never the reverse.
2. **`prototype/main-screen` is the UI mock** for this ticket, untouched since the scaffold. Look at it before designing.
3. **Acceptance criterion 3 is a manual check** against the reality-bar fixtures: the app's run-3 prediction must match `tests/lab_data.py`'s numbers.
4. **Diagnostic 5's banner wording is yours.** See SPEC §6 above; `PeakWidth.plate_count_is_default` is the signal to read.
5. The `resolution_table` output already carries what the UI needs: peaks sorted by predicted tR at the condition, adjacent pairs, and `critical_pair`.

Also still open from earlier tickets (candidates for a diagnostics ticket, and #20 covers some): Δφ_e thresholding into `low_confidence`, the `k_e > 20` warning (§8.2), consuming `Method.t0_is_measured`, and SPEC §6 diagnostic 1 (info flag when a candidate tG leaves the scouting bracket).

Untracked `teach/` folder is the user's learning material — left untouched, as instructed.

## Suggested skills

- `tdd` — #19 is UI, so the per-ticket workflow handoff's flow applies more loosely; use judgement on where the seams are.
- `code-review` — mandatory before each merge (CLAUDE.md Process).
- `run` — #19 needs the app actually launched and looked at; acceptance criterion 1 is a live flow.
