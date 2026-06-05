"""End-to-end integration tests for the sdlc project.

These tests verify the full pipeline works together:
init -> entry detection -> profile resolution -> pipeline build
-> stage execution (mock LLM) -> state/audit verification.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from sdlc.adapter.detector import AdapterDetector
from sdlc.adapter.dongboot import register_dongboot
from sdlc.adapter.registry import AdapterRegistry
from sdlc.audit import AuditEventType, AuditLogger
from sdlc.core.entry_detector import EntryDetector
from sdlc.core.models import EntryKind
from sdlc.core.pipeline_builder import PipelineBuilder
from sdlc.core.run_coordinator import RunCoordinator
from sdlc.gate import GateEngine
from sdlc.kb.knowledge_base import KnowledgeBase
from sdlc.kb.writer import KBWriter
from sdlc.llm.models import CompletionResponse, ContentBlock, Usage
from sdlc.profile import ProfileRegistry, register_builtins
from sdlc.rule.engine import RuleEngine
from sdlc.rule.models import RuleLevel
from sdlc.stage import StageCatalog
from sdlc.stage.models import StageDef
from sdlc.state import StateStore
from sdlc.state.models import StageResult
from sdlc.subagent import SubagentPool, SubagentRegistry
from sdlc.subagent.builtin import register_builtins as register_subagent_builtins
from sdlc.utils.yaml_io import save_yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_llm() -> AsyncMock:
    """Create a mock MultiLLMClient that returns canned responses."""
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(
        return_value=CompletionResponse(
            id="mock-resp-1",
            model="mock-model",
            content=[
                ContentBlock(type="text", text="Mock LLM response: task completed successfully."),
            ],
            stop_reason="end_turn",
            usage=Usage(input_tokens=10, output_tokens=20),
            cost_usd=0.001,
            duration_ms=100,
        )
    )
    return mock_llm


def _make_subagent_pool(tmp_path: Path) -> SubagentPool:
    """Create a SubagentPool with mock LLM and builtin agents."""
    registry = SubagentRegistry()
    register_subagent_builtins(registry)
    audit = AuditLogger(tmp_path / "audit.jsonl")
    mock_llm = _make_mock_llm()
    return SubagentPool(registry=registry, llm=mock_llm, audit=audit)


def _register_builtin_stages(catalog: StageCatalog) -> None:
    """Register the standard builtin stages into the catalog."""
    stage_defs = [
        StageDef(id="s-clarify", name="Clarify", category="planning", subagent="SA-1"),
        StageDef(id="s-design", name="Design", category="planning", subagent="SA-2"),
        StageDef(id="s-impl-backend", name="Implement Backend", category="implementation", subagent="SA-3"),
        StageDef(id="s-impl-frontend", name="Implement Frontend", category="implementation", subagent="SA-4"),
        StageDef(id="s-unit-test", name="Unit Test", category="testing", subagent="SA-5"),
        StageDef(id="s-cr", name="Code Review", category="review", subagent="SA-6"),
        StageDef(id="s-package", name="Package", category="deployment", subagent="SA-7"),
        StageDef(id="s-deploy", name="Deploy", category="deployment", subagent="SA-7"),
        StageDef(id="s-monitor-setup", name="Monitor Setup", category="operations", subagent="SA-7"),
    ]
    for sd in stage_defs:
        catalog.register(sd)


# ---------------------------------------------------------------------------
# Test 1: Full pipeline happy path
# ---------------------------------------------------------------------------


async def test_pipeline_happy_path(tmp_path: Path) -> None:
    """Test a complete pipeline from entry detection to completion."""
    # 1. Set up StateStore + AuditLogger
    state = StateStore(tmp_path / "state.db")
    audit = AuditLogger(tmp_path / "audit.jsonl")

    # 2. Set up StageCatalog (with builtin stages)
    catalog = StageCatalog()
    _register_builtin_stages(catalog)

    # 3. Set up ProfileRegistry + register_builtins
    profile_registry = ProfileRegistry()
    register_builtins(profile_registry)

    # 4. Set up AdapterRegistry + register_dongboot
    adapter_registry = AdapterRegistry()
    register_dongboot(adapter_registry)

    # 5. Set up GateEngine
    gate_engine = GateEngine(audit=audit)

    # 6. Set up SubagentPool with mock LLM
    subagent_pool = _make_subagent_pool(tmp_path)

    # 7. Create RunCoordinator with all deps
    coordinator = RunCoordinator(
        state=state,
        audit=audit,
        catalog=catalog,
        subagent_pool=subagent_pool,
        gate_engine=gate_engine,
        profile_registry=profile_registry,
        adapter_registry=adapter_registry,
    )

    # 8. Run: await coordinator.run("做一个订单查询接口")
    result = await coordinator.run("做一个订单查询接口")

    # 9. Verify: pipeline created in state, stages executed, audit events emitted
    assert result.pipeline_id
    assert result.status in ("completed", "paused", "failed")

    pipeline = state.load_pipeline(result.pipeline_id)
    assert pipeline is not None
    assert pipeline.status in ("COMPLETED", "PAUSED", "FAILED")

    # Verify audit events were emitted (some events have pipeline_id, some don't)
    pipeline_events = list(audit.query(pipeline_id=result.pipeline_id))
    assert len(pipeline_events) >= 2  # pipeline_start + pipeline_end at minimum

    # ENTRY_DETECTED is emitted before pipeline_id is known (no pipeline_id)
    entry_events = list(audit.query(event_type=AuditEventType.ENTRY_DETECTED))
    assert len(entry_events) >= 1

    # PROFILE_RESOLVED is also emitted before pipeline_id is known
    profile_events = list(audit.query(event_type=AuditEventType.PROFILE_RESOLVED))
    assert len(profile_events) >= 1

    # PIPELINE_START and PIPELINE_END have pipeline_id
    start_events = list(audit.query(event_type=AuditEventType.PIPELINE_START, pipeline_id=result.pipeline_id))
    assert len(start_events) >= 1

    end_events = list(audit.query(event_type=AuditEventType.PIPELINE_END, pipeline_id=result.pipeline_id))
    assert len(end_events) >= 1

    # 10. Verify final status is "completed" or "paused"
    # With mock LLM returning success, all stages should succeed
    assert result.status in ("completed", "paused")


# ---------------------------------------------------------------------------
# Test 2: Entry detection integration
# ---------------------------------------------------------------------------


def test_entry_detection_to_profile(tmp_path: Path) -> None:
    """Test entry detection resolves to correct profile."""
    detector = EntryDetector()
    registry = ProfileRegistry()
    register_builtins(registry)

    # Test each entry kind resolves
    test_cases = [
        ("做一个新功能", EntryKind.FEATURE),
        ("线上报错了5xx异常", EntryKind.BUG),
        ("紧急修复线上挂了", EntryKind.HOTFIX),
        ("重构一下代码结构", EntryKind.REFACTOR),
    ]
    for text, expected_kind in test_cases:
        entry = detector.detect(text)
        assert entry.kind == expected_kind
        profile = registry.resolve(entry.kind.value)
        assert profile is not None


# ---------------------------------------------------------------------------
# Test 3: Adapter detection + profile resolution
# ---------------------------------------------------------------------------


def test_adapter_detection_with_dongboot(tmp_path: Path) -> None:
    """Test that dongboot adapter is detected for a Java project."""
    # Create a fake pom.xml with dong-boot-starter
    pom_dir = tmp_path / "project"
    pom_dir.mkdir()
    pom = pom_dir / "pom.xml"
    pom.write_text(
        "<project><dependencies><dependency>"
        "<artifactId>dong-boot-starter</artifactId>"
        "</dependency></dependencies></project>"
    )

    registry = AdapterRegistry()
    register_dongboot(registry)
    detector = AdapterDetector(registry)
    detected = detector.detect(pom_dir)

    assert len(detected) == 1
    assert detected[0].id == "dongboot"


# ---------------------------------------------------------------------------
# Test 4: Pipeline build from entry
# ---------------------------------------------------------------------------


def test_pipeline_build_from_entry(tmp_path: Path) -> None:
    """Test building a pipeline from an entry point."""
    detector = EntryDetector()
    entry = detector.detect("做一个新功能")

    catalog = StageCatalog()
    _register_builtin_stages(catalog)

    registry = ProfileRegistry()
    register_builtins(registry)
    profile = registry.resolve(entry.kind.value)

    builder = PipelineBuilder(catalog)
    pipeline = builder.build(entry, profile)

    assert pipeline is not None
    assert pipeline.id
    assert len(pipeline.stages) > 0
    # Verify stages match the profile's base_stages
    stage_ids = [s.id for s in pipeline.stages]
    for base_stage in profile.base_stages:
        assert base_stage in stage_ids


# ---------------------------------------------------------------------------
# Test 5: State + Audit round-trip
# ---------------------------------------------------------------------------


def test_state_audit_roundtrip(tmp_path: Path) -> None:
    """Test that state and audit are consistent after pipeline operations."""
    store = StateStore(tmp_path / "state.db")
    audit = AuditLogger(tmp_path / "audit.jsonl")

    # Save a pipeline
    store.save_pipeline("test-1", "feature", "new-feature", "RUNNING")
    audit.emit(AuditEventType.PIPELINE_START, {"id": "test-1"}, pipeline_id="test-1")

    # Save a stage result
    store.save_stage_result(
        StageResult(
            id="test-1-s-clarify",
            pipeline_id="test-1",
            stage_def_id="s-clarify",
            status="SUCCESS",
            started_at="2026-06-05T10:00:00Z",
            finished_at="2026-06-05T10:03:00Z",
        )
    )
    audit.emit(
        AuditEventType.STAGE_END,
        {"stage": "s-clarify", "status": "SUCCESS"},
        pipeline_id="test-1",
    )

    # Verify
    pipeline = store.load_pipeline("test-1")
    assert pipeline is not None
    assert pipeline.status == "RUNNING"

    events = list(audit.query(pipeline_id="test-1"))
    assert len(events) == 2

    store.update_pipeline_status("test-1", "COMPLETED")
    pipeline = store.load_pipeline("test-1")
    assert pipeline.status == "COMPLETED"


# ---------------------------------------------------------------------------
# Test 6: sdlc init creates KB structure
# ---------------------------------------------------------------------------


def test_sdlc_init_creates_kb(tmp_path: Path) -> None:
    """Test that 'sdlc init' creates the KB directory structure."""
    from click.testing import CliRunner

    from sdlc.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["init", str(tmp_path)])
    assert result.exit_code == 0

    # Verify directory structure
    assert (tmp_path / ".sdlc").exists()
    assert (tmp_path / "doc" / "kb").exists()
    assert (tmp_path / "doc" / "kb" / "rules").exists()
    assert (tmp_path / "doc" / "kb" / "standards").exists()
    assert (tmp_path / "doc" / "kb" / "architecture").exists()
    assert (tmp_path / "doc" / "kb" / "conventions.md").exists()
    assert (tmp_path / "doc" / "kb" / "rules" / "MUST.yaml").exists()


# ---------------------------------------------------------------------------
# Test 7: sdlc doctor checks pass
# ---------------------------------------------------------------------------


def test_sdlc_doctor_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that 'sdlc doctor' runs all checks."""
    from click.testing import CliRunner

    from sdlc.cli.main import cli

    monkeypatch.setenv("HOME", str(tmp_path))
    # Create .sdlc dir so doctor finds it
    (tmp_path / ".sdlc").mkdir(exist_ok=True)

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    # Should pass (Python >= 3.11, uv may or may not be installed)
    assert "Python >= 3.11" in result.output


