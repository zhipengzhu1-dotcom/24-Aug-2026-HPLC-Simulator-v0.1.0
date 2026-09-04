"""The dense metric panels of the Cockpit's left rail (SPEC §7).

Streamlit has no widget for the label/value block that instrument software uses to
pack a method's state into a narrow column, so these render small HTML tables. Two
rules hold them together:

* **Every user string is escaped.** Peak names are typed by the user and land inside
  markup here; ``html.escape`` is not optional decoration.
* **Nothing is computed here.** The panels take numbers that :mod:`app.pipeline`
  already produced and format them. A panel that did arithmetic would be a second,
  unchecked path to a number the tables also show.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape
from typing import Protocol

# Rs thresholds are the conventional reading, not a diagnostic: 1.5 is baseline
# separation and 2.0 is the usual robustness target. SPEC §6's thresholded diagnostics
# are ticket #20's, and these traffic lights do not pretend to be them.
_RS_BASELINE = 1.5
_RS_ROBUST = 2.0

_GOOD = "#1f9d55"
_FAIR = "#c77700"
_POOR = "#c0392b"


@dataclass(frozen=True)
class Row:
    """One label/value line, optionally colour-coded like a suitability cell."""

    label: str
    value: str
    colour: str | None = None


class WorksheetStep(Protocol):
    """What :func:`worksheet` needs of a step — structurally, so this file imports none.

    :class:`app.worksheet.Step` is the one implementation. Naming it here instead would
    make the rendering module depend on the module that decides what to render, and
    this file is deliberately a leaf: it draws what it is handed and knows nothing about
    where the handing came from.
    """

    number: int
    title: str
    detail: str

    @property
    def marker(self) -> str: ...


def resolution_colour(rs: float) -> str:
    """Green at the robustness target, amber at baseline, red below it."""
    if rs >= _RS_ROBUST:
        return _GOOD
    return _FAIR if rs >= _RS_BASELINE else _POOR


def panel(title: str, rows: Sequence[Row]) -> str:
    """One titled block of label/value lines, as HTML for ``st.markdown``."""
    if not rows:
        body = f'<tr><td class="hs-empty" colspan="2">{escape("—")}</td></tr>'
    else:
        body = "".join(
            "<tr>"
            f'<td class="hs-label">{escape(row.label)}</td>'
            f'<td class="hs-value"{_style(row.colour)}>{escape(row.value)}</td>'
            "</tr>"
            for row in rows
        )
    return (
        f'<div class="hs-panel"><div class="hs-panel-title">{escape(title)}</div>'
        f'<table class="hs-table">{body}</table></div>'
    )


def _style(colour: str | None) -> str:
    return "" if colour is None else f' style="color:{colour};font-weight:600"'


def worksheet(title: str, lead: str, steps: Sequence[WorksheetStep]) -> str:
    """SPEC §7's numbered 1→4 empty state, as HTML for ``st.markdown``.

    Rendered rather than built from ``st.header``/``st.write`` for the same reason the
    metric panels are: what is wanted is one bounded block a reader takes in at a
    glance, and a run of Streamlit elements is a column of full-width sections. The
    step's own text is markdown — ``**required**`` in a detail line reads as bold —
    so the detail is passed through, while the title and the number are escaped.
    """
    items = "".join(
        '<li class="hs-step">'
        f'<span class="hs-step-mark">{escape(step.marker)}</span>'
        f'<span class="hs-step-body"><b>{escape(f"{step.number}. {step.title}")}</b>'
        f'<span class="hs-step-detail">{step.detail}</span></span>'
        "</li>"
        for step in steps
    )
    return (
        f'<div class="hs-worksheet"><div class="hs-worksheet-title">{escape(title)}</div>'
        f'<div class="hs-worksheet-lead">{escape(lead)}</div>'
        f'<ol class="hs-steps">{items}</ol></div>'
    )


def status_bar(fields: Sequence[str]) -> str:
    """The foot of the screen: the condition on show, in one line."""
    cells = "".join(f'<span class="hs-status-cell">{escape(field)}</span>' for field in fields)
    return f'<div class="hs-status">{cells}</div>'


def axis_strip_title(run_end: float, tallest_peak: float) -> str:
    """The axis strip's first cell: what the strip is, and what the run's own range is.

    The strip is a fixed-height row, so the sentence the collapsed expander used to
    carry does not fit in it as prose. What it said that a reader needs is the two
    numbers the boxes are typed against — where the run ends, for the x boxes, and how
    tall the tallest peak is, for the y ones — so both survive, as a two-line note
    under the strip's title rather than a sentence beside it (#62).
    """
    return (
        '<div class="hs-axis-title">Axis range</div>'
        f'<div class="hs-axis-note">run ends {escape(f"{run_end:.2f}")} min</div>'
        f'<div class="hs-axis-note">top peak {escape(f"{tallest_peak:.4g}")}</div>'
    )


# --- the numbers the screen is laid out on --------------------------------------------
#
# Ticket #62's compact Cockpit. These live here rather than in the entry point for the
# same reason every other decision does: the entry point places widgets, this module is
# what a test can read. `STYLE` below is the only consumer of the two that are CSS.

# The left rail against the main view. 1.45 : 3.0 is wide enough for a four-column table
# in the rail without the %B column being clipped (#45's variant D review).
RAIL_COLUMNS = (1.45, 3.0)

# The axis strip's height. Fixed, because the chromatogram block pins itself directly on
# top of the strip and needs to know how much room to leave: one row of number boxes
# with their labels, and nothing else — the strip's content never grows. Measured in a
# real browser at 1440 x 900 rather than guessed: the row of boxes lays out at 92 px,
# and a strip declared shorter than its content clips the boxes' lower edge.
AXIS_STRIP_HEIGHT_PX = 92

# Every data grid's row height. Streamlit's default (35 px) spends a third of the
# chromatogram's budget on four rows of peaks.
TABLE_ROW_HEIGHT_PX = 28

# Streamlit's own gap between blocks is 1rem, which on this screen reads as white space
# between the rail's panels rather than as separation.
BLOCK_GAP_REM = 0.4


def _with_layout_numbers(css: str) -> str:
    """Substitute the layout constants above into the stylesheet.

    A plain ``str.format`` cannot be used on CSS — every rule is braces — and an f-string
    would mean doubling every one of them. The tokens keep the numbers defined once, in
    Python, where :mod:`tests.test_panels` can read them.
    """
    for token, value in (
        ("__AXIS_STRIP_HEIGHT__", f"{AXIS_STRIP_HEIGHT_PX}px"),
        ("__BLOCK_GAP__", f"{BLOCK_GAP_REM}rem"),
    ):
        css = css.replace(token, value)
    return css


STYLE = _with_layout_numbers("""
<style>
  /* The status bar's height is *derived* from the tokens that make it, not measured by
     eye. The pinned chromatogram has to clear that bar exactly, and a number guessed
     once is a number that goes stale the moment the padding or the font size changes;
     this way both rules move together. */
  :root {
    --hs-status-pad: 4px;
    --hs-status-font: 0.76rem;
    --hs-status-line: 1.5;
    --hs-status-height: calc(
      var(--hs-status-font) * var(--hs-status-line) + var(--hs-status-pad) * 2 + 1px
    );
    /* The app's own page colour, which the pinned chromatogram has to match: a sticky
       element that is even slightly transparent shows the tabs scrolling through it.
       This stylesheet is a light palette throughout (#19), and this is its page white. */
    --hs-surface: #ffffff;
    /* The axis strip's height and the page's block gap, from the Python constants
       above — the chromatogram's pin offset is derived from the first of them the same
       way it is derived from the status bar's. */
    --hs-axis-height: __AXIS_STRIP_HEIGHT__;
    --hs-block-gap: __BLOCK_GAP__;
  }

  /* 2.2rem on main, and it has to *grow* in the one ticket that is otherwise about
     compaction (#62): the compact block gap lifts the whole main column, and at
     2.2rem the tab row rides up under Streamlit's own floating header and is clipped
     along its top edge. Checked in a browser at 1440 x 900 both ways. This is the
     only padding in the stylesheet that #62 increases; it costs 14 px of page. */
  .block-container { padding-top: 3.1rem; padding-bottom: 1rem; max-width: 100%; }

  /* Compact spacing (#62). Streamlit's 1rem block gap, its element margins and its
     heading margins are what the white bands between the rail's panels were; the target
     is the rail, the chromatogram and the axis strip all on screen at 1440 × 900. */
  div[data-testid="stVerticalBlock"] { gap: var(--hs-block-gap); }
  div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] { margin: 0; }
  /* A caption is made smaller, never un-margined: zeroing the margin here collapses
     the element container Streamlit wraps it in to nothing, and what disappears is
     the chromatogram's area caveat and diagnostic 6's stamp. Measured in a browser. */
  div[data-testid="stCaptionContainer"] p { font-size: 0.74rem; line-height: 1.3; }
  div[data-testid="stMarkdownContainer"] p { margin-bottom: 0.2rem; }
  div[data-testid="stNumberInput"] label,
  div[data-testid="stSlider"] label { font-size: 0.76rem; }
  div[data-testid="stSelectbox"] > div,
  div[data-testid="stNumberInput"] > div { min-height: 0; }
  /* The sidebar is scrolled, not pinned, so it keeps a little more air than the page. */
  section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] { gap: 0.6rem; }
  section[data-testid="stSidebar"] { border-right: 1px solid #c3ceda; }
  section[data-testid="stSidebar"] .stNumberInput label,
  section[data-testid="stSidebar"] .stRadio label { font-size: 0.78rem; }

  .hs-panel {
    border: 1px solid #b9c6d6; border-radius: 3px; background: #f2f6fb;
    margin-bottom: 4px; overflow: hidden; max-width: 100%; box-sizing: border-box;
  }
  /* A flex child defaults to min-width:auto, which lets a wide table push the whole
     column past its share of the row instead of wrapping inside it. */
  div[data-testid="stColumn"] { min-width: 0; }
  .hs-panel-title {
    background: #dbe6f2; border-bottom: 1px solid #b9c6d6; padding: 3px 8px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: .04em;
    text-transform: uppercase; color: #24445f;
  }
  /* table-layout: fixed is load-bearing. Without it the columns size to their content,
     the table computes wider than the rail, and the panel's overflow clips the values —
     right-aligned ones first, so a short value disappears entirely. Both cells wrap. */
  .hs-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
  .hs-table td {
    padding: 2px 8px; font-size: 0.78rem; border-bottom: 1px solid #e4ebf3;
    overflow-wrap: anywhere; vertical-align: top;
  }
  .hs-table tr:last-child td { border-bottom: none; }
  .hs-label { color: #4a5768; width: 46%; }
  .hs-value {
    text-align: right; font-variant-numeric: tabular-nums; color: #14202e; width: 55%;
  }
  .hs-empty { color: #8d99a8; font-style: italic; font-size: 0.78rem; }

  /* Sticky inside the main column, never fixed to the viewport. A viewport-fixed bar
     starts at left:0 and runs under Streamlit's sidebar — also fixed, at a far higher
     z-index — which paints over the leading fields and hides them outright. Laid out in
     the main column's flow the bar cannot reach the sidebar; and if sticky positioning
     is ever defeated it degrades to sitting at the end of the content, still the foot. */
  .hs-status {
    position: sticky; bottom: 0; z-index: 90; margin-top: 10px;
    background: #dbe6f2; border-top: 1px solid #b9c6d6;
    padding: var(--hs-status-pad) 14px; font-size: var(--hs-status-font);
    line-height: var(--hs-status-line); color: #24445f;
  }
  .hs-status-cell { margin-right: 22px; font-variant-numeric: tabular-nums; }

  /* SPEC §7's sticky chromatogram. Same technique as the status bar and the same
     reason for it: sticky inside the main column, never fixed to the viewport, so it
     cannot reach under the sidebar, and it degrades to sitting in the flow if sticky is
     ever defeated. It sits directly on top of the status bar, which is sticky at 0 —
     hence the derived offset rather than a measured one. Addressed by the container key
     set in streamlit_app.py; Streamlit turns `key="hs-chromatogram"` into this class.

     `max-height` is the guard that matters. A pinned block is screen the user cannot
     scroll out of the way, so a chromatogram that grew tall enough would cover the very
     tabs it is pinned beneath. The plot is drawn short (see CHROMATOGRAM_HEIGHT) and
     this caps the whole block regardless — on a short laptop viewport it yields rather
     than eating the page. */
  .st-key-hs-chromatogram {
    position: sticky; bottom: calc(var(--hs-status-height) + var(--hs-axis-height));
    z-index: 80;
    background: var(--hs-surface); border-top: 1px solid #c3ceda; padding-top: 4px;
    /* `flex: 0 0 auto` for the reason given on `.st-key-hs-axis` below. What this block
       loses off its foot without it is the area caveat and diagnostic 6's stamp, the two
       lines a trace must not be read without. `max-height` still caps it on a short
       viewport, which is the yielding the cap was put there for. */
    flex: 0 0 auto; max-height: 46vh; overflow: auto;
  }

  /* SPEC §7's axis range as its own always-open strip (#62). A pinned row of its own
     between the chromatogram block and the status bar, by the same sticky-in-column
     technique as both of its neighbours and for the same reason — a viewport-fixed row
     would run under the sidebar. Its own row, rather than the last row inside the
     chromatogram block, because that block scrolls: the boxes were reachable only by
     scrolling the plot they act on, which is the one thing the reader is looking at.
     The height is fixed so that the block above can pin exactly on top of it. */
  .st-key-hs-axis {
    position: sticky; bottom: var(--hs-status-height); z-index: 85;
    height: var(--hs-axis-height); overflow: hidden; box-sizing: border-box;
    /* The page is one column flex container, so a fixed height is only a *preferred*
       height: once the content overflows the viewport every child shrinks, and the
       strip clipped its own boxes at the very screen size it was measured for. */
    flex: 0 0 auto;
    background: var(--hs-surface); border-top: 1px solid #c3ceda; padding: 6px 0 0;
  }
  .st-key-hs-axis .stNumberInput label { font-size: 0.72rem; }
  .st-key-hs-axis .stNumberInput input { font-size: 0.8rem; padding: 0.25rem 0.5rem; }
  .st-key-hs-axis .stButton button {
    padding: 0.25rem 0.5rem; font-size: 0.8rem; min-height: 0;
  }
  .hs-axis-title {
    font-size: 0.72rem; font-weight: 700; letter-spacing: .04em;
    text-transform: uppercase; color: #24445f;
  }
  .hs-axis-note { font-size: 0.72rem; color: #6b7a8c; font-variant-numeric: tabular-nums; }

  .hs-worksheet {
    border: 1px solid #b9c6d6; border-radius: 3px; background: #f8fbff;
    margin-bottom: 14px; padding: 12px 16px 8px;
  }
  .hs-worksheet-title {
    font-size: 0.98rem; font-weight: 700; color: #24445f; margin-bottom: 2px;
  }
  .hs-worksheet-lead { font-size: 0.82rem; color: #4a5768; margin-bottom: 10px; }
  .hs-steps { list-style: none; margin: 0; padding: 0; }
  .hs-step { display: flex; gap: 10px; align-items: baseline; margin-bottom: 9px; }
  .hs-step-mark { flex: 0 0 auto; font-size: 0.9rem; }
  .hs-step-body { display: block; font-size: 0.86rem; color: #14202e; }
  .hs-step-detail { display: block; color: #4a5768; margin-top: 1px; }

  div[data-testid="stTabs"] button { font-size: 0.82rem; padding: 4px 14px; }
  div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] { font-size: 0.80rem; }
  h3 { font-size: 1.0rem !important; margin: 0.35rem 0 0.05rem !important; }
</style>
""")
