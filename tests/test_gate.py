from pathlib import Path

from sdlc.gate.catalog import GateCatalog
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
    def test_has_nine_members(self):
        assert len(GateTrigger) == 9

    def test_values(self):
        assert GateTrigger.ALWAYS == "always"
        assert GateTrigger.ON_SEVERITY == "on_severity"
        assert GateTrigger.ON_ARTIFACT == "on_artifact"
        assert GateTrigger.ON_RULE_VIOLATION == "on_rule_violation"
        assert GateTrigger.ON_FAILURE == "on_failure"
        assert GateTrigger.ON_STAGE_END == "on_stage_end"
        assert GateTrigger.ON_RELEASE == "on_release"
        assert GateTrigger.ON_COMPLIANCE_REQUIRED == "on_compliance_required"
        assert GateTrigger.ON_PROFILE == "on_profile"


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
        assert should_trigger(gd, {"stage_status": "COMPLETED"}) is False

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
        decision = engine.evaluate("build", {"stage_status": "COMPLETED"})
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
        decision = engine.evaluate("build", {"stage_status": "COMPLETED"})
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


class TestNewTriggers:
    def test_on_release_triggered(self):
        gd = GateDef(id="g", name="g", after_stage="s", trigger=GateTrigger.ON_RELEASE)
        assert should_trigger(gd, {"is_release": True}) is True

    def test_on_release_not_triggered(self):
        gd = GateDef(id="g", name="g", after_stage="s", trigger=GateTrigger.ON_RELEASE)
        assert should_trigger(gd, {"is_release": False}) is False

    def test_on_release_missing_context(self):
        gd = GateDef(id="g", name="g", after_stage="s", trigger=GateTrigger.ON_RELEASE)
        assert should_trigger(gd, {}) is False

    def test_on_compliance_required_triggered(self):
        gd = GateDef(id="g", name="g", after_stage="s", trigger=GateTrigger.ON_COMPLIANCE_REQUIRED)
        assert should_trigger(gd, {"compliance_required": True}) is True

    def test_on_compliance_required_not_triggered(self):
        gd = GateDef(id="g", name="g", after_stage="s", trigger=GateTrigger.ON_COMPLIANCE_REQUIRED)
        assert should_trigger(gd, {"compliance_required": False}) is False

    def test_on_compliance_required_missing_context(self):
        gd = GateDef(id="g", name="g", after_stage="s", trigger=GateTrigger.ON_COMPLIANCE_REQUIRED)
        assert should_trigger(gd, {}) is False

    def test_on_profile_match(self):
        gd = GateDef(
            id="g",
            name="g",
            after_stage="s",
            trigger=GateTrigger.ON_PROFILE,
            profiles=["new-feature", "hotfix"],
        )
        assert should_trigger(gd, {"profile": "new-feature"}) is True

    def test_on_profile_match_hotfix(self):
        gd = GateDef(
            id="g",
            name="g",
            after_stage="s",
            trigger=GateTrigger.ON_PROFILE,
            profiles=["new-feature", "hotfix"],
        )
        assert should_trigger(gd, {"profile": "hotfix"}) is True

    def test_on_profile_no_match(self):
        gd = GateDef(
            id="g",
            name="g",
            after_stage="s",
            trigger=GateTrigger.ON_PROFILE,
            profiles=["new-feature", "hotfix"],
        )
        assert should_trigger(gd, {"profile": "bugfix"}) is False

    def test_on_profile_missing_context(self):
        gd = GateDef(
            id="g",
            name="g",
            after_stage="s",
            trigger=GateTrigger.ON_PROFILE,
            profiles=["new-feature", "hotfix"],
        )
        assert should_trigger(gd, {}) is False

    def test_on_profile_empty_profiles(self):
        gd = GateDef(
            id="g",
            name="g",
            after_stage="s",
            trigger=GateTrigger.ON_PROFILE,
            profiles=[],
        )
        assert should_trigger(gd, {"profile": "new-feature"}) is False


