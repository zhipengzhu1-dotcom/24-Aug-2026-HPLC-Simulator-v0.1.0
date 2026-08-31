# Handoff — hplcsim, after #20 (diagnostics)

**Date:** 2026-08-30
**Repo:** `/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0`
**Branch:** `main` @ `b2513a2`, clean tree, pushed to origin
**Next focus:** **#21**, then **#22**; #24 is live and the driver is running it

---

## Where things stand

Ticket **#20** (diagnostics and tracking checks) is merged and closed. The account
lives in the places that own it — do not re-derive it here:

- Completion record, walking every acceptance criterion: the closing comment on
  [issue #20](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/20)
- What was built: merge commit `b2513a2`; module layout in `SPEC.md` §9 (amended `26610c1`)
- Review findings and their fixes: `1acb610`, whose message also records the two
  findings that were deliberately *not* acted on and why

Verified on `main` **after** the merge, not just on the branch: **282 tests pass**,
`ruff check`, `ruff format --check` and `mypy` all clean.

The v0.1 build sequence is 10 tickets. #14–#20 and #23 are done. Remaining: **#21, #22**.

## Start here: ticket #21

`gh issue view 21`. #20 left it two things on purpose:

- The **session schema** must learn to store half-paired rows. `app/pipeline.py`'s
  `PeakRow` is the type; `hplcsim/session.py` still round-trips `Peak`, which requires
  both retention times. #19's module docstring already names this as #21's.
- The **guided empty state** and the **sticky chromatogram** (SPEC §7's "carried forward
  from the prototype") are still unbuilt.

## What #20 established that #21 should follow

**Diagnostics are computed in `app/diagnostics.py` and only *placed* by
`streamlit_app.py`.** Every threshold is a named constant with a test pinning it. If #21
adds anything that decides something, it goes in the logic layer — the entry point holds
widgets and layout, and is still the only file excluded from mypy.

**`tests/test_screen.py` is new and is the answer to this project's worst recurring
hazard.** It drives the real entry point through Streamlit's own `AppTest` and asserts
that messages are actually painted. Use it. Its current limit: `st.data_editor` cannot be
driven from `AppTest`, so anything needing a filled peak table still cannot be screen-tested.

## Standing constraints that bite

`CLAUDE.md` is normative — read it. Beyond it:

- **Parallel ticket sessions get separate `git worktree`s.** Never share one checkout.
- **SPEC and research-doc amendments need the driver's approval of the *exact diff*.**
  Show the diff, wait, then apply behind a verbatim-match `assert` on the anchor text.
  `26610c1` is the worked example.
- **Post-v0.1 findings get their own ticket** opening with "Not for v0.1.0". Filed #37
  this way (the two deferred fit-confidence diagnostics).
- **Stage explicit paths, never the working tree.** `docs/research/porosity-for-t0-geometry.md`
  is an untracked skeleton from a killed `/research` run for #33 — it survived this
  session only because every `git add` named its files.

## Hazards this session hit

**The engine could hang, and pytest does not time out.** `_solve_steepness` spun forever
on transposed retention times; the suite presented it as pytest never returning, not as a
failure. `faulthandler.dump_traceback_later(...)` is what located it. Fixed and recorded
as [#38](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/38),
which also suggests `pytest-timeout` — deliberately not added.

**`uv run` contends with itself.** Two concurrent `uv run` invocations blocked on uv's
lock and looked exactly like a hung test. Kill stragglers before believing a hang.

**Stale bytecode still produces false failures.** `PYTHONDONTWRITEBYTECODE=1 uv run pytest
-p no:cacheprovider`, and clear `__pycache__`, before believing a result that contradicts
the source.

## Next after #21 and #22: #24 is live

The driver is running **#24** (estimate t0 from column geometry, and check a measured
one). Its reading is already done — `docs/research/dead-time-from-geometry.md`, 13
primary references — and the ticket says plainly: do not re-derive it. Note that #24 is
four things, not one: the estimator, the two porosity constants, the reverse check on a
*measured* t0, and capturing the marker. The ticket's own framing is that the reverse
check is worth more than the estimator.

`docs/research/porosity-for-t0-geometry.md` is a **skeleton save from a killed `/research`
run** for ticket #33 — section headings with "*(section pending)*" under each. It is
untracked. Whoever resumes that research should re-save early and after each section;
`/research` has been killed by machine sleep twice on this project.

**Closed as not valuable during this session, by the driver:** #37 (two deferred
fit-confidence diagnostics) and #38 (a record of the fit hang). #38 was paperwork only —
the fix is in `3faa5ed` and the regression test in `tests/test_fit.py` stands.

## Conventions worth copying

- Completed tickets get a handoff in `docs/handoffs/`; this is one of them.
- Ticket branches are `build/NN-slug`, merged with `git merge --no-ff`, then the issue is
  closed with a completion comment that walks the acceptance criteria.
- Commit messages explain *why* and name the evidence, and carry the `Co-Authored-By` /
  `Claude-Session` trailers.
- `/implement` for building from a ticket, `/tdd` at agreed seams, `/code-review` before
  every merge — it runs Standards and Spec as parallel sub-agents and does not rerank
  across them. **Verify its findings against the code before relaying them.** Both agents
  were accurate this session; that was checked, not assumed.
