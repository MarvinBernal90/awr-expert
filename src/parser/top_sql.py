"""
Extraction logic for the 'Top SQL' sections of the AWR Report.
Edge-case resilient to survive malformed HTML from giant execution plans.
"""

import logging
from typing import List

from bs4 import BeautifulSoup, Tag

from src.models.base import TopSQL
from src.parser.html_utils import find_table_by_header

logger = logging.getLogger(__name__)

POSSIBLE_HEADERS = [
    "SQL ordered by Elapsed Time",
    "SQL ordered by CPU Time",
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


def extract_top_sql(soup: BeautifulSoup) -> List[TopSQL]:
    """
    Locates the Top SQL table and extracts rows.
    Contains local exception handling to survive malformed HTML rows.
    """
    logger.debug("Starting extraction of Top SQL.")
    table: Tag | None = None

    for header in POSSIBLE_HEADERS:
        table = find_table_by_header(soup, header)
        if table:
            logger.debug(f"Found Top SQL table using header: '{header}'")
            break

    if not table:
        logger.warning("Top SQL table not found.")
        return []

    sql_list: List[TopSQL] = []
    rows = table.find_all("tr")

    for row in rows[1:]:
        # 🛡️ BLINDAJE CONTRA EDGE CASES: Try/Except local por cada fila
        try:
            cells = row.find_all(["td", "th"])
            if len(cells) < 4:
                continue

            # Standard Oracle columns: Elapsed Time, Executions, ..., SQL ID, SQL Text
            elapsed_time_s = _clean_number(cells[0].text)

            executions_str = cells[1].text.strip().replace(",", "")
            executions = int(executions_str) if executions_str.isdigit() else None

            # Identify SQL ID (usually a 13-character alphanumeric string)
            sql_id = None
            for cell in cells:
                text = cell.text.strip()
                if len(text) == 13 and text.isalnum():
                    sql_id = text
                    break

            # Parche de CodeRabbit: Validar estrictamente o saltar
            if not sql_id:
                candidate = cells[5].text.strip() if len(cells) > 5 else ""
                if len(candidate) == 13 and candidate.isalnum():
                    sql_id = candidate
                else:
                    logger.warning("Skipping Top SQL row without a valid SQL ID.")
                    continue

            # SQL Text is usually the last column
            sql_text = cells[-1].text.strip()

            sql_obj = TopSQL(
                sql_id=sql_id,
                elapsed_time_s=elapsed_time_s,
                executions=executions,
                sql_text=sql_text,
            )
            sql_list.append(sql_obj)

        except Exception as e:
            # Capturamos el error, lo logueamos y salvamos el resto del AWR
            logger.warning(f"Malformed SQL row skipped to prevent crash. Error: {e}")
            continue

    return sql_list
