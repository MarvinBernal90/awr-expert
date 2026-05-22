"""
Extractor for the 'Load Profile' table.
"""

import logging

from bs4 import BeautifulSoup
from src.parser.utils.html_utils import find_table_by_summary

from src.models.base import LoadProfile

logger = logging.getLogger(__name__)


def extract_load_profile(soup: BeautifulSoup) -> LoadProfile:
    """
    Extracts key 'Per Second' metrics from the Load Profile table.
    """
    profile = LoadProfile()

    # Try finding the table by summary (standard in modern AWRs)
    table = find_table_by_summary(soup, "This table displays load profile")

    # Fallback for older formats where summary might be slightly different or absent
    if not table:
        headers = soup.find_all(["h2", "h3"])
        for h in headers:
            if h.text and "Load Profile" in h.text:
                table = h.find_next("table")
                break

    if not table:
        logger.warning("Load Profile table not found.")
        return profile

    try:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            row_name = cells[0].get_text(strip=True).lower()

            # The 'Per Second' value is usually in the second column (index 1)
            raw_val = cells[1].get_text(strip=True).replace(",", "")

            if not raw_val:
                continue

            try:
                val = float(raw_val)
            except ValueError:
                continue  # Header row or invalid number

            if "logical reads" in row_name:
                profile.logical_reads_ps = val
            elif "physical reads" in row_name:
                profile.physical_reads_ps = val
            elif "executes" in row_name:
                profile.executes_ps = val
            elif "transactions" in row_name:
                profile.transactions_ps = val

    except Exception as e:
        logger.error(f"Error parsing Load Profile: {e}")

    return profile
