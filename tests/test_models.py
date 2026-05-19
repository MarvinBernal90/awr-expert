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
    THEN it should raise a ValidationError.
    """
    with pytest.raises(ValidationError, match="greater than zero"):
        DBInfoRaw(cpus=-1)

    with pytest.raises(ValidationError, match="greater than zero"):
        DBInfoRaw(cpus=0)


def test_top_event_rejects_invalid_percentage() -> None:
    """
    GIVEN a percentage outside the 0-100 range
    WHEN instantiating TopEvent
    THEN it should raise a ValidationError.
    """
    with pytest.raises(ValidationError, match="between 0 and 100"):
        TopEvent(event_name="DB CPU", pct_db_time=-5.0)

    with pytest.raises(ValidationError, match="between 0 and 100"):
        TopEvent(event_name="DB CPU", pct_db_time=105.0)


def test_top_event_accepts_valid_data() -> None:
    """
    GIVEN valid inputs including a correct percentage
    WHEN instantiating TopEvent
    THEN it should successfully create the model.
    """
    event = TopEvent(
        event_name="db file sequential read",
        wait_class="User I/O",
        waits=1000,
        time_s=50.5,
        avg_wait_ms=50.5,
        pct_db_time=25.0,
    )

    assert event.event_name == "db file sequential read"
    assert event.pct_db_time == 25.0
