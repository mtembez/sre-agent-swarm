"""Data models for chaos engineering experiments and fault injection drills."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field


class ChaosType(str, Enum):
    DB_POOL_STARVATION = "db_pool_starvation"
    MEMORY_LEAK = "memory_leak"
    NETWORK_LATENCY = "network_latency"
    CASCADING_503 = "cascading_503"
    DISK_PRESSURE = "disk_pressure"


class ChaosStatus(str, Enum):
    IDLE = "IDLE"
    INJECTED = "INJECTED"
    TRIGGERED_ALERT = "TRIGGERED_ALERT"
    REMEDIATED = "REMEDIATED"
    REVERTED = "REVERTED"


class ChaosScenario(BaseModel):
    scenario_type: ChaosType
    target_service: str
    description: str
    fault_parameters: Dict[str, Any] = Field(default_factory=dict)
    synthetic_logs: str = ""
    error_signature: str = ""


class ChaosDrillRecord(BaseModel):
    drill_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario: ChaosScenario
    status: ChaosStatus = ChaosStatus.INJECTED
    injected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    incident_id: Optional[str] = None
    mttr_seconds: Optional[float] = None
