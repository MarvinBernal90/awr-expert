"""
Repository layer for AWR Reports.
Handles storage and retrieval of parsed metrics from DuckDB.
"""

import logging
from typing import Optional

import duckdb

from src.models.base import AWRReport

try:
    from src.services.db import DB_PATH
except ImportError:
    DB_PATH = "awr_warehouse.duckdb"

logger = logging.getLogger(__name__)


class AWRRepository:
    """Handles data persistence for AWR Reports."""

    def __init__(self, db_file: Optional[str] = None):
        """Initializes the repository with a specific database file."""
        self.db_path = db_file or DB_PATH

    def save_report(self, awr_hash: str, report: AWRReport) -> None:
        """Saves a parsed AWR report into the DuckDB warehouse."""
        try:
            with duckdb.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO awr_reports (awr_hash, raw_payload)
                    VALUES (?, ?)
                    ON CONFLICT (awr_hash) DO UPDATE
                    SET raw_payload = excluded.raw_payload;
                    """,
                    [awr_hash, report.model_dump_json()],
                )
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            raise

    def get_report(self, awr_hash: str) -> Optional[AWRReport]:
        """
        Retrieves an AWR report from DuckDB by its hash and
        deserializes it back into the AWRReport Pydantic model.
        """
        try:
            with duckdb.connect(self.db_path) as conn:
                result = conn.execute(
                    "SELECT raw_payload FROM awr_reports WHERE awr_hash = ?",
                    [awr_hash],
                ).fetchone()

                if result:
                    # Pydantic v2 magic: reconstruct the object from JSON string
                    return AWRReport.model_validate_json(result[0])
                return None
        except Exception:
            logger.exception("Failed to retrieve report %s", awr_hash)
            raise
