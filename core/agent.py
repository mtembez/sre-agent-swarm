"""Autonomous Agent base class implementing ReAct reasoning state machine."""

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional
from core.events import EventBus
from core.models import (
    AgentThoughtTrace,
    IncidentState,
    ToolCall,
    ToolResult,
)

logger = logging.getLogger(__name__)


class BaseAgent:
    """Foundational agent class supporting ReAct loops, tool execution, and circuit breakers."""

    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        tools: Optional[Dict[str, Callable[..., Coroutine]]] = None,
        max_steps: int = 5,
    ):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.tools: Dict[str, Callable[..., Coroutine]] = tools or {}
        self.max_steps = max_steps
        self.event_bus = EventBus.get_instance()

    def register_tool(self, tool_name: str, tool_func: Callable[..., Coroutine]):
        """Register an async tool executable by this agent."""
        self.tools[tool_name] = tool_func

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a tool with deterministic error capture and execution timing."""
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{tool_name}' is not registered with agent '{self.name}'.",
                duration_ms=0.0,
            )

        t_start = time.perf_counter()
        try:
            tool_func = self.tools[tool_name]
            output = await tool_func(**arguments)
            duration = (time.perf_counter() - t_start) * 1000.0
            return ToolResult(
                success=True,
                output=str(output),
                error=None,
                duration_ms=round(duration, 2),
            )
        except Exception as exc:
            duration = (time.perf_counter() - t_start) * 1000.0
            logger.error("Agent '%s' tool execution failed for '%s': %s", self.name, tool_name, exc)
            return ToolResult(
                success=False,
                output="",
                error=str(exc),
                duration_ms=round(duration, 2),
            )

    async def record_step(
        self,
        state: IncidentState,
        step: int,
        thought: str,
        tool_call: Optional[ToolCall] = None,
        tool_result: Optional[ToolResult] = None,
    ) -> AgentThoughtTrace:
        """Record thought and tool interaction into state and emit to event stream."""
        trace = AgentThoughtTrace(
            agent_name=self.name,
            step=step,
            thought=thought,
            tool_call=tool_call,
            tool_result=tool_result,
        )
        state.thought_traces.append(trace)

        # Broadcast via EventBus
        await self.event_bus.emit(
            "agent_thought",
            {
                "incident_id": state.incident_id,
                "agent": self.name,
                "step": step,
                "thought": thought,
                "tool": tool_call.model_dump() if tool_call else None,
                "result": tool_result.model_dump() if tool_result else None,
            },
        )
        return trace

    async def run(self, state: IncidentState) -> IncidentState:
        """Execute the agent's role-specific logic. Overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement run(state)")
