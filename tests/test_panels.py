"""The Cockpit's label/value panels (SPEC §7, ticket #19).

These render HTML by hand, because Streamlit has no widget for the dense blocks
instrument software uses. That buys two obligations, and this file is both of them:
a peak name is typed by the user and must not be able to reach the page as markup,
and every value handed to a panel must actually appear on it.
"""

from __future__ import annotations

import pytest

from app.panels import STYLE, Row, panel, resolution_colour, status_bar, worksheet


def test_every_row_reaches_the_panel() -> None:
    """The bug this file exists for: a value that is computed but never seen."""
    html = panel("Selected peak", [Row("Name", "P1"), Row("tR", "6.924 min")])

    assert "Selected peak" in html
    for text in ("Name", "P1", "tR", "6.924 min"):
        assert f">{text}<" in html, text


def test_a_peak_name_cannot_carry_markup_onto_the_page() -> None:
    """Peak names are typed by the user. They are data on this page, never markup."""
    html = panel("Selected peak", [Row("Name", '<img src=x onerror="alert(1)">')])

    # The word "onerror" may appear — as text. What must not appear is a tag that
    # opens, or a quote that could close the attribute the value sits in.
    assert "<img" not in html
    assert 'onerror="' not in html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html


def test_an_ampersand_in_a_compound_name_survives_as_an_ampersand() -> None:
    """Escaping must not corrupt an ordinary name — "Cmpd A & B" is a legal label."""
    html = panel("Selected peak", [Row("Name", "Cmpd A & B")])

    assert "Cmpd A &amp; B" in html
    assert "A & B" not in html


def test_a_panel_title_is_escaped_too() -> None:
    assert "&lt;b&gt;" in panel("<b>", [Row("a", "b")])


def test_an_empty_panel_says_so_rather_than_rendering_a_bare_frame() -> None:
    html = panel("Method summary", [])

    assert "hs-empty" in html
    assert "—" in html


def test_the_status_bar_escapes_and_keeps_every_field() -> None:
    html = status_bar(["tG 25 min", "Rs 32.29", "<x>"])

    assert "tG 25 min" in html
    assert "Rs 32.29" in html
    assert "&lt;x&gt;" in html


@pytest.mark.parametrize(
    ("rs", "expected"),
    [
        # 1.5 is baseline separation and 2.0 the usual robustness target — the
        # conventional reading, not SPEC §6's thresholded diagnostics (ticket #20).
        (2.5, "good"),
        (2.0, "good"),
        (1.99, "fair"),
        (1.5, "fair"),
        (1.49, "poor"),
        (0.0, "poor"),
    ],
)
def test_the_resolution_traffic_light_turns_at_baseline_and_at_the_robustness_target(
    rs: float, expected: str
) -> None:
    colours = {
        resolution_colour(2.5): "good",
        resolution_colour(1.7): "fair",
        resolution_colour(1.0): "poor",
    }

    assert colours[resolution_colour(rs)] == expected


def test_the_three_traffic_light_colours_are_distinct() -> None:
    """A threshold nobody can see is not a threshold."""
    assert len({resolution_colour(2.5), resolution_colour(1.7), resolution_colour(1.0)}) == 3


def test_a_value_column_that_cannot_wrap_would_clip_its_own_numbers() -> None:
    """Pins the fix for a real defect: values were cut off mid-number in the rail.

    The panel hides its overflow to keep its rounded border, so the table must be
    sized to the column rather than to its content. Without `table-layout: fixed`
    the columns grow to fit the longest label, the table computes wider than the
    rail, and the right-aligned values are clipped — a short one, like a peak named
    "P1", vanishing completely.
    """
    from app.panels import STYLE

    assert "table-layout: fixed" in STYLE
    assert "white-space: nowrap" not in STYLE
    assert "overflow-wrap: anywhere" in STYLE


def _rule(selector: str) -> str:
    """One CSS rule's body, by selector — so a test names the rule it is about."""
    from app.panels import STYLE

    marker = f"{selector} {{"
    assert STYLE.count(marker) == 1, f"{selector} is not defined exactly once"
    return STYLE.split(marker, 1)[1].split("}", 1)[0]


