"""
Core Domain Models for AWR Expert.
Defines the structure of the data extracted from Oracle AWR HTML reports.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Metadata(BaseModel):
    """Stores metadata about the parsing process itself."""

    parser_warnings: List[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="allow")


class DBInfoRaw(BaseModel):
    """Raw database identification metrics."""

    db_name: Optional[str] = None
    db_id: Optional[int] = None
    version: Optional[str] = None
    host: Optional[str] = None
    cpus: Optional[int] = None
    elapsed_time_min: Optional[float] = None
    is_rac: Optional[bool] = None

    model_config = ConfigDict(extra="allow")

    @field_validator("cpus")
    @classmethod
    def validate_cpus(cls, v):
        if v is not None and v <= 0:
            raise ValueError("CPUs must be greater than zero.")
        return v


class OSStatRaw(BaseModel):
    """Operating System Statistics (e.g., CPU Utilization)."""

    stat_name: Optional[str] = None
    value: Optional[float] = None

    num_cpus: Optional[int] = None
    busy_time_cs: Optional[float] = None
    idle_time_cs: Optional[float] = None
    iowait_time_cs: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class TopEvent(BaseModel):
    """A single wait event from the 'Top 10 Foreground Events' table."""

    event_name: Optional[str] = None
    pct_db_time: Optional[float] = None
    wait_class: Optional[str] = None
    waits: Optional[int] = None
    time_s: Optional[float] = None

    model_config = ConfigDict(extra="allow")

    @field_validator("pct_db_time")
    @classmethod
    def validate_pct(cls, v):
        if v is not None and not (0.0 <= v <= 100.0):
            raise ValueError("Percentage must be between 0 and 100")
        return v


class TopSQL(BaseModel):
    """Statistics for a specific SQL statement (e.g., Top SQL by Elapsed Time)."""

    sql_id: Optional[str] = None
    elapsed_time_s: Optional[float] = None
    executions: Optional[int] = None
    sql_text: Optional[str] = None
    cpu_time_s: Optional[float] = None
    user_io_wait_time_s: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class TimeModelRaw(BaseModel):
    """Raw Time Model Statistics."""

    stat_name: Optional[str] = None
    time_s: Optional[float] = None
    pct_db_time: Optional[float] = None

    db_time_s: Optional[float] = None
    db_cpu_s: Optional[float] = None
    background_cpu_s: Optional[float] = None
    sql_exec_time_s: Optional[float] = None
    hard_parse_s: Optional[float] = None
    sql_execute_s: Optional[float] = None
    parse_time_s: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class WaitHistogramRaw(BaseModel):
    """Raw Wait Event Histogram Statistics."""

    event_name: Optional[str] = None
    wait_time_ms: Optional[float] = None
    wait_count: Optional[int] = None

    model_config = ConfigDict(extra="allow")


# --- Load Profile Models ---
class LoadProfileRaw(BaseModel):
    """Raw metrics per second from the Load Profile (Legacy)."""

    db_time: Optional[float] = None
    logical_reads: Optional[float] = None
    physical_reads: Optional[float] = None
    executes: Optional[float] = None
    transactions: Optional[float] = None

    logical_reads_ps: Optional[float] = None
    physical_reads_ps: Optional[float] = None
    executes_ps: Optional[float] = None
    transactions_ps: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class LoadProfileNormalized(BaseModel):
    """Normalized metrics per second from the Load Profile (Legacy)."""

    db_time: Optional[float] = None
    logical_reads: Optional[float] = None
    physical_reads: Optional[float] = None
    executes: Optional[float] = None
    transactions: Optional[float] = None

    logical_reads_ps: Optional[float] = None
    physical_reads_ps: Optional[float] = None
    executes_ps: Optional[float] = None
    transactions_ps: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class LoadProfile(BaseModel):
    """Unified metrics per second from the Load Profile table."""

    db_time: Optional[float] = None
    logical_reads: Optional[float] = None
    physical_reads: Optional[float] = None
    executes: Optional[float] = None
    transactions: Optional[float] = None

    logical_reads_ps: Optional[float] = None
    physical_reads_ps: Optional[float] = None
    executes_ps: Optional[float] = None
    transactions_ps: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class AWRReport(BaseModel):
    """The root aggregate model representing a fully parsed AWR report."""

    metadata: Metadata
    db_info: Optional[DBInfoRaw] = None
    load_profile_raw: Optional[LoadProfileRaw] = None
    load_profile_normalized: Optional[LoadProfileNormalized] = None
    load_profile: Optional[LoadProfile] = None

    os_stat: Optional[OSStatRaw] = None
    time_model: Optional[TimeModelRaw] = None

    top_events: Optional[List[TopEvent]] = Field(default_factory=list)
    top_sql: Optional[List[TopSQL]] = Field(default_factory=list)
    wait_histograms: Optional[List[WaitHistogramRaw]] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")
