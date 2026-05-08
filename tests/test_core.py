"""
Unit tests for the core AWR parser.
"""

from pathlib import Path

import pytest

from src.models.base import AWRReport
from src.parser.core import AWRParser
from src.parser.exceptions import AWRFileNotFoundError


def test_parser_opens_file_and_returns_base_model(dummy_html_path: Path) -> None:
    """
    GIVEN a valid file path to an HTML file
    WHEN the AWRParser.parse() method is called
    THEN it should read the file without exceptions and return an AWRReport instance.
    """
    parser = AWRParser()
    report = parser.parse(dummy_html_path)

    assert report is not None
    assert isinstance(report, AWRReport)
    # Check that our dummy warning from the skeleton is inside the metadata
    assert len(report.metadata.parser_warnings) == 1


def test_parser_raises_error_for_missing_file() -> None:
    """
    GIVEN a non-existent file path
    WHEN the AWRParser.parse() method is called
    THEN it should raise an AWRFileNotFoundError.
    """
    parser = AWRParser()
    fake_path = Path("this_file_does_not_exist.html")

    with pytest.raises(AWRFileNotFoundError):
        parser.parse(fake_path)
