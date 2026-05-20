"""
Unit tests for the AWR Repository.
"""

from pathlib import Path

from src.models.base import AWRReport, DBInfoRaw, Metadata, TopEvent
from src.services.db import DBManager
from src.services.repository import AWRRepository


def test_repository_upsert_idempotency(tmp_path: Path) -> None:
    """
    GIVEN a valid AWRReport and an initialized DuckDB database
    WHEN the same report is saved twice via the repository
    THEN it should not raise a duplicate key error, and only 1 row should exist.
    """
    # 1. Setup in-memory / temporary DB
    db_file = tmp_path / "test_repo.duckdb"
    db_manager = DBManager(db_path=str(db_file))
    db_manager.initialize_schema()

    repo = AWRRepository(db_manager)

    # 2. Create a dummy Pydantic model
    report = AWRReport(
        metadata=Metadata(parser_warnings=["Test warning"]),
        db_info=DBInfoRaw(
            db_id=123456,
            db_name="PRODDB",
            cpus=8,
            elapsed_time_min=60.1,
            db_time_min=300.5,
        ),
        top_events=[TopEvent(event_name="log file sync", waits=100)],
    )

    # 3. Save it the first time
    hash_1 = repo.save(report)
    assert hash_1 is not None

    # 4. Save it a second time (Simulating parsing the same file again)
    hash_2 = repo.save(report)

    # 5. Assertions
    assert hash_1 == hash_2  # The deterministic hash must be identical

    with db_manager.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM awr_reports").fetchone()[0]

    # Idempotency guarantees exactly 1 row is stored
    assert count == 1