class TestNewBlockConditions:
    def test_block_on_coverage_below_threshold(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="s-test",
                block_conditions={"coverage_below_threshold": True},
            )
        )
        decision = engine.evaluate("s-test", {"test_coverage": 50, "coverage_threshold": 80})
        assert decision is not None
        assert decision.action == GateAction.BLOCK
        assert "50%" in decision.reason
        assert "80%" in decision.reason

    def test_no_block_on_coverage_above_threshold(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="s-test",
                block_conditions={"coverage_below_threshold": True},
            )
        )
        decision = engine.evaluate("s-test", {"test_coverage": 90, "coverage_threshold": 80})
        assert decision is not None
        assert decision.action != GateAction.BLOCK

    def test_block_on_p0_violation(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="s-deploy",
                block_conditions={"on_p0_violation": True},
            )
        )
        ctx = {"rule_violations": [{"id": "r1", "severity": "P0"}]}
        decision = engine.evaluate("s-deploy", ctx)
        assert decision is not None
        assert decision.action == GateAction.BLOCK
        assert "r1" in decision.reason

    def test_no_block_without_p0_violation(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="s-deploy",
                block_conditions={"on_p0_violation": True},
            )
        )
        ctx = {"rule_violations": [{"id": "r1", "severity": "P1"}]}
        decision = engine.evaluate("s-deploy", ctx)
        assert decision is not None
        assert decision.action != GateAction.BLOCK

    def test_block_on_compliance_violation(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="s-design",
                block_conditions={"on_compliance_violation": True},
            )
        )
        ctx = {"compliance_violations": ["GDPR-001"]}
        decision = engine.evaluate("s-design", ctx)
        assert decision is not None
        assert decision.action == GateAction.BLOCK
        assert "GDPR-001" in decision.reason

    def test_no_block_without_compliance_violation(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="s-design",
                block_conditions={"on_compliance_violation": True},
            )
        )
        decision = engine.evaluate("s-design", {"compliance_violations": []})
        assert decision is not None
        assert decision.action != GateAction.BLOCK

    def test_block_on_architecture_violation(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="s-design",
                block_conditions={"on_architecture_violation": True},
            )
        )
        ctx = {"architecture_violations": ["ARCH-001"]}
        decision = engine.evaluate("s-design", ctx)
        assert decision is not None
        assert decision.action == GateAction.BLOCK
        assert "ARCH-001" in decision.reason

    def test_no_block_without_architecture_violation(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="g1",
                name="g1",
                after_stage="s-design",
                block_conditions={"on_architecture_violation": True},
            )
        )
        decision = engine.evaluate("s-design", {"architecture_violations": []})
        assert decision is not None
        assert decision.action != GateAction.BLOCK


class TestGateDefProfiles:
    def test_default_profiles_empty(self):
        gd = GateDef(id="g1", name="gate1", after_stage="build")
        assert gd.profiles == []

    def test_profiles_set(self):
        gd = GateDef(
            id="g1",
            name="gate1",
            after_stage="build",
            profiles=["new-feature", "hotfix"],
        )
        assert gd.profiles == ["new-feature", "hotfix"]


