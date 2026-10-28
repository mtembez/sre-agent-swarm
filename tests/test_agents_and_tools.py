import pytest
from core.models import Alert, AlertSeverity, IncidentState
from agents.commander_agent import CommanderAgent
from agents.log_agent import LogForensicsAgent
from agents.remediation_agent import SandboxRemediationAgent
from agents.root_cause_agent import RootCauseAgent
from agents.triage_agent import TriageAgent
from tools.git_tools import get_recent_commits, inspect_commit_diff
from tools.health_probe import check_service_health
from tools.log_search import search_log_signatures
from tools.sandbox import run_sandboxed_command


@pytest.mark.asyncio
async def test_sandbox_command_execution():
    res = await run_sandboxed_command("echo 'SRE Sandbox Online'")
    assert res["exit_code"] == 0
    assert "SRE Sandbox Online" in res["stdout"]
    assert res["timed_out"] is False


@pytest.mark.asyncio
async def test_sandbox_command_security_rejection():
    with pytest.raises(PermissionError):
        await run_sandboxed_command("rm -rf / --no-preserve-root")


@pytest.mark.asyncio
async def test_sandbox_timeout():
    res = await run_sandboxed_command("sleep 5", timeout_seconds=0.3)
    assert res["timed_out"] is True
    assert res["exit_code"] == -1


@pytest.mark.asyncio
async def test_log_signature_search():
    sample_log = """
    2026-10-28T07:00:01Z [worker-1] INFO Job started
    2026-10-28T07:00:05Z [worker-1] ERROR java.lang.OutOfMemoryError: Java heap space
    2026-10-28T07:00:06Z [db-pool] ERROR PoolExhaustedError: too many connections
    """
    findings = await search_log_signatures(sample_log)
    assert len(findings) >= 2
    types = [f["fault_type"] for f in findings]
    assert "out_of_memory" in types
    assert "db_pool_exhausted" in types


@pytest.mark.asyncio
async def test_git_tools_execution():
    commits = await get_recent_commits(count=2)
    assert isinstance(commits, list)
    diff = await inspect_commit_diff(commit_sha="HEAD")
    assert isinstance(diff, str)


@pytest.mark.asyncio
async def test_triage_agent_scoring():
    alert = Alert(
        title="Payment Service Degradation",
        service="payment-gateway",
        severity=AlertSeverity.HIGH,
        error_message="Deadlock detected during concurrent checkout transactions",
    )
    state = IncidentState(alert=alert)
    agent = TriageAgent()
    updated_state = await agent.run(state)

    assert updated_state.blast_radius["is_core_service"] is True
    assert updated_state.blast_radius["blast_score"] >= 0.85
    assert len(updated_state.thought_traces) >= 1
    assert len(updated_state.timeline) >= 1


@pytest.mark.asyncio
async def test_remediation_and_commander_agents():
    alert = Alert(
        title="High Pool Latency",
        service="auth-service",
        severity=AlertSeverity.HIGH,
        error_message="DatabasePoolExhausted",
    )
    state = IncidentState(alert=alert)
    state.root_cause = "Database connection pool exhaustion"

    remediation_agent = SandboxRemediationAgent()
    state = await remediation_agent.run(state)
    assert state.remediation_success is True
    assert state.remediation_action_taken is not None

    commander_agent = CommanderAgent()
    state = await commander_agent.run(state)
    assert state.verification_passed is True
    assert state.postmortem_markdown is not None
    assert "Incident Post-Mortem" in state.postmortem_markdown


@pytest.mark.asyncio
async def test_base_agent_and_eventbus_edge_cases():
    from core.agent import BaseAgent
    from core.events import EventBus

    agent = BaseAgent(name="TestAgent", role="Tester", system_prompt="Test")
    with pytest.raises(NotImplementedError):
        await agent.run(None)

    # Tool not registered error
    res = await agent.execute_tool("nonexistent_tool", {})
    assert res.success is False
    assert "not registered" in res.error

    bus = EventBus.get_instance()
    received = []

    async def listener(evt):
        received.append(evt)

    bus.subscribe(listener)
    await bus.emit("test_event", {"msg": "hello"})
    assert len(received) == 1
    bus.unsubscribe(listener)
    bus.clear()
    assert len(bus.get_history()) == 0
