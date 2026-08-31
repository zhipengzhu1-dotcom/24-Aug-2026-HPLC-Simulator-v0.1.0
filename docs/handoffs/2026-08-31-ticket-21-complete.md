# Handoff — hplcsim, after #21 (session file, empty state, sticky chromatogram)

**Date:** 2026-08-31
**Repo:** `/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0`
**Branch:** `main` @ `2c3011c`, clean tree
**Next focus:** **#22**, the last v0.1 build ticket; #24 is live and the driver is running it

---

## Where things stand

Ticket **#21** is merged and closed. The account lives where it belongs — do not
re-derive it here:

- Completion record, walking every acceptance criterion: the closing comment on
  [issue #21](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/21)
- What was built: merge commit `2c3011c`; the file format in `SPEC.md` §8 and the module
  layout in §9, both amended in `0256350`
- Review findings and their fixes: `0fbafc1` and `5a15f3c`, whose messages also record
  what was deliberately *not* acted on, and why

Verified on `main` **after** the merge, not just on the branch: **363 tests pass**,
`ruff check`, `ruff format --check` and `mypy` all clean.

The v0.1 build sequence is 10 tickets. #14–#21 and #23 are done. Remaining: **#22**.

## What #21 changed that later tickets will meet

**The session file has two peak tables, not one.** `peaks` holds complete pairs;
`untracked_peaks` holds rows with at most one retention time. `hplcsim.model.Peak` is
still strict and still what the engine receives — that was the whole point of option 1
from #21's own ticket comment. A row with *both* retention times in `untracked_peaks` is
refused on save and on load, because it is a tracked peak in the wrong table and SPEC
§5's visible count would then be wrong. `schema_version` stays **1**: the key is
additive, and a session with nothing half-paired writes no such table at all.

**Two new modules in the app's logic layer**, both listed in SPEC §9 now:

- `app/session_io.py` — the translation between `hplcsim.session.Session` and
  `app.pipeline.CockpitInputs`, which disagree about nearly everything (runs as a pair or
  two fields, N whole or float, the peak table split or joined). Also the download's
  filename, and `Restore`, below.
- `app/worksheet.py` — SPEC §7's guided empty state: the four steps and when each is done.

**The entry point now owns widget identity.** Restoring a session means writing
`st.session_state` *before* the widgets are built, so every widget has a key from `Keys`,
the session controls are drawn before everything they can overwrite, and every bounded
widget's range is a named `_*_RANGE` that both the widget call and the restore read.

## Hazards this session hit

**Streamlit raises on an out-of-range state value, and takes the page with it.**
`load_session` refuses an *impossible* number but has no opinion about a merely large
one — a 500-minute candidate tG is a real method and the slider stops at 180. Written in
raw, the whole page became a traceback. `session_io.Restore` clamps and *names* what it
moved. If you add a bounded widget, give it a `_*_RANGE` and route the restore through
`Restore.within`, or you re-open this.

**A long-lived `streamlit run` caches broken modules.** Editing files under a running
server let its watcher re-import `app/session_io.py` mid-write (`write_text` is not
atomic); it cached a truncated module and reported `ImportError: cannot import name
'Restore'` for code that was correct on disk. This is the #20 handoff's stale-bytecode
hazard in a new place — deleting `__pycache__` does not touch a live `sys.modules`. Stop
the server before editing.

**`AppTest` can drive the file uploader.** This is the way past the limit #20 recorded:
`st.data_editor` still cannot be driven, but loading a session file *can*, so
`tests/test_screen.py` now fills the peak table by uploading one. That is how the
untracked count, the worksheet handing over, and every restored widget got under a
screen test. What is still out of reach is a download's *bytes* — `AppTest` runs with no
Streamlit runtime, so the proto carries only a content-hash URL; assert file content in
`tests/test_session_io.py` and use the URL only to prove the button tracks the session.

**Claude in Chrome refused every `navigate` for the whole session**, for
`https://example.com` as readily as for localhost, while `tabs_context_mcp`,
`list_connected_browsers` and `select_browser` all succeeded, and every setting on both
sides reported enabled. The sticky chromatogram was confirmed by the driver looking at
it. Do not budget on driving a browser from here.

## Standing constraints that bite

`CLAUDE.md` is normative — read it. Beyond it, unchanged from the #20 handoff and all
still true: parallel ticket sessions get separate `git worktree`s; SPEC and research-doc
amendments need the driver's approval of the *exact diff*, applied behind a
verbatim-match `assert` on the anchor (`26610c1` and `0256350` are the worked examples);
post-v0.1 findings get their own ticket opening with "Not for v0.1.0"; stage explicit
paths, never the working tree.

## What `/code-review` earned this session, and what it cost

Run twice, and **both rounds found real defects** — one a page-crashing bug, one a
feature that could never show what it computed. Neither was visible in 348 passing tests.

The lesson worth carrying: **the first round's fix did not work.** The review said the
worksheet's steps 2–4 could never tick; the fix changed the retirement condition and
moved the defect one notch rather than removing it, because a prediction exists exactly
when a peak is fitted. The second round caught that. What let it survive the first round
was a test named
`test_steps_two_and_three_can_be_ticked_while_the_guidance_is_still_on_screen` that
asserted `steps[3] is False` — a test whose name claimed the opposite of its assertion,
which is worse than no test. Read the assertion, not the name, when a test is the reason
you believe something is fixed.

So: re-run `/code-review` after acting on a round of findings if the fix was structural
rather than local. Verify every finding against the code before relaying it — both
agents were accurate across both rounds, and that was checked, not assumed.

## Next: #22, then the driver's #24

`gh issue view 22`. It is the last build ticket for v0.1 and is unblocked now that #21 is
in.

**#24** remains the driver's: estimate t0 from column geometry, and check a measured one.
Its reading is already done (`docs/research/dead-time-from-geometry.md`, 13 primary
references) and the ticket says plainly not to re-derive it. It is four things, not one —
the estimator, the two porosity constants, the reverse check on a *measured* t0, and
capturing the marker — and its own framing is that the reverse check is worth more than
the estimator.

`docs/research/porosity-for-t0-geometry.md` is still an untracked skeleton from a killed
`/research` run for ticket #33. Whoever resumes it should re-save early and after each
section; `/research` has been killed by machine sleep twice on this project.

## Conventions worth copying

Unchanged: completed tickets get a handoff in `docs/handoffs/` (this is one); ticket
branches are `build/NN-slug`, merged with `git merge --no-ff`, then the issue is closed
with a completion comment walking the acceptance criteria; commit messages explain *why*
and name the evidence, and carry the `Co-Authored-By` / `Claude-Session` trailers;
`/implement` for building from a ticket, `/tdd` at agreed seams, `/code-review` before
every merge.
