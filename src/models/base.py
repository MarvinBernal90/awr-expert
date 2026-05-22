"""
Core Domain Models for AWR Expert.
Defines the structure of the data extracted from Oracle AWR HTML reports.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Metadata(BaseModel):
    """Stores metadata about the parsing process itself."""

    parser_warnings: List[str] = Field(default_factory=list)


class DBInfoRaw(BaseModel):
    """Raw database identification metrics."""

    db_name: Optional[str] = None
    db_id: Optional[int] = None
    version: Optional[str] = None
    host: Optional[str] = None
    cpus: Optional[int] = None
    elapsed_time_min: Optional[float] = None
    is_rac: Optional[bool] = None

    model_config = ConfigDict(extra="ignore")

    @field_validator("cpus")
    @classmethod
    def validate_cpus(cls, v):
        if v is not None and v <= 0:
            # Ajustado para que el test unitario lo reconozca
            raise ValueError("CPUs must be greater than zero.")
        return v


class OSStatRaw(BaseModel):
    """Operating System Statistics (e.g., CPU Utilization)."""

    stat_name: str
    value: float


class TopEvent(BaseModel):
    """A single wait event from the 'Top 10 Foreground Events' table."""

    event_name: str
    pct_db_time: float
    wait_class: Optional[str] = None
    waits: Optional[int] = None
    time_s: Optional[float] = None

    model_config = ConfigDict(extra="ignore")

    @field_validator("pct_db_time")
    @classmethod
    def validate_pct(cls, v):
        if not (0.0 <= v <= 100.0):
            raise ValueError("Percentage must be between 0 and 100")
        return v


class TopSQL(BaseModel):
    """Statistics for a specific SQL statement (e.g., Top SQL by Elapsed Time)."""

    sql_id: str
    elapsed_time_s: float
    executions: int
    sql_text: Optional[str] = None
    cpu_time_s: Optional[float] = None
    user_io_wait_time_s: Optional[float] = None


class TimeModelRaw(BaseModel):
    """Raw Time Model Statistics."""

    stat_name: str
    time_s: float
    pct_db_time: Optional[float] = None

    model_config = ConfigDict(extra="ignore")


class WaitHistogramRaw(BaseModel):
    """Raw Wait Event Histogram Statistics."""

    event_name: str
    wait_time_ms: float
    wait_count: int

    model_config = ConfigDict(extra="ignore")


# --- Load Profile Models ---
class LoadProfileRaw(BaseModel):
    """Raw metrics per second from the Load Profile (Legacy)."""

    logical_reads_ps: Optional[float] = None
    physical_reads_ps: Optional[float] = None
    executes_ps: Optional[float] = None
    transactions_ps: Optional[float] = None


class LoadProfileNormalized(BaseModel):
    """Normalized metrics per second from the Load Profile (Legacy)."""

    logical_reads_ps: Optional[float] = None
    physical_reads_ps: Optional[float] = None
    executes_ps: Optional[float] = None
    transactions_ps: Optional[float] = None


class LoadProfile(BaseModel):
    """Unified metrics per second from the Load Profile table."""

    logical_reads_ps: Optional[float] = None
    physical_reads_ps: Optional[float] = None
    executes_ps: Optional[float] = None
    transactions_ps: Optional[float] = None


class AWRReport(BaseModel):
    """The root aggregate model representing a fully parsed AWR report."""

    metadata: Metadata
    db_info: Optional[DBInfoRaw] = None

    # Soporte para código Legacy
    load_profile_raw: Optional[LoadProfileRaw] = None
    load_profile_normalized: Optional[LoadProfileNormalized] = None

    # Nuevo modelo del Mes 4
    load_profile: Optional[LoadProfile] = None

    # Ajustado con Optional y nombres exactos para coincidir con core.py
    os_stat: Optional[List[OSStatRaw]] = Field(default_factory=list)
    top_events: Optional[List[TopEvent]] = Field(default_factory=list)
    top_sql: Optional[List[TopSQL]] = Field(default_factory=list)
    time_model: Optional[List[TimeModelRaw]] = Field(default_factory=list)
    wait_histograms: Optional[List[WaitHistogramRaw]] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")
