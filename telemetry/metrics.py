"""Vectorized telemetry metrics calculations (latency percentiles, error rates, Prometheus format)."""

from typing import Dict, List
import numpy as np


class MetricsTracker:
    """Tracks latency distributions and error counters for SRE observability."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "MetricsTracker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.latencies: List[float] = []
        self.total_requests = 0
        self.status_codes: Dict[int, int] = {200: 0, 400: 0, 500: 0, 502: 0, 503: 0}

    def record_request(self, status_code: int, latency_ms: float):
        """Record point-in-time HTTP transaction."""
        self.total_requests += 1
        self.latencies.append(float(latency_ms))
        if len(self.latencies) > 5000:
            self.latencies.pop(0)

        bucket = status_code if status_code in self.status_codes else (status_code // 100) * 100
        self.status_codes[bucket] = self.status_codes.get(bucket, 0) + 1

    def compute_summary(self) -> Dict[str, float]:
        """Compute latency percentiles (P50, P90, P95, P99) and error rate."""
        if not self.latencies:
            return {
                "total_requests": 0,
                "error_rate_pct": 0.0,
                "p50_ms": 0.0,
                "p90_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "avg_latency_ms": 0.0,
            }

        arr = np.array(self.latencies)
        errors = sum(count for code, count in self.status_codes.items() if code >= 500)
        error_rate = (errors / self.total_requests) * 100.0 if self.total_requests > 0 else 0.0

        return {
            "total_requests": self.total_requests,
            "error_rate_pct": round(float(error_rate), 2),
            "p50_ms": round(float(np.percentile(arr, 50)), 2),
            "p90_ms": round(float(np.percentile(arr, 90)), 2),
            "p95_ms": round(float(np.percentile(arr, 95)), 2),
            "p99_ms": round(float(np.percentile(arr, 99)), 2),
            "avg_latency_ms": round(float(np.mean(arr)), 2),
        }

    def generate_prometheus_metrics(self) -> str:
        """Expose standard Prometheus metrics format."""
        summary = self.compute_summary()
        lines = [
            "# HELP http_requests_total Total number of HTTP requests processed",
            "# TYPE http_requests_total counter",
            f"http_requests_total {self.total_requests}",
            "# HELP http_error_rate_percentage Percentage of 5xx HTTP server errors",
            "# TYPE http_error_rate_percentage gauge",
            f"http_error_rate_percentage {summary['error_rate_pct']}",
            "# HELP http_request_latency_p95_ms 95th percentile request latency in milliseconds",
            "# TYPE http_request_latency_p95_ms gauge",
            f"http_request_latency_p95_ms {summary['p95_ms']}",
            "# HELP http_request_latency_p99_ms 99th percentile request latency in milliseconds",
            "# TYPE http_request_latency_p99_ms gauge",
            f"http_request_latency_p99_ms {summary['p99_ms']}",
        ]
        return "\n".join(lines) + "\n"

    def reset(self):
        self.latencies.clear()
        self.total_requests = 0
        self.status_codes = {200: 0, 400: 0, 500: 0, 502: 0, 503: 0}
