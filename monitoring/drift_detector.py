from __future__ import annotations

import os
from collections import Counter


DEFAULT_REFERENCE_DISTRIBUTION = {
    "AI": 0.40,
    "Business": 0.30,
    "Robotics": 0.08,
    "Research": 0.08,
    "Security": 0.09,
    "Open Source": 0.05,
}


class DriftDetector:
    def __init__(self, threshold: float | None = None) -> None:
        self.threshold = threshold if threshold is not None else float(os.getenv("DRIFT_THRESHOLD", "0.35"))
        self.reference = DEFAULT_REFERENCE_DISTRIBUTION

    def detect(self, current_counts: Counter[str], total: int) -> dict[str, object]:
        if total == 0:
            return {
                "drift_detected": False,
                "reason": "not_enough_predictions",
                "reference_distribution": self.reference,
                "current_distribution": {},
                "max_delta": 0.0,
            }

        current = {category: current_counts.get(category, 0) / total for category in self.reference}
        max_delta = max(abs(current[category] - self.reference[category]) for category in self.reference)
        drift = max_delta >= self.threshold
        return {
            "drift_detected": drift,
            "reason": "Data Drift Detected" if drift else "distribution_within_threshold",
            "reference_distribution": self.reference,
            "current_distribution": current,
            "max_delta": max_delta,
            "threshold": self.threshold,
        }
