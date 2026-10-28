"""Statistical and entropy-based log anomaly detection engine."""

from collections import Counter
import math
from typing import Any, Dict, List
import numpy as np


class LogAnomalyDetector:
    """Detects anomalous error bursts and message distribution shifts using statistical Z-scores and Shannon Entropy."""

    def __init__(self, z_score_threshold: float = 2.5):
        self.z_score_threshold = z_score_threshold
        self.historical_counts: List[int] = []

    def evaluate_error_frequency(self, error_count: int) -> Dict[str, Any]:
        """Compute rolling Z-score to determine if current error frequency constitutes an anomaly."""
        self.historical_counts.append(error_count)
        if len(self.historical_counts) > 100:
            self.historical_counts.pop(0)

        if len(self.historical_counts) < 3:
            return {"is_anomalous": False, "z_score": 0.0, "reason": "Insufficient baseline history"}

        baseline = self.historical_counts[:-1]
        mean = float(np.mean(baseline))
        std = float(np.std(baseline))

        if std == 0.0:
            z_score = float(error_count - mean) if error_count != mean else 0.0
        else:
            z_score = float((error_count - mean) / std)

        is_anomalous = z_score >= self.z_score_threshold
        return {
            "is_anomalous": is_anomalous,
            "z_score": round(z_score, 2),
            "current_count": error_count,
            "baseline_mean": round(mean, 2),
            "baseline_std": round(std, 2),
            "severity": "CRITICAL" if z_score >= 4.0 else "HIGH" if z_score >= 2.5 else "NORMAL",
        }

    @staticmethod
    def calculate_shannon_entropy(messages: List[str]) -> float:
        """Calculate Shannon entropy over message tokens. Low entropy indicates single failure dominance."""
        if not messages:
            return 0.0

        total = len(messages)
        counts = Counter(messages)
        entropy = 0.0

        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)

        return round(float(entropy), 3)
