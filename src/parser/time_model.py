"""
Parser for Time Model Statistics.
"""

import logging
from typing import Optional

from bs4 import BeautifulSoup

from src.models.base import TimeModelRaw

logger = logging.getLogger(__name__)


def extract_time_model(soup: BeautifulSoup) -> Optional[TimeModelRaw]:
    """Extracts database time breakdown metrics from the AWR."""
    try:
        table = None
        for t in soup.find_all("table"):
            ths = [th.get_text(strip=True).lower() for th in t.find_all("th")]
            # Look for headers identifying the Time Model table
            if "statistic name" in ths and any("time (s)" in h for h in ths):
                table = t
                break

        if not table:
            logger.debug("Could not find table for Time Model Statistics.")
            return None

        data = {}
        for tr in table.find_all("tr"):
            tds = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(tds) >= 2:
                stat_name = tds[0].lower().strip()
                try:
                    stat_value = float(tds[1].replace(",", ""))
                    data[stat_name] = stat_value
                except ValueError:
                    pass

        return TimeModelRaw(
            db_time_s=data.get("db time"),
            db_cpu_s=data.get("db cpu"),
            sql_execute_s=data.get("sql execute elapsed time"),
            parse_time_s=data.get("parse time elapsed"),
            hard_parse_s=data.get("hard parse elapsed time"),
        )

    except Exception as e:
        logger.error(f"Error parsing Time Model Statistics: {e}")
        return None
