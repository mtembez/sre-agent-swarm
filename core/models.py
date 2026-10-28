"""Data models and state definitions for SRE multi-agent swarm."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IncidentStatus(str, Enum):
    INGESTED = "INGESTED"
    TRIAGED = "TRIAGED"
    INVESTIGATING = "INVESTIGATING"
    REMEDIATING = "REMEDIATING"
    VERIFIED = "VERIFIED"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class Alert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    service: str
    severity: AlertSeverity = AlertSeverity.HIGH
    error_message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    duration_ms: float = 0.0


class AgentThoughtTrace(BaseModel):
    agent_name: str
    step: int
    thought: str
    tool_call: Optional[ToolCall] = None
    tool_result: Optional[ToolResult] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IncidentTimelineEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent: str
    event_type: str
    description: str


class IncidentState(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    alert: Alert
    status: IncidentStatus = IncidentStatus.INGESTED
    blast_radius: Dict[str, Any] = Field(default_factory=dict)
    log_findings: List[Dict[str, Any]] = Field(default_factory=list)
    root_cause: Optional[str] = None
    suspect_commit: Optional[str] = None
    remediation_action_taken: Optional[str] = None
    remediation_success: bool = False
    verification_passed: bool = False
    timeline: List[IncidentTimelineEvent] = Field(default_factory=list)
    thought_traces: List[AgentThoughtTrace] = Field(default_factory=list)
    postmortem_markdown: Optional[str] = None

    def add_timeline(self, agent: str, event_type: str, description: str):
        self.timeline.append(
            IncidentTimelineEvent(
                agent=agent,
                event_type=event_type,
                description=description,
            )
        )
