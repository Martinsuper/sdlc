"""Error-visibility gate (M-D1) — runs with NO real LLM.

Guards against the GA regression where a failing main-path was invisible: the
stage error only reached audit.jsonl, `sdlc run` still exited 0, and green unit
tests hid a 100%-red pipeline. These tests assert the opposite contract:
  - a failing stage populates PipelineResult.error
  - `sdlc run` prints the error and exits non-zero
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import CliRunner

from sdlc.core.run_coordinator import RunCoordinator
from sdlc.profile import ProfileRegistry
from sdlc.profile.models import ProfileDef
from sdlc.stage.catalog import StageCatalog
from sdlc.stage.models import StageDef
from sdlc.state import StateStore
from sdlc.subagent.models import SubagentResult

pytestmark = pytest.mark.smoke


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


def _failing_pool() -> MagicMock:
    """A subagent pool whose stage raises — simulates an LLM/exec failure."""
    pool = MagicMock()
    exc = RuntimeError("simulated LLM 400: bad request")
    pool.invoke = AsyncMock(side_effect=exc)
    pool.run_agent = AsyncMock(side_effect=exc)
    return pool


def _ok_pool() -> MagicMock:
    pool = MagicMock()
    ok = SubagentResult(success=True, output="done", artifacts={}, cost_usd=0.0)
    pool.invoke = AsyncMock(return_value=ok)
    pool.run_agent = AsyncMock(return_value=ok)
    return pool


@pytest.mark.asyncio
async def test_failing_stage_populates_pipeline_error(tmp_path):
    coord = RunCoordinator(
        state=StateStore(tmp_path / "s.db"),
        audit=MagicMock(),
        catalog=_catalog(),
        subagent_pool=_failing_pool(),
        profile_registry=_profiles(),
    )
    result = await coord.run("add a feature")
    assert result.status == "failed"
    # The concrete failure reason must be visible on the result, not swallowed.
    assert result.error, "PipelineResult.error must be populated on failure"


@pytest.mark.asyncio
async def test_successful_stage_has_no_error(tmp_path):
    coord = RunCoordinator(
        state=StateStore(tmp_path / "s.db"),
        audit=MagicMock(),
        catalog=_catalog(),
        subagent_pool=_ok_pool(),
        profile_registry=_profiles(),
    )
    result = await coord.run("add a feature")
    assert result.status == "completed"
    assert not result.error


def test_run_cmd_exits_nonzero_and_prints_error(monkeypatch):
    """`sdlc run` must exit non-zero and surface the error when a stage fails."""
    from sdlc.core.models import PipelineResult

    container = MagicMock()
    container.cost_tracker.max_budget = 5.0

    async def _fake_run(*args, **kwargs):
        return PipelineResult(
            pipeline_id="p1",
            status="failed",
            stage_results=[
                {"stage_id": "s1", "status": "FAILED", "error": "simulated LLM 400: bad request"}
            ],
            total_cost_usd=0.0,
            error="simulated LLM 400: bad request",
        )

    container.coordinator.run = _fake_run
    # run_cmd imports build_deps lazily inside the function, so patch it at its
    # source module (sdlc.cli.deps), not on run_cmd.
    monkeypatch.setattr("sdlc.cli.deps.build_deps", lambda: container, raising=True)

    from sdlc.cli import run_cmd

    result = CliRunner().invoke(run_cmd.run, ["add a feature"])
    assert result.exit_code != 0, "run must exit non-zero on pipeline failure"
    assert "simulated LLM 400" in result.output or "FAILED" in result.output
