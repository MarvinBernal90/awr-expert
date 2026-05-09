"""
Extraction logic for the Load Profile section of the AWR Report.
"""

import logging
from typing import Tuple

from bs4 import BeautifulSoup, Tag

from src.models.base import LoadProfileNormalized, LoadProfileRaw
from src.parser.html_utils import find_table_by_header

logger = logging.getLogger(__name__)


def _extract_metric_from_table(table: Tag, metric_name: str) -> float | None:
    """Helper to find a metric row and extract its 'Per Second' value."""
    key = metric_name.strip().lower()
    row = table.find(
        "td",
        string=lambda t: isinstance(t, str) and key in t.strip().lower(),
    )
    if not row:
        return None

    # The 'Per Second' value is usually in the very next cell
    next_td = row.find_next_sibling("td")
    if next_td:
        text_val = next_td.text.strip().replace(",", "")
        try:
            return float(text_val)
        except ValueError:
            return None
    return None


def extract_load_profile(
    soup: BeautifulSoup,
) -> Tuple[LoadProfileRaw | None, LoadProfileNormalized | None]:
    """
    Locates the Load Profile table, extracts raw metrics,
    and maps them to normalized ones.
    """
    logger.debug("Starting extraction of Load Profile.")

    table = find_table_by_header(soup, "Load Profile")
    if not table:
        logger.warning("Load Profile table not found.")
        return None, None

    raw = LoadProfileRaw()
    normalized = LoadProfileNormalized()

    # Extract metrics using our helper (now case-insensitive and robust)
    raw.db_time = _extract_metric_from_table(table, "db time")
    raw.logical_reads = _extract_metric_from_table(table, "logical read")
    raw.physical_reads = _extract_metric_from_table(table, "physical read")

    # Map directly to normalized
    normalized.db_time_per_sec = raw.db_time
    normalized.logical_reads_per_sec = raw.logical_reads
    normalized.physical_reads_per_sec = raw.physical_reads

    # Hard parses is an extra metric
    normalized.hard_parses_per_sec = _extract_metric_from_table(table, "hard parses")

    return raw, normalized
