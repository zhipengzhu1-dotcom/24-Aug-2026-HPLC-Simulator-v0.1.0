"""Bench tooling that is not the engine and not the app.

`check_sticky_rows.py` measures the screen in a real browser; `arw.py`, `integrate.py`
and `assign.py` turn Empower PDA exports into measured peak tables. None of it is
imported by `hplcsim` or by `app/` — the dependency runs one way, and this package is
here so `tests/` can import these modules and gate them.
"""