def test_the_status_bar_is_not_pinned_to_the_viewport() -> None:
    """Pins the fix for a real defect: the sidebar hid the bar's leading fields.

    The bar was `position: fixed; left: 0`, so it spanned the whole viewport and ran
    underneath Streamlit's sidebar, which is fixed too and sits at a far higher
    z-index. On screen the first fields — tG, %B, Rs — were simply not there, and the
    text began mid-word. Sticky positioning lays the bar out in the main column's
    flow, where it cannot reach the sidebar at all.

    Since #79 the bar sits inside a keyed container, which is the stable handle the
    `display: contents` rule scopes by; the sticky element is still the painted bar.
    """
    status_rule = _rule(".hs-status")
    assert "position: sticky" in status_rule
    assert "position: fixed" not in status_rule
    assert "left: 0" not in status_rule


# --- the guided empty state and the sticky chromatogram (SPEC §7, ticket #21) ---------


def test_every_step_reaches_the_worksheet() -> None:
    from app.worksheet import Step

    steps = (
        Step(number=1, title="Method", detail="the sidebar", done=True),
        Step(number=2, title="Peaks", detail="the table", done=False),
    )
    html = worksheet("Start here", "Four steps.", steps)

    for fragment in ("1. Method", "the sidebar", "2. Peaks", "the table", "Start here"):
        assert fragment in html
    assert html.count("<li") == 2


def test_a_done_step_and_an_undone_one_are_told_apart_on_the_page() -> None:
    from app.worksheet import Step

    done = worksheet("t", "l", [Step(1, "A", "d", done=True)])
    undone = worksheet("t", "l", [Step(1, "A", "d", done=False)])
    assert done != undone


def test_a_worksheet_title_is_escaped() -> None:
    """Nothing user-typed reaches this page today, but the escaping rule is the file's."""
    html = worksheet("<script>x</script>", "lead", [])
    assert "<script>" not in html


def test_the_chromatogram_is_pinned_without_being_fixed_to_the_viewport() -> None:
    """SPEC §7's sticky chromatogram, on the status bar's hard-won terms.

    A viewport-fixed element starts at left:0 and runs under Streamlit's sidebar,
    which is fixed at a higher z-index and paints over it — the defect ticket #19
    shipped with the status bar. Sticky lays this out inside the main column instead,
    where it cannot reach the sidebar and degrades to sitting in the flow.
    """
    rule = _rule(".st-key-hs-chromatogram")
    assert "position: sticky" in rule
    assert "position: fixed" not in rule


def test_the_three_pinned_rows_stack_without_overlapping() -> None:
    """All three are sticky to the bottom. The lowest owns 0; each one clears the rest.

    Every offset is computed from the tokens that give the rows below it their height,
    not measured by eye — a number guessed once goes stale the moment a padding or a
    font size changes, and the rows would then overlap with nothing to catch it.
    """
    assert "bottom: 0" in _rule(".hs-status")
    assert "bottom: var(--hs-status-height)" in _rule(".st-key-hs-axis")
    # The chromatogram clears both rows below it *and* the block gap between it and the
    # strip: they are two flex items, so its pinned foot sits one gap above the strip's
    # head. Leaving the gap out pinned it one gap lower than it can reach (#79).
    assert (
        "bottom: calc(var(--hs-status-height) + var(--hs-axis-height) + var(--hs-block-gap))"
        in _rule(".st-key-hs-chromatogram")
    )

    # The derivation and the bar itself must read the same tokens, or it is not derived.
    root, bar = _rule(":root"), _rule(".hs-status")
    for token in ("--hs-status-pad", "--hs-status-font", "--hs-status-line"):
        assert token in root, f"{token} is not defined"
        assert f"var({token})" in bar, f"the status bar does not use {token}"
    assert "--hs-status-height: calc(" in root


def test_the_axis_strip_is_pinned_at_the_height_python_says_it_is() -> None:
    """The chromatogram pins on top of the strip, so the two must agree on its height.

    The number is a Python constant substituted into the stylesheet, rather than typed
    into the CSS beside a comment asking the next reader to keep it in step.
    """
    from app.panels import AXIS_STRIP_HEIGHT_PX

    rule = _rule(".st-key-hs-axis")
    assert "position: sticky" in rule
    assert "position: fixed" not in rule
    assert "height: var(--hs-axis-height)" in rule
    assert f"--hs-axis-height: {AXIS_STRIP_HEIGHT_PX}px" in _rule(":root")
    # The page is a column flex container: without this the declared height is only a
    # preference, and the strip shrinks and clips its own boxes on a full screen.
    assert "flex: 0 0 auto" in rule


