"""sdlc.rule.engine — central rule engine: load, filter, check."""

from __future__ import annotations

from pathlib import Path

from sdlc.rule.enforcer import CIEnforcer, CREnforcer, Enforcer, LintEnforcer, RuntimeEnforcer
from sdlc.rule.loader import load_rules_from_yaml
from sdlc.rule.models import Rule, RuleLevel, Violation
from sdlc.utils.exceptions import SdlcError


class RuleNotFoundError(SdlcError):
    pass


# Mapping from enforcer name to enforcer instance
_ENFORCERS: dict[str, Enforcer] = {
    "cr": CREnforcer(),
    "lint": LintEnforcer(),
    "ci": CIEnforcer(),
    "runtime": RuntimeEnforcer(),
}

# Mapping from subagent role to rule categories
_ROLE_CATEGORIES: dict[str, list[str]] = {
    "coder": ["coding", "error-handling", "performance", "concurrency"],
    "reviewer": ["coding", "error-handling", "security", "performance", "architecture"],
    "architect": ["architecture", "dependency", "api-style", "database"],
    "tester": ["coding", "error-handling"],
    "deployer": ["security", "performance", "logging"],
}


class RuleEngine:
    """Central rule engine — load, filter, add, disable, and check rules."""

    def __init__(self) -> None:
        self.rules: dict[str, Rule] = {}

    # -- loading -----------------------------------------------------------

    def load_from_yaml(self, path: Path) -> int:
        """Load rules from a YAML file. Returns count of rules loaded."""
        rules = load_rules_from_yaml(path)
        for r in rules:
            self.rules[r.id] = r
        return len(rules)

    # -- CRUD -------------------------------------------------------------

    def add(self, rule: Rule) -> None:
        """Add or update a rule."""
        self.rules[rule.id] = rule

    def get(self, rule_id: str) -> Rule:
        """Get rule by ID. Raise RuleNotFoundError if not found."""
        rule = self.rules.get(rule_id)
        if rule is None:
            raise RuleNotFoundError(f"Rule not found: {rule_id}")
        return rule

    # -- querying ---------------------------------------------------------

    def list_rules(
        self,
        category: str | None = None,
        level: RuleLevel | None = None,
    ) -> list[Rule]:
        """List rules, optionally filtered by category and/or level."""
        result: list[Rule] = []
        for rule in self.rules.values():
            if rule.disabled:
                continue
            if category is not None and rule.category != category:
                continue
            if level is not None and rule.level != level:
                continue
            result.append(rule)
        return result

    def for_stage(self, stage_id: str) -> list[Rule]:
        """Get rules that apply to a specific stage."""
        result: list[Rule] = []
        for rule in self.rules.values():
            if rule.disabled:
                continue
            stages = rule.scope.get("stages")
            if stages is not None and stage_id not in stages:
                continue
            result.append(rule)
        return result

    def for_role(self, role: str) -> list[Rule]:
        """Get rules relevant to a specific subagent role."""
        categories = _ROLE_CATEGORIES.get(role)
        if categories is None:
            return []
        return [r for r in self.rules.values() if not r.disabled and r.category in categories]

    def for_adapter(self, adapter_id: str) -> list[Rule]:
        """Get rules that apply to a specific adapter."""
        result: list[Rule] = []
        for rule in self.rules.values():
            if rule.disabled:
                continue
            adapters = rule.scope.get("adapters")
            if adapters is not None and adapter_id not in adapters:
                continue
            result.append(rule)
        return result

    # -- enable / disable -------------------------------------------------

    def disable(self, rule_id: str, until: str, reason: str) -> None:
        """Temporarily disable a rule until a given time."""
        rule = self.get(rule_id)
        updated = rule.model_copy(
            update={
                "disabled": True,
                "disabled_reason": reason,
                "disabled_until": until,
            }
        )
        self.rules[rule_id] = updated

    def enable(self, rule_id: str) -> None:
        """Re-enable a previously disabled rule."""
        rule = self.get(rule_id)
        updated = rule.model_copy(
            update={
                "disabled": False,
                "disabled_reason": None,
                "disabled_until": None,
            }
        )
        self.rules[rule_id] = updated

    # -- checking ---------------------------------------------------------

    def check(self, rule_id: str, context: dict[str, object]) -> list[Violation]:
        """Check a single rule against context. Dispatches to appropriate enforcer."""
        rule = self.get(rule_id)
        if rule.disabled:
            return []
        enforcer = _ENFORCERS.get(rule.enforcer)
        if enforcer is None:
            return []
        return enforcer.check(rule, context)

    def check_all(self, stage_id: str, context: dict[str, object]) -> list[Violation]:
        """Check all rules for a stage against context."""
        violations: list[Violation] = []
        for rule in self.for_stage(stage_id):
            if rule.disabled:
                continue
            enforcer = _ENFORCERS.get(rule.enforcer)
            if enforcer is None:
                continue
            violations.extend(enforcer.check(rule, context))
        return violations
