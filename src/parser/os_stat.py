"""
Parser for Operating System Statistics.
"""

import logging
from typing import Optional

from bs4 import BeautifulSoup

from src.models.base import OSStatRaw

logger = logging.getLogger(__name__)


def extract_os_stat(soup: BeautifulSoup) -> Optional[OSStatRaw]:
    """Extracts CPU and OS metrics from the AWR."""
    try:
        table = None
        for t in soup.find_all("table"):
            ths = [th.get_text(strip=True).lower() for th in t.find_all("th")]
            if "statistic" in ths and ("value" in ths or "total" in ths):
                table = t
                break

        if not table:
            logger.debug("Could not find table for Operating System Statistics.")
            return None

        data = {}
        for tr in table.find_all("tr"):
            tds = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(tds) >= 2:
                stat_name = tds[0].upper()
                try:
                    stat_value = float(tds[1].replace(",", ""))
                    data[stat_name] = stat_value
                except ValueError:
                    pass

        return OSStatRaw(
            num_cpus=int(data.get("NUM_CPUS", 0)) if "NUM_CPUS" in data else None,
            busy_time_cs=data.get("BUSY_TIME"),
            idle_time_cs=data.get("IDLE_TIME"),
            user_time_cs=data.get("USER_TIME"),
            sys_time_cs=data.get("SYS_TIME"),
            iowait_time_cs=(
                data["IOWAIT_TIME"]
                if "IOWAIT_TIME" in data
                else data.get("OS_CPU_WAIT_TIME")
            ),
        )

    except Exception as e:
        logger.error(f"Error parsing OS Statistics: {e}")
        return None
