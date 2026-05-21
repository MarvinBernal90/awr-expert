"""
Repository layer to manage read and write operations on DuckDB.
"""

import json
import logging

import duckdb

from src.models.base import AWRReport
from src.services.db import DB_FILE

logger = logging.getLogger(__name__)


class AWRRepository:
    """Handles persistence layer interactions for AWR reports."""

    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file

    def save_report(self, awr_hash: str, report: AWRReport) -> None:
        """
        Saves or updates an AWRReport into DuckDB using its unique SHA-256 hash.
        Performs an idempotent UPSERT operation.
        """
        conn = duckdb.connect(self.db_file)
        try:
            # Prepare flat columns from db_info block
            db_id = report.db_info.db_id if report.db_info else None
            db_name = report.db_info.db_name if report.db_info else None
            version = report.db_info.version if report.db_info else None
            host = report.db_info.host if report.db_info else None
            is_rac = report.db_info.is_rac if report.db_info else False
            cpus = report.db_info.cpus if report.db_info else None
            elapsed = report.db_info.elapsed_time_min if report.db_info else None
            db_time = report.db_info.db_time_min if report.db_info else None

            # Serialize the entire Pydantic object into a clean JSON payload
            raw_payload_json = json.dumps(report.model_dump())

            # Idempotent UPSERT strategy using DuckDB native syntax
            # Notice we removed created_at from the UPDATE SET clause
            query = """
                INSERT INTO awr_reports (
                    awr_hash, db_id, db_name, version, host, is_rac, cpus,
                    elapsed_time_min, db_time_min, raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (awr_hash) DO UPDATE SET
                    db_id = EXCLUDED.db_id,
                    db_name = EXCLUDED.db_name,
                    version = EXCLUDED.version,
                    host = EXCLUDED.host,
                    is_rac = EXCLUDED.is_rac,
                    cpus = EXCLUDED.cpus,
                    elapsed_time_min = EXCLUDED.elapsed_time_min,
                    db_time_min = EXCLUDED.db_time_min,
                    raw_payload = EXCLUDED.raw_payload
            """

            conn.execute(
                query,
                [
                    awr_hash,
                    db_id,
                    db_name,
                    version,
                    host,
                    is_rac,
                    cpus,
                    elapsed,
                    db_time,
                    raw_payload_json,
                ],
            )
            logger.info(f"Report with hash {awr_hash} saved effectively.")

        except Exception as e:
            logger.error(f"Database error during save operation: {e}")
            raise e
        finally:
            conn.close()
