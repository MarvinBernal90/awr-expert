"""
CPU & Operating System Heuristic Engine.
Analyzes CPU utilization, starvation scenarios, and general host health.
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


class CPUDiagnosis(BaseModel):
    """The final verdict emitted by the CPU Engine."""

    area: str = "CPU & OS"
    status: str
    severity: str
    impact: str
    findings: List[Finding]
    recommendation: str


def analyze_cpu(report: AWRReport) -> Optional[CPUDiagnosis]:
    """Runs DBA heuristics on CPU metrics to determine system health."""
    if not report.db_info or not report.os_stat or not report.time_model:
        logger.warning("Insufficient data to run CPU analysis.")
        return None

    # 1. Extract Key Metrics
    cpus = report.os_stat.num_cpus or report.db_info.cpus
    if cpus is None or cpus <= 0:
        logger.warning("Insufficient CPU metadata to run CPU analysis.")
        return None

    elapsed_mins = report.db_info.elapsed_time_min or 0.0
    db_time_s = report.time_model.db_time_s or 0.0
    db_cpu_s = report.time_model.db_cpu_s or 0.0

    if elapsed_mins <= 0 or db_time_s <= 0:
        return None

    # 2. DBA Math (Calculate Capacities and Ratios)
    elapsed_s = elapsed_mins * 60
    total_cpu_capacity_s = elapsed_s * cpus

    # What percentage of the total host capacity did the DB consume?
    db_cpu_utilization = (
        (db_cpu_s / total_cpu_capacity_s) * 100 if total_cpu_capacity_s > 0 else 0.0
    )

    # Of all the time the DB was active, how much was working (CPU) vs waiting (Waits)?
    cpu_vs_wait_ratio = (db_cpu_s / db_time_s) * 100 if db_time_s > 0 else 0.0

    # Default Status (Healthy)
    findings = []
    status = "Normal"
    severity = "OK"
    impact = "Low"
    recommendation = "CPU consumption is healthy. No action required."

    # 3. Heuristic Rules Engine
    if db_cpu_utilization > 85.0:
        status = "Saturated"
        severity = "CRITICAL"
        impact = "High"
        findings.append(
            Finding(
                description=(
                    f"DB consumed {db_cpu_utilization:.1f}% "
                    "of the total host CPU capacity."
                ),
                is_critical=True,
            )
        )
        recommendation = (
            "Review 'Top SQL by CPU Time'. "
            "Consider scaling hardware if SQL is already optimized."
        )

    elif db_time_s > total_cpu_capacity_s and cpu_vs_wait_ratio < 40.0:
        status = "Starvation (Waits)"
        severity = "WARN"
        impact = "Medium"
        findings.append(
            Finding(
                description=(
                    f"High DB Time, but only {cpu_vs_wait_ratio:.1f}% is CPU "
                    "processing. The DB is heavily waiting."
                ),
                is_critical=False,
            )
        )
        recommendation = (
            "CPU is idle but DB is slow. Analyze Top Wait Events "
            "(I/O, Locks) to find the bottleneck."
        )

    elif cpu_vs_wait_ratio > 80.0 and db_cpu_utilization < 70.0:
        findings.append(
            Finding(
                description=(
                    f"Excellent profile. {cpu_vs_wait_ratio:.1f}% of DB Time is "
                    "actual CPU work, with no I/O bottlenecks."
                ),
                is_critical=False,
            )
        )

    return CPUDiagnosis(
        status=status,
        severity=severity,
        impact=impact,
        findings=findings,
        recommendation=recommendation,
    )
