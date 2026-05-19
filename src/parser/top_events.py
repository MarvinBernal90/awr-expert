"""
Extraction logic for the 'Top Timed Events' section of the AWR Report.
"""

import logging
from typing import List

from bs4 import BeautifulSoup, Tag

from src.models.base import TopEvent
from src.parser.html_utils import find_table_by_header

logger = logging.getLogger(__name__)

# Oracle changes this header between versions
POSSIBLE_HEADERS = [
    "Top 10 Foreground Events by Total Wait Time",
    "Top 5 Timed Foreground Events",
    "Top 5 Timed Events",
]


def _clean_number(text: str) -> float | None:
    """Removes commas and converts to float."""
    clean_text = text.strip().replace(",", "")
    if not clean_text:
        return None
    try:
        return float(clean_text)
    except ValueError:
        return None


def extract_top_events(soup: BeautifulSoup) -> List[TopEvent]:
    """
    Locates the Top Events table and extracts each row into a TopEvent model.
    """
    logger.debug("Starting extraction of Top Events.")
    table: Tag | None = None

    # Try to find the table using known headers
    for header in POSSIBLE_HEADERS:
        table = find_table_by_header(soup, header)
        if table:
            logger.debug(f"Found Top Events table using header: '{header}'")
            break

    if not table:
        logger.warning("Top Events table not found.")
        return []

    events: List[TopEvent] = []
    rows = table.find_all("tr")

    # Skip the first row (header)
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 4:
            continue  # Skip malformed rows or sub-headers

        event_name = cells[0].text.strip()

        # Usually: [Event] [Waits] [Total Wait Time (s)] [Avg Wait (ms)]
        # [% DB time] [Wait Class]
        # We extract what we need based on column positions.
        waits = _clean_number(cells[1].text)
        total_time_s = _clean_number(cells[2].text)

        # The percentage is usually the 5th column (index 4),
        # but we'll try to find the one with '%' or just take the 5th
        pct_db_time = None
        if len(cells) >= 5:
            pct_db_time = _clean_number(cells[4].text)

        if not event_name:
            continue

        try:
            event = TopEvent(
                event_name=event_name,
                waits=int(waits) if waits is not None else None,
                time_s=total_time_s,
                pct_db_time=pct_db_time,
            )
            events.append(event)
        except Exception as e:
            logger.warning(f"Failed to parse event row '{event_name}': {e}")

    return events
