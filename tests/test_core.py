from unittest.mock import AsyncMock, MagicMock

import pytest

from sdlc.audit import AuditLogger
from sdlc.core.entry_detector import EntryDetector
from sdlc.core.models import EntryKind, EntryPoint, Pipeline, PipelineResult
from sdlc.core.pipeline_builder import PipelineBuilder
from sdlc.core.run_coordinator import RunCoordinator
from sdlc.profile.models import ProfileDef
from sdlc.profile.registry import ProfileRegistry
from sdlc.stage.catalog import StageCatalog
from sdlc.stage.models import StageDef
from sdlc.state import StateStore
from sdlc.subagent.models import SubagentResult


def _make_state(tmp_path):
    return StateStore(tmp_path / "state.db")


def _make_audit(tmp_path):
    return AuditLogger(tmp_path / "audit.jsonl")


def _make_catalog_with_stages(*ids):
    cat = StageCatalog()
    for sid in ids:
        cat.register(StageDef(id=sid, name=sid, category="unknown", subagent="SA-1"))
    return cat


def _make_subagent_pool():
    pool = MagicMock()
    pool.invoke = AsyncMock()
    pool.invoke.return_value = SubagentResult(
        success=True,
        output="done",
        artifacts={},
        cost_usd=0.01,
    )
    return pool


class TestEntryDetector:
    def setup_method(self):
        self.detector = EntryDetector()

    def test_detect_feature(self):
        ep = self.detector.detect("做一个订单查询接口")
        assert ep.kind == EntryKind.FEATURE

    def test_detect_bug(self):
        ep = self.detector.detect("线上报错")
        assert ep.kind == EntryKind.BUG

    def test_detect_hotfix(self):
        ep = self.detector.detect("紧急P0")
        assert ep.kind == EntryKind.HOTFIX

    def test_detect_refactor(self):
        ep = self.detector.detect("重构代码")
        assert ep.kind == EntryKind.REFACTOR

    def test_detect_test(self):
        ep = self.detector.detect("补单测")
        assert ep.kind == EntryKind.TEST

    def test_detect_default_feature(self):
        ep = self.detector.detect("hello world")
        assert ep.kind == EntryKind.FEATURE

    def test_detect_has_confidence(self):
        ep = self.detector.detect("做一个订单查询接口")
        assert isinstance(ep.confidence, float)
        assert ep.confidence > 0

    def test_detect_default_confidence(self):
        ep = self.detector.detect("hello world")
        assert ep.confidence == 0.3

    def test_detect_attachments(self):
        ep = self.detector.detect("做一个功能 @spec.md ./code.py")
        assert "@spec.md" in ep.detected_attachments
        assert "./code.py" in ep.detected_attachments

    def test_detect_raw_input_preserved(self):
        ep = self.detector.detect("重构代码")
        assert ep.raw_input == "重构代码"


class TestPipelineBuilder:
    def setup_method(self):
        self.catalog = _make_catalog_with_stages("s1", "s2", "s3")
        self.builder = PipelineBuilder(self.catalog)
        self.entry = EntryPoint(kind=EntryKind.FEATURE, raw_input="test")
        self.profile = ProfileDef(
            id="test-profile",
            name="Test",
            base_stages=["s1", "s2", "s3"],
        )

    def test_build_creates_pipeline(self):
        pipeline = self.builder.build(self.entry, self.profile)
        assert isinstance(pipeline, Pipeline)
        assert pipeline.entry is self.entry
        assert pipeline.profile is self.profile
        assert pipeline.status == "NEW"

    def test_build_pipeline_id_contains_kind(self):
        pipeline = self.builder.build(self.entry, self.profile)
        assert pipeline.id.startswith("feature-")

    def test_build_custom_pipeline_id(self):
        pipeline = self.builder.build(self.entry, self.profile, pipeline_id="my-pipe")
        assert pipeline.id == "my-pipe"

    def test_build_stage_nodes(self):
        pipeline = self.builder.build(self.entry, self.profile)
        assert len(pipeline.stages) == 3
        assert [n.id for n in pipeline.stages] == ["s1", "s2", "s3"]

    def test_build_sequential_dependencies(self):
        pipeline = self.builder.build(self.entry, self.profile)
        assert pipeline.stages[0].depends_on == []
        assert pipeline.stages[1].depends_on == ["s1"]
        assert pipeline.stages[2].depends_on == ["s2"]

    def test_build_skip_stages(self):
        profile = ProfileDef(
            id="skip-test",
            name="Skip",
            base_stages=["s1", "s2", "s3"],
            skip_stages=["s2"],
        )
        pipeline = self.builder.build(self.entry, profile)
        ids = [n.id for n in pipeline.stages]
        assert "s2" not in ids
        assert ids == ["s1", "s3"]

    def test_build_extra_stages(self):
        profile = ProfileDef(
            id="extra-test",
            name="Extra",
            base_stages=["s1"],
            extra_stages=["s2"],
        )
        pipeline = self.builder.build(self.entry, profile)
        ids = [n.id for n in pipeline.stages]
        assert ids == ["s1", "s2"]

    def test_build_skip_and_extra(self):
        profile = ProfileDef(
            id="combo",
            name="Combo",
            base_stages=["s1", "s2", "s3"],
            skip_stages=["s2"],
            extra_stages=["s4"],
        )
        pipeline = self.builder.build(self.entry, profile)
        ids = [n.id for n in pipeline.stages]
        assert ids == ["s1", "s3", "s4"]

    def test_build_missing_stage_gets_fallback_def(self):
        profile = ProfileDef(
            id="missing",
            name="Missing",
            base_stages=["unknown-stage"],
        )
        pipeline = self.builder.build(self.entry, profile)
        assert len(pipeline.stages) == 1
        node = pipeline.stages[0]
        assert node.id == "unknown-stage"
        assert node.stage_def is not None
        assert node.stage_def.name == "unknown-stage"

    def test_build_all_nodes_pending(self):
        pipeline = self.builder.build(self.entry, self.profile)
        assert all(n.status == "PENDING" for n in pipeline.stages)

    def test_build_has_timestamps(self):
        pipeline = self.builder.build(self.entry, self.profile)
        assert pipeline.created_at != ""
        assert pipeline.updated_at != ""


