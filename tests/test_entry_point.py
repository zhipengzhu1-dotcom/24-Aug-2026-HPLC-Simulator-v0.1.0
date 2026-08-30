"""The app starts the way its own docstring says to start it.

Separate from `test_app.py` because it asserts something no in-process test can: that
`streamlit run` resolves the imports. Streamlit puts the **script's own folder** on
`sys.path` and does not put the working directory there. Every other test in this suite
runs from the repo root, which is already importable, so all of them stayed green while
the documented launch command raised `ModuleNotFoundError: No module named 'app'`.
Caught in a browser, not in pytest — hence this file.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY_POINT = ROOT / "streamlit_app.py"

# What Streamlit's own bootstrap does: the script's directory goes first, and nothing
# puts the working directory on the path. Reproducing it exactly is the whole point —
# a laxer path would pass against a layout that cannot actually be launched.
_AS_STREAMLIT_RUNS_IT = f"""
import sys
sys.path = [path for path in sys.path if path not in ("", ".", {str(ROOT)!r})]
sys.path.insert(0, {str(ENTRY_POINT.parent)!r})

from streamlit.testing.v1 import AppTest

app = AppTest.from_file({str(ENTRY_POINT)!r}, default_timeout=120).run()
assert not app.exception, app.exception
# It renders something of its own, not just an empty page: the app opens on the
# dwell gate of SPEC §4, so that is what a cold start must show.
assert app.title[0].value.startswith("hplcsim"), app.title[0].value
assert any("dwell" in warning.value.lower() for warning in app.warning), "no dwell gate"
"""


def test_the_entry_point_starts_the_way_streamlit_starts_it() -> None:
    """`uv run --extra app streamlit run streamlit_app.py`, minus the browser."""
    assert ENTRY_POINT.is_file(), (
        f"{ENTRY_POINT.name} must stay at the repo root: Streamlit adds the script's own "
        "folder to sys.path, so an entry point inside app/ cannot import app.pipeline"
    )

    # A directory that is nobody's package root, so a stray "" on the path cannot rescue it.
    with tempfile.TemporaryDirectory() as elsewhere:
        result = subprocess.run(
            [sys.executable, "-c", _AS_STREAMLIT_RUNS_IT],
            cwd=elsewhere,
            capture_output=True,
            text=True,
        )

    assert result.returncode == 0, result.stderr
