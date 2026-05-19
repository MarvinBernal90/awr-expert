"""
Unit tests for the Top Events extraction logic.
"""

from bs4 import BeautifulSoup

from src.parser.top_events import extract_top_events


def test_extract_top_events_valid_table() -> None:
    """
    GIVEN a valid AWR Top Events HTML snippet
    WHEN extract_top_events is called
    THEN it should correctly parse the rows and return a list of TopEvent models.
    """
    html = (
        "<html><body>"
        "<h3>Top 10 Foreground Events by Total Wait Time</h3>"
        '<table summary="This table displays top 10 wait events">'
        "<tr><th>Event</th><th>Waits</th><th>Total Wait Time (sec)</th>"
        "<th>Avg Wait</th><th>% DB time</th><th>Wait Class</th></tr>"
        "<tr><td>db file sequential read</td><td>1,234,567</td>"
        "<td>8,901.50</td><td>7.21</td><td>45.2</td><td>User I/O</td></tr>"
        "<tr><td>log file sync</td><td>89,012</td><td>1,234.00</td>"
        "<td>13.86</td><td>10.5</td><td>Commit</td></tr>"
        "</table></body></html>"
    )
    soup = BeautifulSoup(html, "lxml")
    events = extract_top_events(soup)

    assert len(events) == 2

    # Check first event (Testing comma removal and float parsing)
    assert events[0].event_name == "db file sequential read"
    assert events[0].waits == 1234567
    assert events[0].time_s == 8901.50
    assert events[0].pct_db_time == 45.2

    # Check second event
    assert events[1].event_name == "log file sync"
    assert events[1].pct_db_time == 10.5


def test_extract_top_events_table_not_found() -> None:
    """
    GIVEN an HTML snippet without the Top Events table
    WHEN extract_top_events is called
    THEN it should return an empty list without crashing.
    """
    html = "<html><body><p>Random data</p></body></html>"
    soup = BeautifulSoup(html, "lxml")
    events = extract_top_events(soup)

    assert isinstance(events, list)
    assert len(events) == 0
