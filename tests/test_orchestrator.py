"""Tests for M-A5 Orchestrator-Worker multi-agent execution."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from sdlc.subagent.models import Subagent, SubagentResult, SubagentTask
from sdlc.subagent.orchestrator import (
    DelegationDepthError,
    Orchestrator,
    WorkerSpec,
)


def _lead() -> Subagent:
    return Subagent(id="architect", name="architect", role="lead", model="m")


def _task(depth: int = 0) -> SubagentTask:
    return SubagentTask(
        agent_id="architect", input="design it", context={"_delegate_depth": depth},
        pipeline_id="p1", stage_id="s1",
    )


def _specs() -> list[WorkerSpec]:
    return [
        WorkerSpec("db-designer", "design the schema", ["normalized"]),
        WorkerSpec("api-designer", "design the API", ["RESTful"]),
        WorkerSpec("risk-assessor", "assess risks"),
    ]


def _pool_with_workers(cost_tracker=None) -> MagicMock:
    pool = MagicMock()
    pool.audit = None
    pool.cost_tracker = cost_tracker

    async def _invoke(agent_id, task):
        return SubagentResult(success=True, output=f"{agent_id} output", artifacts={"k": agent_id}, cost_usd=0.01)

    pool.invoke = AsyncMock(side_effect=_invoke)
    return pool


@pytest.mark.asyncio
async def test_dispatches_all_workers_and_merges():
    pool = _pool_with_workers()
    orch = Orchestrator(pool)
    result = await orch.run(_lead(), _task(), _specs())

    assert pool.invoke.await_count == 3
    assert result.success
    # Merged output carries every worker's section and namespaced artifacts.
    assert "db-designer output" in result.output
    assert "db-designer.k" in result.artifacts
    assert result.artifacts["_delegated_workers"] == ["db-designer", "api-designer", "risk-assessor"]


@pytest.mark.asyncio
async def test_workers_receive_incremented_depth():
    pool = _pool_with_workers()
    orch = Orchestrator(pool)
    await orch.run(_lead(), _task(depth=0), _specs()[:1])
    # The worker task context must carry depth=1 so it cannot re-delegate.
    (_agent_id, worker_task), _ = pool.invoke.await_args
    assert worker_task.context["_delegate_depth"] == 1


@pytest.mark.asyncio
async def test_depth_guard_blocks_second_level():
    pool = _pool_with_workers()
    orch = Orchestrator(pool, max_delegate_depth=1)
    with pytest.raises(DelegationDepthError):
        await orch.run(_lead(), _task(depth=1), _specs())
    assert pool.invoke.await_count == 0


@pytest.mark.asyncio
async def test_worker_failure_isolated():
    pool = MagicMock()
    pool.audit = None
    pool.cost_tracker = None

    async def _invoke(agent_id, task):
        if agent_id == "api-designer":
            raise RuntimeError("boom")
        return SubagentResult(success=True, output=f"{agent_id} ok", cost_usd=0.0)

    pool.invoke = AsyncMock(side_effect=_invoke)
    orch = Orchestrator(pool)
    result = await orch.run(_lead(), _task(), _specs())

    # One worker failing does not abort the others; failure is surfaced.
    assert pool.invoke.await_count == 3
    assert "api-designer" in (result.error or "")
    assert result.success  # majority succeeded


@pytest.mark.asyncio
async def test_budget_gate_blocks_dispatch():
    from sdlc.llm.cost import CostTracker

    ct = CostTracker(max_budget_usd=1.0)
    ct._session_cost = 1.0  # already at budget
    pool = _pool_with_workers(cost_tracker=ct)
    orch = Orchestrator(pool)
    result = await orch.run(_lead(), _task(), _specs())

    # Over budget => no worker actually runs; all report the budget stop.
    assert pool.invoke.await_count == 0
    assert not result.success


@pytest.mark.asyncio
async def test_empty_subtasks_is_noop():
    pool = _pool_with_workers()
    orch = Orchestrator(pool)
    result = await orch.run(_lead(), _task(), [])
    assert result.success
    assert pool.invoke.await_count == 0


@pytest.mark.asyncio
async def test_delegate_tool_end_to_end():
    from sdlc.subagent.pool import SubagentPool
    from sdlc.subagent.registry import SubagentRegistry
    from sdlc.subagent.tools import ToolContext

    reg = SubagentRegistry()
    pool = SubagentPool(registry=reg, llm=MagicMock())

    async def _invoke(agent_id, task):
        return SubagentResult(success=True, output=f"{agent_id} done", cost_usd=0.0)

    pool.invoke = AsyncMock(side_effect=_invoke)
    tool = pool.tools._tools["delegate"]
    ctx = ToolContext(project_root=__import__("pathlib").Path("."), agent_id="architect")
    out = await tool.run(
        {"subtasks": [{"worker_agent_id": "db", "description": "schema"}]}, ctx
    )
    assert "db done" in out
