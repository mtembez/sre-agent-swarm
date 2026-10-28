"""Log Forensics Agent: Scans log streams and classifies error stack traces."""

import logging
from core.agent import BaseAgent
from core.models import IncidentState, IncidentStatus, ToolCall
from tools.log_search import search_log_signatures

logger = logging.getLogger(__name__)


class LogForensicsAgent(BaseAgent):
    """SRE agent responsible for deep log forensics and stack trace signature classification."""

    def __init__(self):
        super().__init__(
            name="LogForensicsAgent",
            role="Distributed Log & Trace Investigator",
            system_prompt=(
                "You are an SRE Log Forensics Investigator. Parse application and system logs, "
                "identify fatal exceptions, trace call stacks, and isolate recurring error patterns."
            ),
        )
        self.register_tool("search_log_signatures", search_log_signatures)

    async def run(self, state: IncidentState) -> IncidentState:
        logger.info("[%s] Investigating logs for incident %s...", self.name, state.incident_id)

        # Retrieve log sample from alert raw payload or construct simulated stream
        logs_text = state.alert.raw_payload.get("logs") or (
            f"2026-10-28T07:30:10.123Z INFO [main] Server initialized.\n"
            f"2026-10-28T07:31:45.981Z WARN [worker-3] High connection pool latency: 2450ms\n"
            f"2026-10-28T07:32:00.012Z ERROR [worker-3] {state.alert.error_message}\n"
            f"Traceback (most recent call last):\n"
            f"  File \"app/database/pool.py\", line 84, in acquire\n"
            f"    raise PoolExhaustedError(\"Active connections exceeded limit 50/50\")\n"
            f"PoolExhaustedError: Active connections exceeded limit 50/50\n"
        )

        thought = f"Analyzing log buffer ({len(logs_text)} bytes) to extract fault signatures."
        tool_call = ToolCall(tool_name="search_log_signatures", arguments={"logs_text": logs_text})

        tool_result = await self.execute_tool("search_log_signatures", {"logs_text": logs_text})
        await self.record_step(state, step=1, thought=thought, tool_call=tool_call, tool_result=tool_result)

        findings = []
        if tool_result.success:
            import json
            import ast
            try:
                # Parse result
                findings = ast.literal_eval(tool_result.output) if isinstance(tool_result.output, str) else tool_result.output
            except Exception:
                findings = [{"fault_type": "generic_error", "matched_text": state.alert.error_message}]

        state.log_findings = findings
        state.status = IncidentStatus.INVESTIGATING
        state.add_timeline(
            self.name,
            "LOG_FORENSICS_COMPLETE",
            f"Identified {len(findings)} fault signature matches in application logs.",
        )
        return state
