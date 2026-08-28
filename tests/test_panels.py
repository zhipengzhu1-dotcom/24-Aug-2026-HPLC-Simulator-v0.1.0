"""The Cockpit's label/value panels (SPEC §7, ticket #19).

These render HTML by hand, because Streamlit has no widget for the dense blocks
instrument software uses. That buys two obligations, and this file is both of them:
a peak name is typed by the user and must not be able to reach the page as markup,
and every value handed to a panel must actually appear on it.
"""

from __future__ import annotations

import pytest

from app.panels import Row, panel, resolution_colour, status_bar


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