class TestRunCoordinator:
    @pytest.fixture
    def tmp(self, tmp_path):
        return tmp_path

    @pytest.fixture
    def state(self, tmp):
        return _make_state(tmp)

    @pytest.fixture
    def audit(self, tmp):
        return _make_audit(tmp)

    @pytest.fixture
    def catalog(self):
        return _make_catalog_with_stages("s1", "s2", "s3")

    @pytest.fixture
    def pool(self):
        return _make_subagent_pool()

    @pytest.fixture
    def profile_registry(self):
        reg = ProfileRegistry()
        reg.register(
            ProfileDef(
                id="feature",
                name="Feature",
                entry_kinds=["feature"],
                base_stages=["s1", "s2", "s3"],
                severity="P2",
            )
        )
        return reg

    @pytest.fixture
    def coordinator(self, state, audit, catalog, pool, profile_registry):
        return RunCoordinator(
            state=state,
            audit=audit,
            catalog=catalog,
            subagent_pool=pool,
            profile_registry=profile_registry,
        )

    @pytest.mark.asyncio
    async def test_run_returns_pipeline_result(self, coordinator):
        result = await coordinator.run("开发一个新功能")
        assert isinstance(result, PipelineResult)
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_run_pipeline_id_in_result(self, coordinator):
        result = await coordinator.run("开发一个新功能")
        assert result.pipeline_id != ""
        assert "feature" in result.pipeline_id

    @pytest.mark.asyncio
    async def test_run_detects_entry(self, coordinator, audit):
        await coordinator.run("开发一个新功能")
        events = list(audit.query(event_type="entry_detected"))
        assert len(events) >= 1
        assert events[0]["payload"]["kind"] == "feature"

    @pytest.mark.asyncio
    async def test_run_resolves_profile(self, coordinator, audit):
        await coordinator.run("开发一个新功能")
        events = list(audit.query(event_type="profile_resolved"))
        assert len(events) >= 1
        assert events[0]["payload"]["profile_id"] == "feature"

    @pytest.mark.asyncio
    async def test_run_emits_pipeline_start(self, coordinator, audit):
        await coordinator.run("开发一个新功能")
        events = list(audit.query(event_type="pipeline_start"))
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_run_emits_pipeline_end(self, coordinator, audit):
        await coordinator.run("开发一个新功能")
        events = list(audit.query(event_type="pipeline_end"))
        assert len(events) >= 1
        assert events[0]["payload"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_saves_pipeline_to_state(self, coordinator, state):
        await coordinator.run("开发一个新功能")
        pipelines = state.list_pipelines()
        assert len(pipelines) >= 1
        assert pipelines[0].status == "COMPLETED"

    @pytest.mark.asyncio
    async def test_run_with_explicit_profile(self, coordinator, state, audit):
        result = await coordinator.run("做点什么", profile_id="feature")
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_run_total_cost(self, coordinator):
        result = await coordinator.run("开发一个新功能")
        assert result.total_cost_usd > 0

    @pytest.mark.asyncio
    async def test_run_subagent_invoked(self, coordinator, pool):
        await coordinator.run("开发一个新功能")
        assert pool.invoke.call_count == 3

    @pytest.mark.asyncio
    async def test_run_failed_status(self, state, audit, catalog, pool, profile_registry):
        pool.invoke.return_value = SubagentResult(
            success=False,
            output="",
            error="fail",
            cost_usd=0.01,
        )
        coord = RunCoordinator(
            state=state,
            audit=audit,
            catalog=catalog,
            subagent_pool=pool,
            profile_registry=profile_registry,
        )
        result = await coord.run("开发一个新功能")
        assert result.status == "failed"
