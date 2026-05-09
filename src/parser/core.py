"""
Core parsing logic for AWR Reports.
"""

import logging
from pathlib import Path

from bs4 import BeautifulSoup

from src.models.base import AWRReport, Metadata
from src.parser.db_info import extract_db_info
from src.parser.exceptions import AWRFileNotFoundError, ParserError

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

        Args:
            file_path: Absolute or relative path to the AWR HTML file.

        Returns:
            A validated AWRReport object.

        Raises:
            AWRFileNotFoundError: If the file does not exist.
            ParserError: If an unexpected error occurs during reading.
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

            # --- NUEVA LÓGICA DE EXTRACCIÓN HTML ---
            soup = BeautifulSoup(content, "lxml")
            db_info_data = extract_db_info(soup)
            # ---------------------------------------

        except Exception as e:
            logger.error(f"Unexpected error reading file {path_obj}: {e}")
            raise ParserError(f"Failed to process AWR file: {e}") from e

        logger.info("Parsing completed successfully.")

        # Return the root model injected with the real db_info
        return AWRReport(metadata=Metadata(), db_info=db_info_data)
