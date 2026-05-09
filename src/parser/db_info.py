"""
Extraction logic for the Database context (DB Info) from AWR headers.
"""

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

from src.models.base import DBInfoRaw

logger = logging.getLogger(__name__)


def _extract_float_from_text(text: str) -> Optional[float]:
    """Helper to extract the first float number from a string (e.g. '240.50 (mins)')."""
    match = re.search(r"([\d\.]+)", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def extract_db_info(soup: BeautifulSoup) -> DBInfoRaw:
    """
    Parses the AWR header to extract context metrics.
    Tolerates missing or corrupt data by leveraging Pydantic's Optional fields.
    """
    logger.debug("Starting extraction of DB Info.")
    db_info = DBInfoRaw()

    # 1. Extract Version (Release)
    release_td = soup.find(["td", "th"], string=re.compile(r"Release", re.IGNORECASE))
    if release_td and release_td.find_next_sibling("td"):
        db_info.version = release_td.find_next_sibling("td").text.strip()
    else:
        logger.warning("Version missing in AWR header.")

    # 2. Extract RAC status
    rac_td = soup.find(["td", "th"], string=re.compile(r"RAC", re.IGNORECASE))
    if rac_td and rac_td.find_next_sibling("td"):
        rac_val = rac_td.find_next_sibling("td").text.strip().upper()
        db_info.is_rac = rac_val == "YES"

    # 3. Extract CPUs
    cpu_td = soup.find(["td", "th"], string=re.compile(r"CPUs:", re.IGNORECASE))
    if cpu_td and cpu_td.find_next_sibling("td"):
        try:
            db_info.cpus = int(cpu_td.find_next_sibling("td").text.strip())
        except ValueError:
            logger.warning("Could not parse CPUs value as integer.")

    # 4. Extract Elapsed Time
    elapsed_td = soup.find(["td", "th"], string=re.compile(r"Elapsed:", re.IGNORECASE))
    if elapsed_td and elapsed_td.find_next_sibling("td"):
        db_info.elapsed_time_min = _extract_float_from_text(
            elapsed_td.find_next_sibling("td").text
        )

    # 5. Extract DB Time
    db_time_td = soup.find(["td", "th"], string=re.compile(r"DB Time:", re.IGNORECASE))
    if db_time_td and db_time_td.find_next_sibling("td"):
        db_info.db_time_min = _extract_float_from_text(
            db_time_td.find_next_sibling("td").text
        )

    return db_info
