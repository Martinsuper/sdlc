"""Tests for M-A3 structured clarification (ask_user → suspend → answer → resume).

Reuses the M-B1 waiting mechanism with kind='clarification'. The subagent's
ask_user raises ClarificationNeeded, which the coordinator turns into a
WAITING_CLARIFICATION suspension; `answer` resolves it and the injected answer
is returned on resume instead of re-suspending.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sdlc.core.run_coordinator import RunCoordinator
from sdlc.profile import ProfileRegistry
from sdlc.profile.models import ProfileDef
from sdlc.stage.catalog import StageCatalog
from sdlc.stage.models import StageDef
from sdlc.state import StateStore
from sdlc.subagent.models import Subagent, SubagentTask
from sdlc.subagent.pool import SubagentPool
from sdlc.subagent.registry import SubagentRegistry
from sdlc.utils.exceptions import ClarificationNeeded


def _catalog() -> StageCatalog:
    cat = StageCatalog()
    cat.register(StageDef(id="s1", name="Stage 1", category="impl", subagent="asker"))
    return cat


def _profiles() -> ProfileRegistry:
    reg = ProfileRegistry()
    reg.register(
        ProfileDef(
            id="feature", name="Feature", entry_kinds=["feature"], base_stages=["s1"], severity="P2"
        )
    )
    return reg


def _asking_pool() -> SubagentPool:
    """Real pool + registry with an agent that only has ask_user; LLM emits a
    single ask_user tool call."""
    reg = SubagentRegistry()
    reg.register(Subagent(id="asker", name="asker", role="analyst", model="m", tools=["ask_user"]))

    llm = MagicMock()

    async def _complete(req):
        from sdlc.llm.models import CompletionResponse, ContentBlock

        # Once the injected clarification answer appears as a tool result in the
        # conversation, the agent finishes; until then it asks.
        text_seen = any(
            isinstance(m.content, str) and "User answered" in m.content for m in req.messages
        )
        if text_seen:
            content = [ContentBlock(type="text", text="Design complete using the chosen database.")]
        else:
            content = [
                ContentBlock(
                    type="tool_use",
                    id="tc1",
                    name="ask_user",
                    input={"question": "Which database should we use?"},
                )
            ]
        return CompletionResponse(id="r", model="m", content=content, cost_usd=0.0)

    llm.complete = _complete
    return SubagentPool(registry=reg, llm=llm)


def _coord(tmp_path):
    store = StateStore(tmp_path / "s.db")
    coord = RunCoordinator(
        state=store,
        audit=MagicMock(),
        catalog=_catalog(),
        subagent_pool=_asking_pool(),
        profile_registry=_profiles(),
    )
    return coord, store


@pytest.mark.asyncio
async def test_ask_user_suspends_pipeline(tmp_path):
    coord, store = _coord(tmp_path)
    result = await coord.run("build a thing")
    assert result.status == "waiting_clarification"
    pending = store.load_waiting(result.pipeline_id, kind="clarification", pending_only=True)
    assert len(pending) == 1
    assert "database" in pending[0]["payload"]["question"].lower()
    assert store.load_pipeline(result.pipeline_id).status == "WAITING_CLARIFICATION"


@pytest.mark.asyncio
async def test_ask_user_answer_injected_on_resume(tmp_path):
    # On resume with the answer injected, the pool must return it (not re-suspend).
    reg = SubagentRegistry()
    agent = Subagent(id="asker", name="asker", role="analyst", model="m", tools=["ask_user"])
    qid = SubagentPool._question_id("Which database should we use?")
    task = SubagentTask(
        agent_id="asker",
        input="x",
        context={"clarifications": {qid: "PostgreSQL"}},
    )
    pool = SubagentPool(registry=reg, llm=MagicMock())
    out = pool._handle_ask_user({"question": "Which database should we use?"}, task, agent)
    assert "PostgreSQL" in out


@pytest.mark.asyncio
async def test_ask_user_without_answer_raises(tmp_path):
    agent = Subagent(id="asker", name="asker", role="analyst", model="m", tools=["ask_user"])
    task = SubagentTask(agent_id="asker", input="x", context={})
    pool = SubagentPool(registry=SubagentRegistry(), llm=MagicMock())
    with pytest.raises(ClarificationNeeded) as ei:
        pool._handle_ask_user({"question": "Which database?"}, task, agent)
    assert ei.value.question_id.startswith("q-")


@pytest.mark.asyncio
async def test_clarification_answer_and_resume_endtoend(tmp_path):
    coord, store = _coord(tmp_path)
    result = await coord.run("build a thing")
    pid = result.pipeline_id
    qid = store.load_waiting(pid, kind="clarification", pending_only=True)[0]["ref_id"]

    store.resolve_waiting(pid, "clarification", qid, {"answer": "PostgreSQL"})
    # On resume the agent still only emits ask_user, but the injected answer
    # short-circuits it — so the stage completes rather than re-suspending.
    resumed = await coord.resume_from_waiting(pid)
    assert resumed.status == "completed"
    assert not store.has_pending_waiting(pid)
