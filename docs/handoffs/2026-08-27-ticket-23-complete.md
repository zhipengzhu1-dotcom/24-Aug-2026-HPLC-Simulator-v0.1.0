# Handoff — ticket #23 (Fit plate count N from measured peak widths) complete → back to the orchestrator

**Repo**: `/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0` · **Remote**: https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0 · **Written**: 2026-08-27 · **Prior handoffs**: `2026-08-27-tdd-engine-14-17.md` (per-ticket workflow, still authoritative), `2026-08-27-tdd-ticket-23.md` (the brief this session worked from), `2026-08-27-ticket-17-complete.md` (where #23 came from).

## Status: #23 DONE

- Issue #23 closed with a completion comment (the numbers live there — not repeated in full here).
- `main` = **`6769b90`**, local and origin in sync. Branch `build/23-fitted-plate-count` merged `--no-ff`, deletable.
- Commits: `5bb21a4` (research + brief) → `ec8b7dd` (TDD build) → `f663f27` (SPEC/doc amendments, driver-approved) → `4bc562a` (review fixes) → `e709f7a` (SPEC touch-ups, driver-approved) → `6769b90` (merge). Read them with `git show`.
- **174 tests pass on main** (143 before); `uv run ruff check`, `ruff format --check`, `mypy` (strict) all clean.
- `/code-review` run on both axes against `main`; every finding fixed or explicitly declined (see `4bc562a`'s message).

## The headline

**N is fitted per peak from the scouting widths, measured-first.** The largest error in the width model is gone: held-out widths go from 0.69–0.92× measured (geometry default) to 0.99–1.16× (fitted), and held-out Rs from 1.18–1.39× optimistic to 0.90–0.96× — slightly pessimistic, 1.5–11.6 absolute Rs units at Rs 30–116. **SPEC §10's Rs ± 0.3 stays unmet**, now only because of the sample; it is pinned as unmet by a test that fails the day it is met.

## Things a fresh agent should not re-derive

- **The estimator is the geometric mean of the implied N** (least squares in ln W — maximum likelihood when width error scales with width; research doc `plate-count-from-widths.md` §3.2–3.3). On the lab data every combination rule agrees within 0.5% except least squares in absolute σ (2–5%); do not re-open it.
- **The inverse has one home**: `plate_count_from_width` = `(peak_width(..., plate_count=1.0).w_half / w_half)²`. Do not restate G·t0·(1+k_e)/√N anywhere. Same discipline as `retention.gradient_steepness` for b_e.
- **Precedence is fitted > global knob > column default**, stamped via `PeakWidth.plate_count_source` (`"default"` / `"supplied"` / `"fitted"`). `plate_count_is_default` no longer exists — the #17 handoff and SPEC §6 used to name it; SPEC is amended, the old handoff is a dated record.
- **The post-gradient rule**: a width from a run that eluted the peak post-gradient is reported in `implied_run1/2` but left out of `plate_count` when the other run's width is usable; used, with `low_confidence = True`, only when it is the peak's only width. The review argued — correctly — that dropping a known-biased measurement is not a block. Tested with widths built at 4000 and 9000 so the fit's basis is visible.
- **The tG = 25 comparison cannot resolve the residual** — `run3.csv`'s two-decimal W½ leaves measured Rs uncertain by ±9–13%; tG = 60 (three decimals, ±0.5%) can, and its −6.5% / −10% is real. Both are pinned as tests (`..._inside_the_measurement_band`, `..._residual_is_real`); SPEC §10 words it the same way.
- **The 2.303 slip in G is invisible to the fitted-N prediction tests** — a G error is absorbed into the fitted N when the same G fits and predicts (research §2.3). G is guarded by the §5.4 N-constancy tests, which are N-free. Never weaken them.
- **What is fitted is not a USP plate number.** It is an apparent, instrument-inclusive efficiency conditional on the calibrated G (research §1.4, §2.2–2.3). The UI should name it that way. USP's half-height constant is 5.54; the engine uses the exact 8 ln 2 = 5.5452.
- **Unknown-3's N is 1.6× the others' and its two scouting widths disagree by 16%** — two different facts (the review caught me conflating them). The first is intrinsic (its peaks are the narrowest, so extra-column dispersion cannot explain it); the second is the ratio diagnostic #20 will threshold.
- **Every mutation was caught**: eleven slips, each by ≥1 test; the table is in the #23 close comment and `ec8b7dd`/`4bc562a`.

## SPEC was amended in four places (driver-approved, diff shown before applying)

Precedent: #15 amended research §7.2, #16 amended §1.2, #17 SPEC §3/§6/§10, #18 SPEC §8.

- **§3** — N per peak, measured-first; a fitted N is apparent, instrument-inclusive, G-conditional.
- **§4** — the N row: fitted from W½ > global knob > column default, stamped lower-confidence.
- **§6 diagnostic 5** — the banner is scoped to `plate_count_source == "default"`; `FittedPlateCount.low_confidence` is a per-peak badge. **Wording is still #19's.**
- **§10** — Rs ± 0.3 re-evaluated: still unmet, only for the sample; what is asserted instead.
- Research docs: `gradient-elution-math.md` §5.1 (the "v0.2 direction" is v0.1; Molnár §9/§16 citation fixed) and §6 (obstacle 1 closed, with numbers); `plate-count-from-widths.md` is new — §7 lists what could not be verified against primary sources.

## Next: #19 Streamlit Cockpit — entry to fit to prediction, live

Frontier, unblocked (#17 was its only blocker; #23 was never in its chain). `gh issue view 19` for criteria. Things that shorten that session:

1. **The engine is complete and stable**: `model` / `retention` / `fit` / `width` / `resolution` / `session`. #19 is a pure UI ticket — `app/` depends on the engine, never the reverse.
2. **Wiring N**: `fits = fit_peaks(peaks, method, run1, run2)`; then `resolution_table([f.params ...], method, candidate, names=..., plate_count=session.plate_count, plate_counts=[f.plate_count ...])`. The sidebar N knob is the global `plate_count`; peaks with widths override it per peak; show `FittedPlateCount.plate_count`, `ratio` and `low_confidence` per peak.
3. **Diagnostic 5's banner** reads `PeakWidth.plate_count_source == "default"` on the predicted peaks; the wording is yours.
4. `prototype/main-screen` is the UI mock, untouched since the scaffold. Acceptance criterion 3 is a manual check against `tests/lab_data.py`'s run-3 numbers.
5. If #19 runs in parallel with anything else, **separate worktrees from the start** (CLAUDE.md Process).

Also open for #20 (diagnostics): a threshold for `FittedPlateCount.ratio` (lab: 1.011 / 1.074 / 1.162; research §6 suggests ~±10%), precision gating for two-decimal widths, plus the earlier list — Δφ_e thresholding into `low_confidence`, the `k_e > 20` warning (§8.2), consuming `Method.t0_is_measured`, SPEC §6 diagnostic 1. And a design note for whoever touches `resolution_table` next: it now carries three parallel sequences (`params`, `names`, `plate_counts`); bundle them once #19 shows the shape the UI needs.

Untracked `teach/` folder is the user's learning material — left untouched, as instructed.

## Suggested skills

- `tdd` — #19 is UI, so the per-ticket flow applies more loosely; use judgement on where the seams are and confirm them with the driver first.
- `code-review` — mandatory before each merge (CLAUDE.md Process).
- `run` — #19 needs the app actually launched and looked at; acceptance criterion 1 is a live flow.
- `research` — when the driver says "research", invoke it; it writes to `docs/research/` and the driver expects the file.
