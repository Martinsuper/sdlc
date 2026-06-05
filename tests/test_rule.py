"""Tests for sdlc.rule package."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sdlc.rule.enforcer import CIEnforcer, CREnforcer, LintEnforcer, RuntimeEnforcer
from sdlc.rule.engine import RuleEngine, RuleNotFoundError
from sdlc.rule.exceptions import ExceptionManager
from sdlc.rule.loader import load_rules_from_yaml
from sdlc.rule.models import Rule, RuleAction, RuleException, RuleLevel, Violation
from sdlc.utils.yaml_io import save_yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rule(**overrides: object) -> Rule:
    defaults = {
        "id": "TEST-RULE",
        "level": RuleLevel.MUST,
        "category": "coding",
        "description": "A test rule",
        "enforcer": "cr",
        "pattern": r"bad\(\)",
        "message": "Do not use bad()",
        "applies_to": ["**/*.py"],
        "action": RuleAction.WARN,
        "severity": "P2",
    }
    defaults.update(overrides)
    return Rule(**defaults)  # type: ignore[arg-type]


def _future_iso(days: int = 7) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def _past_iso(days: int = 1) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestRuleLevel:
    def test_values(self) -> None:
        assert RuleLevel.MUST == "MUST"
        assert RuleLevel.MUST_NOT == "MUST_NOT"
        assert RuleLevel.SHOULD == "SHOULD"
        assert RuleLevel.SHOULD_NOT == "SHOULD_NOT"
        assert RuleLevel.MAY == "MAY"
        assert RuleLevel.MAY_NOT == "MAY_NOT"

    def test_is_str(self) -> None:
        assert isinstance(RuleLevel.MUST, str)


class TestRuleAction:
    def test_values(self) -> None:
        assert RuleAction.BLOCK == "block"
        assert RuleAction.WARN == "warn"

    def test_is_str(self) -> None:
        assert isinstance(RuleAction.BLOCK, str)


class TestRule:
    def test_defaults(self) -> None:
        r = Rule(id="MY-RULE")
        assert r.level == RuleLevel.MUST
        assert r.category == "coding"
        assert r.enforcer == "cr"
        assert r.pattern is None
        assert r.applies_to == []
        assert r.action == RuleAction.WARN
        assert r.severity == "P2"
        assert r.scope == {}
        assert r.references == []
        assert not r.auto_generated
        assert not r.disabled

    def test_full_construction(self) -> None:
        r = _make_rule()
        assert r.id == "TEST-RULE"
        assert r.level == RuleLevel.MUST
        assert r.pattern == r"bad\(\)"

    def test_model_copy(self) -> None:
        r = _make_rule()
        r2 = r.model_copy(update={"disabled": True, "disabled_reason": "testing"})
        assert r2.disabled is True
        assert r2.disabled_reason == "testing"
        assert r.disabled is False  # original unchanged


class TestViolation:
    def test_basic(self) -> None:
        v = Violation(rule_id="R1", message="bad code")
        assert v.rule_id == "R1"
        assert v.file is None
        assert v.line is None
        assert v.severity == "error"

    def test_full(self) -> None:
        v = Violation(rule_id="R1", file="a.py", line=10, message="bad", severity="warn")
        assert v.file == "a.py"
        assert v.line == 10


class TestRuleException:
    def test_basic(self) -> None:
        e = RuleException(
            id="exc-1",
            rule_id="R1",
            reason="legacy code",
            granted_by="admin",
            granted_at=_past_iso(1),
            expires_at=_future_iso(7),
        )
        assert e.rule_id == "R1"
        assert not e.auto_renew
        assert e.scope == {}


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class TestLoadRulesFromYaml:
    def test_load_basic(self, tmp_dir: Path) -> None:
        data = [
            {
                "id": "NO-THREAD-SLEEP",
                "level": "MUST",
                "category": "coding",
                "description": "No Thread.sleep",
                "enforcer": "cr",
                "pattern": r"java\.lang\.Thread\.sleep",
                "message": "No Thread.sleep",
                "action": "block",
                "severity": "P1",
                "applies_to": ["**/*.java"],
            }
        ]
        p = tmp_dir / "rules.yaml"
        save_yaml(p, data)
        rules = load_rules_from_yaml(p)
        assert len(rules) == 1
        assert rules[0].id == "NO-THREAD-SLEEP"
        assert rules[0].level == RuleLevel.MUST
        assert rules[0].action == RuleAction.BLOCK

    def test_load_empty(self, tmp_dir: Path) -> None:
        p = tmp_dir / "empty.yaml"
        p.write_text("[]")
        rules = load_rules_from_yaml(p)
        assert rules == []

    def test_load_none(self, tmp_dir: Path) -> None:
        p = tmp_dir / "null.yaml"
        p.write_text("---\n")
        rules = load_rules_from_yaml(p)
        assert rules == []

    def test_load_non_list_raises(self, tmp_dir: Path) -> None:
        p = tmp_dir / "bad.yaml"
        save_yaml(p, {"key": "value"})
        with pytest.raises(TypeError, match="Expected a list"):
            load_rules_from_yaml(p)

    def test_load_multiple(self, tmp_dir: Path) -> None:
        data = [
            {"id": "RULE-A", "level": "MUST", "category": "security"},
            {"id": "RULE-B", "level": "SHOULD", "category": "performance"},
        ]
        p = tmp_dir / "multi.yaml"
        save_yaml(p, data)
        rules = load_rules_from_yaml(p)
        assert len(rules) == 2
        assert rules[0].id == "RULE-A"
        assert rules[1].id == "RULE-B"


# ---------------------------------------------------------------------------
# Enforcers
# ---------------------------------------------------------------------------


class TestCREnforcer:
    def test_no_pattern(self) -> None:
        rule = _make_rule(pattern=None)
        enforcer = CREnforcer()
        assert enforcer.check(rule, {"files": {"a.py": "bad()"}}) == []

    def test_pattern_match(self) -> None:
        rule = _make_rule()
        enforcer = CREnforcer()
        ctx = {"files": {"src/main.py": "result = bad()"}}
        violations = enforcer.check(rule, ctx)
        assert len(violations) == 1
        assert violations[0].rule_id == "TEST-RULE"
        assert violations[0].file == "src/main.py"
        assert violations[0].line == 1

    def test_pattern_no_match(self) -> None:
        rule = _make_rule()
        enforcer = CREnforcer()
        ctx = {"files": {"src/main.py": "result = good()"}}
        assert enforcer.check(rule, ctx) == []

    def test_applies_to_filter(self) -> None:
        rule = _make_rule(applies_to=["**/*.java"])
        enforcer = CREnforcer()
        ctx = {"files": {"src/main.py": "bad()"}}
        assert enforcer.check(rule, ctx) == []

    def test_applies_to_match(self) -> None:
        rule = _make_rule(applies_to=["**/*.java"])
        enforcer = CREnforcer()
        ctx = {"files": {"src/Main.java": "bad()"}}
        violations = enforcer.check(rule, ctx)
        assert len(violations) == 1

    def test_multiple_matches(self) -> None:
        rule = _make_rule()
        enforcer = CREnforcer()
        ctx = {"files": {"a.py": "x = bad()\ny = bad()"}}
        violations = enforcer.check(rule, ctx)
        assert len(violations) == 2

    def test_invalid_regex(self) -> None:
        rule = _make_rule(pattern="[invalid")
        enforcer = CREnforcer()
        ctx = {"files": {"a.py": "bad()"}}
        assert enforcer.check(rule, ctx) == []

    def test_empty_files(self) -> None:
        rule = _make_rule()
        enforcer = CREnforcer()
        assert enforcer.check(rule, {}) == []
        assert enforcer.check(rule, {"files": {}}) == []

    def test_non_string_content(self) -> None:
        rule = _make_rule()
        enforcer = CREnforcer()
        ctx = {"files": {"a.py": 12345}}  # type: ignore[dict-item]
        assert enforcer.check(rule, ctx) == []


class TestLintEnforcer:
    def test_returns_empty(self) -> None:
        rule = _make_rule()
        enforcer = LintEnforcer()
        assert enforcer.check(rule, {}) == []


class TestCIEnforcer:
    def test_returns_empty(self) -> None:
        rule = _make_rule()
        enforcer = CIEnforcer()
        assert enforcer.check(rule, {}) == []


class TestRuntimeEnforcer:
    def test_returns_empty(self) -> None:
        rule = _make_rule()
        enforcer = RuntimeEnforcer()
        assert enforcer.check(rule, {}) == []


# ---------------------------------------------------------------------------
# ExceptionManager
# ---------------------------------------------------------------------------


class TestExceptionManager:
    def test_add_and_is_active(self) -> None:
        mgr = ExceptionManager()
        exc = RuleException(
            id="exc-1",
            rule_id="R1",
            reason="legacy",
            granted_by="admin",
            granted_at=_past_iso(1),
            expires_at=_future_iso(7),
        )
        mgr.add(exc)
        result = mgr.is_active("R1")
        assert result is not None
        assert result.id == "exc-1"

    def test_is_active_expired(self) -> None:
        mgr = ExceptionManager()
        exc = RuleException(
            id="exc-2",
            rule_id="R2",
            reason="legacy",
            granted_by="admin",
            granted_at=_past_iso(10),
            expires_at=_past_iso(1),
        )
        mgr.add(exc)
        assert mgr.is_active("R2") is None

    def test_is_active_wrong_rule(self) -> None:
        mgr = ExceptionManager()
        exc = RuleException(
            id="exc-3",
            rule_id="R1",
            reason="legacy",
            granted_by="admin",
            granted_at=_past_iso(1),
            expires_at=_future_iso(7),
        )
        mgr.add(exc)
        assert mgr.is_active("R2") is None

    def test_is_active_with_scope_match(self) -> None:
        mgr = ExceptionManager()
        exc = RuleException(
            id="exc-4",
            rule_id="R1",
            reason="legacy",
            granted_by="admin",
            granted_at=_past_iso(1),
            expires_at=_future_iso(7),
            scope={"files": ["src/legacy/**/*.java"]},
        )
        mgr.add(exc)
        ctx = {"files": ["src/legacy/OldService.java"]}
        assert mgr.is_active("R1", ctx) is not None

    def test_is_active_with_scope_no_match(self) -> None:
        mgr = ExceptionManager()
        exc = RuleException(
            id="exc-5",
            rule_id="R1",
            reason="legacy",
            granted_by="admin",
            granted_at=_past_iso(1),
            expires_at=_future_iso(7),
            scope={"files": ["src/legacy/**/*.java"]},
        )
        mgr.add(exc)
        ctx = {"files": ["src/new/NewService.java"]}
        assert mgr.is_active("R1", ctx) is None

    def test_expire_check(self) -> None:
        mgr = ExceptionManager()
        active_exc = RuleException(
            id="exc-a",
            rule_id="R1",
            reason="temp",
            granted_by="admin",
            granted_at=_past_iso(1),
            expires_at=_future_iso(7),
        )
        expired_exc = RuleException(
            id="exc-b",
            rule_id="R2",
            reason="temp",
            granted_by="admin",
            granted_at=_past_iso(10),
            expires_at=_past_iso(1),
        )
        mgr.add(active_exc)
        mgr.add(expired_exc)
        expired = mgr.expire_check()
        assert len(expired) == 1
        assert expired[0].id == "exc-b"

    def test_expiring_soon(self) -> None:
        mgr = ExceptionManager()
        far_future = RuleException(
            id="exc-far",
            rule_id="R1",
            reason="temp",
            granted_by="admin",
            granted_at=_past_iso(1),
            expires_at=_future_iso(30),
        )
        soon = RuleException(
            id="exc-soon",
            rule_id="R2",
            reason="temp",
            granted_by="admin",
            granted_at=_past_iso(1),
            expires_at=_future_iso(2),
        )
        already_expired = RuleException(
            id="exc-exp",
            rule_id="R3",
            reason="temp",
            granted_by="admin",
            granted_at=_past_iso(10),
            expires_at=_past_iso(1),
        )
        mgr.add(far_future)
        mgr.add(soon)
        mgr.add(already_expired)
        result = mgr.expiring_soon(days=3)
        assert len(result) == 1
        assert result[0].id == "exc-soon"

    def test_remove(self) -> None:
        mgr = ExceptionManager()
        exc = RuleException(
            id="exc-rm",
            rule_id="R1",
            reason="temp",
            granted_by="admin",
            granted_at=_past_iso(1),
            expires_at=_future_iso(7),
        )
        mgr.add(exc)
        assert mgr.remove("exc-rm") is True
        assert mgr.is_active("R1") is None

    def test_remove_not_found(self) -> None:
        mgr = ExceptionManager()
        assert mgr.remove("nonexistent") is False


# ---------------------------------------------------------------------------
# RuleEngine
# ---------------------------------------------------------------------------


class TestRuleEngine:
    def test_add_and_get(self) -> None:
        engine = RuleEngine()
        rule = _make_rule()
        engine.add(rule)
        assert engine.get("TEST-RULE") == rule

    def test_get_not_found(self) -> None:
        engine = RuleEngine()
        with pytest.raises(RuleNotFoundError, match="Rule not found"):
            engine.get("MISSING")

    def test_add_overwrites(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(category="coding"))
        engine.add(_make_rule(category="security"))
        assert engine.get("TEST-RULE").category == "security"

    def test_list_rules_no_filter(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(id="R1", category="coding"))
        engine.add(_make_rule(id="R2", category="security"))
        assert len(engine.list_rules()) == 2

    def test_list_rules_by_category(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(id="R1", category="coding"))
        engine.add(_make_rule(id="R2", category="security"))
        result = engine.list_rules(category="security")
        assert len(result) == 1
        assert result[0].id == "R2"

    def test_list_rules_by_level(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(id="R1", level=RuleLevel.MUST))
        engine.add(_make_rule(id="R2", level=RuleLevel.SHOULD))
        result = engine.list_rules(level=RuleLevel.SHOULD)
        assert len(result) == 1
        assert result[0].id == "R2"

    def test_list_rules_category_and_level(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(id="R1", category="coding", level=RuleLevel.MUST))
        engine.add(_make_rule(id="R2", category="coding", level=RuleLevel.SHOULD))
        engine.add(_make_rule(id="R3", category="security", level=RuleLevel.MUST))
        result = engine.list_rules(category="coding", level=RuleLevel.MUST)
        assert len(result) == 1
        assert result[0].id == "R1"

    def test_list_rules_excludes_disabled(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(id="R1"))
        engine.add(_make_rule(id="R2", disabled=True))
        result = engine.list_rules()
        assert len(result) == 1
        assert result[0].id == "R1"

    def test_for_stage(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(id="R1", scope={"stages": ["build", "test"]}))
        engine.add(_make_rule(id="R2", scope={"stages": ["deploy"]}))
        engine.add(_make_rule(id="R3"))  # no stage filter
        result = engine.for_stage("build")
        ids = {r.id for r in result}
        assert "R1" in ids
        assert "R3" in ids
        assert "R2" not in ids

    def test_for_stage_excludes_disabled(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(id="R1", scope={"stages": ["build"]}, disabled=True))
        assert engine.for_stage("build") == []

    def test_for_role(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(id="R1", category="coding"))
        engine.add(_make_rule(id="R2", category="security"))
        engine.add(_make_rule(id="R3", category="architecture"))
        coder_rules = engine.for_role("coder")
        coder_cats = {r.category for r in coder_rules}
        assert "coding" in coder_cats
        assert "security" not in coder_cats

    def test_for_role_unknown(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(id="R1"))
        assert engine.for_role("unknown-role") == []

    def test_for_adapter(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(id="R1", scope={"adapters": ["java-adapter"]}))
        engine.add(_make_rule(id="R2", scope={"adapters": ["python-adapter"]}))
        engine.add(_make_rule(id="R3"))  # no adapter filter
        result = engine.for_adapter("java-adapter")
        ids = {r.id for r in result}
        assert "R1" in ids
        assert "R3" in ids
        assert "R2" not in ids

    def test_disable_and_enable(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule())
        assert not engine.get("TEST-RULE").disabled

        engine.disable("TEST-RULE", until=_future_iso(), reason="testing")
        assert engine.get("TEST-RULE").disabled
        assert engine.get("TEST-RULE").disabled_reason == "testing"

        engine.enable("TEST-RULE")
        assert not engine.get("TEST-RULE").disabled
        assert engine.get("TEST-RULE").disabled_reason is None

    def test_disable_nonexistent_raises(self) -> None:
        engine = RuleEngine()
        with pytest.raises(RuleNotFoundError):
            engine.disable("MISSING", until=_future_iso(), reason="x")

    def test_enable_nonexistent_raises(self) -> None:
        engine = RuleEngine()
        with pytest.raises(RuleNotFoundError):
            engine.enable("MISSING")

    def test_load_from_yaml(self, tmp_dir: Path) -> None:
        data = [{"id": "YAML-R1", "level": "MUST", "category": "coding"}]
        p = tmp_dir / "rules.yaml"
        save_yaml(p, data)
        engine = RuleEngine()
        count = engine.load_from_yaml(p)
        assert count == 1
        assert engine.get("YAML-R1").category == "coding"

    def test_load_from_yaml_merges(self, tmp_dir: Path) -> None:
        data1 = [{"id": "R1", "category": "coding"}]
        data2 = [{"id": "R2", "category": "security"}]
        p1 = tmp_dir / "a.yaml"
        p2 = tmp_dir / "b.yaml"
        save_yaml(p1, data1)
        save_yaml(p2, data2)
        engine = RuleEngine()
        engine.load_from_yaml(p1)
        engine.load_from_yaml(p2)
        assert len(engine.rules) == 2

    def test_check_dispatches_to_enforcer(self) -> None:
        engine = RuleEngine()
        rule = _make_rule()
        engine.add(rule)
        ctx = {"files": {"main.py": "x = bad()"}}
        violations = engine.check("TEST-RULE", ctx)
        assert len(violations) == 1
        assert violations[0].rule_id == "TEST-RULE"

    def test_check_disabled_rule(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(disabled=True))
        violations = engine.check("TEST-RULE", {"files": {"a.py": "bad()"}})
        assert violations == []

    def test_check_unknown_enforcer(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(enforcer="custom-unknown"))
        violations = engine.check("TEST-RULE", {})
        assert violations == []

    def test_check_all(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(id="R1", scope={"stages": ["build"]}))
        engine.add(_make_rule(id="R2", scope={"stages": ["deploy"]}))
        engine.add(_make_rule(id="R3", scope={"stages": ["build"]}, pattern=None))
        ctx = {"files": {"main.py": "bad()"}}
        violations = engine.check_all("build", ctx)
        rule_ids = {v.rule_id for v in violations}
        assert "R1" in rule_ids
        # R2 not in build stage, R3 has no pattern
        assert "R2" not in rule_ids

    def test_check_all_no_stage_rules(self) -> None:
        engine = RuleEngine()
        engine.add(_make_rule(id="R1", scope={"stages": ["deploy"]}))
        ctx = {"files": {"main.py": "bad()"}}
        violations = engine.check_all("build", ctx)
        assert violations == []
