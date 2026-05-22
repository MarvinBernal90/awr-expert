"""
Unit tests for the AWR Repository.
"""

import duckdb
import pytest

from src.models.base import AWRReport, DBInfoRaw, Metadata
from src.services.repository import AWRRepository


@pytest.fixture
def test_db(tmp_path):
    """Creates a temporary DuckDB database with the required schema."""
    db_file = str(tmp_path / "test_repo.duckdb")
    with duckdb.connect(db_file) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS awr_reports (
                awr_hash VARCHAR PRIMARY KEY,
                raw_payload JSON,
                version VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_rac BOOLEAN
            )
            """
        )
    return db_file


def test_save_and_get_report(test_db):
    """Tests the UPSERT operation and retrieval of the AWRRepository."""
    repo = AWRRepository(db_file=test_db)

    # 1. Create a mock Pydantic report
    mock_report = AWRReport(
        metadata=Metadata(parser_warnings=[]),
        db_info=DBInfoRaw(
            db_name="TEST_DB",
            db_id=999,
            version="19c",
            host="test_host",
            cpus=4,
            elapsed_time_min=60.0,
        ),
    )

    test_hash = "fake_sha256_hash_123"

    # 2. Save twice to validate UPSERT/idempotency doesn't crash
    repo.save_report(test_hash, mock_report)
    repo.save_report(test_hash, mock_report)

    # 3. Retrieve the report using our new get_report method
    retrieved_report = repo.get_report(test_hash)

    # 4. Verify the object was perfectly reconstructed from DuckDB
    assert retrieved_report is not None
    assert retrieved_report.db_info is not None
    assert retrieved_report.db_info.db_name == "TEST_DB"
    assert retrieved_report.db_info.host == "test_host"
    assert retrieved_report.db_info.cpus == 4
