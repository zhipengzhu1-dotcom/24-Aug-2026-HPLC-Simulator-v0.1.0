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


STYLE = """
<style>
  .block-container { padding-top: 2.2rem; padding-bottom: 1rem; max-width: 100%; }
  section[data-testid="stSidebar"] { border-right: 1px solid #c3ceda; }
  section[data-testid="stSidebar"] .stNumberInput label,
  section[data-testid="stSidebar"] .stRadio label { font-size: 0.78rem; }

  .hs-panel {
    border: 1px solid #b9c6d6; border-radius: 3px; background: #f2f6fb;
    margin-bottom: 8px; overflow: hidden; max-width: 100%; box-sizing: border-box;
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
    padding: 3px 8px; font-size: 0.78rem; border-bottom: 1px solid #e4ebf3;
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
    padding: 4px 14px; font-size: 0.76rem; color: #24445f;
  }
  .hs-status-cell { margin-right: 22px; font-variant-numeric: tabular-nums; }

  /* SPEC §7's sticky chromatogram. Same technique as the status bar and the same
     reason for it: sticky inside the main column, never fixed to the viewport, so it
     cannot reach under the sidebar and it degrades to sitting in the flow if sticky is
     defeated. `bottom` clears the status bar, which is sticky at 0 and shorter than
     this; the opaque background is load-bearing, because a transparent sticky element
     shows the tab content scrolling through it. Addressed by the container key set in
     streamlit_app.py — Streamlit turns `key="hs-chromatogram"` into this class. */
  .st-key-hs-chromatogram {
    position: sticky; bottom: 34px; z-index: 80;
    background: #ffffff; border-top: 1px solid #c3ceda; padding-top: 4px;
  }

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
  h3 { font-size: 1.0rem !important; margin-bottom: .3rem !important; }
</style>
"""
