"""
Utility functions for HTML parsing using BeautifulSoup.
"""

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


def find_table_by_header(soup: BeautifulSoup, header_text: str) -> Optional[Tag]:
    """
    Locates an HTML table by searching for specific header text nearby.
    It handles varying Oracle AWR HTML structures without relying on CSS classes or IDs.

    Args:
        soup: The parsed BeautifulSoup object.
        header_text: The text to search for (e.g., "Top 5 Timed Events").

    Returns:
        The BeautifulSoup Tag representing the <table>, or None if not found.
    """
    logger.debug(f"Searching for table with header: '{header_text}'")
    pattern = re.compile(re.escape(header_text), re.IGNORECASE)

    # Strategy 1: Oracle AWRs often put the title in a 'summary' attribute of the table
    table_with_summary = soup.find("table", summary=pattern)
    if table_with_summary and isinstance(table_with_summary, Tag):
        return table_with_summary

    # Strategy 2: Text inside a standard header tag preceding the table
    text_node = soup.find(string=pattern)
    if text_node:
        # Check if the text is already inside a table header (<th>)
        parent_table = text_node.find_parent("table")
        if parent_table and isinstance(parent_table, Tag):
            return parent_table

        # Check if the table is a sibling following the text
        # (e.g. <h3>Title</h3> \n <table>)
        current = text_node.parent
        while current and current.name not in ["body", "html"]:
            next_element = current.find_next_sibling("table")
            if next_element and isinstance(next_element, Tag):
                return next_element
            current = current.parent

    logger.warning(f"Could not find table for header: '{header_text}'")
    return None
