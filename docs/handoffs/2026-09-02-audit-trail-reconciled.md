# Handoff — hplcsim: **audit trail reconciled after the 2026-09-02 bench session**

**Date:** 2026-09-02
**Repo:** `/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0`
**Branch:** `main`, pushed; working tree clean; 392 tests, ruff, mypy green
**Current map:** [#41 — v0.2 map: gradient freedom](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/41)
**This session's ticket:** [#50 — Reconcile the audit trail](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/50), a `wayfinder:task`; closed

---

## What was wrong

After v0.1.0 the checkout and the tracker drifted apart. Locally: campaign #27's φ-range
arm (runs 5–7), a 55 KB research document, and an app feature all sat uncommitted on main
with no ticket; three #49 commits were unpushed. On GitHub: #49 was merged but open, #27's
checklist described a campaign that was not the one run, and #44 / #46 did not know about
either the new data or the research that reads it.

## What this session did

| Where | What |
|---|---|
| [#49](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/49) | closed — close-out records the merge and one correction to its dwell argument |
| [#27](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/27) | closed — the φ-range arm ran; dwell **withdrawn** by the driver's fixed-0.375 mL decision; S-range and replicates moved to #53 |
| [#51](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/51) | build ticket filed retroactively for the chromatogram work; `/code-review` both axes applied; merged at `4ab206f`; closed |
| [#52](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/52) | research ticket filed retroactively; `docs/research/phi0-dependent-retention-residual.md` merged from `research/phi0-retention-residual`; resolved and closed |
| [#53](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/53) | **new, HITL** — bench follow-up: E1 (5→85 %B, tG 20, Validation_2), E4 replicates, E5 re-run of the s\*-matched pair, the pre-registered 4peaks_run5, a wider-S sample |
| [#54](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/54) | **new, task** — five document corrections from #52 §8; blocks #47 alongside #39 and #48 |
| [#44](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/44), [#46](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/46), [#24](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/24) | comments carrying #52's consequences: s\* necessary but not sufficient, φ0 needs its own term, E1 into the bar, settle t0 first |
| main | `a068b22` campaign data + fixtures + fixed-dwell record + Validation_2 README + gitignore; `3791994` research merge; `4ab206f` #51 merge |
| map #41 | Notes, Decisions so far, Not yet specified and Out of scope refreshed |

## The science, in three lines

Held-out over-prediction grows with φ0 — +0.35 / +0.73 / +1.52 % mean at φ0 = 5 / 15 / 25 %B
— and **survives s\*-matching** (runs 3 and 5). Every s\*-mediated mechanism is eliminated,
dwell by cross-dataset inconsistency. The axis (φ0 vs Δφ) is one injection away: **E1**.

## Where to pick up

Frontier on #41, unclaimed: **#44** (now with a fifth sub-question), **#46** (has its data),
**#45** (prototype), **#39 / #48 / #54** (exact-diff doc tasks), **#53** (bench, driver).
#47 is blocked by all of #44, #45, #46, #39, #48, #54. Take #24 seriously as an ordering
constraint before #46 pins numbers.

## Lessons

- **Data and research without a ticket vanish from the record.** Both were good work and
  neither could be found from GitHub. File the ticket first, even retroactively.
- **A review can catch what tests pass.** Both review axes found the stale-window bug
  independently; the 390 green tests never exercised a rerun.
- **"Not measured" and "withdrawn by decision" are different states.** #27's dwell
  criterion was the second; the close-out says so, so nobody re-opens it as a gap.

## Housekeeping

- Branches on origin after this push: `build/51-chromatogram-axes`, `research/phi0-retention-residual` (both merged)
- `HTML Screenshots/` is gitignored (driver's working folder)
- `validation/run-sheets/4peaks_run5-predicted.csv` still awaits its measurement (#53)
