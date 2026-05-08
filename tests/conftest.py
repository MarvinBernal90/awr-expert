"""
Pytest configuration and global fixtures.
"""

import os
from pathlib import Path

import pytest


@pytest.fixture
def test_awrs_dir() -> Path:
    """Returns the absolute path to the test_awrs directory."""
    # Gets the directory where conftest.py lives,
    # then goes up one level to the root.
    base_dir = Path(os.path.dirname(__file__)).parent
    return base_dir / "test_awrs"


@pytest.fixture
def dummy_html_path(test_awrs_dir: Path) -> Path:
    """Returns the path to a dummy HTML file for basic IO testing."""
    return test_awrs_dir / "edge_cases" / "dummy_corrupt.html"