# ---------------------------------------------------------------------------
# Test 8: KnowledgeBase round-trip
# ---------------------------------------------------------------------------


def test_kb_roundtrip(tmp_path: Path) -> None:
    """Test KnowledgeBase create -> read -> update -> verify."""
    kb_root = tmp_path / "doc" / "kb"
    kb_root.mkdir(parents=True)

    # Create some KB files
    (kb_root / "conventions.md").write_text("# Conventions\n")
    rules_dir = kb_root / "rules"
    rules_dir.mkdir(exist_ok=True)
    (rules_dir / "MUST.yaml").write_text("[]\n")

    audit = AuditLogger(tmp_path / "audit.jsonl")
    kb = KnowledgeBase(kb_root)

    # Read
    assert kb.exists("conventions.md")
    content = kb.read_content("conventions.md")
    assert "Conventions" in content

    # Write
    writer = KBWriter(kb, audit)
    deltas = writer.update_after_stage(
        "s-clarify",
        [
            {
                "target": "conventions.md",
                "operation": "append",
                "content": "## New Section\nAdded by s-clarify\n",
            }
        ],
    )
    # conventions.md is human-only so it should be skipped
    assert len(deltas) == 1
    assert deltas[0].skipped is True

    # Stats
    layers = kb.list_layers()
    assert len(layers) >= 1


