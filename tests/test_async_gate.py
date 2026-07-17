"""Tests for M-B1 async approval gates (suspend → approve/reject → resume)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from sdlc.core.run_coordinator import RunCoordinator
from sdlc.gate import GateEngine
from sdlc.gate.models import GateDef, GateTrigger
from sdlc.profile import ProfileRegistry
from sdlc.profile.models import ProfileDef
from sdlc.stage.catalog import StageCatalog
from sdlc.stage.models import StageDef
from sdlc.state import StateStore
from sdlc.subagent.models import SubagentResult


def _catalog() -> StageCatalog:
    cat = StageCatalog()
    cat.register(StageDef(id="s1", name="Stage 1", category="impl", subagent="coder"))
    return cat


def _profiles() -> ProfileRegistry:
    reg = ProfileRegistry()
    reg.register(
        ProfileDef(
            id="feature",
            name="Feature",
            entry_kinds=["feature"],
            base_stages=["s1"],
            severity="P2",
        )
    )
    return reg


def _manual_gate_engine() -> GateEngine:
    # A gate with no auto_pass/block conditions => MANUAL_REVIEW after s1.
    engine = GateEngine()
    engine.register(
        GateDef(id="g-review", name="Human review", after_stage="s1", trigger=GateTrigger.ALWAYS)
    )
    return engine


def _ok_pool() -> MagicMock:
    pool = MagicMock()
    res = SubagentResult(success=True, output="done", artifacts={}, cost_usd=0.0)
    pool.invoke = AsyncMock(return_value=res)
    pool.run_agent = AsyncMock(return_value=res)
    return pool


def _coord(tmp_path, gate_approved_store=None) -> tuple[RunCoordinator, StateStore]:
    store = gate_approved_store or StateStore(tmp_path / "s.db")
    coord = RunCoordinator(
        state=store,
        audit=MagicMock(),
        catalog=_catalog(),
        subagent_pool=_ok_pool(),
        gate_engine=_manual_gate_engine(),
        profile_registry=_profiles(),
    )
    return coord, store


@pytest.mark.asyncio
async def test_manual_gate_suspends_pipeline(tmp_path):
    coord, store = _coord(tmp_path)
    result = await coord.run("add a feature")
    assert result.status == "waiting_approval"
    # A pending approval record exists and the pipeline state is WAITING_APPROVAL.
    assert store.has_pending_waiting(result.pipeline_id)
    summary = store.load_pipeline(result.pipeline_id)
    assert summary.status == "WAITING_APPROVAL"


@pytest.mark.asyncio
async def test_approve_then_resume_completes(tmp_path):
    coord, store = _coord(tmp_path)
    result = await coord.run("add a feature")
    pid = result.pipeline_id

    # Approver releases the gate.
    assert store.resolve_waiting(pid, "approval", "g-review", {"approved": True})
    resumed = await coord.resume_from_waiting(pid)
    assert resumed.status == "completed"
    assert not store.has_pending_waiting(pid)


@pytest.mark.asyncio
async def test_reject_then_resume_fails(tmp_path):
    coord, store = _coord(tmp_path)
    result = await coord.run("add a feature")
    pid = result.pipeline_id

    store.resolve_waiting(pid, "approval", "g-review", {"approved": False, "reason": "no"})
    resumed = await coord.resume_from_waiting(pid)
    assert resumed.status == "failed"
    assert "Rejected" in (resumed.error or "")


@pytest.mark.asyncio
async def test_resume_refuses_while_pending(tmp_path):
    coord, _store = _coord(tmp_path)
    result = await coord.run("add a feature")
    with pytest.raises(ValueError, match="unresolved"):
        await coord.resume_from_waiting(result.pipeline_id)


def test_waiting_store_roundtrip(tmp_path):
    store = StateStore(tmp_path / "s.db")
    store.save_pipeline(
        pipeline_id="p1", entry_kind="feature", profile_id="feature", status="RUNNING"
    )
    store.save_waiting("p1", "approval", "g1", {"reason": "x"}, stage_id="s1", reviewer="tl")
    assert store.has_pending_waiting("p1")
    pending = store.load_waiting("p1", pending_only=True)
    assert len(pending) == 1 and pending[0]["reviewer"] == "tl"

    # Resolving twice: second time no pending row matches.
    assert store.resolve_waiting("p1", "approval", "g1", {"approved": True})
    assert not store.resolve_waiting("p1", "approval", "g1", {"approved": True})
    assert not store.has_pending_waiting("p1")
