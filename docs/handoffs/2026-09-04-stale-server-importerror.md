# Handoff — 2026-09-04: the ImportError was a stale server, not a broken tree

For the next session. The driver hit an `ImportError` on the running app; the tree was
never broken. Written at the end of the session that diagnosed and cleared it. This is a
short handoff: one incident, one operational fix, one doc change.

## The symptom

```
ImportError: cannot import name 'critical_pair_is_indicative' from 'app.diagnostics'
  File ".../streamlit_app.py", line 47, in <module>
    from app.diagnostics import (
```

## What it actually was

The server process was **eight hours older than the code it was serving**.

| When | What |
|---|---|
| 03:47:03 | `streamlit run` started (pid 83749/83751). At that commit `critical_pair_is_indicative` **did not exist** — `git show f28df5f:app/diagnostics.py` has 0 occurrences. `app.diagnostics` entered `sys.modules` in that shape and stayed. |
| 11:01:08 | `aaca039` ("Fix #74 after /code-review") added the function to `app/diagnostics.py` **and** the import line to `streamlit_app.py`, in the same commit. |
| 11:46:26 | `git pull --ff-only` brought it to `main` in the working folder. |
| after that | Every rerun: Streamlit re-executes `streamlit_app.py` **from disk** (new import line) against the **cached** `app.diagnostics` module object (old, no such name). ImportError. |

The tell is that the traceback names the current file while the name is plainly defined
in it — at `app/diagnostics.py:564`. Disk and process had diverged.

Why the module never reloaded: **Watchdog is not installed** in this venv, so Streamlit
falls back to its polling watcher, which does not reliably invalidate changed local
modules. The server log says so itself on every boot ("For better performance, install
the Watchdog module").

The last handoff had already flagged the process — *"A Streamlit server from main may
still be running on http://localhost:8501 (pid 83751 at the time of writing); kill it or
reuse it."* It was reused, and it went stale under five merges.

## The fix

Restarted the server. No source change was needed or made.

```
kill 83749 83751
uv run --extra app streamlit run streamlit_app.py --server.headless true --server.port 8501
```

Verified after the restart:

- HTTP 200 on `/` and `/healthz`; server log has **zero** `ImportError`/`Traceback`.
- The script runs to `main()` (`streamlit_app.py:1403`) — no exception.
- Real browser render (cached chromium 1223, via `scripts/check_sticky_rows.py`'s
  `browser_binary()`): `stException` elements **0**, no "ImportError"/"Traceback" in the
  DOM, sidebar and the fresh-session dwell notice paint correctly.
- Fresh-process import of all 14 modules `streamlit_app.py` imports: **no failures**.

## Main was green the whole time

At `3f6556c`, unchanged by this session:

- **847 passed** (`uv run pytest`)
- `ruff check` — all checks passed; `ruff format --check` — 85 files already formatted
- `mypy` — no issues in 17 source files

So nothing on the tracker follows from this. It was purely an artefact of a long-lived
dev process.

## What changed in the repo

One bullet added to `docs/running-the-app.md` §5 ("When something looks wrong"): the
symptom, the cause, and the one-line cure. §5 already warned about *switching branches*
under a running app; it did not cover the case that actually bit — **the branch never
moved, `main` did**, via pull and merge.

## What the next session should know

1. **Restart the app after every pull or merge.** `pkill -f "streamlit run"` then start
   again. Reusing a day-old server is how this happened; it will keep happening while
   several worktrees merge into `main` through the day.
2. **Installing Watchdog would largely prevent it** (`uv add --optional app watchdog`,
   or the xcode-select + pip route the log prints). Not done here — it is a dependency
   change and nobody asked for one. Worth a small ticket if the driver wants it; it is
   not a v0.1 scope item.
3. **Diagnose this class before editing anything.** The sequence that settled it in four
   calls, none of which touched source: `git status` (clean) → `grep -n` the name in the
   module (present, line 564) → `ps -eo pid,lstart` for the server's boot time → `git
   log -1 --format=%ci` on the commit that added the name. Boot time earlier than the
   commit time is the whole diagnosis.
4. The three worktrees (`hplcsim-89`, `hplcsim-90`, `hplcsim-91`) were left alone. Each
   can hold its own stale server on its own port; the same rule applies to them.

## Where things stand otherwise (unchanged by this session)

- Main is `3f6556c`, pushed, level with `origin/main`. No open PRs. **v0.2.0 shipped**
  (PR #86); #74's overlay (PR #85) and #79's sticky rows (PR #87) are merged.
- Open and unclaimed: **#91** (PeakRow becomes the engine's row shape), **#92** (split
  `app/pipeline.py` at the entry stage), **#93** (`app/screen_state.py` owns `Keys`),
  all `ready-for-agent`; **#94** (bug: a flat one-segment candidate reports no eluting
  segment where the walker reports 0); **#95** and **#96** from the grilling pass;
  **#88** the architecture review; **#25**/**#26** backlog.
- `build/91-peakrow` has a commit at `87d931a` in `../hplcsim-91`, not yet a PR.