class TestGateCatalogBuiltin:
    def test_load_builtin_loads_all_10_gates(self):
        catalog = GateCatalog()
        count = catalog.load_builtin()
        assert count == 10
        assert len(catalog.list_gates()) == 10

    def test_g6_code_quality_loaded(self):
        catalog = GateCatalog()
        catalog.load_builtin()
        g = catalog.get("G6-code-quality")
        assert g.name == "Code Quality Gate"
        assert g.after_stage == "s-implement"
        assert g.trigger == GateTrigger.ALWAYS
        assert g.reviewer == "TechLead"
        assert g.deadline_hours == 4
        assert g.block_conditions.get("on_must_violation") is True

    def test_g7_test_coverage_loaded(self):
        catalog = GateCatalog()
        catalog.load_builtin()
        g = catalog.get("G7-test-coverage")
        assert g.name == "Test Coverage Gate"
        assert g.after_stage == "s-test"
        assert g.trigger == GateTrigger.ALWAYS
        assert g.reviewer == "QA"
        assert g.deadline_hours == 8
        assert g.block_conditions.get("coverage_below_threshold") is True

    def test_g8_release_readiness_loaded(self):
        catalog = GateCatalog()
        catalog.load_builtin()
        g = catalog.get("G8-release-readiness")
        assert g.name == "Release Readiness Gate"
        assert g.after_stage == "s-deploy"
        assert g.trigger == GateTrigger.ON_RELEASE
        assert g.reviewer == "ReleaseManager"
        assert g.block_conditions.get("on_p0_violation") is True

    def test_g9_compliance_loaded(self):
        catalog = GateCatalog()
        catalog.load_builtin()
        g = catalog.get("G9-compliance")
        assert g.name == "Compliance Gate"
        assert g.after_stage == "s-design"
        assert g.trigger == GateTrigger.ON_COMPLIANCE_REQUIRED
        assert g.reviewer == "Compliance"
        assert g.block_conditions.get("on_compliance_violation") is True

    def test_g10_architecture_loaded(self):
        catalog = GateCatalog()
        catalog.load_builtin()
        g = catalog.get("G10-architecture")
        assert g.name == "Architecture Gate"
        assert g.after_stage == "s-design"
        assert g.trigger == GateTrigger.ON_PROFILE
        assert g.reviewer == "Architect"
        assert g.profiles == ["new-feature", "hotfix"]
        assert g.block_conditions.get("on_architecture_violation") is True


class TestGate6CodeQualityIntegration:
    def test_g6_auto_pass_no_violations(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="G6-code-quality",
                name="Code Quality Gate",
                after_stage="s-implement",
                trigger=GateTrigger.ALWAYS,
                reviewer="TechLead",
                deadline_hours=4,
                auto_pass_conditions={"no_violations": True},
                block_conditions={"on_must_violation": True},
            )
        )
        decision = engine.evaluate("s-implement", {"stage_status": "COMPLETED"})
        assert decision is not None
        assert decision.action == GateAction.AUTO_PASS

    def test_g6_block_on_must_violation(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="G6-code-quality",
                name="Code Quality Gate",
                after_stage="s-implement",
                trigger=GateTrigger.ALWAYS,
                reviewer="TechLead",
                deadline_hours=4,
                auto_pass_conditions={"no_violations": True},
                block_conditions={"on_must_violation": True},
            )
        )
        ctx = {"rule_violations": [{"id": "cq-1", "level": "MUST"}]}
        decision = engine.evaluate("s-implement", ctx)
        assert decision is not None
        assert decision.action == GateAction.BLOCK


class TestGate7TestCoverageIntegration:
    def test_g7_block_on_low_coverage(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="G7-test-coverage",
                name="Test Coverage Gate",
                after_stage="s-test",
                trigger=GateTrigger.ALWAYS,
                reviewer="QA",
                deadline_hours=8,
                block_conditions={"coverage_below_threshold": True},
            )
        )
        decision = engine.evaluate("s-test", {"test_coverage": 40, "coverage_threshold": 80})
        assert decision is not None
        assert decision.action == GateAction.BLOCK


class TestGate8ReleaseReadinessIntegration:
    def test_g8_not_triggered_non_release(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="G8-release-readiness",
                name="Release Readiness Gate",
                after_stage="s-deploy",
                trigger=GateTrigger.ON_RELEASE,
                reviewer="ReleaseManager",
                deadline_hours=4,
                block_conditions={"on_p0_violation": True},
            )
        )
        decision = engine.evaluate("s-deploy", {"is_release": False})
        assert decision is None

    def test_g8_triggered_on_release(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="G8-release-readiness",
                name="Release Readiness Gate",
                after_stage="s-deploy",
                trigger=GateTrigger.ON_RELEASE,
                reviewer="ReleaseManager",
                deadline_hours=4,
                block_conditions={"on_p0_violation": True},
            )
        )
        decision = engine.evaluate("s-deploy", {"is_release": True})
        assert decision is not None
        assert decision.action == GateAction.MANUAL_REVIEW

    def test_g8_block_on_p0_violation(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="G8-release-readiness",
                name="Release Readiness Gate",
                after_stage="s-deploy",
                trigger=GateTrigger.ON_RELEASE,
                reviewer="ReleaseManager",
                deadline_hours=4,
                block_conditions={"on_p0_violation": True},
            )
        )
        ctx = {"is_release": True, "rule_violations": [{"id": "rv1", "severity": "P0"}]}
        decision = engine.evaluate("s-deploy", ctx)
        assert decision is not None
        assert decision.action == GateAction.BLOCK


