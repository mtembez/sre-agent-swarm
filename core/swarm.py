"""SRE Swarm Orchestrator coordinating multi-agent DAG execution."""

import logging
from typing import Dict
from agents.commander_agent import CommanderAgent
from agents.log_agent import LogForensicsAgent
from agents.remediation_agent import SandboxRemediationAgent
from agents.root_cause_agent import RootCauseAgent
from agents.triage_agent import TriageAgent
from core.dag import WorkflowDAG
from core.events import EventBus
from core.models import Alert, IncidentState

logger = logging.getLogger(__name__)


class SRESwarmOrchestrator:
    """Orchestrates the lifecycle of an incident through the specialized SRE agent DAG."""

    def __init__(self):
        self.triage_agent = TriageAgent()
        self.log_agent = LogForensicsAgent()
        self.root_cause_agent = RootCauseAgent()
        self.remediation_agent = SandboxRemediationAgent()
        self.commander_agent = CommanderAgent()
        self.event_bus = EventBus.get_instance()
        self.active_incidents: Dict[str, IncidentState] = {}

    def build_dag(self) -> WorkflowDAG:
        """Construct the dependency DAG between the specialized agents."""
        dag = WorkflowDAG()

        # Step 1: Triage
        dag.add_node("triage", lambda state: self.triage_agent.run(state))

        # Step 2: Log Forensics (depends on Triage)
        dag.add_node("log_forensics", lambda state: self.log_agent.run(state), depends_on=["triage"])

        # Step 3: Root Cause Analysis (depends on Log Forensics)
        dag.add_node("root_cause", lambda state: self.root_cause_agent.run(state), depends_on=["log_forensics"])

        # Step 4: Remediation (depends on Root Cause)
        dag.add_node("remediation", lambda state: self.remediation_agent.run(state), depends_on=["root_cause"])

        # Step 5: Verification & Post-Mortem (depends on Remediation)
        dag.add_node("commander", lambda state: self.commander_agent.run(state), depends_on=["remediation"])

        return dag

    async def handle_alert(self, alert: Alert) -> IncidentState:
        """Trigger the autonomous swarm workflow for an incoming alert."""
        state = IncidentState(alert=alert)
        self.active_incidents[state.incident_id] = state

        logger.info("Dispatched SRE Swarm for incident %s (%s)", state.incident_id, alert.title)
        await self.event_bus.emit(
            "incident_started",
            {
                "incident_id": state.incident_id,
                "title": alert.title,
                "service": alert.service,
                "severity": alert.severity.value,
            },
        )

        dag = self.build_dag()
        await dag.execute(state)

        await self.event_bus.emit(
            "incident_completed",
            {
                "incident_id": state.incident_id,
                "status": state.status.value,
                "remediation": state.remediation_action_taken,
                "postmortem_ready": bool(state.postmortem_markdown),
            },
        )

        return state

    def get_incident(self, incident_id: str) -> IncidentState:
        return self.active_incidents.get(incident_id)