def test_the_axis_strip_says_what_the_boxes_are_typed_against() -> None:
    """The two numbers a reader needs while typing a range, in the strip's own cell."""
    from app.panels import axis_strip_title

    html = axis_strip_title(25.126, 0.10804)
    assert "Axis range" in html
    # Both numbers the boxes are typed against: the x ones against the run's end, the y
    # ones against the tallest peak. Losing either leaves half the strip unreferenced.
    assert "25.13 min" in html
    assert "0.108" in html


def test_the_block_gap_is_the_compact_one() -> None:
    """#62's compact spacing: the rail, the chromatogram and the strip on one screen."""
    from app.panels import BLOCK_GAP_REM, RAIL_COLUMNS, STYLE, TABLE_ROW_HEIGHT_PX

    assert pytest.approx(0.4) == BLOCK_GAP_REM
    assert f"--hs-block-gap: {BLOCK_GAP_REM}rem" in _rule(":root")
    assert "gap: var(--hs-block-gap)" in STYLE
    # A rail that clips its own table is the defect this ratio was widened for.
    assert RAIL_COLUMNS == (1.45, 3.0)
    assert TABLE_ROW_HEIGHT_PX == 28


def test_the_pinned_chromatogram_is_opaque() -> None:
    """A sticky element that is even slightly transparent shows the tabs scroll through."""
    surface = _rule(":root")
    assert "--hs-surface: #ffffff" in surface
    assert "background: var(--hs-surface)" in _rule(".st-key-hs-chromatogram")


def test_the_pinned_chromatogram_cannot_grow_to_cover_the_tabs_it_sits_beneath() -> None:
    """Pinned screen is screen the reader cannot scroll away, so its height is capped.

    Ticket #19 drew the plot at 380 px in normal flow. Pinned, that plus its caption
    takes over half a laptop viewport — it would cover the tabs SPEC §7 puts it beneath.
    """
    from app.chromatogram import CHROMATOGRAM_HEIGHT

    assert CHROMATOGRAM_HEIGHT < 380
    rule = _rule(".st-key-hs-chromatogram")
    assert "max-height: 46vh" in rule
    # Capping without a scroll would clip the plot instead of yielding.
    assert "overflow: auto" in rule


def test_the_pinned_rows_wrappers_are_taken_out_of_the_box_tree() -> None:
    """#79's fix, as a rule that must not be deleted by tidying.

    Streamlit wraps each app container in a generated box that hugs its child exactly,
    and a sticky box is clamped to its containing block — so with the wrapper in the box
    tree there is no area below the row to be held across, and nothing ever pinned.
    `display: contents` removes the wrapper's box. Only a browser can prove the rows then
    hold their place (`scripts/check_sticky_rows.py`); this only proves the rule is still
    here, and that all three rows are covered by it.
    """
    assert "{ display: contents; }" in STYLE
    for row in ("hs-chromatogram", "hs-axis", "hs-status"):
        assert f"div:has(> .st-key-{row})" in STYLE, row
    # The bar is markup inside a markdown block, so its own chain is collapsed as well —
    # by shape, because one of those wrappers is an unnamed emotion-cache div and a
    # single box left in that chain hugs the bar and stops it pinning at all.
    assert ".st-key-hs-status div:has(.hs-status)" in STYLE


def test_nothing_sits_between_the_status_bars_block_and_the_foot_of_the_page() -> None:
    """The bar's offset is measured from the foot, so the foot must be reachable.

    The page's own bottom padding and the block gap above the row both sat inside that
    distance, and a sticky box may not be positioned outside its containing block, so
    the bar stopped short by exactly their sum.
    """
    # `.block-container` is `stMainBlockContainer`; one element, one declaration.
    assert "padding-bottom: 0" in _rule(".block-container")
    outer = _rule('div[data-testid="stMainBlockContainer"] > div[data-testid="stVerticalBlock"]')
    assert "gap: 0" in outer


def test_the_chromatogram_absorbs_the_columns_slack_above_itself() -> None:
    """The two Cockpit columns are stretched to equal height, so when the rail is the
    taller one its extra height lands as free space at the foot of the other column. A
    sticky row is never pushed *below* its natural position, so both pinned rows floated
    that far above the status bar at full scroll until the slack was collected above
    them (#79)."""
    assert "margin-top: auto" in _rule(".st-key-hs-chromatogram")
