# Handoff — 2026-09-03: ticket #24 complete (t0 from geometry, and the re-baseline to 0.525)

For the next session on the v0.2 gradient-freedom map. Written at the end of the #24 session.
Everything below is a pointer; the detail lives on the tracker and in the commits.

## Where things stand

- **Main is at `37a1fbb`** (merge of PR #67). Two PRs landed today under ticket
  [#24](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/24),
  now **closed**:
  - [PR #66](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/pull/66) —
    the estimator (`src/hplcsim/dead_time.py`), the reverse check as a readout, the marker
    field, the Cockpit autofill, two optional session-file fields. Built to the decisions on
    #33 and #34.
  - [PR #67](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/pull/67) —
    every fixture at **t0 = 0.525 min**, every pinned number re-derived, and SPEC §1, §3, §6,
    §10 amended on the driver's approved diffs (the SPEC on main is current; read it there).
- **Gate:** 510 passed, ruff check and format clean, mypy strict clean.
- **The map** is [v0.2 map: gradient freedom #41](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/41).
  Its Notes carry the one-line state of #24. Open on the frontier:
  - [#55 Re-pin the extrapolation thresholds after E1, E4 and the t0 re-baseline](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/55)
    — **now unblocked** (both blockers, #53 and #24, are closed). Its inputs are the last
    comment on that ticket: E1 sits two fifths of the way from run3 to run4; every on-ramp
    four-peak run moved late by 0.007–0.010 min; the 0.4 % ceiling holds with E1 at 0.14 %.
  - [#47 Assemble the v0.2 SPEC amendment](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/47)
    — the map's final ticket. Has two inputs from today posted as comments: the §4 / §6 / §8
    text the estimator implies, and a §10 caveat ("inside the noise" is now *every on-ramp
    condition*, since run5's Rs left the repeatability band at 0.525).

## What the next session must know that is not on a ticket

1. **Four claims changed shape at 0.525 and are pinned as they now stand, not loosened.**
   Each is recorded in `tests/test_reality.py` beside its pin with the 0.6-era value, and in
   the #24 close-out comment. In one line each: the base-10 rival convention now scatters
   3.8 % vs the shipped 1.2 % (floor 4 % → 3 %, still > 2×); the default N beats the fitted
   N for Unknown-3 at tG 60 (`_DEFAULT_WIDTH_WINS`); the dwell-sensitivity bound is 0.3 %;
   run5's Rs is 0.009–0.020 below the repeatability band (`_V2_REPEATABILITY_SHORTFALL`).
2. **Research-doc tables computed at 0.6 stay as computed**, each with a provenance note:
   `dead-time-from-geometry.md` §6, `gradient-elution-math.md` §5.4,
   `composition-extrapolation.md` §2.2, research #52 §3. Do not re-derive them unless a
   ticket asks; the regimes and arguments are the point, not the baseline.
3. **The shared checkout collision.** Two sessions ran in the main checkout
   (`24-Aug-2026 HPLC Simulator v0.1.0/`) at once. The #24 session created its branch there;
   the #47 session ran `git checkout task/47-spec-amendment` and back to `main` in the same
   directory, so the #24 commit landed on local main and had to be moved. Nothing was lost
   and nothing wrong reached origin. The #47 session then continued in its own worktree
   (`../hplcsim-task-47`, branch `task/47-spec-amendment` at `a30ef59`, one commit ahead of
   the *old* main). **Rule from now on:** `git worktree add ../hplcsim-<ticket>-<slug> -b
   <branch>` as the first step of any ticket, and `git branch --show-current` in the same
   Bash call as every `git commit`. Also: `validation/method.csv` is CRLF — write bytes.
4. **#47's branch needs a rebase onto main** before its SPEC diff is re-presented: SPEC §1,
   §3, §6 and §10 changed on main today (numbers at 0.525). Its §4 diff should be built
   against the drafted text on #36 / #47 comments, not against line 39 as it stood.
5. **Driver decisions recorded today on #24** (do not re-ask): re-baseline yes, on its own
   branch (done); the `particle_um` acceptance clause dropped; the typed value stays stamped
   as estimated when "Geometry estimate" is chosen with no architecture; the Cockpit opens on
   t0 = 0.525.

## Suggested skills

- `/wayfinder work on #55` — the next decision ticket; it is a grilling ticket, so
  `/grilling` and `/domain-modeling` inside it. Start by reading the last comment on #55.
- `/wayfinder work on #47` — only after #55 if the driver wants the provisional numbers
  re-pinned first; otherwise it can run now with the numbers marked provisional (its body
  says so).
- `/code-review` before any merge to main (repo process; both of today's PRs went through
  it and each review found real prose or units defects).
- `/research` only if a ticket names a research question; #55 does not.

## Pointers

- Close-out with the before/after table: #24, last long comment.
- Memory notes for this project live outside the repo; the new one from today is
  "worktree before any commit".
- Screenshots of the sidebar flow were taken in real Chrome via Playwright (see the
  project memory "screenshot Streamlit with Playwright"); nothing is committed from them.
