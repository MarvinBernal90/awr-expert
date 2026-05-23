"""
Workload Classifier Engine.
Analyzes the Load Profile to determine the type of database workload (OLTP, DW, MIXED).
"""

import logging
from typing import Any, Dict

from src.models.base import AWRReport

logger = logging.getLogger(__name__)


def classify_workload(report: AWRReport) -> Dict[str, Any]:
    """
    Classifies the database workload based on Load Profile heuristics.
    Returns a dictionary with the classification and the confidence score.
    """
    lp = report.load_profile or report.load_profile_raw

    if not lp:
        logger.warning("No Load Profile data available for classification.")
        return {
            "workload_type": "UNKNOWN",
            "confidence": 0.0,
            "reason": "Missing Load Profile data in AWR.",
        }

    # Extract metrics safely
    logical_reads = (
        lp.logical_reads_ps
        if lp.logical_reads_ps is not None
        else (lp.logical_reads if lp.logical_reads is not None else 0.0)
    )
    physical_reads = (
        lp.physical_reads_ps
        if lp.physical_reads_ps is not None
        else (lp.physical_reads if lp.physical_reads is not None else 0.0)
    )
    executes = (
        lp.executes_ps
        if lp.executes_ps is not None
        else (lp.executes if lp.executes is not None else 0.0)
    )
    transactions = (
        lp.transactions_ps
        if lp.transactions_ps is not None
        else (lp.transactions if lp.transactions is not None else 0.0)
    )

    if all(v == 0.0 for v in (logical_reads, physical_reads, executes, transactions)):
        return {
            "workload_type": "UNKNOWN",
            "confidence": 0.0,
            "reason": "Load Profile present but required metrics are missing.",
        }

    workload_type = "MIXED"
    confidence = 50.0
    reason = "Metrics do not strongly align with pure OLTP or DW patterns."

    if transactions < 50 and physical_reads > 5000:
        workload_type = "DATA_WAREHOUSE"
        confidence = min(100.0, 60.0 + (physical_reads / 10000.0) * 10)
        reason = "High physical reads and low transactions indicate analytical queries."

    elif executes > 1000 or transactions > 100:
        workload_type = "OLTP"
        if logical_reads > 0:
            hit_ratio = (logical_reads - physical_reads) / logical_reads
            if hit_ratio > 0.90:
                confidence = min(100.0, 70.0 + (hit_ratio * 20))
                reason = "High execution rate and good hit ratio indicates OLTP."
            else:
                confidence = 65.0
                reason = "High execution rate, but physical reads are somewhat high."

    return {
        "workload_type": workload_type,
        "confidence": round(confidence, 1),
        "reason": reason,
    }
