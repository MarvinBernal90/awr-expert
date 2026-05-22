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

    # Verify that the core returns a valid Pydantic object
    assert isinstance(report, AWRReport)
    assert report.metadata is not None

    # Since the HTML is fake, the default lists must be strictly empty
    assert report.top_events == []
    assert report.top_sql == []
    assert report.wait_histograms == []


def test_parser_raises_error_for_missing_file(tmp_path: Path) -> None:
    """
    GIVEN a non-existent file path
    WHEN the AWRParser.parse() method is called
    THEN it should raise a FileNotFoundError.
    """
    parser = AWRParser()

    # Use a guaranteed-missing path under tmp_path
    fake_path = tmp_path / "this_file_does_not_exist.html"

    with pytest.raises(FileNotFoundError):
        parser.parse(fake_path)
