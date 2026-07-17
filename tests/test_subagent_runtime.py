"""Tests for the Plan-Act-Reflect runtime (M-A2).

Covers: reflection retries until criteria pass, reflection trace persisted as
an artifact, budget gating short-circuits retries, JSON extraction tolerance,
and that single-mode agents are untouched.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from sdlc.llm.cost import CostTracker
from sdlc.subagent.models import Subagent, SubagentResult, SubagentTask
from sdlc.subagent.runtime import PlanActReflectRuntime, _extract_json


def _agent(runtime: str = "par") -> Subagent:
    return Subagent(id="SA-1", name="arch", role="architect", model="m", runtime=runtime)


def _task() -> SubagentTask:
    return SubagentTask(agent_id="SA-1", input="design the thing", pipeline_id="p1", stage_id="s1")


def _pool_returning(output: str) -> MagicMock:
    pool = MagicMock()
    pool.invoke = AsyncMock(
        return_value=SubagentResult(success=True, output=output, artifacts={}, cost_usd=0.01)
    )
    return pool


class _ScriptedLLM:
    """Returns queued JSON replies in order (plan, then reflect verdicts)."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = replies
        self.calls = 0

    async def complete(self, req):
        text = self._replies[min(self.calls, len(self._replies) - 1)]
        self.calls += 1
        block = MagicMock()
        block.type = "text"
        block.text = text
        resp = MagicMock()
        resp.content = [block]
        resp.cost_usd = 0.0
        return resp


# --------------------------------------------------------------------------- #
# JSON extraction
# --------------------------------------------------------------------------- #

def test_extract_json_from_fence():
    assert _extract_json('x ```json\n{"a":1}\n``` y') == {"a": 1}


def test_extract_json_bare_object():
    assert _extract_json('the result is {"a": 2} ok') == {"a": 2}


def test_extract_json_none_on_garbage():
    assert _extract_json("no json here") is None


# --------------------------------------------------------------------------- #
# Reflect loop
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_reflect_retries_until_pass():
    # plan -> 1 subtask; reflect: first fail, then pass. Expect 2 ACT calls.
    llm = _ScriptedLLM(
        [
            '[{"description":"do it","acceptance_criteria":["c1"]}]',  # plan
            '{"passed": false, "score": 0.4, "unmet": ["c1"], "fix_hint": "add c1"}',
            '{"passed": true, "score": 0.9, "unmet": [], "fix_hint": ""}',
        ]
    )
    pool = _pool_returning("draft output")
    rt = PlanActReflectRuntime(pool=pool, llm=llm, max_reflect=2)

    result = await rt.run(_agent(), _task())

    assert pool.invoke.await_count == 2  # failed once, retried, then passed
    trace = result.artifacts["_reflection_trace"]
    assert [t["passed"] for t in trace] == [False, True]
    assert result.success


@pytest.mark.asyncio
async def test_reflect_stops_at_max_reflect():
    # Always fails; max_reflect=2 => 1 initial + 2 retries = 3 ACT calls.
    llm = _ScriptedLLM(
        [
            '[{"description":"do it","acceptance_criteria":["c1"]}]',
            '{"passed": false, "score": 0.1, "unmet": ["c1"], "fix_hint": "try harder"}',
        ]
    )
    pool = _pool_returning("draft")
    rt = PlanActReflectRuntime(pool=pool, llm=llm, max_reflect=2)

    result = await rt.run(_agent(), _task())

    assert pool.invoke.await_count == 3
    assert result.success  # keeps the last output even if never passed


@pytest.mark.asyncio
async def test_budget_gate_short_circuits():
    llm = _ScriptedLLM(
        [
            '[{"description":"a","acceptance_criteria":["c"]}, {"description":"b","acceptance_criteria":["c"]}]',
            '{"passed": false, "score": 0.1, "unmet": ["c"], "fix_hint": "x"}',
        ]
    )
    pool = _pool_returning("draft")
    # Budget already exceeded => no ACT calls should run.
    ct = CostTracker(max_budget_usd=0.0)
    rt = PlanActReflectRuntime(pool=pool, llm=llm, max_reflect=3, cost_tracker=ct)

    await rt.run(_agent(), _task())
    assert pool.invoke.await_count == 0


@pytest.mark.asyncio
async def test_plan_failure_falls_back_to_single_subtask():
    # Plan returns garbage -> one subtask covering whole task; no criteria => pass immediately.
    llm = _ScriptedLLM(["not json at all"])
    pool = _pool_returning("draft")
    rt = PlanActReflectRuntime(pool=pool, llm=llm, max_reflect=2)

    result = await rt.run(_agent(), _task())
    assert pool.invoke.await_count == 1  # single subtask, no reflect criteria
    assert result.success


# --------------------------------------------------------------------------- #
# Dispatch / backward-compat
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_pool_run_agent_single_mode_uses_invoke():
    from sdlc.subagent.pool import SubagentPool
    from sdlc.subagent.registry import SubagentRegistry

    reg = SubagentRegistry()
    reg.register(_agent(runtime="single"))
    pool = SubagentPool(registry=reg, llm=MagicMock())
    pool.invoke = AsyncMock(
        return_value=SubagentResult(success=True, output="ok", cost_usd=0.0)
    )
    result = await pool.run_agent("SA-1", _task())
    pool.invoke.assert_awaited_once()
    assert result.output == "ok"
