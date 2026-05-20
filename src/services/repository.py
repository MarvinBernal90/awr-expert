"""
Repository layer for AWR Reports.
Handles data persistence, hashing (idempotency), and JSON serialization for DuckDB.
"""

import hashlib
import json
import logging

from src.models.base import AWRReport
from src.services.db import DBManager

logger = logging.getLogger(__name__)


class AWRRepository:
    """
    Handles the insertion and updates of AWR Reports into DuckDB.
    """

    def __init__(self, db_manager: DBManager) -> None:
        self.db = db_manager

    def generate_hash(self, report: AWRReport) -> str:
        """
        Generates a deterministic SHA-256 hash representing the actual content.
        Avoids collisions by hashing the exact parsed metrics, bypassing the
        need for explicit Snap IDs and avoiding the 0-0.0-0.0 fallback.
        """
        # Create a deterministic dictionary from core data
        core_data = {
            "db_info": report.db_info.model_dump() if report.db_info else None,
            "top_events": [e.model_dump() for e in report.top_events],
        }
        # sort_keys=True ensures the JSON string is always generated
        # in the exact same order
        raw_str = json.dumps(core_data, sort_keys=True)
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    def save(self, report: AWRReport) -> str:
        """
        Saves the AWR report to the database.
        Uses UPSERT logic (ON CONFLICT) to prevent duplicates and ensure idempotency.
        """
        awr_hash = self.generate_hash(report)
        logger.info(f"Saving AWR Report with Hash: {awr_hash}")

        # DuckDB supports Postgres-like ON CONFLICT DO UPDATE
        # Notice we DO NOT update created_at here to preserve
        # the original insertion time.
        query = """
        INSERT INTO awr_reports (
            awr_hash, schema_version, db_name, db_id, version, is_rac, cpus,
            elapsed_time_min, db_time_min, load_profile_raw,
            load_profile_normalized, top_events, top_sql, metadata_warnings
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (awr_hash) DO UPDATE SET
            schema_version = EXCLUDED.schema_version,
            load_profile_raw = EXCLUDED.load_profile_raw,
            load_profile_normalized = EXCLUDED.load_profile_normalized,
            top_events = EXCLUDED.top_events,
            top_sql = EXCLUDED.top_sql,
            metadata_warnings = EXCLUDED.metadata_warnings
        """

        # Serialize nested Pydantic models to JSON strings for DuckDB
        params = (
            awr_hash,
            report.metadata.schema_version,
            report.db_info.db_name if report.db_info else None,
            report.db_info.db_id if report.db_info else None,
            report.db_info.version if report.db_info else None,
            report.db_info.is_rac if report.db_info else False,
            report.db_info.cpus if report.db_info else None,
            report.db_info.elapsed_time_min if report.db_info else None,
            report.db_info.db_time_min if report.db_info else None,
            json.dumps(report.load_profile_raw.model_dump())
            if report.load_profile_raw
            else None,
            json.dumps(report.load_profile_normalized.model_dump())
            if report.load_profile_normalized
            else None,
            json.dumps([e.model_dump() for e in report.top_events]),
            json.dumps([s.model_dump() for s in report.top_sql]),
            json.dumps(report.metadata.parser_warnings),
        )

        try:
            with self.db.get_connection() as conn:
                conn.execute(query, params)
            logger.debug("Report saved successfully (UPSERT applied).")
            return awr_hash
        except Exception as e:
            logger.error(f"Failed to save AWR report to DB: {e}")
            raise
