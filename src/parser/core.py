"""
Core Parser module for AWR Expert.
Coordinates the extraction of HTML sections into a unified model.
"""

import logging
from pathlib import Path

from bs4 import BeautifulSoup

from src.models.base import AWRReport, LoadProfile, Metadata
from src.parser.db_info import extract_db_info

# Soporte flexible para el extractor de Load Profile
try:
    from src.parser.extractors.load_profile import extract_load_profile
except ImportError:
    from src.parser.load_profile import extract_load_profile

from src.parser.os_stat import extract_os_stat
from src.parser.time_model import extract_time_model
from src.parser.top_events import extract_top_events
from src.parser.top_sql import extract_top_sql
from src.parser.wait_histogram import extract_wait_histograms

logger = logging.getLogger(__name__)


class AWRParser:
    """Main parser orchestrator for Oracle AWR HTML reports."""

    def parse(self, file_path: Path) -> AWRReport:
        """
        Parses the HTML AWR report and returns a structured AWRReport model.
        """
        logger.debug(f"Starting parsing for {file_path.name}")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f, "lxml")

        db_info = extract_db_info(soup)

        lp_raw = None
        lp_norm = None
        new_lp = None

        extracted_lp = extract_load_profile(soup)
        if extracted_lp:
            if isinstance(extracted_lp, tuple) and len(extracted_lp) == 2:
                lp_raw, lp_norm = extracted_lp
                if lp_raw or lp_norm:
                    new_lp = LoadProfile(
                        db_time=getattr(lp_raw, "db_time", None),
                        logical_reads=getattr(lp_raw, "logical_reads", None),
                        physical_reads=getattr(lp_raw, "physical_reads", None),
                        executes=getattr(lp_raw, "executes", None),
                        transactions=getattr(lp_raw, "transactions", None),
                        logical_reads_ps=getattr(
                            lp_norm,
                            "logical_reads_ps",
                            getattr(lp_norm, "logical_reads_per_sec", None),
                        ),
                        physical_reads_ps=getattr(
                            lp_norm,
                            "physical_reads_ps",
                            getattr(lp_norm, "physical_reads_per_sec", None),
                        ),
                        executes_ps=getattr(
                            lp_norm,
                            "executes_ps",
                            getattr(lp_norm, "executes_per_sec", None),
                        ),
                        transactions_ps=getattr(
                            lp_norm,
                            "transactions_ps",
                            getattr(lp_norm, "transactions_per_sec", None),
                        ),
                    )
            else:
                new_lp = extracted_lp

        top_events = extract_top_events(soup)
        top_sql = extract_top_sql(soup)
        os_stat = extract_os_stat(soup)
        time_model = extract_time_model(soup)
        wait_histograms = extract_wait_histograms(soup)

        return AWRReport(
            metadata=Metadata(parser_warnings=[]),
            db_info=db_info,
            load_profile_raw=lp_raw,
            load_profile_normalized=lp_norm,
            load_profile=new_lp,
            os_stat=os_stat,
            time_model=time_model,
            top_events=top_events if top_events else [],
            top_sql=top_sql if top_sql else [],
            wait_histograms=wait_histograms if wait_histograms else [],
        )
