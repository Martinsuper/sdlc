from unittest.mock import AsyncMock, MagicMock

import pytest

from sdlc.stage.catalog import StageCatalog, StageNotFoundError
from sdlc.stage.models import StageDef, StageNode
from sdlc.stage.runner import StageRunner
from sdlc.subagent.models import SubagentResult


def _make_stage_def(**overrides):
    defaults = dict(
        id="s-clarify",
        name="Clarify",
        category="requirement",
        description="Clarify requirements",
        subagent="SA-1",
        produces_artifacts=["requirements_doc"],
    )
    defaults.update(overrides)
    return StageDef(**defaults)


def _make_state(tmp_path):
    from sdlc.state import StateStore

    return StateStore(tmp_path / "state.db")


def _make_audit(tmp_path):
    from sdlc.audit import AuditLogger

    return AuditLogger(tmp_path / "audit.jsonl")


def _make_subagent_pool():
    pool = MagicMock()
    pool.invoke = AsyncMock()
    return pool


class TestStageDef:
    def test_create_defaults(self):
        sd = StageDef(id="s1", name="Stage1", category="impl")
        assert sd.id == "s1"
        assert sd.model == "claude-sonnet-4-20250514"
        assert sd.timeout == 1800
        assert sd.max_retries == 2
        assert sd.required_artifacts == []
        assert sd.produces_artifacts == []
        assert sd.gates == []

    def test_create_with_overrides(self):
        sd = StageDef(
            id="s2",
            name="Stage2",
            category="test",
            subagent="SA-2",
            timeout=3600,
            produces_artifacts=["report"],
        )
        assert sd.subagent == "SA-2"
        assert sd.timeout == 3600
        assert sd.produces_artifacts == ["report"]


class TestStageNode:
    def test_create_defaults(self):
        node = StageNode(id="n1")
        assert node.id == "n1"
        assert node.stage_def is None
        assert node.depends_on == []
        assert node.status == "PENDING"

    def test_create_with_deps(self):
        sd = _make_stage_def()
        node = StageNode(id="n2", stage_def=sd, depends_on=["n1"], status="RUNNING")
        assert node.stage_def is sd
        assert node.depends_on == ["n1"]
        assert node.status == "RUNNING"


class TestStageCatalog:
    def test_register_and_get(self):
        cat = StageCatalog()
        sd = _make_stage_def()
        cat.register(sd)
        assert cat.get("s-clarify") is sd

    def test_get_not_found_raises(self):
        cat = StageCatalog()
        with pytest.raises(StageNotFoundError, match="not found"):
            cat.get("nonexistent")

    def test_list(self):
        cat = StageCatalog()
        sd1 = _make_stage_def(id="s1", name="S1", category="impl")
        sd2 = _make_stage_def(id="s2", name="S2", category="test")
        cat.register(sd1)
        cat.register(sd2)
        result = cat.list_stages()
        ids = {s.id for s in result}
        assert "s1" in ids
        assert "s2" in ids

    def test_has(self):
        cat = StageCatalog()
        sd = _make_stage_def()
        cat.register(sd)
        assert cat.has("s-clarify") is True
        assert cat.has("missing") is False

    def test_for_category(self):
        cat = StageCatalog()
        cat.register(_make_stage_def(id="s1", name="S1", category="requirement"))
        cat.register(_make_stage_def(id="s2", name="S2", category="impl"))
        cat.register(_make_stage_def(id="s3", name="S3", category="requirement"))
        result = cat.for_category("requirement")
        assert all(s.category == "requirement" for s in result)
        assert "s1" in {s.id for s in result}
        assert "s3" in {s.id for s in result}

    def test_load_from_yaml(self, tmp_path):
        yaml_content = (
            "stages:\n"
            "  - id: s-clarify\n"
            "    name: Clarify\n"
            "    category: requirement\n"
            "    subagent: SA-1\n"
            "  - id: s-design\n"
            "    name: Design\n"
            "    category: design\n"
            "    produces_artifacts:\n"
            "      - design_doc\n"
        )
        p = tmp_path / "stages.yaml"
        p.write_text(yaml_content, encoding="utf-8")
        cat = StageCatalog()
        count = cat.load_from_yaml(p)
        assert count == 2
        assert cat.has("s-clarify")
        assert cat.has("s-design")
        sd = cat.get("s-design")
        assert sd.produces_artifacts == ["design_doc"]

    def test_load_from_yaml_empty(self, tmp_path):
        p = tmp_path / "empty.yaml"
        p.write_text("{}", encoding="utf-8")
        cat = StageCatalog()
        assert cat.load_from_yaml(p) == 0

    def test_load_from_yaml_no_id_skipped(self, tmp_path):
        yaml_content = "stages:\n  - name: NoId\n    category: impl\n"
        p = tmp_path / "noid.yaml"
        p.write_text(yaml_content, encoding="utf-8")
        cat = StageCatalog()
        assert cat.load_from_yaml(p) == 0


