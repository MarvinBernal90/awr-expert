"""
Unit tests for the Core AWR Parser.
"""

from pathlib import Path

import pytest

from src.models.base import AWRReport
from src.parser.core import AWRParser


@pytest.fixture
def sample_html_file(tmp_path: Path) -> Path:
    """Creates a dummy HTML file for testing."""
    file_path = tmp_path / "dummy_awr.html"
    file_path.write_text("<html><body>Dummy AWR Report</body></html>", encoding="utf-8")
    return file_path


def test_parser_returns_awr_report(sample_html_file: Path) -> None:
    """
    GIVEN a valid (but dummy) HTML file
    WHEN the AWRParser.parse() method is called
    THEN it should return an AWRReport object.
    """
    parser = AWRParser()
    report = parser.parse(sample_html_file)

    # Verifica que el core devuelve un objeto válido de Pydantic
    assert isinstance(report, AWRReport)
    assert report.metadata is not None
    # Como el HTML es falso, las listas por defecto deben estar vacías
    assert isinstance(report.top_events, list)
    assert isinstance(report.top_sql, list)


def test_parser_raises_error_for_missing_file() -> None:
    """
    GIVEN a non-existent file path
    WHEN the AWRParser.parse() method is called
    THEN it should raise a FileNotFoundError.
    """
    parser = AWRParser()
    fake_path = Path("this_file_does_not_exist.html")

    # Aquí esperamos la excepción estándar de Python
    with pytest.raises(FileNotFoundError):
        parser.parse(fake_path)
