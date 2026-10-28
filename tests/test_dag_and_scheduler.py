import asyncio
import pytest
from core.dag import CycleDetectedError, WorkflowDAG


@pytest.mark.asyncio
async def test_dag_linear_execution():
    dag = WorkflowDAG()
    execution_order = []

    async def step_a(ctx):
        execution_order.append("A")
        return "result_A"

    async def step_b(ctx):
        execution_order.append("B")
        return "result_B"

    dag.add_node("A", step_a)
    dag.add_node("B", step_b, depends_on=["A"])

    results = await dag.execute({})
    assert execution_order == ["A", "B"]
    assert results["A"] == "result_A"
    assert results["B"] == "result_B"


@pytest.mark.asyncio
async def test_dag_parallel_tier_execution():
    dag = WorkflowDAG()
    completed = []

    async def root(ctx):
        completed.append("root")

    async def branch_1(ctx):
        completed.append("b1")

    async def branch_2(ctx):
        completed.append("b2")

    async def join(ctx):
        completed.append("join")

    dag.add_node("root", root)
    dag.add_node("b1", branch_1, depends_on=["root"])
    dag.add_node("b2", branch_2, depends_on=["root"])
    dag.add_node("join", join, depends_on=["b1", "b2"])

    tiers = dag.topological_sort()
    assert len(tiers) == 3
    assert tiers[0] == ["root"]
    assert set(tiers[1]) == {"b1", "b2"}
    assert tiers[2] == ["join"]

    await dag.execute({})
    assert completed[0] == "root"
    assert set(completed[1:3]) == {"b1", "b2"}
    assert completed[3] == "join"


def test_dag_cycle_detection():
    dag = WorkflowDAG()

    async def dummy(ctx):
        pass

    dag.add_node("A", dummy, depends_on=["B"])
    dag.add_node("B", dummy, depends_on=["A"])

    with pytest.raises(CycleDetectedError):
        dag.topological_sort()
