"""
Pydantic data models representing the schema of the extracted AWR data.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Metadata(BaseModel):
    """Metadata regarding the parser execution and schema versioning."""

    schema_version: str = "1.0.0"
    parser_warnings: List[str] = Field(default_factory=list)


class DBInfoRaw(BaseModel):
    """Database identity and core context metrics from the AWR header."""

    db_name: Optional[str] = None
    db_id: Optional[int] = None
    version: Optional[str] = None
    host: str = "UNKNOWN"
    is_rac: bool = False
    cpus: Optional[int] = None
    elapsed_time_min: Optional[float] = None
    db_time_min: Optional[float] = None

    @field_validator("cpus")
    @classmethod
    def validate_cpus(cls, v: Optional[int]) -> Optional[int]:
        """Ensures that the CPU count is strictly greater than zero."""
        if v is not None and v <= 0:
            raise ValueError("CPUs must be greater than zero")
        return v


class LoadProfileRaw(BaseModel):
    """Raw metrics gathered from the Load Profile table."""

    db_time: Optional[float] = None
    logical_reads: Optional[float] = None
    physical_reads: Optional[float] = None


class LoadProfileNormalized(BaseModel):
    """Normalized 'per second' or 'per transaction' load profile metrics."""

    db_time_per_sec: Optional[float] = None
    logical_reads_per_sec: Optional[float] = None
    physical_reads_per_sec: Optional[float] = None
    hard_parses_per_sec: Optional[float] = None


class OSStatRaw(BaseModel):
    """Operating System Statistics (Values usually in centi-seconds)."""

    num_cpus: Optional[int] = None
    busy_time_cs: Optional[float] = None
    idle_time_cs: Optional[float] = None
    user_time_cs: Optional[float] = None
    sys_time_cs: Optional[float] = None
    iowait_time_cs: Optional[float] = None


class TimeModelRaw(BaseModel):
    """Time Model Statistics (Values usually in seconds)."""

    db_time_s: Optional[float] = None
    db_cpu_s: Optional[float] = None
    sql_execute_s: Optional[float] = None
    parse_time_s: Optional[float] = None
    hard_parse_s: Optional[float] = None


class TopEvent(BaseModel):
    """Represents a single database wait event entry from Top Events."""

    event_name: str
    wait_class: Optional[str] = None
    waits: Optional[int] = None
    time_s: Optional[float] = None
    avg_wait_ms: Optional[float] = None
    pct_db_time: Optional[float] = None

    @field_validator("pct_db_time")
    @classmethod
    def validate_percentage(cls, v: Optional[float]) -> Optional[float]:
        """Ensures the DB Time percentage falls within a logical 0-100 range."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Percentage must be between 0 and 100")
        return v


class TopSQL(BaseModel):
    """Represents a heavily consuming SQL statement from Top SQL sections."""

    sql_id: str
    elapsed_time_s: Optional[float] = None
    executions: Optional[int] = None
    sql_text: Optional[str] = None


class WaitHistogramRaw(BaseModel):
    """Represents a single bucket of latency for a specific wait event."""

    event_name: str
    wait_time_milli: float
    wait_count: float


class AWRReport(BaseModel):
    """The root model schema encompassing the entirety of the parsed AWR data."""

    metadata: Metadata
    db_info: Optional[DBInfoRaw] = None
    load_profile_raw: Optional[LoadProfileRaw] = None
    load_profile_normalized: Optional[LoadProfileNormalized] = None
    os_stat: Optional[OSStatRaw] = None
    time_model: Optional[TimeModelRaw] = None

    top_events: List[TopEvent] = Field(default_factory=list)
    top_sql: List[TopSQL] = Field(default_factory=list)
    wait_histograms: List[WaitHistogramRaw] = Field(default_factory=list)