class TestGate9ComplianceIntegration:
    def test_g9_not_triggered_when_not_required(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="G9-compliance",
                name="Compliance Gate",
                after_stage="s-design",
                trigger=GateTrigger.ON_COMPLIANCE_REQUIRED,
                reviewer="Compliance",
                deadline_hours=8,
                block_conditions={"on_compliance_violation": True},
            )
        )
        decision = engine.evaluate("s-design", {"compliance_required": False})
        assert decision is None

    def test_g9_triggered_when_required(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="G9-compliance",
                name="Compliance Gate",
                after_stage="s-design",
                trigger=GateTrigger.ON_COMPLIANCE_REQUIRED,
                reviewer="Compliance",
                deadline_hours=8,
                block_conditions={"on_compliance_violation": True},
            )
        )
        decision = engine.evaluate("s-design", {"compliance_required": True})
        assert decision is not None
        assert decision.action == GateAction.MANUAL_REVIEW

    def test_g9_block_on_compliance_violation(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="G9-compliance",
                name="Compliance Gate",
                after_stage="s-design",
                trigger=GateTrigger.ON_COMPLIANCE_REQUIRED,
                reviewer="Compliance",
                deadline_hours=8,
                block_conditions={"on_compliance_violation": True},
            )
        )
        ctx = {"compliance_required": True, "compliance_violations": ["SOC2-001"]}
        decision = engine.evaluate("s-design", ctx)
        assert decision is not None
        assert decision.action == GateAction.BLOCK


class TestGate10ArchitectureIntegration:
    def test_g10_not_triggered_wrong_profile(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="G10-architecture",
                name="Architecture Gate",
                after_stage="s-design",
                trigger=GateTrigger.ON_PROFILE,
                reviewer="Architect",
                deadline_hours=4,
                profiles=["new-feature", "hotfix"],
                block_conditions={"on_architecture_violation": True},
            )
        )
        decision = engine.evaluate("s-design", {"profile": "bugfix"})
        assert decision is None

    def test_g10_triggered_new_feature_profile(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="G10-architecture",
                name="Architecture Gate",
                after_stage="s-design",
                trigger=GateTrigger.ON_PROFILE,
                reviewer="Architect",
                deadline_hours=4,
                profiles=["new-feature", "hotfix"],
                block_conditions={"on_architecture_violation": True},
            )
        )
        decision = engine.evaluate("s-design", {"profile": "new-feature"})
        assert decision is not None
        assert decision.action == GateAction.MANUAL_REVIEW

    def test_g10_triggered_hotfix_profile(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="G10-architecture",
                name="Architecture Gate",
                after_stage="s-design",
                trigger=GateTrigger.ON_PROFILE,
                reviewer="Architect",
                deadline_hours=4,
                profiles=["new-feature", "hotfix"],
                block_conditions={"on_architecture_violation": True},
            )
        )
        decision = engine.evaluate("s-design", {"profile": "hotfix"})
        assert decision is not None
        assert decision.action == GateAction.MANUAL_REVIEW

    def test_g10_block_on_architecture_violation(self):
        engine = GateEngine()
        engine.register(
            GateDef(
                id="G10-architecture",
                name="Architecture Gate",
                after_stage="s-design",
                trigger=GateTrigger.ON_PROFILE,
                reviewer="Architect",
                deadline_hours=4,
                profiles=["new-feature", "hotfix"],
                block_conditions={"on_architecture_violation": True},
            )
        )
        ctx = {"profile": "new-feature", "architecture_violations": ["ARCH-001"]}
        decision = engine.evaluate("s-design", ctx)
        assert decision is not None
        assert decision.action == GateAction.BLOCK
