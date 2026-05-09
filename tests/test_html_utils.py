"""
Unit tests for the HTML utility functions.
"""

from bs4 import BeautifulSoup

from src.parser.html_utils import find_table_by_header


def test_find_table_by_summary() -> None:
    """
    GIVEN an HTML table with a matching summary attribute
    WHEN find_table_by_header is called
    THEN it should return the table tag.
    """
    html = (
        '<html><body><table summary="Load Profile metrics">'
        "<tr><td>Data</td></tr></table></body></html>"
    )
    soup = BeautifulSoup(html, "lxml")
    table = find_table_by_header(soup, "Load Profile")

    assert table is not None
    assert table.name == "table"


def test_find_table_by_preceding_text() -> None:
    """
    GIVEN an HTML table immediately following a heading with the target text
    WHEN find_table_by_header is called
    THEN it should return the subsequent table tag.
    """
    html = (
        "<html><body><h3>Top 5 Timed Events</h3><p>random info</p>"
        "<table><tr><td>Event</td></tr></table></body></html>"
    )
    soup = BeautifulSoup(html, "lxml")
    table = find_table_by_header(soup, "Top 5 Timed Events")

    assert table is not None
    assert table.name == "table"


def test_find_table_not_found() -> None:
    """
    GIVEN an HTML document without the target text or table
    WHEN find_table_by_header is called
    THEN it should return None, avoiding crashes.
    """
    html = "<html><body><table><tr><td>Data</td></tr></table></body></html>"
    soup = BeautifulSoup(html, "lxml")
    table = find_table_by_header(soup, "Missing Header")

    assert table is None
