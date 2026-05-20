"""
Parser for Database and Snapshot Information.
"""

import logging
from typing import Optional

from bs4 import BeautifulSoup

from src.models.base import DBInfoRaw

logger = logging.getLogger(__name__)


def extract_db_info(soup: BeautifulSoup) -> Optional[DBInfoRaw]:
    """
    Extracts General DB Information and Snapshot times.
    Supports Oracle 10g, 11g, 12c, and 19c formats using pure BeautifulSoup.
    """
    try:
        # Helper interno para encontrar una tabla basándose en sus encabezados
        def find_table(headers: list) -> tuple:
            for table in soup.find_all("table"):
                ths = [th.get_text(strip=True) for th in table.find_all("th")]
                if all(h in ths for h in headers):
                    return table, ths
            return None, []

        # 1. DB Info
        db_name = "UNKNOWN"
        db_id = 0
        version = "UNKNOWN"
        is_rac = False
        cpus = None

        table, ths = find_table(["DB Name", "DB Id"])
        if table:
            tds = [td.get_text(strip=True) for td in table.find_all("td")]
            if tds:
                # Mapeamos los encabezados con los valores
                data = dict(zip(ths, tds))
                db_name = data.get("DB Name", "UNKNOWN")
                try:
                    db_id = int(data.get("DB Id", "0"))
                except ValueError:
                    pass
                version = data.get("Release", "UNKNOWN")
                is_rac = data.get("RAC", "").upper() == "YES"
                if "CPUs" in data:
                    try:
                        cpus = int(data["CPUs"])
                    except ValueError:
                        pass

        if version == "UNKNOWN":
            logger.warning("Version missing in AWR header.")

        # 2. Rescate de CPUs para Oracle 10g (Operating System Statistics)
        if cpus is None:
            os_table, _ = find_table(["Statistic", "Value"])
            if not os_table:
                os_table, _ = find_table(["Statistic", "Total"])

            if os_table:
                for tr in os_table.find_all("tr"):
                    row_tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if len(row_tds) >= 2 and "NUM_CPUS" in row_tds[0].upper():
                        try:
                            cpus = int(row_tds[1])
                        except ValueError:
                            pass
                        break

        # Fallback de seguridad para Pydantic
        if cpus is None or cpus <= 0:
            logger.warning("Could not extract CPUs. Defaulting to 1.")
            cpus = 1

        # 3. Elapsed and DB Time
        elapsed_time_min = 0.0
        db_time_min = 0.0

        snap_table, _ = find_table(["Snap Id", "Snap Time"])
        if snap_table:
            for tr in snap_table.find_all("tr"):
                row_tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                for i, td_text in enumerate(row_tds):
                    lower_text = td_text.lower()

                    # Buscamos la etiqueta "Elapsed:" y tomamos el siguiente valor numérico
                    if "elapsed" in lower_text and ":" in lower_text:
                        for val_td in row_tds[i + 1 :]:
                            if val_td:
                                try:
                                    elapsed_time_min = float(
                                        val_td.split()[0].replace(",", "")
                                    )
                                except ValueError:
                                    pass
                                break

                    # Buscamos la etiqueta "DB Time:" y tomamos el siguiente valor numérico
                    if "db time" in lower_text and ":" in lower_text:
                        for val_td in row_tds[i + 1 :]:
                            if val_td:
                                try:
                                    db_time_min = float(
                                        val_td.split()[0].replace(",", "")
                                    )
                                except ValueError:
                                    pass
                                break

        return DBInfoRaw(
            db_name=db_name,
            db_id=db_id,
            version=version,
            is_rac=is_rac,
            cpus=cpus,
            elapsed_time_min=elapsed_time_min,
            db_time_min=db_time_min,
        )

    except Exception as e:
        logger.error(f"Error parsing DB info: {e}")
        return None
