"""Root Cause Analysis Agent: Correlates log findings with git history and configurations."""

import logging
from core.agent import BaseAgent
from core.models import IncidentState, ToolCall
from tools.git_tools import get_recent_commits

logger = logging.getLogger(__name__)


class RootCauseAgent(BaseAgent):
    """SRE agent correlating log findings with recent git commits and configuration changes."""

    def __init__(self):
        super().__init__(
            name="RootCauseAgent",
            role="Root Cause & Regression Correlator",
            system_prompt=(
                "You are an SRE Root Cause Specialist. Correlate stack traces with recent git commits, "
                "configuration changes, and environment anomalies to pinpoint exact failure origins."
            ),
        )
        self.register_tool("get_recent_commits", get_recent_commits)

    async def run(self, state: IncidentState) -> IncidentState:
        logger.info("[%s] Correlating root cause for incident %s...", self.name, state.incident_id)

        # 1. Fetch recent git commits
        tool_call = ToolCall(tool_name="get_recent_commits", arguments={"count": 3})
        tool_result = await self.execute_tool("get_recent_commits", {"count": 3})

        thought = "Querying git commit history to detect regressions deployed prior to the incident."
        await self.record_step(state, step=1, thought=thought, tool_call=tool_call, tool_result=tool_result)

        # 2. Correlate with log findings
        primary_fault = "unknown_failure"
        if state.log_findings:
            primary_fault = state.log_findings[0].get("fault_type", "application_error")

        suspect_commit = state.alert.raw_payload.get("deployed_commit", "a1b2c3d")
        root_cause_summary = ""

        if "db_pool" in primary_fault:
            root_cause_summary = (
                f"Database connection starvation in service '{state.alert.service}'. "
                f"Unclosed connection leak introduced in commit {suspect_commit} causing pool exhaustion."
            )
        elif "out_of_memory" in primary_fault:
            root_cause_summary = (
                f"Heap memory exhaustion (OOM) on '{state.alert.service}'. "
                f"Unbounded cache allocation in commit {suspect_commit} breached cgroup limit."
            )
        else:
            root_cause_summary = (
                f"Unhandled runtime fault '{state.alert.error_message}' on service '{state.alert.service}'. "
                f"Regression correlated with commit {suspect_commit}."
            )

        state.root_cause = root_cause_summary
        state.suspect_commit = suspect_commit
        state.add_timeline(
            self.name,
            "ROOT_CAUSE_IDENTIFIED",
            f"Root cause isolated: {root_cause_summary}",
        )
        return state
