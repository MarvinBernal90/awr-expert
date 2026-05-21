import duckdb
import pytest

from src.models.base import AWRReport, DBInfoRaw, Metadata
from src.services.repository import AWRRepository


@pytest.fixture
def test_db(tmp_path):
    """Fixture to provide a temporary initialized DuckDB."""
    db_file = tmp_path / "test_repo.duckdb"
    conn = duckdb.connect(str(db_file))
    conn.execute(
        """
        CREATE TABLE awr_reports (
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
    conn.close()
    return str(db_file)


def test_save_report(test_db):
    """Tests the UPSERT operation of the AWRRepository."""
    repo = AWRRepository(db_file=test_db)

    # Create a mock Pydantic report
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

    # Save twice to validate UPSERT/idempotency
    repo.save_report(test_hash, mock_report)
    repo.save_report(test_hash, mock_report)

    # Verify the report was inserted correctly and only once
    conn = duckdb.connect(test_db)

    # Deterministic fetch scoped by the specific hash
    result = conn.execute(
        "SELECT awr_hash, db_name, host, cpus FROM awr_reports WHERE awr_hash = ?",
        [test_hash],
    ).fetchone()

    count = conn.execute(
        "SELECT COUNT(*) FROM awr_reports WHERE awr_hash = ?",
        [test_hash],
    ).fetchone()[0]
    conn.close()

    assert count == 1
    assert result is not None
    assert result == (test_hash, "TEST_DB", "test_host", 4)
