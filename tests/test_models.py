"""
Unit tests for the Pydantic data models.
"""

import pytest
from pydantic import ValidationError

from src.models.base import DBInfoRaw, TopEvent


def test_db_info_rejects_negative_cpu() -> None:
    """
    GIVEN a negative or zero CPU count
    WHEN instantiating DBInfoRaw
    THEN it should raise a ValueError.
    """
    import pytest

    with pytest.raises(ValueError, match="greater than zero"):
        DBInfoRaw(cpus=-1)

    with pytest.raises(ValueError, match="greater than zero"):
        DBInfoRaw(cpus=0)


def test_top_event_rejects_invalid_percentage() -> None:
    """
    GIVEN an invalid percentage over 100
    WHEN a TopEvent model is instantiated
    THEN a ValidationError should be raised.
    """
    with pytest.raises(ValidationError):
        TopEvent(event_name="db file sequential read", pct_db_time=150.0)


def test_top_event_accepts_valid_data() -> None:
    """
    GIVEN valid edge-case data (exactly 100%)
    WHEN a TopEvent model is instantiated
    THEN it should be created successfully.
    """
    event = TopEvent(event_name="log file sync", pct_db_time=100.0)
    assert event.pct_db_time == 100.0
