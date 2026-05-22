"""
I/O & Storage Heuristic Engine.
Analyzes wait event histograms to diagnose storage latency bottlenecks.
"""

import logging
from typing import List, Optional

from pydantic import BaseModel

from src.models.base import AWRReport

logger = logging.getLogger(__name__)


class Finding(BaseModel):
    """Represents a specific observation made by the engine."""

    description: str
    is_critical: bool


class IODiagnosis(BaseModel):
    """The final verdict emitted by the I/O Engine."""

    area: str = "I/O & Storage"
    status: str
    severity: str
    impact: str
    findings: List[Finding]
    recommendation: str


def analyze_io(report: AWRReport) -> Optional[IODiagnosis]:
    """Runs DBA heuristics on I/O latency metrics."""
    if not report.wait_histograms:
        logger.debug("No wait histograms found to run I/O analysis.")
        return None

    # Key Oracle events to monitor
    SEQ_READ = "db file sequential read"
    LOG_SYNC = "log file sync"

    # Strict SLA Thresholds (milliseconds)
    FAST_READ_MS = 8.0
    FAST_LOG_MS = 8.0

    seq_read_total = 0.0
    seq_read_fast = 0.0
    log_sync_total = 0.0
    log_sync_fast = 0.0

    # Process all histogram buckets
    for h in report.wait_histograms:
        event = h.event_name.lower()
        if event == SEQ_READ:
            seq_read_total += h.wait_count
            if h.wait_time_milli <= FAST_READ_MS:
                seq_read_fast += h.wait_count
        elif event == LOG_SYNC:
            log_sync_total += h.wait_count
            if h.wait_time_milli <= FAST_LOG_MS:
                log_sync_fast += h.wait_count

    # If there is zero relevant I/O activity, skip diagnosis
    if seq_read_total == 0 and log_sync_total == 0:
        return None

    # Default Status (Healthy)
    findings = []
    severity = "OK"
    status = "Healthy"
    impact = "Low"
    recommendation = "Storage latencies are within optimal DBA thresholds."

    # 1. Analyze Sequential Reads (Index access)
    # Using > 0 because 19c uses percentages (total ~ 100.0)
    if seq_read_total > 0:
        pct_fast = (seq_read_fast / seq_read_total) * 100
        if pct_fast < 70.0:
            severity = "CRITICAL" if pct_fast < 50.0 else "WARN"
            status = "High Latency"
            impact = "High" if severity == "CRITICAL" else "Medium"
            findings.append(
                Finding(
                    description=(
                        f"Only {pct_fast:.1f}% of '{SEQ_READ}' completed "
                        f"under {FAST_READ_MS}ms. Storage array is struggling."
                    ),
                    is_critical=(severity == "CRITICAL"),
                )
            )
        elif pct_fast > 90.0:
            findings.append(
                Finding(
                    description=(
                        f"Excellent read latency: {pct_fast:.1f}% of "
                        f"'{SEQ_READ}' finished under {FAST_READ_MS}ms."
                    ),
                    is_critical=False,
                )
            )

    # 2. Analyze Log File Sync (Commits)
    if log_sync_total > 0:
        pct_fast_log = (log_sync_fast / log_sync_total) * 100
        if pct_fast_log < 75.0:
            if severity != "CRITICAL":
                severity = "WARN" if pct_fast_log >= 60.0 else "CRITICAL"
            status = "Commit Bottleneck"
            impact = "High"
            findings.append(
                Finding(
                    description=(
                        f"Commit latency issue: only {pct_fast_log:.1f}% of "
                        f"'{LOG_SYNC}' completed under {FAST_LOG_MS}ms."
                    ),
                    is_critical=(pct_fast_log < 60.0),
                )
            )

    # 3. Dynamic Recommendations based on final severity
    if severity == "WARN":
        recommendation = (
            "Investigate storage array performance. Check for I/O saturation "
            "or consider migrating hot objects to Flash/SSD."
        )
    elif severity == "CRITICAL":
        recommendation = (
            "Severe storage bottleneck detected. Engage the storage/SAN team "
            "immediately. Review IOPS limits and physical disk health."
        )

    return IODiagnosis(
        status=status,
        severity=severity,
        impact=impact,
        findings=findings,
        recommendation=recommendation,
    )