class TestStageRunner:
    @pytest.fixture
    def tmp(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def state(self, tmp):
        s = _make_state(tmp)
        return s

    @pytest.fixture
    def audit(self, tmp):
        return _make_audit(tmp)

    @pytest.fixture
    def pool(self):
        pool = _make_subagent_pool()
        pool.invoke.return_value = SubagentResult(
            success=True,
            output="Clarified output text",
            artifacts={"requirements_doc": "req content"},
            cost_usd=0.05,
        )
        return pool

    @pytest.fixture
    def runner(self, state, audit, pool):
        return StageRunner(
            catalog=StageCatalog(),
            state=state,
            audit=audit,
            subagent_pool=pool,
        )

    @pytest.mark.asyncio
    async def test_run_stage_success(self, runner, pool, state):
        state.save_pipeline("pipe-1", "issue", "default")
        sd = _make_stage_def()
        result = await runner.run_stage(sd, "pipe-1")
        assert result["status"] == "COMPLETED"
        assert result["stage_id"] == "s-clarify"
        assert result["cost_usd"] == 0.05
        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["name"] == "requirements_doc"

    @pytest.mark.asyncio
    async def test_run_stage_audit_events(self, runner, audit, state):
        state.save_pipeline("pipe-2", "issue", "default")
        sd = _make_stage_def()
        await runner.run_stage(sd, "pipe-2")
        events = list(audit.query())
        types = [e["type"] for e in events]
        assert "stage_start" in types
        assert "stage_end" in types

    @pytest.mark.asyncio
    async def test_run_stage_saves_result(self, runner, state):
        state.save_pipeline("pipe-3", "issue", "default")
        sd = _make_stage_def()
        await runner.run_stage(sd, "pipe-3")
        sr = state.load_stage_result("pipe-3", f"pipe-3-{sd.id}")
        assert sr is not None
        assert sr.status == "COMPLETED"
        assert sr.stage_def_id == "s-clarify"

    @pytest.mark.asyncio
    async def test_run_stage_registers_artifact(self, runner, state):
        state.save_pipeline("pipe-4", "issue", "default")
        sd = _make_stage_def()
        await runner.run_stage(sd, "pipe-4")
        artifacts = state.list_artifacts("pipe-4")
        assert len(artifacts) == 1
        assert artifacts[0].stage_id == "s-clarify"
        assert artifacts[0].type == "doc"

    @pytest.mark.asyncio
    async def test_run_stage_subagent_fails(self, runner, pool, state):
        state.save_pipeline("pipe-5", "issue", "default")
        pool.invoke.return_value = SubagentResult(
            success=False,
            output="",
            error="Agent crashed",
            cost_usd=0.01,
        )
        sd = _make_stage_def()
        result = await runner.run_stage(sd, "pipe-5")
        assert result["status"] == "FAILED"
        assert result["error"] == "Agent crashed"

    @pytest.mark.asyncio
    async def test_run_pipeline_stages_sequential(self, runner, pool, state):
        state.save_pipeline("pipe-6", "issue", "default")
        sd1 = _make_stage_def(id="s1", name="S1", category="impl", produces_artifacts=["a1"])
        sd2 = _make_stage_def(id="s2", name="S2", category="test", produces_artifacts=["a2"])
        n1 = StageNode(id="s1", stage_def=sd1)
        n2 = StageNode(id="s2", stage_def=sd2, depends_on=["s1"])
        results = await runner.run_pipeline_stages([n1, n2], "pipe-6")
        assert results[0]["status"] == "COMPLETED"
        assert results[1]["status"] == "COMPLETED"
        assert pool.invoke.call_count == 2

    @pytest.mark.asyncio
    async def test_run_pipeline_stages_skip_unmet(self, runner, state):
        sd = _make_stage_def(id="s1", name="S1", category="impl")
        node = StageNode(id="s1", stage_def=sd, depends_on=["missing-dep"])
        results = await runner.run_pipeline_stages([node], "pipe-7")
        assert results[0]["status"] == "SKIPPED"
        assert "missing-dep" in results[0]["error"]

    @pytest.mark.asyncio
    async def test_run_pipeline_stages_stop_on_failure(self, runner, pool, state):
        state.save_pipeline("pipe-8", "issue", "default")
        pool.invoke.return_value = SubagentResult(
            success=False,
            output="",
            error="fail",
            cost_usd=0.0,
        )
        sd1 = _make_stage_def(id="s1", name="S1", category="impl")
        sd2 = _make_stage_def(id="s2", name="S2", category="test")
        n1 = StageNode(id="s1", stage_def=sd1)
        n2 = StageNode(id="s2", stage_def=sd2, depends_on=["s1"])
        results = await runner.run_pipeline_stages([n1, n2], "pipe-8")
        assert len(results) == 1
        assert results[0]["status"] == "FAILED"

    @pytest.mark.asyncio
    async def test_run_stage_with_gate_block(self, state, audit, pool):
        state.save_pipeline("pipe-9", "issue", "default")
        from sdlc.gate import GateDef, GateEngine, GateTrigger

        gate_engine = GateEngine(audit=audit)
        gate_engine.register(
            GateDef(
                id="g1",
                name="Gate1",
                after_stage="s-clarify",
                trigger=GateTrigger.ALWAYS,
                block_conditions={"on_failure": True},
            )
        )
        runner = StageRunner(
            catalog=StageCatalog(),
            state=state,
            audit=audit,
            subagent_pool=pool,
            gate_engine=gate_engine,
        )
        pool.invoke.return_value = SubagentResult(
            success=True,
            output="ok",
            cost_usd=0.0,
        )
        sd = _make_stage_def()
        result = await runner.run_stage(sd, "pipe-9")
        assert result["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_run_pipeline_stages_block_stops_pipeline(self, state, audit, pool):
        state.save_pipeline("pipe-10", "issue", "default")
        from sdlc.gate import GateDef, GateEngine, GateTrigger

        gate_engine = GateEngine(audit=audit)
        gate_engine.register(
            GateDef(
                id="g1",
                name="Gate1",
                after_stage="s1",
                trigger=GateTrigger.ALWAYS,
                block_conditions={"on_failure": True},
            )
        )
        pool.invoke.side_effect = [
            SubagentResult(success=False, output="", error="fail", cost_usd=0.0),
        ]
        sd1 = _make_stage_def(id="s1", name="S1", category="impl")
        sd2 = _make_stage_def(id="s2", name="S2", category="test")
        n1 = StageNode(id="s1", stage_def=sd1)
        n2 = StageNode(id="s2", stage_def=sd2, depends_on=["s1"])
        runner = StageRunner(
            catalog=StageCatalog(),
            state=state,
            audit=audit,
            subagent_pool=pool,
            gate_engine=gate_engine,
        )
        results = await runner.run_pipeline_stages([n1, n2], "pipe-10")
        assert len(results) == 1
        assert results[0]["status"] == "FAILED"