# ---------------------------------------------------------------------------
# Test 9: Rule engine integration
# ---------------------------------------------------------------------------


def test_rule_engine_with_yaml(tmp_path: Path) -> None:
    """Test loading rules from YAML and checking."""
    # Create a rules file
    rules_file = tmp_path / "MUST.yaml"
    save_yaml(
        rules_file,
        [
            {
                "id": "test-no-sleep",
                "level": "MUST",
                "category": "coding",
                "description": "No Thread.sleep",
                "enforcer": "cr",
                "pattern": "Thread\\.sleep",
                "message": "Use scheduled executor",
                "action": "block",
                "severity": "P1",
            }
        ],
    )

    engine = RuleEngine()
    count = engine.load_from_yaml(rules_file)
    assert count == 1

    rules = engine.list_rules(level=RuleLevel.MUST)
    assert len(rules) == 1
    assert rules[0].id == "test-no-sleep"

    # Check with context
    violations = engine.check_all(
        "s-impl-backend",
        {
            "files": [{"path": "Test.java", "content": "Thread.sleep(1000);"}],
        },
    )
    # The CREnforcer expects files as a dict, not a list
    # Let's use the correct format
    violations = engine.check_all(
        "s-impl-backend",
        {
            "files": {"Test.java": "Thread.sleep(1000);"},
        },
    )
    assert len(violations) == 1


# ---------------------------------------------------------------------------
# Test 10: Full CLI workflow
# ---------------------------------------------------------------------------


def test_cli_full_workflow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test: init -> stage list -> adapter list -> profile list -> agent list -> version."""
    from click.testing import CliRunner

    from sdlc.cli.main import cli

    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".sdlc").mkdir(exist_ok=True)

    runner = CliRunner()

    # Init
    r = runner.invoke(cli, ["init", str(tmp_path), "--force"])
    assert r.exit_code == 0

    # Stage list
    r = runner.invoke(cli, ["stage", "list"])
    assert r.exit_code == 0

    # Adapter list
    r = runner.invoke(cli, ["adapter", "list"])
    assert r.exit_code == 0

    # Profile list
    r = runner.invoke(cli, ["profile", "list"])
    assert r.exit_code == 0

    # Agent list
    r = runner.invoke(cli, ["agent", "list"])
    assert r.exit_code == 0

    # Version
    r = runner.invoke(cli, ["version"])
    assert "0.4.0" in r.output
