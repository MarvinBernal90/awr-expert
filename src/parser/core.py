"""
Core parsing logic for AWR Reports.
"""

import logging
from pathlib import Path

from bs4 import BeautifulSoup

from src.models.base import AWRReport, Metadata
from src.parser.db_info import extract_db_info
from src.parser.exceptions import AWRFileNotFoundError, ParserError
from src.parser.load_profile import extract_load_profile
from src.parser.top_events import extract_top_events

# Initialize the logger for this specific module
logger = logging.getLogger(__name__)


class AWRParser:
    """
    Main parser class responsible for extracting data from AWR HTML files.
    """

    def parse(self, file_path: str | Path) -> AWRReport:
        """
        Reads the AWR file and extracts all available metrics
        into a validated Pydantic model.
        """
        path_obj = Path(file_path)
        logger.info(f"Starting AWR parsing for file: {path_obj}")

        if not path_obj.exists():
            logger.error(f"File not found: {path_obj}")
            raise AWRFileNotFoundError(f"AWR file not found at: {path_obj}")

        try:
            with open(path_obj, "r", encoding="utf-8") as f:
                content = f.read()
            logger.debug("Successfully read file content.")

            # --- HTML EXTRACTION LOGIC ---
            soup = BeautifulSoup(content, "lxml")

            db_info_data = extract_db_info(soup)
            raw_lp, norm_lp = extract_load_profile(soup)
            top_events_data = extract_top_events(soup)
            # -----------------------------

        except Exception as e:
            logger.error(f"Unexpected error reading file {path_obj}: {e}")
            raise ParserError(f"Failed to process AWR file: {e}") from e

        logger.info("Parsing completed successfully.")

        # Return the root model injected with the real extracted data
        return AWRReport(
            metadata=Metadata(),
            db_info=db_info_data,
            load_profile_raw=raw_lp,
            load_profile_normalized=norm_lp,
            top_events=top_events_data,
        )
