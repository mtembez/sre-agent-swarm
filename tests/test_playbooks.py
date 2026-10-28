import pytest
from core.models import Alert, AlertSeverity, IncidentState
from core.playbooks import PLAYBOOK_REGISTRY, PlaybookEngine
from agents.remediation_agent import SandboxRemediationAgent


def test_playbook_matching():
    # Test DB pool signature
    pb_db = PlaybookEngine.match_playbook("Error: PoolExhaustedError: active db connections maxed out")
    assert pb_db is not None
    assert pb_db.playbook_id == "PB-001"
    assert len(pb_db.remediation_steps) == 2

    # Test OOM signature
    pb_oom = PlaybookEngine.match_playbook("Kernel alert: OOMKilled cgroup process terminated")
    assert pb_oom is not None
    assert pb_oom.playbook_id == "PB-002"

    # Test 502 signature
    pb_502 = PlaybookEngine.match_playbook("Nginx reverse proxy: upstream prematurely closed 502")
    assert pb_502 is not None
    assert pb_502.playbook_id == "PB-003"

    # Test disk saturation signature
    pb_disk = PlaybookEngine.match_playbook("IOError: no space left on device")
    assert pb_disk is not None
    assert pb_disk.playbook_id == "PB-004"

    # Test unknown
    pb_none = PlaybookEngine.match_playbook("Completely unrelated string with no matching fault")
    assert pb_none is None


@pytest.mark.asyncio
async def test_remediation_agent_executes_matched_playbook():
    agent = SandboxRemediationAgent()
    alert = Alert(
        title="PostgreSQL Starvation",
        service="payment-gateway",
        severity=AlertSeverity.CRITICAL,
        error_message="PoolExhaustedError: too many connections",
    )
    state = IncidentState(alert=alert)
    state.root_cause = "Database connection pool exhausted"

    updated = await agent.run(state)
    assert updated.remediation_success is True
    assert "PB-001" in updated.remediation_action_taken
    assert len(updated.thought_traces) >= 2  # Pre-flight + steps
