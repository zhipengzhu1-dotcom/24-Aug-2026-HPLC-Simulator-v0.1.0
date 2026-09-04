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
from dataclasses import dataclass
from typing import Any, Literal

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

# Below this much scroll travel the check proves nothing: with nothing to scroll past, a
# row that cannot pin looks exactly like one that can. Two of the three rows are about
# 120 px of stacked height, so a page that overflows by less than a third of that has no
# room to show a failure.
MIN_USEFUL_TRAVEL_PX = 40.0

# The browser already on this machine. The pip package's expected build moves faster than
# the cache, so the launch names the cached binary rather than downloading a new one.
CACHED_CHROMIUM = (
    "~/Library/Caches/ms-playwright/chromium_headless_shell-1223"
    "/chrome-headless-shell-mac-arm64/chrome-headless-shell"
)


def browser_binary() -> pathlib.Path:
    """The cached headless build, or a message naming what to install.

    The path is machine-specific by design — the pip package's expected build moves
    faster than the cache, so naming the cached one is what avoids a download on every
    run. When it is not there, say so rather than letting Playwright fail with its own
    "run playwright install" banner, which points at the *newer* build and would leave
    two copies on disk.
    """
    binary = pathlib.Path(CACHED_CHROMIUM).expanduser()
    if not binary.is_file():
        raise SystemExit(
            f"no cached browser at {binary}\n"
            "Install one with `uv run --with playwright playwright install chromium`, "
            "then point CACHED_CHROMIUM at whatever landed under "
            "~/Library/Caches/ms-playwright."
        )
    return binary


@dataclass(frozen=True)
class Rect:
    """One row's box in scrollport coordinates, and the offset it asked to sit at."""

    top: float
    bottom: float
    height: float
    offset: float
    """The row's own computed `bottom`, i.e. how far above the foot it asked to be."""


@dataclass(frozen=True)
class Sample:
    """Every row's box at one scroll offset, with the scrollport it was measured in."""

    label: str
    port_height: float
    scroll_height: float
    rows: dict[str, Rect]

    @property
    def travel(self) -> float:
        return self.scroll_height - self.port_height

    def wanted(self, name: str) -> float:
        """Where this row's foot belongs: the foot of the scrollport, less its offset."""
        return self.port_height - self.rows[name].offset


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


ScrollTo = float | Literal["max"]


def measure(page: Any, label: str, scroll_to: ScrollTo) -> Sample:
    """Every row's rectangle, in scrollport coordinates, at one scroll offset."""
    page.evaluate(
        "([sel, top]) => { const p = document.querySelector(sel);"
        " p.scrollTop = top === 'max' ? p.scrollHeight : top; }",
        [SCROLLPORT, scroll_to],
    )
    page.wait_for_timeout(400)
    script = _MEASURE % (json.dumps(SCROLLPORT), json.dumps([list(r) for r in ROWS]))
    raw = page.evaluate(script)
    return Sample(
        label=label,
        port_height=float(raw["port"]["height"]),
        scroll_height=float(raw["port"]["scrollHeight"]),
        rows={
            name: Rect(**{k: float(v) for k, v in raw[name].items()})
            for name, _selector in ROWS
            if raw.get(name) is not None
        },
    )


def stacking_faults(sample: Sample) -> list[str]:
    """The rows must sit in SPEC §7's order, not overlap, and all be on screen.

    A row that reaches its own offset is still wrong if the offsets put two of them on
    top of each other, or push one below the fold — so the arithmetic is checked against
    the picture as well as against itself.
    """
    faults = []
    for name, rect in sample.rows.items():
        if rect.bottom > sample.port_height + TOLERANCE_PX:
            faults.append(f"{sample.label}: {name} hangs below the fold")
        if rect.top < -TOLERANCE_PX:
            faults.append(f"{sample.label}: {name} is cut off at the top")
    for (lower, _a), (upper, _b) in zip(ROWS, ROWS[1:], strict=False):
        low, up = sample.rows.get(lower), sample.rows.get(upper)
        if low is not None and up is not None and up.bottom > low.top + TOLERANCE_PX:
            faults.append(f"{sample.label}: {upper} overlaps {lower}")
    return faults


def report(samples: list[Sample]) -> list[str]:
    """Every row that failed to hold its place, worded for the issue's own table."""
    failures = []
    for sample in samples:
        for name, _selector in ROWS:
            rect = sample.rows.get(name)
            if rect is None:
                failures.append(f"{sample.label}: {name} is not on the page at all")
                continue
            wanted = sample.wanted(name)
            drift = rect.bottom - wanted
            verdict = "held" if abs(drift) <= TOLERANCE_PX else "MOVED"
            print(
                f"  {sample.label:<14} {name:<14} top {rect.top:7.1f}"
                f"  bottom {rect.bottom:7.1f}  wanted {wanted:7.1f}"
                f"  drift {drift:+7.1f}  {verdict}"
            )
            if verdict == "MOVED":
                failures.append(
                    f"{sample.label}: {name} sits {drift:+.0f} px from its pinned position"
                )
        failures.extend(stacking_faults(sample))
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
        browser = pw.chromium.launch(executable_path=str(browser_binary()))
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        page.goto(f"http://localhost:{args.port}/", wait_until="networkidle")
        page.set_input_files(
            'section[data-testid="stFileUploaderDropzone"] input[type=file]', str(session)
        )
        # Wait on the thing being measured rather than on a clock: the pinned rows only
        # exist once a session has been read and a chromatogram drawn, and a fixed sleep
        # long enough for a slow machine is wasted on every fast one.
        page.wait_for_selector(".st-key-hs-chromatogram", timeout=30_000)
        page.wait_for_selector(".hs-status", timeout=30_000)
        page.wait_for_timeout(1500)

        samples = [measure(page, "at rest", 0.0)]
        first = samples[0]
        print(
            f"\nviewport {args.width}x{args.height} · scrollport {first.port_height:.0f} px"
            f" · content {first.scroll_height:.0f} px · travel {first.travel:.0f} px\n"
        )
        if first.travel < MIN_USEFUL_TRAVEL_PX:
            print("the page barely overflows, so there is nothing to scroll past —")
            print("shorten the viewport or load a session with more peaks.\n")
        samples.append(measure(page, "mid scroll", first.travel / 2.0))
        samples.append(measure(page, "at the foot", "max"))

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
