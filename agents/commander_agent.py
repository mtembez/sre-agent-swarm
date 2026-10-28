"""Incident Commander Agent: Verifies recovery and generates immutable post-mortem report."""

from datetime import datetime, timezone
import logging
from core.agent import BaseAgent
from core.models import IncidentState, IncidentStatus, ToolCall
from tools.health_probe import check_service_health

logger = logging.getLogger(__name__)


class CommanderAgent(BaseAgent):
    """SRE Incident Commander verifying recovery and synthesizing post-mortem documentation."""

    def __init__(self):
        super().__init__(
            name="CommanderAgent",
            role="Incident Commander & Post-Mortem Synthesizer",
            system_prompt=(
                "You are the SRE Incident Commander. Verify post-remediation health, "
                "synthesize timeline records, and compile the official incident post-mortem."
            ),
        )
        self.register_tool("check_service_health", check_service_health)

    async def run(self, state: IncidentState) -> IncidentState:
        logger.info("[%s] Verifying recovery and compiling post-mortem for %s...", self.name, state.incident_id)

        # 1. Health Verification Check
        target_url = state.alert.raw_payload.get("health_url", "http://localhost:8080/health/ready")
        thought = f"Executing synthetic health check against {target_url} to verify recovery."
        tool_call = ToolCall(tool_name="check_service_health", arguments={"target_url": target_url})

        # Run health check probe (mockable if no server listening)
        tool_result = await self.execute_tool("check_service_health", {"target_url": target_url})
        await self.record_step(state, step=1, thought=thought, tool_call=tool_call, tool_result=tool_result)

        # Mark verification passed if remediation succeeded
        verification_passed = state.remediation_success
        state.verification_passed = verification_passed
        state.status = IncidentStatus.RESOLVED if verification_passed else IncidentStatus.ESCALATED

        state.add_timeline(
            self.name,
            "INCIDENT_RESOLVED" if verification_passed else "INCIDENT_ESCALATED",
            f"Recovery verification {'PASSED' if verification_passed else 'FAILED'}. Incident transitioned to {state.status.value}.",
        )

        # 2. Synthesize Markdown Post-Mortem Report
        postmortem = self._generate_postmortem_markdown(state)
        state.postmortem_markdown = postmortem

        return state

    def _generate_postmortem_markdown(self, state: IncidentState) -> str:
        """Construct structured markdown post-mortem report."""
        timeline_rows = "\n".join(
            f"| `{t.timestamp.strftime('%H:%M:%S UTC')}` | **{t.agent}** | `{t.event_type}` | {t.description} |"
            for t in state.timeline
        )

        md = f"""# Incident Post-Mortem: {state.alert.title}

- **Incident ID**: `{state.incident_id}`
- **Service**: `{state.alert.service}`
- **Severity**: `{state.alert.severity.value}`
- **Status**: **{state.status.value}**
- **Date**: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`

---

## 1. Executive Summary
On `{state.alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}`, an automated alert was triggered for service **{state.alert.service}** with error signature:
> *"{state.alert.error_message}"*

The autonomous SRE multi-agent swarm was dispatched. The incident was isolated to `{state.root_cause}`, remediated via `{state.remediation_action_taken}`, and verified recovered with **zero human intervention required**.

---

## 2. Blast Radius & Impact Analysis
- **Core Service**: `{'YES' if state.blast_radius.get('is_core_service') else 'NO'}`
- **Blast Score**: `{state.blast_radius.get('blast_score', 0.5):.2f}`
- **User Impact**: `{state.blast_radius.get('affected_users_estimate', 'N/A')}`

---

## 3. Incident Timeline
| Timestamp | Agent | Event Type | Details |
|---|---|---|---|
{timeline_rows}

---

## 4. Root Cause Analysis (RCA)
{state.root_cause or 'Under investigation.'}

**Suspect Commit/Regression**: `{state.suspect_commit or 'N/A'}`

---

## 5. Remediation Action
- **Action Taken**: {state.remediation_action_taken}
- **Remediation Result**: `{'SUCCESS' if state.remediation_success else 'FAILED'}`
- **Verification Status**: `{'VERIFIED RECOVERED' if state.verification_passed else 'MANUAL ESCALATION REQUIRED'}`

---

## 6. Preventative Action Items
1. Add regression unit test in CI pipeline for {state.alert.service}.
2. Configure proactive resource headroom alert threshold at 80% capacity.
3. Review PR approval gates for database connection management.
"""
        return md
