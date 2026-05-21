"""
DuckDB Storage initialization service.
"""

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

DB_FILE = "awr_warehouse.duckdb"


def initialize_warehouse() -> None:
    """Initializes the DuckDB database and creates tables if they do not exist."""
    db_path = Path(DB_FILE)
    logger.info(f"Initializing DuckDB warehouse at: {db_path.absolute()}")

    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS awr_reports (
                awr_hash VARCHAR PRIMARY KEY,
                db_id BIGINT,
                db_name VARCHAR,
                version VARCHAR,
                host VARCHAR,
                is_rac BOOLEAN,
                cpus INTEGER,
                elapsed_time_min DOUBLE,
                db_time_min DOUBLE,
                raw_payload JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        logger.info("Database warehouse schema validated successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize DuckDB warehouse: {e}")
        raise e
    finally:
        conn.close()
