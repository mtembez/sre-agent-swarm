import pytest
import sys
from starlette.testclient import TestClient
import cli
from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_metrics_endpoint(client):
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "# HELP http_requests_total" in res.text
    assert "http_request_latency_p95_ms" in res.text


def test_api_playbooks_endpoint(client):
    res = client.get("/api/v1/playbooks")
    assert res.status_code == 200
    pbs = res.json()
    assert isinstance(pbs, list)
    assert len(pbs) >= 4
    pb_ids = [p["playbook_id"] for p in pbs]
    assert "PB-001" in pb_ids
    assert "PB-002" in pb_ids


def test_api_chaos_endpoints(client):
    # Inject chaos
    payload = {"chaos_type": "db_pool_starvation"}
    inject_res = client.post("/api/v1/chaos/inject", json=payload)
    assert inject_res.status_code == 200
    drill = inject_res.json()
    assert "drill_id" in drill
    assert drill["status"] in ["REMEDIATED", "ACTIVE", "TRIGGERED"]

    # Invalid chaos type
    invalid_res = client.post("/api/v1/chaos/inject", json={"chaos_type": "quantum_collapse"})
    assert invalid_res.status_code == 400
    assert "Invalid chaos type" in invalid_res.json()["error"]

    # Invalid JSON
    bad_json = client.post("/api/v1/chaos/inject", content="invalid json", headers={"Content-Type": "application/json"})
    assert bad_json.status_code == 400

    # List chaos drills
    list_res = client.get("/api/v1/chaos/drills")
    assert list_res.status_code == 200
    drills = list_res.json()
    assert isinstance(drills, list)
    assert len(drills) >= 1
    assert any(d["drill_id"] == drill["drill_id"] for d in drills)


def test_api_edge_cases(client):
    # Nonexistent incident detail
    res_404 = client.get("/api/v1/incidents/nonexistent-id")
    assert res_404.status_code == 404

    # Nonexistent incident postmortem
    pm_404 = client.get("/api/v1/incidents/nonexistent-id/postmortem")
    assert pm_404.status_code == 404

    # Bad JSON to alert ingestion
    bad_alert = client.post("/api/v1/alerts", content="not json", headers={"Content-Type": "application/json"})
    assert bad_alert.status_code == 400


def test_cli_playbooks(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["cli.py", "playbooks"])
    cli.main()
    captured = capsys.readouterr()
    assert "SRE PLAYBOOK REGISTRY" in captured.out
    assert "PB-001" in captured.out


def test_cli_metrics(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["cli.py", "metrics"])
    cli.main()
    captured = capsys.readouterr()
    assert "http_requests_total" in captured.out
    assert "http_request_latency_p95_ms" in captured.out


def test_cli_chaos_list(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["cli.py", "chaos", "list"])
    cli.main()
    captured = capsys.readouterr()
    assert "Available Chaos Scenarios:" in captured.out
    assert "db_pool_starvation" in captured.out


def test_cli_chaos_inject(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["cli.py", "chaos", "inject", "--type", "memory_leak"])
    cli.main()
    captured = capsys.readouterr()
    assert "[CHAOS RESULT]" in captured.out
    assert "Drill ID" in captured.out


def test_cli_trigger(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cli.py",
            "trigger",
            "--service",
            "auth-service",
            "--error",
            "Deadlock detected on auth_sessions table",
            "--title",
            "Auth Service Deadlock Outage",
            "--severity",
            "CRITICAL",
        ],
    )
    cli.main()
    captured = capsys.readouterr()
    assert "INCIDENT RESOLUTION SUMMARY:" in captured.out
    assert "auth-service" in captured.out
    assert "Remediation Success : True" in captured.out


def test_cli_no_args_prints_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["cli.py"])
    cli.main()
    captured = capsys.readouterr()
    assert "usage:" in captured.out or "SRE Sentinel CLI" in captured.out
