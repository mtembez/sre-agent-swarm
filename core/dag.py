"""Directed Acyclic Graph (DAG) task scheduling engine for multi-agent workflows."""

import asyncio
from collections import defaultdict, deque
import logging
from typing import Any, Callable, Coroutine, Dict, List, Set

logger = logging.getLogger(__name__)


class CycleDetectedError(Exception):
    """Raised when circular dependencies are detected in the agent workflow DAG."""


class WorkflowNode:
    """Discrete task node in the multi-agent DAG."""

    def __init__(self, node_id: str, action: Callable[..., Coroutine], depends_on: List[str] = None):
        self.node_id = node_id
        self.action = action
        self.depends_on: Set[str] = set(depends_on or [])
        self.is_completed = False
        self.result: Any = None
        self.error: Exception = None


class WorkflowDAG:
    """Asynchronous Directed Acyclic Graph scheduler for coordinating agent executions."""

    def __init__(self):
        self.nodes: Dict[str, WorkflowNode] = {}
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.in_degree: Dict[str, int] = defaultdict(int)

    def add_node(self, node_id: str, action: Callable[..., Coroutine], depends_on: List[str] = None) -> "WorkflowDAG":
        """Register a node with its prerequisite upstream dependencies."""
        if node_id in self.nodes:
            raise ValueError(f"Node '{node_id}' already registered in DAG.")

        node = WorkflowNode(node_id, action, depends_on)
        self.nodes[node_id] = node

        for dep in node.depends_on:
            self.adjacency[dep].add(node_id)
            self.in_degree[node_id] += 1

        if node_id not in self.in_degree:
            self.in_degree[node_id] = 0

        return self

    def topological_sort(self) -> List[List[str]]:
        """Compute execution tiers using Kahn's algorithm with cycle detection."""
        in_deg = dict(self.in_degree)
        queue = deque([node_id for node_id, deg in in_deg.items() if deg == 0])
        levels: List[List[str]] = []
        visited_count = 0

        while queue:
            current_level = []
            for _ in range(len(queue)):
                curr = queue.popleft()
                current_level.append(curr)
                visited_count += 1

                for neighbor in self.adjacency[curr]:
                    in_deg[neighbor] -= 1
                    if in_deg[neighbor] == 0:
                        queue.append(neighbor)

            levels.append(current_level)

        if visited_count != len(self.nodes):
            unresolved = [k for k, v in in_deg.items() if v > 0]
            raise CycleDetectedError(f"Circular dependency detected in DAG involving nodes: {unresolved}")

        return levels

    async def execute(self, context: Any) -> Dict[str, Any]:
        """Execute the DAG concurrently tier-by-tier using asyncio.gather."""
        levels = self.topological_sort()
        results: Dict[str, Any] = {}

        for tier in levels:
            logger.info("Executing concurrent DAG tier: %s", tier)

            async def run_node(node_id: str):
                node = self.nodes[node_id]
                try:
                    res = await node.action(context)
                    node.result = res
                    node.is_completed = True
                    return node_id, res, None
                except Exception as exc:
                    logger.error("Node '%s' failed: %s", node_id, exc)
                    node.error = exc
                    return node_id, None, exc

            tasks = [run_node(n_id) for n_id in tier]
            tier_results = await asyncio.gather(*tasks)

            for n_id, res, err in tier_results:
                if err:
                    raise RuntimeError(f"DAG execution halted at node '{n_id}': {err}") from err
                results[n_id] = res

        return results
