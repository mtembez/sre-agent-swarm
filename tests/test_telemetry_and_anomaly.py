import pytest
from telemetry.anomaly import LogAnomalyDetector
from telemetry.metrics import MetricsTracker


def test_metrics_tracker_percentiles_and_prometheus():
    tracker = MetricsTracker()
    tracker.reset()

    # Record 100 sample latencies: 1ms to 100ms
    for i in range(1, 101):
        status = 200 if i <= 95 else 500
        tracker.record_request(status, float(i))

    summary = tracker.compute_summary()
    assert summary["total_requests"] == 100
    assert summary["error_rate_pct"] == 5.0
    assert summary["p50_ms"] == 50.5
    assert summary["p95_ms"] == 95.05
    assert summary["p99_ms"] == 99.01

    prom_text = tracker.generate_prometheus_metrics()
    assert "http_requests_total 100" in prom_text
    assert "http_error_rate_percentage 5.0" in prom_text
    assert "http_request_latency_p95_ms" in prom_text


def test_empty_metrics_tracker():
    tracker = MetricsTracker()
    tracker.reset()
    summary = tracker.compute_summary()
    assert summary["total_requests"] == 0
    assert summary["error_rate_pct"] == 0.0


def test_log_anomaly_detector_z_score():
    detector = LogAnomalyDetector(z_score_threshold=2.5)

    # Establish baseline: 10 errors per minute
    detector.evaluate_error_frequency(10)
    detector.evaluate_error_frequency(10)
    detector.evaluate_error_frequency(10)

    # Sudden burst: 50 errors (should trigger anomaly)
    res = detector.evaluate_error_frequency(50)
    assert res["is_anomalous"] is True
    assert res["z_score"] > 2.5
    assert res["severity"] in ["CRITICAL", "HIGH"]


def test_shannon_entropy_calculation():
    # Identical messages -> 0 entropy
    single_err = ["ConnectionTimeout"] * 20
    ent_single = LogAnomalyDetector.calculate_shannon_entropy(single_err)
    assert ent_single == 0.0

    # Diverse messages -> higher entropy
    diverse_errs = ["ErrA", "ErrB", "ErrC", "ErrD"] * 5
    ent_diverse = LogAnomalyDetector.calculate_shannon_entropy(diverse_errs)
    assert ent_diverse > 1.5
