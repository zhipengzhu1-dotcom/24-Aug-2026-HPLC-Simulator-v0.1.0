# Handoff — hplcsim, after #22: **v0.1.0 is released**

**Date:** 2026-09-01
**Repo:** `/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0`
**Branch:** `main` @ `1046311`, tagged **`v0.1.0`**
**Next focus:** the v0.2 cycle — resolution map / optimizer (SPEC §11), carrying #24

---

## Where things stand

**The v0.1 build sequence is complete.** Ten of ten tickets: #14–#21, #23, and now #22.
The account lives where it belongs — do not re-derive it here:

- Completion record, walking all three acceptance criteria: the closing comment on
  [issue #22](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/22)
- What shipped: merge `1046311`; the release note is the annotated tag's own message
  (`git tag -n99 -l v0.1.0`), which records the known limits honestly
- The two SPEC amendments and why: `cc4a6f0` (§4) and `76194ba` (§6)

Verified on `main` **after** the merge: **363 tests pass**, `ruff check`,
`ruff format --check` and `mypy` all clean.

**Nothing is pushed.** `main` is 4 commits ahead of `origin/main` and the `v0.1.0` tag is
local only (`git push origin main --follow-tags` when the driver wants it public). This is
the first thing to check if a later session thinks the release is missing.

## What #22 changed

Documentation only — no engine or app code was touched, which is the right shape for a
release wrap.

- **SPEC §4** no longer promises a geometry-based t0 estimator. t0 is entered, required, in
  v0.1; the estimator is deferred to v0.2 (#24), which §11's roadmap already covers.
- **SPEC §6 item 6** now states the trigger the code actually implements (see the lesson
  below).
- **README** is a real quickstart: the uv commands, a worked walkthrough on the `validation/`
  data, and a map of where things are documented.

## The lesson worth carrying: a review finding can be right and its conclusion wrong

`/code-review`'s Spec axis flagged SPEC §6 item 6 — "Estimated-t0 stamp … when the geometry
fallback was used", under a heading reading "All six ship in v0.1" — as an orphaned promise
left behind by the §4 softening. Correct. It then concluded the diagnostic was vestigial and
should move to v0.2. **That conclusion was wrong**, and applying it would have deferred a
feature that ships and works:

- `app/diagnostics.py:282` stamps every output whenever `Method.t0_is_measured` is false
- `streamlit_app.py:511` sets that flag from a sidebar control
- `src/hplcsim/session.py:43` round-trips `t0_source` as `measured` / `estimated`

The stamp fires on a **user-declared** estimated t0 and never needed a geometry estimator.
Verifying the finding against the code turned a proposed feature deferral into a six-word
wording fix. The #21 handoff said to verify every finding before relaying it; this is the
session where that actually paid, and the failure mode was subtler than a wrong finding — it
was a true observation with a false remedy attached.

Standards axis was clean, and usefully so: it independently confirmed the two README claims
most likely to be wrong (the `--extra app` requirement, and that every cited path is tracked).
Point a reviewer at the claims you least trust in your own work.

## Hazards this session hit

**`uv run streamlit run streamlit_app.py` works on this machine and fails on a fresh clone.**
streamlit, pandas and plotly are an *optional* extra (`[project.optional-dependencies] app`),
so the bare command only succeeds in a venv that already carries them — which every machine
that has built this repo does. `uv sync --dry-run` shows a bare sync *removing* all three.
The correct command, now in the README, is `uv run --extra app streamlit run streamlit_app.py`.
Any command you have only ever run on a developed machine is an untested claim.

**Streamlit's first-run email prompt kills a non-interactive launch.** Backgrounded, it blocks
on stdin and exits 255 with nothing but a welcome banner in the log. `--server.headless true`
skips it (and stops it opening a browser tab). Do not read the exit code as a broken app.

**Git identity was auto-derived from the hostname.** Commits up to and including `b7d1576`
carry `Maracchi <maracchi@Maracchis-MacBook-Pro.local>`; the driver fixed the config
mid-session and re-authored from `cc4a6f0` on. Worth knowing before anyone reads `git log`
and concludes there were two contributors.

**The browser tooling still refuses to drive this app**, unchanged from #21. SPEC §§3–9 were
cross-checked by the driver at the screen. Budget for a human on any criterion phrased "against
the running app".

## Open threads for v0.2

- **#24** — estimate t0 from column geometry, and check a measured one. Reading is done
  (`docs/research/dead-time-from-geometry.md`, 13 primary references) and the ticket says not
  to re-derive it. Its own framing: the reverse check on a *measured* t0 is worth more than the
  estimator. SPEC §4 and §6 now point at it truthfully, so it inherits no false promise.
- **t0 0.525 vs 0.6.** `validation/method.csv` records t0 = 0.525 min (solvent front, read off
  `run1-chromatogram.png`), but `tests/lab_data.py:19` still fits at `t0=0.6`. Deliberate:
  re-baselining is #24's call. Anyone diffing app output against test expectations will meet
  this; the README's walkthrough compares against real `run3`/`run4` data instead, so it does
  not bite a new user.
- **`docs/research/porosity-for-t0-geometry.md`** is still an untracked skeleton from a killed
  `/research` run for #33. Re-save early and after each section; `/research` has been killed by
  machine sleep twice on this project.
- **`validation/runs-combined.csv` and `paste-run1-run2.tsv`** are the driver's paste sheets —
  deliberately untracked scratch, derived entirely from the tracked `run*.csv` and `method.csv`.
  Do not commit them, and do not cite them from anything a stranger reads. A duplicate copy of
  the run-1 chromatogram was deleted this session for the same reason.
- The dedupe of `session._check_gradient` against `fit.py` remains **parked indefinitely** by
  driver decision. Parked, not forgotten — do not helpfully action it.

## Conventions worth copying

Unchanged: one build ticket per branch (`build/NN-slug`), merged with `git merge --no-ff`;
`/code-review` before every merge, and re-run it after a *structural* fix (a local wording fix,
like §6's here, does not need a second round); the issue closed with a completion comment
walking the acceptance criteria; SPEC and research-doc amendments need the driver's approval of
the *exact diff*, applied behind a verbatim-match `assert` on the anchor (`cc4a6f0` and
`76194ba` are this session's worked examples); post-v0.1 findings get their own ticket;
stage explicit paths, never the working tree; commit messages explain *why* and name the
evidence, with the `Co-Authored-By` / `Claude-Session` trailers.

v0.2 gets a fresh wayfinder map, per the driver's decision on #22.
