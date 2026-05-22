"""
Workload Classifier Engine (Month 4 - Adaptive Intelligence).
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
    # 1. Obtain Load Profile Data (Supporting both legacy and new structures)
    lp = report.load_profile or report.load_profile_raw

    if not lp:
        logger.warning("No Load Profile data available for classification.")
        return {
            "workload_type": "UNKNOWN",
            "confidence": 0.0,
            "reason": "Missing Load Profile data in AWR.",
        }

    # Extract metrics safely (Check for None instead of relying on falsy 0.0)
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

    logger.debug(
        f"Metrics - L.Reads: {logical_reads}, P.Reads: {physical_reads}, "
        f"Execs: {executes}, Tx: {transactions}"
    )

    # 2. Heuristic Rules Engine
    workload_type = "MIXED"
    confidence = 50.0
    reason = "Metrics do not strongly align with pure OLTP or DW patterns."

    # DW / DSS Heuristics (Low transactions, high physical reads)
    if transactions < 50 and physical_reads > 5000:
        workload_type = "DATA_WAREHOUSE"
        confidence = min(100.0, 60.0 + (physical_reads / 10000.0) * 10)
        reason = (
            "High physical reads with very low transaction rate "
            "indicates analytical queries."
        )

    # OLTP Heuristics (High executes, high transactions, mostly logical reads)
    elif executes > 1000 or transactions > 100:
        workload_type = "OLTP"
        # Confidence increases if physical reads are low compared to logical reads
        if logical_reads > 0:
            hit_ratio = (logical_reads - physical_reads) / logical_reads
            if hit_ratio > 0.90:
                confidence = min(100.0, 70.0 + (hit_ratio * 20))
                reason = (
                    "High execution rate and excellent memory hit ratio "
                    "indicates transactional workload."
                )
            else:
                confidence = 65.0
                reason = (
                    "High execution rate detected, but physical reads "
                    "are somewhat high for pure OLTP."
                )

    return {
        "workload_type": workload_type,
        "confidence": round(confidence, 1),
        "reason": reason,
    }
