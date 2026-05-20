"""
DuckDB database manager for the AWR Expert tool.
Handles connection pooling and schema initialization.
"""

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


class DBManager:
    """
    Manages interactions with the DuckDB database.
    """

    def __init__(self, db_path: str = "awr_warehouse.duckdb") -> None:
        self.db_path = str(Path(db_path).resolve())

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Returns a new connection to the DuckDB database."""
        return duckdb.connect(self.db_path)

    def initialize_schema(self) -> None:
        """
        Creates the base tables if they do not exist.
        Leverages DuckDB's native JSON capabilities for complex nested objects.
        """
        logger.info(f"Initializing DuckDB schema at {self.db_path}")

        # Note: awr_hash will be our idempotency key (DBID + Snapshots)
        query = """
        CREATE TABLE IF NOT EXISTS awr_reports (
            awr_hash VARCHAR PRIMARY KEY,
            schema_version VARCHAR,
            db_name VARCHAR,
            db_id BIGINT,
            version VARCHAR,
            is_rac BOOLEAN,
            cpus INTEGER,
            elapsed_time_min DOUBLE,
            db_time_min DOUBLE,
            load_profile_raw JSON,
            load_profile_normalized JSON,
            top_events JSON,
            top_sql JSON,
            metadata_warnings JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            with self.get_connection() as conn:
                conn.execute(query)
            logger.debug("Schema initialization completed successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB schema: {e}")
            raise
