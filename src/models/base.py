"""
Pydantic models defining the strict data contracts for the AWR Report.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Metadata(BaseModel):
    """Internal metadata for the parsed report."""

    schema_version: str = "1.0.0"
    parser_warnings: List[str] = Field(default_factory=list)


class DBInfoRaw(BaseModel):
    """Raw database context extracted from the AWR header."""

    db_name: Optional[str] = None
    db_id: Optional[str] = None
    version: Optional[str] = None
    is_rac: bool = False
    cpus: Optional[int] = None
    elapsed_time_min: Optional[float] = None
    db_time_min: Optional[float] = None

    @field_validator("cpus", "elapsed_time_min", "db_time_min")
    @classmethod
    def must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Time and CPU metrics must be positive.")
        return v


class LoadProfileRaw(BaseModel):
    """Raw load profile metrics directly from the AWR."""

    db_time: Optional[float] = None
    logical_reads: Optional[float] = None
    physical_reads: Optional[float] = None


class LoadProfileNormalized(BaseModel):
    """Normalized load profile metrics (per second / per transaction)."""

    db_time_per_sec: Optional[float] = None
    logical_reads_per_sec: Optional[float] = None
    physical_reads_per_sec: Optional[float] = None
    hard_parses_per_sec: Optional[float] = None


class TopEvent(BaseModel):
    """Represents a single wait event from 'Top 5 Timed Events'."""

    event_name: str
    wait_class: Optional[str] = None
    waits: Optional[int] = None
    time_s: Optional[float] = None
    avg_wait_ms: Optional[float] = None
    pct_db_time: Optional[float] = None

    @field_validator("pct_db_time")
    @classmethod
    def valid_percentage(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Percentage must be between 0 and 100.")
        return v


class SQLStat(BaseModel):
    """Represents a heavy SQL statement."""

    sql_id: str
    elapsed_time_s: Optional[float] = None
    executions: Optional[int] = None
    elapsed_per_exec_s: Optional[float] = None
    pct_total_db_time: Optional[float] = None
    sql_module: Optional[str] = None


class AWRReport(BaseModel):
    """Root model encapsulating the entire parsed AWR Report."""

    metadata: Metadata = Field(default_factory=Metadata)
    db_info: Optional[DBInfoRaw] = None
    load_profile_raw: Optional[LoadProfileRaw] = None
    load_profile_normalized: Optional[LoadProfileNormalized] = None
    top_events: List[TopEvent] = Field(default_factory=list)
    top_sql: List[SQLStat] = Field(default_factory=list)
