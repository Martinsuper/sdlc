from pathlib import Path

from sdlc.gate.engine import GateEngine
from sdlc.gate.models import GateAction, GateDecision, GateDef, GateTrigger
from sdlc.gate.triggers import should_trigger


class TestGateAction:
    def test_has_four_members(self):
        assert len(GateAction) == 4

    def test_values(self):
        assert GateAction.AUTO_PASS == "auto_pass"
        assert GateAction.MANUAL_REVIEW == "manual_review"
        assert GateAction.BLOCK == "block"
        assert GateAction.ESCALATE == "escalate"


class TestGateTrigger:
    def test_has_six_members(self):
        assert len(GateTrigger) == 6

    def test_values(self):
        assert GateTrigger.ALWAYS == "always"
        assert GateTrigger.ON_SEVERITY == "on_severity"
        assert GateTrigger.ON_ARTIFACT == "on_artifact"
        assert GateTrigger.ON_RULE_VIOLATION == "on_rule_violation"
        assert GateTrigger.ON_FAILURE == "on_failure"
        assert GateTrigger.ON_STAGE_END == "on_stage_end"


class TestGateDef:
    def test_create(self):
        gd = GateDef(id="g1", name="gate1", after_stage="build")
        assert gd.id == "g1"
        assert gd.name == "gate1"
        assert gd.after_stage == "build"
        assert gd.trigger == GateTrigger.ALWAYS
        assert gd.reviewer == ""
        assert gd.deadline_hours == 4
        assert gd.severities == []
        assert gd.auto_pass_conditions == {}
        assert gd.block_conditions == {}

    def test_create_with_optional_fields(self):
        gd = GateDef(
            id="g2",
            name="gate2",
            after_stage="test",
            trigger=GateTrigger.ON_SEVERITY,
            reviewer="alice",
            deadline_hours=8,
            severities=["P0", "P1"],
            auto_pass_conditions={"no_violations": True},
            block_conditions={"on_failure": True},
        )
        assert gd.trigger == GateTrigger.ON_SEVERITY
        assert gd.reviewer == "alice"
        assert gd.deadline_hours == 8
        assert gd.severities == ["P0", "P1"]


class TestGateDecision:
    def test_create(self):
        d = GateDecision(gate_id="g1", action=GateAction.MANUAL_REVIEW)
        assert d.gate_id == "g1"
        assert d.action == GateAction.MANUAL_REVIEW
        assert d.reason == ""
        assert d.reviewer == ""
        assert d.deadline == ""
        assert d.metadata == {}

    def test_create_with_optional_fields(self):
        d = GateDecision(
            gate_id="g1",
            action=GateAction.BLOCK,
            reason="violation",
            reviewer="bob",
            deadline="2025-01-01T00:00:00Z",
            metadata={"key": "val"},
        )
        assert d.reason == "violation"
        assert d.deadline == "2025-01-01T00:00:00Z"


class TestShouldTrigger:
    def test_always_returns_true(self):
        gd = GateDef(id="g", name="g", after_stage="s", trigger=GateTrigger.ALWAYS)
        assert should_trigger(gd, {}) is True

    def test_on_severity_match(self):
        gd = GateDef(
            id="g",
            name="g",
            after_stage="s",
            trigger=GateTrigger.ON_SEVERITY,
            severities=["P0", "P1"],
        )
        assert should_trigger(gd, {"severity": "P0"}) is True

    def test_on_severity_no_match(self):
        gd = GateDef(
            id="g",
            name="g",
            after_stage="s",
            trigger=GateTrigger.ON_SEVERITY,
            severities=["P0", "P1"],
        )
        assert should_trigger(gd, {"severity": "P3"}) is False

    def test_on_severity_no_context(self):
        gd = GateDef(
            id="g",
            name="g",
            after_stage="s",
            trigger=GateTrigger.ON_SEVERITY,
            severities=["P0"],
        )
        assert should_trigger(gd, {}) is False

    def test_on_artifact_match(self):
        gd = GateDef(
            id="g",
            name="g",
            after_stage="s",
            trigger=GateTrigger.ON_ARTIFACT,
            auto_pass_conditions={"artifact_types": ["docker"]},
        )
        assert should_trigger(gd, {"artifact_types": ["docker", "wheel"]}) is True

    def test_on_artifact_no_match(self):
        gd = GateDef(
            id="g",
            name="g",
            after_stage="s",
            trigger=GateTrigger.ON_ARTIFACT,
            auto_pass_conditions={"artifact_types": ["docker"]},
        )
        assert should_trigger(gd, {"artifact_types": ["wheel"]}) is False

    def test_on_artifact_no_target_types_defaults_to_any(self):
        gd = GateDef(
            id="g",
            name="g",
            after_stage="s",
            trigger=GateTrigger.ON_ARTIFACT,
        )
        assert should_trigger(gd, {"artifact_types": ["wheel"]}) is True
        assert should_trigger(gd, {"artifact_types": []}) is False

    def test_on_failure_triggered(self):
        gd = GateDef(id="g", name="g", after_stage="s", trigger=GateTrigger.ON_FAILURE)
        assert should_trigger(gd, {"stage_status": "FAILED"}) is True

    def test_on_failure_not_triggered(self):
        gd = GateDef(id="g", name="g", after_stage="s", trigger=GateTrigger.ON_FAILURE)
        assert should_trigger(gd, {"stage_status": "SUCCESS"}) is False

    def test_on_stage_end_match(self):
        gd = GateDef(id="g", name="g", after_stage="build", trigger=GateTrigger.ON_STAGE_END)
        assert should_trigger(gd, {"stage_id": "build"}) is True

    def test_on_stage_end_no_match(self):
        gd = GateDef(id="g", name="g", after_stage="build", trigger=GateTrigger.ON_STAGE_END)
        assert should_trigger(gd, {"stage_id": "test"}) is False

    def test_on_rule_violation_with_must(self):
        gd = GateDef(
            id="g",
            name="g",
            after_stage="s",
            trigger=GateTrigger.ON_RULE_VIOLATION,
            auto_pass_conditions={"min_violation_level": "MUST"},
        )
        ctx = {"rule_violations": [{"id": "r1", "level": "MUST"}]}
        assert should_trigger(gd, ctx) is True

    def test_on_rule_violation_without_must(self):
        gd = GateDef(
            id="g",
            name="g",
            after_stage="s",
            trigger=GateTrigger.ON_RULE_VIOLATION,
            auto_pass_conditions={"min_violation_level": "MUST"},
        )
        ctx = {"rule_violations": [{"id": "r1", "level": "SHOULD"}]}
        assert should_trigger(gd, ctx) is False


