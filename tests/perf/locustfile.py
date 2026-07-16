"""Locust performance tests for SDLC core subsystems.

Since the SDLC tool is a CLI (not an HTTP server), we use Locust's
User class directly rather than HttpUser.  Each "task" simulates a
heavyweight internal operation so we can measure throughput under
concurrency.
"""

import time
from pathlib import Path

from locust import User, between, events, task

from sdlc.gate.engine import GateEngine
from sdlc.gate.models import GateDef, GateTrigger
from sdlc.kb.knowledge_base import KnowledgeBase
from sdlc.profile.registry import ProfileRegistry, register_builtins
from sdlc.rule.engine import RuleEngine
from sdlc.rule.models import Rule, RuleLevel

# ---------------------------------------------------------------------------
# Shared fixtures (initialised once per Locust worker)
# ---------------------------------------------------------------------------

_registry: ProfileRegistry | None = None
_rule_engine: RuleEngine | None = None
_gate_engine: GateEngine | None = None
_kb: KnowledgeBase | None = None


def _init_registry() -> ProfileRegistry:
    reg = ProfileRegistry()
    register_builtins(reg)
    return reg


def _init_rule_engine() -> RuleEngine:
    eng = RuleEngine()
    for i in range(50):
        eng.add(
            Rule(
                id=f"perf-rule-{i}",
                level=RuleLevel.MUST if i % 3 == 0 else RuleLevel.SHOULD,
                category="coding" if i % 4 == 0 else "security",
                description=f"Performance test rule #{i}",
                enforcer="cr",
                scope={"stages": ["s-unit-test", "s-cr"]},
            )
        )
    return eng


def _init_gate_engine() -> GateEngine:
    eng = GateEngine()
    for i in range(20):
        eng.register(
            GateDef(
                id=f"perf-gate-{i}",
                name=f"Perf Gate {i}",
                after_stage="s-unit-test" if i % 2 == 0 else "s-cr",
                trigger=GateTrigger.ALWAYS,
                auto_pass_conditions={"no_violations": True} if i % 3 == 0 else {},
                block_conditions={"on_must_violation": True} if i % 3 == 1 else {},
            )
        )
    return eng


def _init_kb() -> KnowledgeBase | None:
    # Try to load the project KB; skip gracefully if not present.
    root = Path.cwd() / "doc" / "kb"
    if root.is_dir():
        return KnowledgeBase(root)
    return None


