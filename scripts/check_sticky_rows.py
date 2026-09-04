"""Do SPEC §7's three pinned rows actually hold their place while the page scrolls? (#79)

`AppTest` has no frontend and no scroll, so `tests/test_screen.py` cannot answer this and
never could — the same blind spot that let #57 ship. This drives a real browser instead,
scrolls the Cockpit's scrollport and measures the three rows' viewport rectangles at
every offset.

**What "pinned" means here, as a number.** The three rows stack off the foot of the
scrollport, in the order SPEC §7 puts them: the status bar sits on the bottom edge, the
axis strip sits on top of the status bar, and the chromatogram block sits on top of the
strip. So each row's *bottom* edge has one expected viewport position, derived from the
heights of the rows below it, and a pinned row holds that position at every scroll offset
where its natural position would otherwise be lower. A row that is not pinned moves up by
exactly the scroll delta, which is the symptom #79 reports.

Run it against a server you started yourself::

    uv run --extra app streamlit run streamlit_app.py --server.headless true --server.port 8767
    uv run --with playwright python scripts/check_sticky_rows.py --port 8767

Exit code 0 means every row held. Exit code 1 prints the table of what moved.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

# The rows of SPEC §7, foot of the screen upward, with the class the app addresses each
# by. `app/panels.py` sets the offsets; this only has to know which boxes to measure.
ROWS = (
    ("status bar", ".hs-status"),
    ("axis strip", ".st-key-hs-axis"),
    ("chromatogram", ".st-key-hs-chromatogram"),
)

# Streamlit's own scrollport. Not the window: the page itself does not scroll.
SCROLLPORT = "section.stMain"

# How far a rect may sit from where it is expected and still count as held. One CSS pixel
# of rounding is ordinary; anything more is the row moving with the page.
TOLERANCE_PX = 2.0

# The browser already on this machine. The pip package's expected build moves faster than
# the cache, so the launch names the cached binary rather than downloading a new one.
CACHED_CHROMIUM = (
    "~/Library/Caches/ms-playwright/chromium_headless_shell-1223"
    "/chrome-headless-shell-mac-arm64/chrome-headless-shell"
)

# The row list crosses into the browser as JSON, not as a Python repr: a repr'd tuple
# is a comma expression in JavaScript, not an array, so `for (const [a, b] of ...)`
# destructured a string and every row read as missing. The script's own first bug.
_MEASURE = """
() => {
  const port = document.querySelector(%s);
  const box = port.getBoundingClientRect();
  const read = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {top: r.top - box.top, bottom: r.bottom - box.top, height: r.height,
            offset: parseFloat(cs.bottom) || 0};
  };
  const out = {port: {height: box.height, scrollTop: port.scrollTop,
                      scrollHeight: port.scrollHeight}};
  for (const [name, sel] of %s) out[name] = read(sel);
  return out;
}
"""


def measure(page: Any, scroll_top: float | None) -> dict[str, Any]:
    """Every row's rectangle, in scrollport coordinates, at one scroll offset."""
    if scroll_top is not None:
        page.evaluate(
            "([sel, top]) => { const p = document.querySelector(sel);"
            " p.scrollTop = top === 'max' ? p.scrollHeight : top; }",
            [SCROLLPORT, scroll_top],
        )
        page.wait_for_timeout(400)
    script = _MEASURE % (json.dumps(SCROLLPORT), json.dumps([list(r) for r in ROWS]))
    return dict(page.evaluate(script))


def expected_bottoms(sample: dict[str, Any]) -> dict[str, float]:
    """Where each row's bottom edge belongs: the foot of the scrollport, less its offset.

    Read from the row's own computed `bottom` rather than summed from the heights of the
    rows beneath it. Those two agreed until the chromatogram's offset gained the block
    gap that separates it from the axis strip, at which point the summed version was
    simply wrong by one gap. Whether the offsets themselves are the right ones is
    `tests/test_panels.py`'s question; this one asks only whether each row *reaches* the
    place it asks for, which is the whole of #79.
    """
    return {
        name: sample["port"]["height"] - sample[name]["offset"]
        for name, _selector in ROWS
        if sample.get(name) is not None
    }


