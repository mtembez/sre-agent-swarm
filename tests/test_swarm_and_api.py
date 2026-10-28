import pytest
from starlette.testclient import TestClient
from api.main import app, orchestrator
from core.models import Alert, AlertSeverity
from core.swarm import SRESwarmOrchestrator


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_full_swarm_orchestration_lifecycle():
    orch = SRESwarmOrchestrator()
    alert = Alert(
        title="Production OOM Killer Invoked",
        service="worker-service",
        severity=AlertSeverity.CRITICAL,
        error_message="OOMKilled: process terminated by cgroup controller",
        raw_payload={"deployed_commit": "c4d5e6f"},
    )
    state = await orch.handle_alert(alert)

    assert state.status.value in ["RESOLVED", "VERIFIED"]
    assert state.remediation_success is True
    assert state.verification_passed is True
    assert state.root_cause is not None
    assert "c4d5e6f" in state.suspect_commit
    assert len(state.timeline) >= 5
    assert len(state.thought_traces) >= 5
    assert state.postmortem_markdown is not None
    assert "Incident Post-Mortem: Production OOM Killer Invoked" in state.postmortem_markdown


def test_api_probes_and_alert_ingestion(test_client):
    # Health checks
    live_res = test_client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "UP"

    ready_res = test_client.get("/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "READY"

    # Ingest Alert
    payload = {
        "title": "API Gateway Latency Spike",
        "service": "api-gateway",
        "severity": "CRITICAL",
        "error_message": "PoolExhaustedError: active db connections maxed out",
        "deployed_commit": "b8a9c0d",
        "logs": "2026-10-28 07:45:00 ERROR [gateway] PoolExhaustedError: active db connections maxed out\n",
    }
    ingest_res = test_client.post("/api/v1/alerts", json=payload)
    assert ingest_res.status_code == 200
    data = ingest_res.json()
    assert "incident_id" in data
    assert data["status"] == "RESOLVED"
    assert data["remediation_success"] is True

    inc_id = data["incident_id"]

    # List incidents
    list_res = test_client.get("/api/v1/incidents")
    assert list_res.status_code == 200
    assert any(i["incident_id"] == inc_id for i in list_res.json())

    # Get incident detail
    detail_res = test_client.get(f"/api/v1/incidents/{inc_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["incident_id"] == inc_id

    # Get postmortem
    pm_res = test_client.get(f"/api/v1/incidents/{inc_id}/postmortem")
    assert pm_res.status_code == 200
    assert "postmortem_markdown" in pm_res.json()
    assert "Incident Post-Mortem" in pm_res.json()["postmortem_markdown"]

    # 404 on nonexistent incident
    err_res = test_client.get("/api/v1/incidents/nonexistent-id-000")
    assert err_res.status_code == 404

    # 400 on malformed json
    bad_res = test_client.post("/api/v1/alerts", content="not-json", headers={"Content-Type": "application/json"})
    assert bad_res.status_code == 400


def test_api_websocket_stream_ping(test_client):
    with test_client.websocket_connect("/ws/stream") as websocket:
        websocket.send_text("ping")
        received = []
        for _ in range(25):
            msg = websocket.receive_text()
            received.append(msg)
            if msg == "pong":
                break
        assert "pong" in received
