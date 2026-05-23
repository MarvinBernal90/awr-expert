"""
Behavioral Analytics & Anomaly Detection Engine.
Calculates percentiles, standard deviations, and Z-Scores for time-series data.
"""

import logging
import math
import statistics
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BehavioralAnalyzer:
    """
    Evaluates current database metrics against historical
    time-series distributions.
    """

    def __init__(self, min_samples: int = 3):
        """
        Args:
            min_samples: Minimum historical snapshots required to calculate
                         variance safely. Below this, we fallback to simple math.
        """
        self.min_samples = min_samples

        # Define thresholds for anomaly classification based on Z-Scores
        self.Z_SCORE_CRITICAL = 3.0  # 99.7% confidence of anomaly
        self.Z_SCORE_WARNING = 2.0  # 95% confidence of anomaly

    def _calculate_p95(self, data: List[float]) -> float:
        """Calculates the 95th percentile using nearest-rank method safely."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        # Safe nearest-rank index to prevent out-of-bounds on exact multiples
        index = max(0, math.ceil(0.95 * len(sorted_data)) - 1)
        return sorted_data[index]

    def _evaluate_metric(
        self, current_val: float, historical_vals: List[float]
    ) -> Dict[str, Any]:
        """Runs statistical evaluation for a single metric against its history."""
        # Fallback for empty history
        if not historical_vals:
            return {
                "current": round(current_val, 2),
                "mean": 0.0,
                "p95": 0.0,
                "stdev": 0.0,
                "z_score": 0.0,
                "deviation_pct": 0.0,
                "status": "INSUFFICIENT_DATA",
            }

        mean = statistics.mean(historical_vals)
        p95 = self._calculate_p95(historical_vals)

        # Calculate percentage deviation from the mean
        deviation_pct = ((current_val - mean) / mean * 100.0) if mean > 0 else 0.0

        # If we have enough samples, use proper statistics (Z-Score)
        if len(historical_vals) >= self.min_samples:
            stdev = statistics.stdev(historical_vals)

            # Prevent division by zero if all historical values are perfectly identical
            if stdev == 0.0:
                if current_val == mean:
                    z_score = 0.0
                else:
                    z_score = float("inf") if current_val > mean else float("-inf")
            else:
                z_score = (current_val - mean) / stdev
        else:
            # Not enough data for variance, fallback to simple deviation proxy
            stdev = 0.0
            z_score = deviation_pct / 25.0

        # Determine Cognitive Status
        status = "NORMAL"
        if z_score > self.Z_SCORE_CRITICAL:
            status = "CRITICAL_SPIKE"
        elif z_score < -self.Z_SCORE_CRITICAL:
            status = "CRITICAL_DROP"
        elif z_score > self.Z_SCORE_WARNING:
            status = "WARNING_SPIKE"
        elif z_score < -self.Z_SCORE_WARNING:
            status = "WARNING_DROP"

        return {
            "current": round(current_val, 2),
            "mean": round(mean, 2),
            "p95": round(p95, 2),
            "stdev": round(stdev, 2),
            "z_score": round(z_score, 2),
            "deviation_pct": round(deviation_pct, 1),
            "status": status,
        }

    def analyze_workload(
        self, current_metrics: Dict[str, float], time_series: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Takes the current snapshot metrics and evaluates them against
        the DuckDB time-series. Returns a cognitive assessment ready
        for the LLM correlation engine.
        """
        metrics_to_eval = [
            "logical_reads_ps",
            "physical_reads_ps",
            "executes_ps",
            "transactions_ps",
        ]

        analysis_result = {"history_size": len(time_series), "metrics": {}}

        for metric in metrics_to_eval:
            current_val = current_metrics.get(metric, 0.0)

            # Extract just this metric's history from the full time-series list
            historical_vals = [
                float(snapshot.get(metric, 0.0))
                for snapshot in time_series
                if metric in snapshot
            ]

            # Execute the statistical engine
            analysis_result["metrics"][metric] = self._evaluate_metric(
                current_val, historical_vals
            )

        return analysis_result
