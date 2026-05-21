import duckdb

from src.services import db


def test_initialize_warehouse(tmp_path, monkeypatch):
    """Tests that the DuckDB warehouse is initialized with the correct schema."""
    # Mock the DB_FILE to point to a temporary test directory
    test_db = tmp_path / "test_warehouse.duckdb"
    monkeypatch.setattr(db, "DB_FILE", str(test_db))

    # Run the initialization
    db.initialize_warehouse()

    # Verify the file was created
    assert test_db.exists()

    # Verify the table schema exists
    conn = duckdb.connect(str(test_db))
    tables = conn.execute("SHOW TABLES").fetchall()
    conn.close()

    # DuckDB returns a list of tuples, e.g., [('awr_reports',)]
    assert ("awr_reports",) in tables
