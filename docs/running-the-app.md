# Running the Cockpit: start, open, stop

The app is a Streamlit script at the repo root. Everything runs through `uv`, from the
project folder:

```
cd "/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0"
```

## 1. Start the app (main branch)

```
git checkout main
uv run --extra app streamlit run streamlit_app.py
```

Streamlit prints a **Local URL**, normally `http://localhost:8501`, and opens it in your
default browser. Leave that terminal window open: the app runs for as long as the command
does.

To pick the port yourself (useful when something else already holds 8501):

```
uv run --extra app streamlit run streamlit_app.py --server.port 8765
```

Then open `http://localhost:8765` yourself.

## 2. Start a prototype branch

Prototypes live on `prototype/*` branches and never merge. The one from ticket #45 is
`prototype/candidate-programme`. Check it out, run the same command, and flip variants
with the URL:

```
git checkout prototype/candidate-programme
uv run --extra app streamlit run streamlit_app.py --server.port 8765
```

| URL | What it shows |
|---|---|
| `http://localhost:8765/?variant=D&data=lab` | the pick (paired tables + chromatogram overlay), lab data |
| `http://localhost:8765/?variant=D&data=lab&b0=15&b1=55&tg=25` | the same, seeded with the 15→55 %B trap case |
| `http://localhost:8765/?variant=D&data=v2` | the pick on the Validation_2 data |
| `?variant=A`, `?variant=B`, `?variant=C` | the three original variants |

The switcher at the foot of the sidebar does the same without editing the URL. The
branch's `prototype/README.md` documents the rest. **Go back to `main` when you are
done** (`git checkout main`), so the folder is in its normal state next time.

Do not switch branches while the app is running: Streamlit reloads the script from disk
on the next interaction and you would be looking at a different branch than you think.
Stop first, switch, start again.

## 3. Open it again later

Nothing runs by itself. Each time you want the app, repeat step 1 (or step 2 for a
prototype) in a terminal. If a browser tab from last time still shows the old page, it
will say "connecting" or show an error until the server is started again; reload it once
the terminal prints the Local URL.

## 4. Stop the app

In the terminal window that is running it: press **Ctrl+C**. That is the normal way.

If you closed that window, or the app was started in the background, find and stop it by
port:

```
lsof -i :8765          # shows what is listening on the port, if anything
kill $(lsof -ti :8765) # stops it
```

Or stop every Streamlit app at once:

```
pkill -f "streamlit run"
```

Check with `lsof -i :8501 -i :8765`; no output means nothing is running.

## 5. When something looks wrong

- **Blank page or "connecting" forever**: the server is not running. Look at the
  terminal; start it again.
- **Port already in use**: something else has it. Use `lsof -i :8501` to see what, stop
  it, or start on another port with `--server.port`.
- **The page shows a different layout than expected**: check `git branch --show-current`.
  Stop the app, check out the branch you meant, start again.
- **Stale caches**: safe to delete any time — `.pytest_cache`, `.ruff_cache`,
  `.mypy_cache`, every `__pycache__`. `uv` recreates what it needs. Never delete `.venv`
  unless you are prepared to wait for `uv` to rebuild it (it will, on the next
  `uv run`).
- **Session file will not save on the prototype branch**: expected. v0.1's save refuses a
  candidate whose %B range differs from the scouting runs'; ticket #44 decided this
  becomes a warning path in v0.2.

## 6. Where things are

| | |
|---|---|
| App entry point | `streamlit_app.py` (root); UI modules in `app/`; engine in `src/hplcsim/` |
| Real instrument data | `validation/` (three peaks) and `validation/Validation_2/` (four peaks) |
| Spec and research | `SPEC.md`; `docs/research/`; glossary in `CONTEXT.md` |
| Tickets and the map | GitHub issues; the v0.2 map is #41 |
| Prototype branches | `prototype/main-screen`, `prototype/resolution-map`, `prototype/candidate-programme` (chosen for #45), `prototype/candidate-phi` (stood down) |
| Screenshots of the #45 prototype | `prototype/screenshots/` on `prototype/candidate-programme` |
| The #45 pick page | https://claude.ai/code/artifact/37245417-410f-4730-9407-419ddb87a56b (private) |
| Local, not in git | `Front-End Design/` (the ACD reference screenshot), `HTML Screenshots/` |

## 7. Tests and checks

```
uv run pytest
uv run ruff check
uv run mypy
```

All three must pass on `main`. On a prototype branch a few screen tests fail on wording
the prototype deliberately changes; that is expected and documented in the branch README.
