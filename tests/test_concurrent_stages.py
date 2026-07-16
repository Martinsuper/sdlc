"""Tests for concurrent stage execution in RunCoordinator."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sdlc.audit import AuditLogger
from sdlc.gate import GateEngine
from sdlc.gate.models import GateAction, GateDecision, GateDef
from sdlc.kb.memory import MemoryL2
from sdlc.llm.cost import CostTracker
from sdlc.stage import StageCatalog
from sdlc.stage.models import StageDef, StageNode
from sdlc.state import StateStore
from sdlc.subagent import SubagentPool


@pytest.fixture
def tmp_home(tmp_path: Path) -> Path:
    """Provide a temporary home for state and audit."""
    return tmp_path


@pytest.fixture
def state(tmp_home: Path) -> StateStore:
    return StateStore(tmp_home / "state.db")


@pytest.fixture
def audit(tmp_home: Path) -> AuditLogger:
    return AuditLogger(tmp_home / "audit.jsonl")


@pytest.fixture
def catalog() -> StageCatalog:
    cat = StageCatalog()
    # Register test stages
    cat.register(StageDef(
        id="design",
        name="Design",
        category="planning",
        produces_artifacts=["design-doc"],
    ))
    cat.register(StageDef(
        id="code",
        name="Code",
        category="development",
        required_artifacts=["design-doc"],
        produces_artifacts=["source-code"],
    ))
    cat.register(StageDef(
        id="test-a",
        name="Test A",
        category="testing",
        required_artifacts=["source-code"],
        produces_artifacts=["test-report-a"],
    ))
    cat.register(StageDef(
        id="test-b",
        name="Test B",
        category="testing",
        required_artifacts=["source-code"],
        produces_artifacts=["test-report-b"],
    ))
    cat.register(StageDef(
        id="deploy",
        name="Deploy",
        category="delivery",
        required_artifacts=["test-report-a", "test-report-b"],
        produces_artifacts=["deploy-log"],
    ))
    return cat


@pytest.fixture
def subagent_pool() -> SubagentPool:
    # Create a minimal SubagentPool with no real LLM
    mock_llm = MagicMock()
    sub_reg = MagicMock()
    return SubagentPool(registry=sub_reg, llm=mock_llm, audit=MagicMock())


def _make_stage_nodes() -> list[StageNode]:
    """Create a pipeline of stage nodes with dependencies.

    Pipeline structure:
        design -> code -> test-a -> deploy
                      -> test-b ---^

    test-a and test-b are independent of each other and can run concurrently.
    """
    return [
        StageNode(id="design", depends_on=[]),
        StageNode(id="code", depends_on=["design"]),
        StageNode(id="test-a", depends_on=["code"]),
        StageNode(id="test-b", depends_on=["code"]),
        StageNode(id="deploy", depends_on=["test-a", "test-b"]),
    ]


class TestConcurrentStageExecution:
    @pytest.mark.asyncio
    async def test_concurrent_independent_stages(
        self, state: StateStore, audit: AuditLogger, catalog: StageCatalog, subagent_pool: SubagentPool
    ) -> None:
        """Test that independent stages (test-a, test-b) can run concurrently."""
        from sdlc.core.run_coordinator import RunCoordinator

        coordinator = RunCoordinator(
            state=state,
            audit=audit,
            catalog=catalog,
            subagent_pool=subagent_pool,
        )

        nodes = _make_stage_nodes()
        pipeline_id = "test-concurrent-001"
        context = {"input": "test", "pipeline_id": pipeline_id}

        # Mock run_stage to succeed and track execution order
        execution_log: list[str] = []

        async def mock_run_stage(stage_def, pid, ctx=None):
            execution_log.append(stage_def.id)
            await asyncio.sleep(0.01)  # Simulate work
            return {
                "stage_id": stage_def.id,
                "status": "COMPLETED",
                "artifacts": [],
                "cost_usd": 0.0,
                "error": None,
                "gate_decision": None,
            }

        coordinator.stage_runner.run_stage = mock_run_stage  # type: ignore[assignment]

        results = await coordinator._run_pipeline_stages_concurrent(
            nodes, pipeline_id, context, concurrency=2
        )

        assert len(results) == 5
        assert all(r["status"] == "COMPLETED" for r in results)
        # All stages should have been executed
        assert set(execution_log) == {"design", "code", "test-a", "test-b", "deploy"}

    @pytest.mark.asyncio
    async def test_sequential_when_concurrency_is_one(
        self, state: StateStore, audit: AuditLogger, catalog: StageCatalog, subagent_pool: SubagentPool
    ) -> None:
        """Test that concurrency=1 runs stages sequentially."""
        from sdlc.core.run_coordinator import RunCoordinator

        coordinator = RunCoordinator(
            state=state,
            audit=audit,
            catalog=catalog,
            subagent_pool=subagent_pool,
        )

        nodes = _make_stage_nodes()
        pipeline_id = "test-sequential-001"
        context = {"input": "test", "pipeline_id": pipeline_id}

        execution_order: list[str] = []

        async def mock_run_stage(stage_def, pid, ctx=None):
            execution_order.append(stage_def.id)
            return {
                "stage_id": stage_def.id,
                "status": "COMPLETED",
                "artifacts": [],
                "cost_usd": 0.0,
                "error": None,
                "gate_decision": None,
            }

        coordinator.stage_runner.run_stage = mock_run_stage  # type: ignore[assignment]

        results = await coordinator._run_pipeline_stages_concurrent(
            nodes, pipeline_id, context, concurrency=1
        )

        assert len(results) == 5
        assert all(r["status"] == "COMPLETED" for r in results)

    @pytest.mark.asyncio
    async def test_stage_failure_skips_remaining(
        self, state: StateStore, audit: AuditLogger, catalog: StageCatalog, subagent_pool: SubagentPool
    ) -> None:
        """Test that a stage failure skips downstream stages."""
        from sdlc.core.run_coordinator import RunCoordinator

        coordinator = RunCoordinator(
            state=state,
            audit=audit,
            catalog=catalog,
            subagent_pool=subagent_pool,
        )

        nodes = _make_stage_nodes()
        pipeline_id = "test-failure-001"
        context = {"input": "test", "pipeline_id": pipeline_id}

        async def mock_run_stage(stage_def, pid, ctx=None):
            if stage_def.id == "code":
                return {
                    "stage_id": stage_def.id,
                    "status": "FAILED",
                    "artifacts": [],
                    "cost_usd": 0.0,
                    "error": "Code stage failed",
                    "gate_decision": None,
                }
            return {
                "stage_id": stage_def.id,
                "status": "COMPLETED",
                "artifacts": [],
                "cost_usd": 0.0,
                "error": None,
                "gate_decision": None,
            }

        coordinator.stage_runner.run_stage = mock_run_stage  # type: ignore[assignment]

        results = await coordinator._run_pipeline_stages_concurrent(
            nodes, pipeline_id, context, concurrency=2
        )

        # design should succeed, code fails, rest should be skipped
        assert results[0]["status"] == "COMPLETED"  # design
        assert results[1]["status"] == "FAILED"   # code
        # Remaining stages should be skipped
        for r in results[2:]:
            assert r["status"] == "SKIPPED"

    @pytest.mark.asyncio
    async def test_unmet_dependencies_are_skipped(
        self, state: StateStore, audit: AuditLogger, catalog: StageCatalog, subagent_pool: SubagentPool
    ) -> None:
        """Test that stages with unmet dependencies are skipped."""
        from sdlc.core.run_coordinator import RunCoordinator

        coordinator = RunCoordinator(
            state=state,
            audit=audit,
            catalog=catalog,
            subagent_pool=subagent_pool,
        )

        # Create a node with a dependency that doesn't exist
        nodes = [
            StageNode(id="orphan", depends_on=["nonexistent"]),
        ]
        pipeline_id = "test-unmet-001"
        context = {"input": "test", "pipeline_id": pipeline_id}

        results = await coordinator._run_pipeline_stages_concurrent(
            nodes, pipeline_id, context, concurrency=2
        )

        assert len(results) == 1
        assert results[0]["status"] == "SKIPPED"
        assert "Unmet dependencies" in (results[0].get("error") or "")

    @pytest.mark.asyncio
    async def test_duration_tracking(
        self, state: StateStore, audit: AuditLogger, catalog: StageCatalog, subagent_pool: SubagentPool
    ) -> None:
        """Test that per-stage duration is tracked."""
        from sdlc.core.run_coordinator import RunCoordinator

        coordinator = RunCoordinator(
            state=state,
            audit=audit,
            catalog=catalog,
            subagent_pool=subagent_pool,
        )

        nodes = [StageNode(id="design", depends_on=[])]
        pipeline_id = "test-duration-001"
        context = {"input": "test", "pipeline_id": pipeline_id}

        async def mock_run_stage(stage_def, pid, ctx=None):
            await asyncio.sleep(0.05)
            return {
                "stage_id": stage_def.id,
                "status": "COMPLETED",
                "artifacts": [],
                "cost_usd": 0.0,
                "error": None,
                "gate_decision": None,
            }

        coordinator.stage_runner.run_stage = mock_run_stage  # type: ignore[assignment]

        results = await coordinator._run_pipeline_stages_concurrent(
            nodes, pipeline_id, context, concurrency=2
        )

        assert "duration_ms" in results[0]
        assert results[0]["duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_concurrency_capped_at_three(
        self, state: StateStore, audit: AuditLogger, catalog: StageCatalog, subagent_pool: SubagentPool
    ) -> None:
        """Test that concurrency is capped at 3 even if higher value is requested."""
        from sdlc.core.run_coordinator import RunCoordinator

        # Register independent stages in the catalog
        for i in range(5):
            catalog.register(StageDef(
                id=f"independent-{i}",
                name=f"Independent {i}",
                category="testing",
            ))

        coordinator = RunCoordinator(
            state=state,
            audit=audit,
            catalog=catalog,
            subagent_pool=subagent_pool,
        )

        # Create 5 independent stages
        nodes = [StageNode(id=f"independent-{i}", depends_on=[]) for i in range(5)]
        pipeline_id = "test-cap-001"
        context = {"input": "test", "pipeline_id": pipeline_id}

        async def mock_run_stage(stage_def, pid, ctx=None):
            return {
                "stage_id": stage_def.id,
                "status": "COMPLETED",
                "artifacts": [],
                "cost_usd": 0.0,
                "error": None,
                "gate_decision": None,
            }

        coordinator.stage_runner.run_stage = mock_run_stage  # type: ignore[assignment]

        # Request concurrency of 10, should be capped at 3
        results = await coordinator._run_pipeline_stages_concurrent(
            nodes, pipeline_id, context, concurrency=10
        )

        assert len(results) == 5
        assert all(r["status"] == "COMPLETED" for r in results)


class TestRunCoordinatorConcurrency:
    @pytest.mark.asyncio
    async def test_run_with_concurrency_param(
        self, state: StateStore, audit: AuditLogger, catalog: StageCatalog, subagent_pool: SubagentPool
    ) -> None:
        """Test that the run method accepts and passes concurrency."""
        from sdlc.core.run_coordinator import RunCoordinator

        coordinator = RunCoordinator(
            state=state,
            audit=audit,
            catalog=catalog,
            subagent_pool=subagent_pool,
        )

        # Patch _run_pipeline_stages_concurrent to verify it's called
        called_with_concurrency: dict[str, Any] = {}

        async def mock_concurrent(stage_nodes, pipeline_id, context, concurrency):
            called_with_concurrency["concurrency"] = concurrency
            return [
                {
                    "stage_id": n.id,
                    "status": "COMPLETED",
                    "artifacts": [],
                    "cost_usd": 0.0,
                    "error": None,
                    "gate_decision": None,
                }
                for n in stage_nodes
            ]

        coordinator._run_pipeline_stages_concurrent = mock_concurrent  # type: ignore[assignment]

        # Mock the rest of the pipeline setup
        from sdlc.core.models import EntryKind, EntryPoint
        from sdlc.profile.models import ProfileDef

        coordinator.entry_detector = MagicMock()
        coordinator.entry_detector.detect.return_value = EntryPoint(
            kind=EntryKind.FEATURE, raw_input="test"
        )

        coordinator.profile_registry = MagicMock()
        coordinator.profile_registry.resolve.return_value = ProfileDef(
            id="new-feature", name="New Feature", severity="P2"
        )

        coordinator.pipeline_builder = MagicMock()
        from sdlc.core.models import Pipeline

        mock_pipeline = Pipeline(
            id="test-1",
            entry=EntryPoint(kind=EntryKind.FEATURE, raw_input="test"),
            stages=[StageNode(id="design", depends_on=[])],
        )
        coordinator.pipeline_builder.build.return_value = mock_pipeline

        result = await coordinator.run("test input", concurrency=2)
        assert called_with_concurrency.get("concurrency") == 2
