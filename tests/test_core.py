"""
Unit tests for the core AWR parser.
"""

from pathlib import Path

from src.models.base import AWRReport
from src.parser.core import AWRParser


def test_parser_opens_file_and_returns_base_model(dummy_html_path: Path) -> None:
    """
    GIVEN a valid file path to an HTML file
    WHEN the AWRParser.parse() method is called
    THEN it should read the file without exceptions and return an AWRReport instance.
    """
    # 1. Arrange
    parser = AWRParser()

    # 2. Act
    # We pass the fixture which contains the path to dummy_corrupt.html
    report = parser.parse(dummy_html_path)

    # 3. Assert
    assert report is not None
    assert isinstance(report, AWRReport)
