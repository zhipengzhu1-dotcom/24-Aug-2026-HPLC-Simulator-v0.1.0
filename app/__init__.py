"""The Streamlit Cockpit (SPEC §7) — a thin app over the ``hplcsim`` engine.

The dependency runs one way only (CLAUDE.md): this package imports the engine,
the engine never imports this package. Streamlit itself is confined to
:mod:`app.streamlit_app`; :mod:`app.pipeline`, :mod:`app.chromatogram` and
:mod:`app.tables` are ordinary functions the test suite can call directly, which
is what lets the run-3 acceptance check live in pytest rather than in a habit.
"""
