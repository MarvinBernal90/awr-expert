"""
Core AWR Parser module.
Orchestrates the extraction of different sections of the AWR HTML report.
"""

import logging
from pathlib import Path

from bs4 import BeautifulSoup

from src.models.base import AWRReport, Metadata
from src.parser.db_info import extract_db_info
from src.parser.load_profile import extract_load_profile
from src.parser.os_stat import extract_os_stat
from src.parser.time_model import extract_time_model
from src.parser.top_events import extract_top_events
from src.parser.top_sql import extract_top_sql

logger = logging.getLogger(__name__)


class AWRParser:
    """Main parser class for Oracle AWR HTML reports."""

    def parse(self, file_path: Path) -> AWRReport:
        """
        Parses the HTML AWR report and returns a structured AWRReport model.
        """
        logger.debug(f"Starting parsing for {file_path.name}")

        # Read and parse HTML
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f, "lxml")

        # Extract Core Sections (Month 1)
        db_info = extract_db_info(soup)

        # Desempacar la tupla del Load Profile de forma segura
        lp_raw = None
        lp_norm = None
        extracted_lp = extract_load_profile(soup)
        if extracted_lp and isinstance(extracted_lp, tuple) and len(extracted_lp) == 2:
            lp_raw, lp_norm = extracted_lp

        top_events = extract_top_events(soup)
        top_sql = extract_top_sql(soup)

        # Extract CPU & System Sections (Month 2)
        os_stat = extract_os_stat(soup)
        time_model = extract_time_model(soup)

        # Assemble and return the complete report
        return AWRReport(
            metadata=Metadata(parser_warnings=[]),
            db_info=db_info,
            load_profile_raw=lp_raw,
            load_profile_normalized=lp_norm,
            os_stat=os_stat,
            time_model=time_model,
            top_events=top_events if top_events else [],
            top_sql=top_sql if top_sql else [],
        )
