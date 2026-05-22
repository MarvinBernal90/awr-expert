"""
Parser for Wait Event Histograms.
"""

import logging
import re
from typing import List

from bs4 import BeautifulSoup

from src.models.base import WaitHistogramRaw

logger = logging.getLogger(__name__)


def extract_wait_histograms(soup: BeautifulSoup) -> List[WaitHistogramRaw]:
    """Extracts wait event histogram buckets and normalizes times to milliseconds."""
    histograms = []

    for table in soup.find_all("table"):
        try:
            bucket_cols = {}
            event_col_idx = -1

            for tr in table.find_all("tr"):
                # Extract all cells in this row (both headers and data)
                raw_cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                lower_cells = [c.lower() for c in raw_cells]

                # 1. Search for the exact row that defines the table schema
                if event_col_idx == -1 or not bucket_cols:
                    temp_event = -1
                    temp_buckets = {}

                    for idx, cell in enumerate(lower_cells):
                        # Identify the Event column
                        if cell in ("event", "event name", "wait event"):
                            temp_event = idx

                        # Identify time buckets (e.g., "<1ms", "% < 2ms", "<= 1s")
                        match = re.search(r"([0-9.]+)\s*(ms|s)", cell)
                        if match and any(sym in cell for sym in ("<", ">", "=")):
                            try:
                                val = float(match.group(1))
                            except ValueError:
                                # Skip invalid numbers like "."
                                continue

                            unit = match.group(2)
                            if unit == "s":
                                val *= 1000.0
                            temp_buckets[idx] = val

                    # If this row contains BOTH the event and buckets, lock the schema
                    if temp_event != -1 and temp_buckets:
                        event_col_idx = temp_event
                        bucket_cols = temp_buckets
                    continue

                # 2. Extract Data Rows
                if event_col_idx != -1 and bucket_cols:
                    max_col = max(bucket_cols.keys())

                    # Ensure the row has enough columns to match the schema
                    if len(raw_cells) > max_col and len(raw_cells) > event_col_idx:
                        event_name = raw_cells[event_col_idx]

                        # Skip repeated sub-headers or empty events
                        if not event_name or event_name.lower() in (
                            "event",
                            "event name",
                            "wait event",
                        ):
                            continue

                        # Extract each bucket value
                        for col_idx, wait_milli in bucket_cols.items():
                            val_str = raw_cells[col_idx].replace(",", "").strip()
                            if not val_str or val_str.lower() in ("-", "n/a"):
                                continue

                            try:
                                # Float supports 10g exact counts & 19c percentages
                                count = float(val_str)
                                if count > 0:
                                    histograms.append(
                                        WaitHistogramRaw(
                                            event_name=event_name,
                                            wait_time_milli=wait_milli,
                                            wait_count=count,
                                        )
                                    )
                            except ValueError:
                                pass

        except Exception:
            # Use logger.exception to print the stack trace in debug logs but continue
            logger.exception("Error parsing one Wait Histogram table; continuing.")

    return histograms
