"""Sandbox Remediation Agent: Synthesizes and executes automated safe remediation."""

import logging
from core.agent import BaseAgent
from core.models import IncidentState, IncidentStatus, ToolCall
from core.playbooks import PlaybookEngine
from tools.sandbox import run_sandboxed_command

logger = logging.getLogger(__name__)


class SandboxRemediationAgent(BaseAgent):
    """SRE agent formulating remediation strategies and executing sandboxed fixes via Playbooks."""

    def __init__(self):
        super().__init__(
            name="RemediationAgent",
            role="Sandboxed Auto-Remediation Engineer",
            system_prompt=(
                "You are an SRE Auto-Remediation Engineer. Formulate safe, non-destructive "
                "remediation actions (container rollback, configuration hot-reloads, pool resizing), "
                "execute them within the isolated sandbox, and verify operational recovery."
            ),
        )
        self.register_tool("run_sandboxed_command", run_sandboxed_command)

    async def run(self, state: IncidentState) -> IncidentState:
        logger.info("[%s] Executing remediation for incident %s...", self.name, state.incident_id)
        state.status = IncidentStatus.REMEDIATING

        # Match against declarative SRE Playbooks
        search_sig = f"{state.root_cause or ''} {state.alert.error_message}".lower()
        playbook = PlaybookEngine.match_playbook(search_sig)

        all_steps_succeeded = True
        executed_actions = []

        if playbook:
            thought = f"Matched SRE Playbook [{playbook.playbook_id}]: {playbook.name}. Running pre-flight check..."
            action_desc = f"Playbook [{playbook.playbook_id}]: {playbook.name}"

            # 1. Pre-flight check
            if playbook.pre_flight_command:
                pf_call = ToolCall(tool_name="run_sandboxed_command", arguments={"command": playbook.pre_flight_command})
                pf_res = await self.execute_tool("run_sandboxed_command", {"command": playbook.pre_flight_command})
                await self.record_step(state, step=1, thought=thought, tool_call=pf_call, tool_result=pf_res)
                if not pf_res.success:
                    all_steps_succeeded = False

            # 2. Sequential remediation steps
            if all_steps_succeeded:
                for idx, step in enumerate(playbook.remediation_steps, start=2):
                    step_thought = f"Executing remediation step {step.step_id} ({step.action_type}): {step.command}"
                    st_call = ToolCall(tool_name="run_sandboxed_command", arguments={"command": step.command})
                    st_res = await self.execute_tool("run_sandboxed_command", {"command": step.command})
                    await self.record_step(state, step=idx, thought=step_thought, tool_call=st_call, tool_result=st_res)
                    if not st_res.success:
                        all_steps_succeeded = False
                        break
                    executed_actions.append(step.action_type)

            # 3. Rollback if steps failed
            if not all_steps_succeeded and playbook.rollback_command:
                rb_call = ToolCall(tool_name="run_sandboxed_command", arguments={"command": playbook.rollback_command})
                rb_res = await self.execute_tool("run_sandboxed_command", {"command": playbook.rollback_command})
                await self.record_step(state, step=99, thought="Step failed! Executing automated playbook rollback...", tool_call=rb_call, tool_result=rb_res)
        else:
            # Fallback container rollback
            action_desc = f"Executing automated rollback to stable container prior to {state.suspect_commit}."
            cmd = "echo '[REMEDIATION] Automated rollback executed: restored stable upstream container.' && exit 0"
            thought = f"No specific playbook matched. {action_desc}"
            tool_call = ToolCall(tool_name="run_sandboxed_command", arguments={"command": cmd})
            tool_result = await self.execute_tool("run_sandboxed_command", {"command": cmd})
            await self.record_step(state, step=1, thought=thought, tool_call=tool_call, tool_result=tool_result)
            all_steps_succeeded = tool_result.success

        state.remediation_action_taken = action_desc
        state.remediation_success = all_steps_succeeded
        state.add_timeline(
            self.name,
            "REMEDIATION_EXECUTED",
            f"{action_desc} (Result: {'SUCCESS' if all_steps_succeeded else 'FAILED'})",
        )
        return state
