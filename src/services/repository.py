"""
Repository layer for AWR Reports.
Handles storage and retrieval of parsed metrics from DuckDB.
"""

import logging
from typing import Any, Dict, List, Optional

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

    # --- SPRINT 12: DYNAMIC BASELINES ---
    def get_historical_baselines(self, db_name: str) -> Dict[str, Any]:
        """
        Dives into the JSON payloads using DuckDB analytics to calculate
        historical averages for a specific database.
        """
        try:
            with duckdb.connect(self.db_path) as conn:
                l_ps = "'$.load_profile.logical_reads_ps'"
                l_rw = "'$.load_profile.logical_reads'"
                p_ps = "'$.load_profile.physical_reads_ps'"
                p_rw = "'$.load_profile.physical_reads'"
                e_ps = "'$.load_profile.executes_ps'"
                e_rw = "'$.load_profile.executes'"
                t_ps = "'$.load_profile.transactions_ps'"
                t_rw = "'$.load_profile.transactions'"
                db_n = "'$.db_info.db_name'"

                query = f"""
                    SELECT
                        COUNT(*) as total_reports,
                        AVG(CAST(COALESCE(
                            json_extract_string(raw_payload, {l_ps}),
                            json_extract_string(raw_payload, {l_rw})
                        ) AS DOUBLE)) as a_lr,
                        AVG(CAST(COALESCE(
                            json_extract_string(raw_payload, {p_ps}),
                            json_extract_string(raw_payload, {p_rw})
                        ) AS DOUBLE)) as a_pr,
                        AVG(CAST(COALESCE(
                            json_extract_string(raw_payload, {e_ps}),
                            json_extract_string(raw_payload, {e_rw})
                        ) AS DOUBLE)) as a_ex,
                        AVG(CAST(COALESCE(
                            json_extract_string(raw_payload, {t_ps}),
                            json_extract_string(raw_payload, {t_rw})
                        ) AS DOUBLE)) as a_tx
                    FROM awr_reports
                    WHERE json_extract_string(raw_payload, {db_n}) = ?
                """

                result = conn.execute(query, [db_name]).fetchone()

                if result and result[0] > 0:
                    return {
                        "total_reports": result[0],
                        "logical_reads_ps": round(result[1] or 0.0, 2),
                        "physical_reads_ps": round(result[2] or 0.0, 2),
                        "executes_ps": round(result[3] or 0.0, 2),
                        "transactions_ps": round(result[4] or 0.0, 2),
                    }
                return {}
        except Exception as e:
            logger.error(f"Failed to calculate baselines for {db_name}: {e}")
            return {}

    # --- SPRINT 13: TIME-SERIES INTELLIGENCE ---
    def get_time_series(self, db_name: str, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Extracts the historical time-series data for a specific database.
        Returns a list of metrics per snapshot to feed the Analytics Engine.
        """
        try:
            with duckdb.connect(self.db_path) as conn:
                l_ps = "'$.load_profile.logical_reads_ps'"
                l_rw = "'$.load_profile.logical_reads'"
                p_ps = "'$.load_profile.physical_reads_ps'"
                p_rw = "'$.load_profile.physical_reads'"
                e_ps = "'$.load_profile.executes_ps'"
                e_rw = "'$.load_profile.executes'"
                t_ps = "'$.load_profile.transactions_ps'"
                t_rw = "'$.load_profile.transactions'"
                db_n = "'$.db_info.db_name'"

                query = f"""
                    SELECT
                        awr_hash,
                        CAST(COALESCE(
                            json_extract_string(raw_payload, {l_ps}),
                            json_extract_string(raw_payload, {l_rw})
                        ) AS DOUBLE) as lr,
                        CAST(COALESCE(
                            json_extract_string(raw_payload, {p_ps}),
                            json_extract_string(raw_payload, {p_rw})
                        ) AS DOUBLE) as pr,
                        CAST(COALESCE(
                            json_extract_string(raw_payload, {e_ps}),
                            json_extract_string(raw_payload, {e_rw})
                        ) AS DOUBLE) as ex,
                        CAST(COALESCE(
                            json_extract_string(raw_payload, {t_ps}),
                            json_extract_string(raw_payload, {t_rw})
                        ) AS DOUBLE) as tx
                    FROM awr_reports
                    WHERE json_extract_string(raw_payload, {db_n}) = ?
                    LIMIT ?
                """

                results = conn.execute(query, [db_name, limit]).fetchall()

                time_series = []
                for row in results:
                    time_series.append(
                        {
                            "snapshot_id": row[0],
                            "logical_reads_ps": row[1] or 0.0,
                            "physical_reads_ps": row[2] or 0.0,
                            "executes_ps": row[3] or 0.0,
                            "transactions_ps": row[4] or 0.0,
                        }
                    )

                return time_series
        except Exception as e:
            logger.error(f"Failed to extract time-series for {db_name}: {e}")
            return []