# ---------------------------------------------------------------------------
# Custom metrics via Locust events
# ---------------------------------------------------------------------------


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Pre-populate shared objects when Locust workers start."""
    global _registry, _rule_engine, _gate_engine, _kb
    _registry = _init_registry()
    _rule_engine = _init_rule_engine()
    _gate_engine = _init_gate_engine()
    _kb = _init_kb()


# ---------------------------------------------------------------------------
# Locust User definition
# ---------------------------------------------------------------------------

ENTRY_KINDS = ["feature", "bug", "hotfix", "refactor", "test", "infra", "release", "doc"]
TECH_STACKS = [
    [],
    ["backend"],
    ["frontend"],
    ["backend", "frontend"],
]
SEVERITIES = ["P0", "P1", "P2", "P3"]


class SDLCPerfUser(User):
    """Simulates concurrent CLI invocations hitting internal subsystems."""

    # Think-time between tasks (0.5-2s simulates interactive usage)
    wait_time = between(0.5, 2)

    # ------------------------------------------------------------------
    # Profile resolution under load
    # ------------------------------------------------------------------

    @task(5)
    def resolve_profile(self):
        """Resolve a profile with varying entry kinds and context."""
        if _registry is None:
            return
        entry = ENTRY_KINDS[self._loop_count % len(ENTRY_KINDS)]
        ts = TECH_STACKS[self._loop_count % len(TECH_STACKS)]
        sev = SEVERITIES[self._loop_count % len(SEVERITIES)]
        start = time.perf_counter()
        _registry.resolve(entry, tech_stack=ts, severity=sev)
        elapsed = time.perf_counter() - start
        self.environment.events.request.fire(
            request_type="profile_resolve",
            name="resolve",
            response_time=elapsed * 1000,
            response_length=0,
            exception=None,
        )
        # Keep a simple loop counter for deterministic variety
        self._loop_count = getattr(self, "_loop_count", 0) + 1

    @task(3)
    def resolve_all_profiles(self):
        """Resolve all ranked profiles."""
        if _registry is None:
            return
        entry = ENTRY_KINDS[self._loop_count % len(ENTRY_KINDS)]
        start = time.perf_counter()
        results = _registry.resolve_all(entry, tech_stack=["frontend"], severity="P2")
        elapsed = time.perf_counter() - start
        self.environment.events.request.fire(
            request_type="profile_resolve_all",
            name="resolve_all",
            response_time=elapsed * 1000,
            response_length=len(results),
            exception=None,
        )

    @task(2)
    def match_score_profile(self):
        """Compute match score for a single profile."""
        if _registry is None:
            return
        profile = _registry.list_profiles()[0]
        start = time.perf_counter()
        _registry.match_score(profile, "feature", tech_stack=["frontend"])
        elapsed = time.perf_counter() - start
        self.environment.events.request.fire(
            request_type="profile_match_score",
            name="match_score",
            response_time=elapsed * 1000,
            response_length=0,
            exception=None,
        )

    # ------------------------------------------------------------------
    # Rule evaluation under load
    # ------------------------------------------------------------------

    @task(4)
    def rule_list(self):
        """List rules with category/level filters."""
        if _rule_engine is None:
            return
        start = time.perf_counter()
        rules = _rule_engine.list_rules(category="coding")
        elapsed = time.perf_counter() - start
        self.environment.events.request.fire(
            request_type="rule_list",
            name="list_rules",
            response_time=elapsed * 1000,
            response_length=len(rules),
            exception=None,
        )

    @task(3)
    def rule_for_stage(self):
        """Query rules applicable to a stage."""
        if _rule_engine is None:
            return
        start = time.perf_counter()
        rules = _rule_engine.for_stage("s-unit-test")
        elapsed = time.perf_counter() - start
        self.environment.events.request.fire(
            request_type="rule_for_stage",
            name="for_stage",
            response_time=elapsed * 1000,
            response_length=len(rules),
            exception=None,
        )

    @task(2)
    def rule_check_all(self):
        """Check all rules for a stage."""
        if _rule_engine is None:
            return
        context = {"diff": "+def foo(): pass"}
        start = time.perf_counter()
        violations = _rule_engine.check_all("s-unit-test", context)
        elapsed = time.perf_counter() - start
        self.environment.events.request.fire(
            request_type="rule_check",
            name="check_all",
            response_time=elapsed * 1000,
            response_length=len(violations),
            exception=None,
        )

    # ------------------------------------------------------------------
    # Gate evaluation under load
    # ------------------------------------------------------------------

    @task(4)
    def gate_evaluate(self):
        """Evaluate gates after a stage."""
        if _gate_engine is None:
            return
        context = {
            "pipeline_id": "perf-pipeline",
            "stage_status": "COMPLETED",
            "rule_violations": [],
        }
        start = time.perf_counter()
        _gate_engine.evaluate("s-unit-test", context)
        elapsed = time.perf_counter() - start
        self.environment.events.request.fire(
            request_type="gate_evaluate",
            name="evaluate",
            response_time=elapsed * 1000,
            response_length=0,
            exception=None,
        )

    # ------------------------------------------------------------------
    # KB scan performance
    # ------------------------------------------------------------------

    @task(1)
    def kb_list_layers(self):
        """List KB layers."""
        if _kb is None:
            return
        start = time.perf_counter()
        layers = _kb.list_layers()
        elapsed = time.perf_counter() - start
        self.environment.events.request.fire(
            request_type="kb_scan",
            name="list_layers",
            response_time=elapsed * 1000,
            response_length=len(layers),
            exception=None,
        )
