"""Triage Agent: Analyzes alert severity, service topology, and blast radius."""

import logging
from core.agent import BaseAgent
from core.models import AlertSeverity, IncidentState, IncidentStatus

logger = logging.getLogger(__name__)


class TriageAgent(BaseAgent):
    """SRE agent responsible for initial alert ingestion, classification, and blast radius scoring."""

    def __init__(self):
        super().__init__(
            name="TriageAgent",
            role="Incident Classifier & Blast Radius Analyst",
            system_prompt=(
                "You are an SRE Triage Specialist. Classify incoming incident telemetry, "
                "determine service dependencies, and evaluate potential user impact."
            ),
        )

    async def run(self, state: IncidentState) -> IncidentState:
        logger.info("[%s] Triaging incident %s for service '%s'...", self.name, state.incident_id, state.alert.service)

        # 1. Evaluate Alert Severity & Blast Radius
        service = state.alert.service.lower()
        error_msg = state.alert.error_message.lower()

        # Critical services define core infrastructure
        critical_services = ["payment-gateway", "auth-service", "database-primary", "api-gateway"]
        is_core_service = any(cs in service for cs in critical_services)

        blast_score = 0.85 if is_core_service else 0.45
        affected_users_est = "HIGH (>10,000 req/min)" if is_core_service else "MODERATE (<1,000 req/min)"

        if "oom" in error_msg or "deadlock" in error_msg or "panic" in error_msg:
            severity = AlertSeverity.CRITICAL
            blast_score = min(1.0, blast_score + 0.15)
        else:
            severity = state.alert.severity

        blast_radius = {
            "is_core_service": is_core_service,
            "blast_score": blast_score,
            "affected_users_estimate": affected_users_est,
            "downstream_dependencies": ["frontend-gateway", "analytics-worker"] if is_core_service else [],
        }

        thought_text = (
            f"Alert evaluated: Service '{state.alert.service}' classified as {severity.value}. "
            f"Blast radius score: {blast_score:.2f} ({affected_users_est}). Downstream impact assessed."
        )

        await self.record_step(state, step=1, thought=thought_text)

        state.blast_radius = blast_radius
        state.status = IncidentStatus.TRIAGED
        state.add_timeline(self.name, "TRIAGE_COMPLETE", f"Incident classified as {severity.value} on {state.alert.service}")

        return state
