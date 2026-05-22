"""
Unit tests for the Memory & Concurrency Engine.
"""

from src.engine.memory import analyze_memory
from src.models.base import AWRReport, Metadata, TopEvent


def create_dummy_report(events: list) -> AWRReport:
    """Helper function to mock an AWRReport with specific top events."""
    return AWRReport(
        metadata=Metadata(parser_warnings=[]),
        top_events=events,
    )


def test_analyze_memory_no_events() -> None:
    """It should return None if there are no Top Events."""
    report = create_dummy_report([])
    assert analyze_memory(report) is None


def test_analyze_memory_healthy_events() -> None:
    """It should return None if events are not related to memory or locks."""
    events = [
        TopEvent(event_name="db file sequential read", pct_db_time=50.0),
        TopEvent(event_name="CPU time", pct_db_time=40.0),
    ]
    report = create_dummy_report(events)
    assert analyze_memory(report) is None


def test_analyze_memory_shared_pool_warn() -> None:
    """It should return WARN if Shared Pool contention is between 15% and 30%."""
    events = [
        TopEvent(event_name="latch: shared pool", pct_db_time=20.0),
    ]
    report = create_dummy_report(events)
    result = analyze_memory(report)

    assert result is not None
    assert result.severity == "WARN"
    assert len(result.findings) == 1
    assert "Shared Pool" in result.findings[0].description


def test_analyze_memory_temp_spill_critical() -> None:
    """It should return CRITICAL if Temp spills are above 25%."""
    events = [
        TopEvent(event_name="direct path read temp", pct_db_time=30.0),
    ]
    report = create_dummy_report(events)
    result = analyze_memory(report)

    assert result is not None
    assert result.severity == "CRITICAL"
    assert "PGA memory spills" in result.findings[0].description


def test_analyze_memory_locks_warn() -> None:
    """It should return WARN if Enqueues consume between 10% and 20%."""
    events = [
        TopEvent(event_name="enq: TX - row lock contention", pct_db_time=15.0),
    ]
    report = create_dummy_report(events)
    result = analyze_memory(report)

    assert result is not None
    assert result.severity == "WARN"
    assert "Application locks" in result.findings[0].description