class TestGateEngine:
    def test_register_and_list(self):
        engine = GateEngine()
        gd = GateDef(id="g1", name="g1", after_stage="build")
        engine.register(gd)
        assert len(engine.list_gates()) == 1
        assert engine.list_gates()[0].id == "g1"

    def test_register_all(self):
        engine = GateEngine()
        gates = [
            GateDef(id="g1", name="g1", after_stage="build"),
            GateDef(id="g2", name="g2", after_stage="test"),
        ]
        engine.register_all(gates)
        assert len(engine.list_gates()) == 2

    def test_evaluate_always_returns_manual_review(self):
        engine = GateEngine()
        engine.register(GateDef(id="g1", name="g1", after_stage="build"))
        decision = engine.evaluate("build", {})
        assert decision is not None
        assert decision.action == GateAction.MANUAL_REVIEW
        assert decision.gate_id == "g1"

    def test_evaluate_auto_pass(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="build",
                auto_pass_conditions={"no_violations": True},
            )
        )
        decision = engine.evaluate("build", {"stage_status": "SUCCESS"})
        assert decision is not None
        assert decision.action == GateAction.AUTO_PASS

    def test_evaluate_auto_pass_no_violations_fails_when_violations_exist(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="build",
                auto_pass_conditions={"no_violations": True},
            )
        )
        decision = engine.evaluate("build", {"rule_violations": [{"id": "r1", "level": "MUST"}]})
        assert decision is not None
        assert decision.action != GateAction.AUTO_PASS

    def test_evaluate_block_on_must_violation(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="build",
                block_conditions={"on_must_violation": True},
            )
        )
        ctx = {"rule_violations": [{"id": "r1", "level": "MUST"}]}
        decision = engine.evaluate("build", ctx)
        assert decision is not None
        assert decision.action == GateAction.BLOCK
        assert "r1" in decision.reason

    def test_evaluate_block_on_failure(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="build",
                block_conditions={"on_failure": True},
            )
        )
        decision = engine.evaluate("build", {"stage_status": "FAILED"})
        assert decision is not None
        assert decision.action == GateAction.BLOCK

    def test_evaluate_no_applicable_gate(self):
        engine = GateEngine()
        engine.register(GateDef(id="g1", name="g1", after_stage="build"))
        decision = engine.evaluate("test", {})
        assert decision is None

    def test_evaluate_non_auto_pass_takes_priority(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g-auto",
                name="auto",
                after_stage="build",
                auto_pass_conditions={"no_violations": True},
            )
        )
        engine.register(
            GateDef(
                id="g-block",
                name="block",
                after_stage="build",
                block_conditions={"on_failure": True},
            )
        )
        decision = engine.evaluate("build", {"stage_status": "FAILED"})
        assert decision is not None
        assert decision.action == GateAction.BLOCK
        assert decision.gate_id == "g-block"

    def test_evaluate_all_auto_pass_returns_last(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="build",
                auto_pass_conditions={"no_violations": True},
            )
        )
        engine.register(
            GateDef(
                id="g2",
                name="g2",
                after_stage="build",
                auto_pass_conditions={"no_failures": True},
            )
        )
        decision = engine.evaluate("build", {"stage_status": "SUCCESS"})
        assert decision is not None
        assert decision.action == GateAction.AUTO_PASS
        assert decision.gate_id == "g2"

    def test_decision_contains_deadline(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="build",
                deadline_hours=4,
            )
        )
        decision = engine.evaluate("build", {})
        assert decision is not None
        assert decision.deadline != ""
        assert decision.deadline.endswith("Z")

    def test_decision_zero_deadline_no_deadline(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="build",
                deadline_hours=0,
            )
        )
        decision = engine.evaluate("build", {})
        assert decision is not None
        assert decision.deadline == ""

    def test_evaluate_with_audit(self, tmp_path: Path):
        from sdlc.audit.logger import AuditLogger

        log_path = tmp_path / "audit.jsonl"
        audit = AuditLogger(log_path)
        engine = GateEngine(audit=audit)
        engine.register(GateDef(id="g1", name="g1", after_stage="build"))
        engine.evaluate("build", {"pipeline_id": "p1"})
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 1
        import json

        event = json.loads(lines[0])
        assert event["type"] == "gate_triggered"
        assert event["pipeline_id"] == "p1"
