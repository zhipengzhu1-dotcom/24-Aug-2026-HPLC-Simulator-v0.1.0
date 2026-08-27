# Handoff — HPLC Gradient Method Simulator (teach session next)

**Date**: 2026-08-26 · **Local repo**: `/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0` · **Remote**: https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0

## What the next session is for

The user wants a **/teach session** so they fully understand (a) *what type of prototype was built* and (b) *the knowledge that made it work*. That is the whole focus. Invoke the `teach` skill and teach; don't resume build/planning work unless asked (see "Parked state" for what's pending afterwards).

## Who the user is

A **working chromatographer** (Waters Acquity H-Class, CORTECS UPLC Shield RP18 2.1×100 mm 1.6 µm, Empower, 0.1% FA water/ACN methods). Deep bench expertise; the *modeling/software side* is what they're learning. Teach LSS math and software architecture from a chromatographer's vantage point — lab intuition can carry the load (they already understand dwell volume, t0, gradients experientially). They chose every design decision themselves via grilling, so referencing "your decision on X" lands well.

## What was actually built (be precise — three different things get called "the prototype")

1. **A UI mock** (throwaway): three Streamlit layout variants on branch `prototype/main-screen`, file `prototype_main_screen.py`. Cartoon math inside, clearly labeled. The Cockpit variant won. Run: `uv run --with streamlit,pandas,numpy,plotly streamlit run prototype_main_screen.py` from that branch.
2. **A live engine preview** (in-conversation only, ~50 lines of Python, **not committed anywhere**): implemented the real two-run LSS fit + prediction from the research equations and ran it against the user's lab data. This is what the user calls "the simulation". Its logic = the equations in `docs/research/gradient-elution-math.md` (branch `research/gradient-math`): retention tR = τ + t0 + (t0/b_e)·ln[b_e·(k0 − τ/t0) + 1]; b_e = t0·Δφ·S_e/tG; per-peak fit by bisection on S_e with K = (exp(b1·t′1)−1)/b1 from run 1, residual on run 2.
3. **The planned product** (no production code exists yet): spec drafted at `SPEC.md` (repo root, **uncommitted**) — thin Streamlit app over a pure `src/hplcsim` engine library.

## The headline result (the emotional core of the teach session)

From two scouting runs (tG = 15 & 45 min, three unknown peaks), the engine preview **blindly predicted** the user's confirmation runs:

- tG = 25 (interpolation): predicted 13.861 / 16.729 / 24.383 vs measured 13.787 / 16.658 / 24.358 → **0.35% avg, 0.53% worst**
- tG = 60 (extrapolation, 1.33× outside bracket): predicted 25.480 / 32.236 / 50.774 vs measured 25.587 / 32.320 / 50.821 → **0.26% avg**
- Fitted parameters: S(base-10) ≈ 5.08 / 4.99 / 5.18; log10 k0 ≈ 2.76 / 3.24 / 4.76 — textbook small-molecule ranges.
- Signed bias flips between conditions (+0.35% at 25, −0.26% at 60) → mild LSS curvature, *not* dwell error (this interpretation was corrected mid-conversation; the ticket #8 comments record it).

## Knowledge inventory to teach (all sourced in the repo, don't re-derive from scratch)

Primary sources on branches (fetchable, merge pending): `docs/research/gradient-elution-math.md` on `research/gradient-math` (1058 lines: symbol table, derivations, log-base trap §0, two-run fit §3, edge cases §4, band compression §5, β=3 rationale §7); `docs/research/validation-datasets.md` on `research/validation-datasets`.

Concepts that made it work, roughly in teaching order:
1. LSS model (log k linear in φ) and why two runs determine two parameters per peak.
2. The pre-gradient period τ = dwell + hold — why the +1% bias findings made t_D and t_init required inputs (user's own H-Class: t_D = 0.94 min > 2× t0 = 0.6 min).
3. The log-base trap (natural-log internal, base-10 display — spec §3).
4. Why β = tG2/tG1 ≈ 3 (error amplification at close spacing: 8.8% S error at β=1.05 vs 0.13% at β=3).
5. No closed form for the fit → seed + Brent root-find; closed-form-only fails small molecules (138% error at k0=8).
6. Validation design: interpolation vs extrapolation, mean-*signed*-error as the systematic-bias detector, the sign-flip → curvature reasoning.
7. Open hazard: band-compression G log-base convention (10–15% width effect) — settled later by the W½ data the user already measured.
8. Architecture knowledge: why engine library ≠ UI (testability), inputs-only session files (fit recomputed), warnings-over-blocks philosophy.

Lab dataset for concrete examples: `validation/` on main (PROTOCOL.md, method.csv, run1–run4.csv — real numbers, including the raw-area inconsistency on peaks 2–3 that trips the tracking check by design).

## Parked state (do NOT lose)

- Wayfinder map: issue #1; **10 of 11 tickets closed**. Ticket **#11 "Assemble the v0.1 spec" is claimed and open**; `SPEC.md` is drafted at repo root but **uncommitted**, awaiting the user's review. The pending question when they paused: approve spec → commit, close #11, close map. Resume via `/wayfinder` after the teach session.
- Minor gaps: `method.csv` lacks sample identity and t0-marker name; dwell is spec-sheet (375 µL), not measured; run3/run4 lack areas/widths.
- Working dir is on `main`, clean except untracked `SPEC.md` (and gitignored `.DS_Store`).

## Suggested skills

- **`teach`** — the session's purpose; run it on the material above.
- `wayfinder` — only afterwards, to resume spec approval (#11) and complete the map.
- `artifact-design` — load first if the teach output warrants a visual/artifact explainer.
