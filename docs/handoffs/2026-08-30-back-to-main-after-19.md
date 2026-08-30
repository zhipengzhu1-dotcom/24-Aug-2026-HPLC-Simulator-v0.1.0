# Handoff — hplcsim, back to the main line after #19

**Date:** 2026-08-30
**Repo:** `/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0`
**Branch:** `main` @ `b7b688c`, clean tree, pushed to origin
**Next focus:** resume the v0.1 build sequence — **ticket #20** is the next unblocked one

---

## Where things stand

Ticket **#19** (Streamlit Cockpit) is merged and closed. The full account is in the
places that already own it — do not re-derive it here:

- Completion record and lessons: the closing comment on
  [issue #19](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/19)
- What was built and why: merge commit `b7b688c`, and `SPEC.md` §7 (amended `2b82e8b`)
- Review findings and their fixes: commit `1640e60`
- Module layout: `SPEC.md` §9 (amended `e1b7ab7`)

Verified on `main` **after** the merge, not just on the branch: **231 tests pass**,
`ruff check`, `ruff format --check` and `mypy` all clean.

The v0.1 build sequence is 10 tickets. #14–#19 and #23 are done. Remaining: **#20, #21,
#22**.

## Start here: ticket #20

`gh issue view 20` — "Diagnostics and tracking checks wired end-to-end", SPEC §5–§6,
build ticket 8 of 10. It was blocked by #19 and is now free. Label `ready-for-agent`.

Note the shape it asks for, because #19 established the pattern it should follow:
diagnostics must be **computed in a testable logic layer** and only *surfaced* by the
UI. `app/pipeline.py` is that layer and imports no Streamlit; `streamlit_app.py` holds
widgets and layout only and is the one file excluded from mypy. Put diagnostic logic in
`app/` (or the engine where it belongs to the science), never in the entry point.

One diagnostic is already partly present: SPEC §6's diagnostic 5 (the width/Rs caveat
banner) has its wording in `streamlit_app.py` as `_DIAGNOSTIC_5`, and
`Cockpit.defaulted_width_names` computes its scope. #19 owned the wording; #20 owns
wiring the rest.

## Standing constraints that bite

`CLAUDE.md` is normative and was realigned with SPEC §9 in `bd47425` — read it. Beyond it:

- **Parallel ticket sessions get separate `git worktree`s.** Never share one checkout.
  This is in CLAUDE.md and was learned painfully during #16/#18.
- **SPEC and research-doc amendments need the driver's approval of the *exact diff*,
  not the idea.** Show the diff, wait, then apply with a verbatim-match `assert` guard.
- **Post-v0.1 findings get their own ticket** opening with "Not for v0.1.0" — never
  folded into an open v0.1 build ticket, because that silently moves the release
  finish line. Filed #25 and #26 this way.
- **Warnings over blocks.** #20's acceptance criteria say this explicitly for the entry
  checks. Hard-fail only on impossibilities.

## Hazards this session hit — expect them again

**Tests do not see the screen.** Three defects on #19 were found only by the driver
looking at a rendered page, and zero by the 200+ passing tests: the app did not start
at all under `streamlit run`; the left-rail panels clipped their own values; the status
bar sat behind the sidebar. **An HTTP 200 from the Streamlit server proves only that the
HTML shell was served** — do not report "the app is up" on that basis. Guards now exist
for those three specific failures (`tests/test_entry_point.py`, `tests/test_panels.py`)
but they do not generalise.

**Browser automation does not work here.** Two independent causes, both need fixing:
the Claude session must be launched `claude --chrome` (a launch flag, not a runtime
toggle), *and* Chrome must actually be running — `list_connected_browsers` returned `[]`
with Chrome closed. Until both hold, ask the driver for a screenshot; that has a far
better track record than the tooling.

**Stale bytecode cache produces false test failures.** Hit twice on this project. If a
test fails in a way that contradicts the source you just read, re-run with
`PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider` and clear `__pycache__`
before believing it.

**Stage explicit paths, never the working tree.** A `git add` on this session swept the
driver's untracked `teach/` folder into a UI commit. The driver chose to keep it
tracked, so it is now on `main` — but the near-miss stands.

## Running app

A Streamlit process from 2026-08-27 is still serving on **http://localhost:8508**
(`uv run --extra app streamlit run streamlit_app.py --server.port 8508`). It predates
the merge, so restart it before judging current behaviour.

## Open decisions the driver has not made

1. **SPEC §4 promises a geometry t0 estimator that v0.1 does not have.** It is
   [#24](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/24),
   and **#22 (the acceptance sweep) does not currently depend on it.** Either add that
   edge so v0.1 keeps the promise, or soften §4. This is a release-scope call — raise
   it, do not decide it.
2. **The dwell ticket is still unfiled.** `validation/method.csv` records the dwell
   volume as *"from instrument spec sheet, NOT measured"* (0.375 mL ÷ 0.4 = 0.9375 min,
   ~1.6× t0). Unlike t0 it is **not** absorbed by the two-run fit, so it is plausibly
   the largest uncorrected error in the validation dataset. Offer it; it has been
   flagged twice and never commissioned.

## Do not re-litigate

The **default plate count** (`_REDUCED_PLATE_HEIGHT = 2.0` in `src/hplcsim/width.py`) is
a deliberate, documented choice, not a bug. It makes predicted peaks ~1.4× too narrow on
the lab column and Rs correspondingly optimistic — this is already stated in the code
comment and quantified in `docs/research/plate-count-from-widths.md` §2 ("The default N
gave W½ ratios of 0.69–0.92"). I mistakenly reported it as a defect this session and
withdrew it. If it comes up, it is a design-posture question for the driver, not a
finding.

## Suggested skills

- **`/implement`** — for building #20 from its ticket. It expects: work from the ticket,
  use `/tdd` at pre-agreed seams, typecheck and run single test files as you go, full
  suite at the end, then `/code-review`, then commit to the branch.
- **`/tdd`** — #20's diagnostics are pure functions with threshold behaviour and the
  acceptance criteria name specific cases (β under 2.5 / under 1.2, ~30% area-share
  disagreement, the lab dataset's peaks 2–3 inconsistency). Genuinely test-first work;
  #19 was written code-first and that was a real divergence from the skill.
- **`/code-review`** — mandatory before merging to `main` per CLAUDE.md. Fixed point is
  `main`. It runs Standards and Spec as two parallel sub-agents and deliberately does
  not rerank across the axes. **Verify its findings against the code before relaying
  them** — this session's agents were accurate, but that was checked, not assumed.
- **`/research`** — only if a science question needs primary sources. It spawns a
  background agent and writes to `docs/research/`. It has been killed twice by machine
  sleep; instruct it to write a partial file early and re-save after each section.

## Conventions worth copying

- Completed tickets get a handoff in `docs/handoffs/`; this is one of them.
- Commit messages on this project explain *why* and name the evidence, and end with the
  `Co-Authored-By` / `Claude-Session` trailers.
- Ticket branches are `build/NN-slug`, merged with `git merge --no-ff`, then the issue
  is closed with a completion comment that walks the acceptance criteria.
