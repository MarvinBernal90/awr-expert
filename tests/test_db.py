"""
Unit tests for the DuckDB Manager.
"""

from pathlib import Path

from src.services.db import DBManager


def test_initialize_schema_creates_table(tmp_path: Path) -> None:
    """
    GIVEN a DBManager pointing to a temporary path
    WHEN initialize_schema is called
    THEN it should create the database file and the 'awr_reports' table.
    """
    db_file = tmp_path / "test_warehouse.duckdb"
    manager = DBManager(db_path=str(db_file))

    manager.initialize_schema()

    # Verify the physical file exists
    assert db_file.exists()

    # Verify the table was created
    with manager.get_connection() as conn:
        tables = conn.execute("SHOW TABLES").fetchall()
        # tables is a list of tuples like: [('awr_reports',)]
        table_names = [table[0] for table in tables]

        assert "awr_reports" in table_names