def stacking_faults(label: str, sample: dict[str, Any]) -> list[str]:
    """The rows must sit in SPEC §7's order, not overlap, and all be on screen.

    A row that reaches its own offset is still wrong if the offsets put two of them on
    top of each other, or push one below the fold — so the arithmetic is checked against
    the picture as well as against itself.
    """
    faults = []
    for name, _selector in ROWS:
        row = sample.get(name)
        if row is None:
            continue
        if row["bottom"] > sample["port"]["height"] + TOLERANCE_PX:
            faults.append(f"{label}: {name} hangs below the fold")
        if row["top"] < -TOLERANCE_PX:
            faults.append(f"{label}: {name} is cut off at the top")
    for (lower, _a), (upper, _b) in zip(ROWS, ROWS[1:], strict=False):
        low, up = sample.get(lower), sample.get(upper)
        if low is None or up is None:
            continue
        if up["bottom"] > low["top"] + TOLERANCE_PX:
            faults.append(f"{label}: {upper} overlaps {lower}")
    return faults


def report(samples: list[tuple[str, dict[str, Any]]]) -> list[str]:
    """Every row that failed to hold its place, worded for the issue's own table."""
    failures = []
    for label, sample in samples:
        wanted = expected_bottoms(sample)
        for name, _selector in ROWS:
            row = sample.get(name)
            if row is None:
                failures.append(f"{label}: {name} is not on the page at all")
                continue
            drift = row["bottom"] - wanted[name]
            verdict = "held" if abs(drift) <= TOLERANCE_PX else "MOVED"
            print(
                f"  {label:<14} {name:<14} top {row['top']:7.1f}  bottom {row['bottom']:7.1f}"
                f"  wanted {wanted[name]:7.1f}  drift {drift:+7.1f}  {verdict}"
            )
            if verdict == "MOVED":
                failures.append(f"{label}: {name} sits {drift:+.0f} px from its pinned position")
        failures.extend(stacking_faults(label, sample))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument(
        "--session",
        default="validation/Validation_2/sticky-check.json",
        help="session file to load, so the page has a chromatogram to pin",
    )
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--shot", default=None, help="write a screenshot at full scroll")
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    session = pathlib.Path(args.session).resolve()
    if not session.is_file():
        print(f"no session file at {session}", file=sys.stderr)
        return 2

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=str(pathlib.Path(CACHED_CHROMIUM).expanduser())
        )
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        page.goto(f"http://localhost:{args.port}/", wait_until="networkidle")
        page.wait_for_timeout(2000)
        page.set_input_files(
            'section[data-testid="stFileUploaderDropzone"] input[type=file]', str(session)
        )
        page.wait_for_timeout(6000)

        samples = [("at rest", measure(page, 0))]
        port = samples[0][1]["port"]
        travel = port["scrollHeight"] - port["height"]
        print(
            f"\nviewport {args.width}x{args.height} · scrollport {port['height']:.0f} px"
            f" · content {port['scrollHeight']:.0f} px · travel {travel:.0f} px\n"
        )
        if travel < 40:
            print("the page barely overflows, so there is nothing to scroll past —")
            print("shorten the viewport or load a session with more peaks.\n")
        samples.append(("mid scroll", measure(page, travel / 2.0)))
        samples.append(("at the foot", measure(page, "max")))

        failures = report(samples)
        if args.shot:
            page.screenshot(path=args.shot)
        browser.close()

    print()
    if failures:
        print(f"FAIL — {len(failures)} row/offset pairs did not hold:")
        for line in failures:
            print(f"  · {line}")
        return 1
    print("PASS — every pinned row held its place at every offset.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
