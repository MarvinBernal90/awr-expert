"""
Memory & Concurrency Heuristic Engine.
Analyzes Top Events to diagnose Shared Pool, PGA spills, and Lock contention.
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


class MemoryDiagnosis(BaseModel):
    """The final verdict emitted by the Memory & Concurrency Engine."""

    area: str = "Memory & Concurrency"
    status: str
    severity: str
    impact: str
    findings: List[Finding]
    recommendation: str


def analyze_memory(report: AWRReport) -> Optional[MemoryDiagnosis]:
    """Runs DBA heuristics on Top Events to find memory and lock bottlenecks."""
    if not report.top_events:
        logger.debug("No Top Events found to run Memory analysis.")
        return None

    # Accumulators for % DB Time
    shared_pool_pct = 0.0
    pga_temp_pct = 0.0
    lock_pct = 0.0

    for event_obj in report.top_events:
        event = event_obj.event_name.lower()
        pct = event_obj.pct_db_time or 0.0

        # 1. Shared Pool / Library Cache contention
        if any(
            x in event for x in ("library cache", "latch: shared pool", "cursor: pin")
        ):
            shared_pool_pct += pct

        # 2. PGA / Temp Spills (Direct path to temp)
        elif "temp" in event and "direct path" in event:
            pga_temp_pct += pct

        # 3. Application Locks / Enqueues
        elif "enq:" in event or "row cache lock" in event:
            lock_pct += pct

    # If no relevant events are consuming DB Time, the system is healthy in this area
    if shared_pool_pct == 0 and pga_temp_pct == 0 and lock_pct == 0:
        return None

    findings = []
    severity = "OK"
    impact = "Low"
    status = "Healthy"
    recommendation = "Memory areas and concurrency are within normal parameters."

    # Heuristics rules for Shared Pool
    if shared_pool_pct > 15.0:
        is_crit = shared_pool_pct > 30.0
        severity = "CRITICAL" if is_crit else "WARN"
        findings.append(
            Finding(
                description=(
                    f"Shared Pool / Parsing contention accounts for "
                    f"{shared_pool_pct:.1f}% of DB Time."
                ),
                is_critical=is_crit,
            )
        )

    # Heuristics rules for PGA
    if pga_temp_pct > 10.0:
        is_crit = pga_temp_pct > 25.0
        if severity != "CRITICAL":
            severity = "CRITICAL" if is_crit else "WARN"
        findings.append(
            Finding(
                description=(
                    f"PGA memory spills to Temp space consume "
                    f"{pga_temp_pct:.1f}% of DB Time."
                ),
                is_critical=is_crit,
            )
        )

    # Heuristics rules for Locks
    if lock_pct > 10.0:
        is_crit = lock_pct > 20.0
        if severity != "CRITICAL":
            severity = "CRITICAL" if is_crit else "WARN"
        findings.append(
            Finding(
                description=(
                    f"Application locks (Enqueues) block {lock_pct:.1f}% of DB Time."
                ),
                is_critical=is_crit,
            )
        )

    # Contextual Recommendations based on Severity
    if severity == "WARN":
        status = "Moderate Contention"
        impact = "Medium"
        recommendation = (
            "Review Top SQL for unshared cursors (hard parsing), large sorts, "
            "or long-running transactions causing row locks."
        )
    elif severity == "CRITICAL":
        status = "Severe Bottleneck"
        impact = "High"
        recommendation = (
            "Immediate action required: Check for missing bind variables, "
            "undersized PGA/SGA, or massive application lock contention."
        )

    return MemoryDiagnosis(
        status=status,
        severity=severity,
        impact=impact,
        findings=findings,
        recommendation=recommendation,
    )
