"""Chaos Engineering Fault Injection Engine."""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Dict, List, Optional
from chaos.models import (
    ChaosDrillRecord,
    ChaosScenario,
    ChaosStatus,
    ChaosType,
)
from core.models import Alert, AlertSeverity
from core.swarm import SRESwarmOrchestrator

logger = logging.getLogger(__name__)

SCENARIO_CATALOG: Dict[ChaosType, ChaosScenario] = {
    ChaosType.DB_POOL_STARVATION: ChaosScenario(
        scenario_type=ChaosType.DB_POOL_STARVATION,
        target_service="payment-gateway",
        description="Simulates 100% active connection saturation on PostgreSQL primary pool.",
        fault_parameters={"max_connections": 50, "leak_rate_per_sec": 12},
        error_signature="PoolExhaustedError: active db connections maxed out (50/50)",
        synthetic_logs=(
            "2026-10-28 07:30:10 WARN [pool-monitor] Active connections: 45/50\n"
            "2026-10-28 07:30:12 ERROR [payment-gw] PoolExhaustedError: active db connections maxed out (50/50)\n"
            "Traceback (most recent call last):\n"
            "  File \"checkout/transact.py\", line 84, in acquire_handle\n"
            "    raise PoolExhaustedError('Database connection pool exhausted')\n"
        ),
    ),
    ChaosType.MEMORY_LEAK: ChaosScenario(
        scenario_type=ChaosType.MEMORY_LEAK,
        target_service="auth-service",
        description="Simulates unbounded in-memory session cache expansion triggering Linux cgroup OOM kill.",
        fault_parameters={"growth_rate_mb_per_sec": 128, "cgroup_limit_mb": 2048},
        error_signature="OOMKilled: process terminated by linux cgroup memory controller",
        synthetic_logs=(
            "2026-10-28 07:35:00 WARN [cgroup] Resident memory at 97.8% of limit (1.95GiB / 2.0GiB)\n"
            "2026-10-28 07:35:04 ERROR [kernel] oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null)\n"
            "2026-10-28 07:35:05 ERROR [cgroup] Killed process 14092 (python3 auth/main.py) anon-rss:2096000kB\n"
        ),
    ),
    ChaosType.CASCADING_503: ChaosScenario(
        scenario_type=ChaosType.CASCADING_503,
        target_service="api-gateway",
        description="Simulates upstream downstream timeout cascade and 502 Bad Gateway storm.",
        fault_parameters={"timeout_ms": 5000, "error_rate": 0.85},
        error_signature="502 Bad Gateway: Upstream prematurely closed connection",
        synthetic_logs=(
            "2026-10-28 07:40:11 ERROR [nginx] *40212 connect() failed (111: Connection refused)\n"
            "2026-10-28 07:40:12 WARN [gateway] 502 Bad Gateway returned to client 192.168.1.15\n"
        ),
    ),
    ChaosType.DISK_PRESSURE: ChaosScenario(
        scenario_type=ChaosType.DISK_PRESSURE,
        target_service="analytics-worker",
        description="Simulates /var/log volume saturation exceeding 99% disk capacity.",
        fault_parameters={"available_space_mb": 5, "mount_point": "/var/log"},
        error_signature="No space left on device: write error on wal_segment",
        synthetic_logs=(
            "2026-10-28 07:45:00 ERROR [worker] IOError: [Errno 28] No space left on device\n"
            "2026-10-28 07:45:01 CRITICAL [worker] Failed to flush WAL buffer to persistent disk\n"
        ),
    ),
    ChaosType.NETWORK_LATENCY: ChaosScenario(
        scenario_type=ChaosType.NETWORK_LATENCY,
        target_service="inventory-service",
        description="Simulates 1200ms synthetic cross-region latency spike and packet drop.",
        fault_parameters={"added_delay_ms": 1200, "packet_drop_pct": 5},
        error_signature="ConnectionTimeout: request timed out after 1000ms",
        synthetic_logs=(
            "2026-10-28 07:50:01 WARN [http-client] Request duration exceeded P99 bound: 1420ms\n"
            "2026-10-28 07:50:02 ERROR [http-client] ConnectionTimeout: read timed out after 1000ms\n"
        ),
    ),
}


class ChaosInjector:
    """Orchestrates chaos drills, monitors Swarm auto-remediation, and computes MTTR metrics."""

    def __init__(self, orchestrator: SRESwarmOrchestrator = None):
        self.orchestrator = orchestrator or SRESwarmOrchestrator()
        self.active_drills: Dict[str, ChaosDrillRecord] = {}

    async def inject_fault(self, chaos_type: ChaosType) -> ChaosDrillRecord:
        """Inject simulated production fault and trigger autonomous SRE Swarm."""
        scenario = SCENARIO_CATALOG.get(chaos_type)
        if not scenario:
            raise ValueError(f"Unknown chaos scenario: {chaos_type}")

        drill = ChaosDrillRecord(scenario=scenario)
        self.active_drills[drill.drill_id] = drill
        logger.info("[CHAOS] Injected fault '%s' on target '%s' (Drill ID: %s)", chaos_type.value, scenario.target_service, drill.drill_id)

        t_start = time.perf_counter()

        # Construct alert corresponding to the chaos injection
        alert = Alert(
            title=f"Chaos Drill: {scenario.scenario_type.value.replace('_', ' ').title()}",
            service=scenario.target_service,
            severity=AlertSeverity.CRITICAL if "pool" in scenario.scenario_type or "oom" in scenario.scenario_type else AlertSeverity.HIGH,
            error_message=scenario.error_signature,
            raw_payload={
                "logs": scenario.synthetic_logs,
                "deployed_commit": "chaos-drill-tag",
                "fault_parameters": scenario.fault_parameters,
            },
        )

        drill.status = ChaosStatus.TRIGGERED_ALERT

        # Dispatch the swarm
        state = await self.orchestrator.handle_alert(alert)

        duration = time.perf_counter() - t_start
        drill.incident_id = state.incident_id
        drill.resolved_at = datetime.now(timezone.utc)
        drill.mttr_seconds = round(duration, 2)
        drill.status = ChaosStatus.REMEDIATED if state.remediation_success else ChaosStatus.TRIGGERED_ALERT

        logger.info("[CHAOS] Drill %s completed in %.2fs. Swarm status: %s", drill.drill_id, duration, state.status.value)
        return drill

    def get_drill(self, drill_id: str) -> Optional[ChaosDrillRecord]:
        return self.active_drills.get(drill_id)

    def list_drills(self) -> List[ChaosDrillRecord]:
        return list(self.active_drills.values())
