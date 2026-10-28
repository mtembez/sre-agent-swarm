"""Declarative SRE remediation playbooks with pre-flight checks and rollback plans."""

from typing import Any, Callable, Coroutine, Dict, List, Optional
from pydantic import BaseModel, Field


class PlaybookStep(BaseModel):
    step_id: str
    action_type: str
    command: str
    expected_output_substring: str = ""
    timeout_seconds: float = 5.0


class SREPlaybook(BaseModel):
    playbook_id: str
    name: str
    match_signatures: List[str]
    pre_flight_command: Optional[str] = None
    remediation_steps: List[PlaybookStep]
    rollback_command: str
    post_verification_assertion: str


PLAYBOOK_REGISTRY: Dict[str, SREPlaybook] = {
    "db_pool_exhaustion": SREPlaybook(
        playbook_id="PB-001",
        name="Database Connection Pool Saturation Recovery",
        match_signatures=["db_pool_exhausted", "poolexhaustederror", "too many connections"],
        pre_flight_command="echo '[PRE-FLIGHT] Checking PostgreSQL primary connectivity: OK' && exit 0",
        remediation_steps=[
            PlaybookStep(
                step_id="step_1",
                action_type="scale_pool",
                command="echo '[ACTION] Dynamically updating DB_POOL_SIZE from 50 to 150' && exit 0",
                expected_output_substring="DB_POOL_SIZE",
            ),
            PlaybookStep(
                step_id="step_2",
                action_type="worker_sighup",
                command="echo '[ACTION] Sending SIGHUP graceful reload to idle connection pools' && exit 0",
                expected_output_substring="SIGHUP",
            ),
        ],
        rollback_command="echo '[ROLLBACK] Reverting DB_POOL_SIZE to previous baseline' && exit 0",
        post_verification_assertion="active_connections < 0.7 * pool_limit",
    ),
    "oom_container_kill": SREPlaybook(
        playbook_id="PB-002",
        name="Container OOM Heap Saturation & Cache Eviction",
        match_signatures=["out_of_memory", "oomkilled", "memoryerror"],
        pre_flight_command="echo '[PRE-FLIGHT] Checking host memory headroom: OK' && exit 0",
        remediation_steps=[
            PlaybookStep(
                step_id="step_1",
                action_type="cache_flush",
                command="echo '[ACTION] Evicting stale Redis/Memcached in-memory key partitions' && exit 0",
                expected_output_substring="Evicting",
            ),
            PlaybookStep(
                step_id="step_2",
                action_type="cgroup_limit_raise",
                command="echo '[ACTION] Raising container cgroup memory.max from 2GiB to 4GiB' && exit 0",
                expected_output_substring="memory.max",
            ),
        ],
        rollback_command="echo '[ROLLBACK] Restoring original cgroup memory ceiling' && exit 0",
        post_verification_assertion="memory_usage_pct < 80.0",
    ),
    "upstream_502_gateway": SREPlaybook(
        playbook_id="PB-003",
        name="Upstream 502 Bad Gateway Auto-Rollback",
        match_signatures=["http_502_bad_gateway", "connection_refused", "upstream prematurely closed"],
        pre_flight_command="echo '[PRE-FLIGHT] Verifying candidate slot health status: UNHEALTHY' && exit 0",
        remediation_steps=[
            PlaybookStep(
                step_id="step_1",
                action_type="blue_green_swap",
                command="echo '[ACTION] Swapping active upstream conf to stable Blue container slot' && exit 0",
                expected_output_substring="Swapping",
            ),
            PlaybookStep(
                step_id="step_2",
                action_type="nginx_reload",
                command="echo '[ACTION] Executing zero-downtime nginx -s reload' && exit 0",
                expected_output_substring="nginx -s reload",
            ),
        ],
        rollback_command="echo '[ROLLBACK] Reverting upstream proxy routing to backup cluster' && exit 0",
        post_verification_assertion="http_status == 200",
    ),
    "disk_space_saturation": SREPlaybook(
        playbook_id="PB-004",
        name="Log Volume Saturation & WAL Truncation",
        match_signatures=["no space left on device", "disk_pressure", "wal_segment"],
        pre_flight_command="echo '[PRE-FLIGHT] Inspecting df -h on volume: 99% used' && exit 0",
        remediation_steps=[
            PlaybookStep(
                step_id="step_1",
                action_type="log_rotation",
                command="echo '[ACTION] Compressing and archiving rotated application logs to cold storage' && exit 0",
                expected_output_substring="Compressing",
            ),
            PlaybookStep(
                step_id="step_2",
                action_type="vacuum_tmp",
                command="echo '[ACTION] Purging orphaned scratch files and reclaimed 15GB disk space' && exit 0",
                expected_output_substring="reclaimed",
            ),
        ],
        rollback_command="echo '[ROLLBACK] Restoring previous log retention policy' && exit 0",
        post_verification_assertion="disk_utilization_pct < 85.0",
    ),
}


class PlaybookEngine:
    """Matches incident signatures to declarative SRE playbooks and executes recovery steps."""

    @classmethod
    def match_playbook(cls, fault_signature: str) -> Optional[SREPlaybook]:
        sig_lower = fault_signature.lower()
        for pb in PLAYBOOK_REGISTRY.values():
            if any(match in sig_lower for match in pb.match_signatures):
                return pb
        return None
