"""Stage runner -- executes pipeline stages with caching and lazy loading.

Performance optimizations:
- YAML template caching: stage definitions are parsed once and reused
- Lazy KB context loading: KB files are only read when a stage requires them
- Pre-compiled regex patterns in rule enforcer
"""

from __future__ import annotations

import re
from typing import Any

from sdlc.audit import AuditEventType, AuditLogger
from sdlc.gate import GateAction, GateEngine
from sdlc.stage.catalog import StageCatalog
from sdlc.stage.models import StageDef, StageNode
from sdlc.state import Artifact, StateStore
from sdlc.state import StageResult as StateStageResult
from sdlc.subagent import SubagentPool, SubagentTask
from sdlc.utils.time import now_utc

# ---------------------------------------------------------------------------
# YAML template cache -- avoid re-parsing the same YAML files
# ---------------------------------------------------------------------------

_yaml_cache: dict[str, Any] = {}


def _cached_yaml_load(path_str: str) -> Any:
    """Load a YAML file with in-process caching keyed by path + mtime."""
    from pathlib import Path

    from sdlc.utils.yaml_io import load_yaml

    p = Path(path_str)
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return load_yaml(p)

    cache_key = f"{path_str}:{mtime}"
    if cache_key in _yaml_cache:
        return _yaml_cache[cache_key]

    data = load_yaml(p)
    _yaml_cache[cache_key] = data
    return data


def clear_yaml_cache() -> None:
    """Clear the YAML template cache (useful for tests or forced reload)."""
    _yaml_cache.clear()


# ---------------------------------------------------------------------------
# KB context cache -- lazy load + memoize per pipeline run
# ---------------------------------------------------------------------------

_kb_context_cache: dict[str, dict[str, str]] = {}


def _load_kb_context_lazy(stage_def: StageDef, pipeline_id: str) -> dict[str, str]:
    """Load KB context for a stage, with per-pipeline caching.

    The KB files are read at most once per pipeline_id, then reused across
    stages in the same pipeline run.
    """
    if not stage_def.pre_kb_load:
        return {}

    # Check per-pipeline cache
    cache_key = pipeline_id
    if cache_key in _kb_context_cache:
        cached = _kb_context_cache[cache_key]
        # Only return files requested by this stage
        return {k: v for k, v in cached.items() if k in stage_def.pre_kb_load}

    kb_context: dict[str, str] = {}
    from sdlc.utils.paths import project_root

    try:
        kb_root = project_root() / "doc" / "kb"
    except Exception:
        kb_root = None

    if kb_root and kb_root.exists():
        for kb_file in stage_def.pre_kb_load:
            target = kb_root / kb_file
            if target.exists():
                try:
                    kb_context[kb_file] = target.read_text(encoding="utf-8")[:5000]
                except Exception:
                    kb_context[kb_file] = f"[KB: {kb_file}] (could not read)"
            else:
                kb_context[kb_file] = f"[KB: {kb_file}] (not found)"

    # Store in per-pipeline cache
    _kb_context_cache[pipeline_id] = kb_context
    return kb_context


def clear_kb_context_cache() -> None:
    """Clear the KB context cache."""
    _kb_context_cache.clear()


# ---------------------------------------------------------------------------
# Rule context cache with pre-compiled regex
# ---------------------------------------------------------------------------

_rule_context_cache: dict[str, list[dict[str, str]]] = {}
_compiled_patterns: dict[str, re.Pattern[str]] = {}


def _precompile_pattern(pattern: str) -> re.Pattern[str] | None:
    """Pre-compile a regex pattern with caching."""
    if pattern in _compiled_patterns:
        return _compiled_patterns[pattern]
    try:
        compiled = re.compile(pattern)
        _compiled_patterns[pattern] = compiled
        return compiled
    except re.error:
        _compiled_patterns[pattern] = None  # type: ignore[assignment]
        return None


def _load_rules_context(stage_id: str) -> list[dict[str, str]]:
    """Load rules context for a stage, with caching by stage_id."""
    if stage_id in _rule_context_cache:
        return _rule_context_cache[stage_id]

    rules_context: list[dict[str, str]] = []
    try:
        from sdlc.rule.engine import RuleEngine
        from sdlc.rule.models import RuleLevel
        from sdlc.utils.paths import project_root

        rule_engine = RuleEngine()
        rules_dir = project_root() / "doc" / "kb" / "rules"
        if rules_dir.exists():
            for f in rules_dir.glob("*.yaml"):
                rule_engine.load_from_yaml(f)
        rules_context = [
            {
                "id": r.id,
                "level": r.level.value,
                "description": r.description,
                "message": r.message or "",
            }
            for r in rule_engine.for_stage(stage_id)
            if r.level
            in (RuleLevel.MUST, RuleLevel.MUST_NOT, RuleLevel.SHOULD, RuleLevel.SHOULD_NOT)
        ]
    except Exception:
        pass

    _rule_context_cache[stage_id] = rules_context
    return rules_context


def clear_rule_context_cache() -> None:
    """Clear the rule context cache."""
    _rule_context_cache.clear()


# ---------------------------------------------------------------------------
# StageRunner
# ---------------------------------------------------------------------------


class StageRunner:
    def __init__(
        self,
        catalog: StageCatalog,
        state: StateStore,
        audit: AuditLogger,
        subagent_pool: SubagentPool,
        gate_engine: GateEngine | None = None,
    ) -> None:
        self.catalog = catalog
        self.state = state
        self.audit = audit
        self.subagent_pool = subagent_pool
        self.gate_engine = gate_engine

    async def run_stage(
        self,
        stage_def: StageDef,
        pipeline_id: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        started_at = now_utc().isoformat()
        total_cost = 0.0
        error = None
        status = "SUCCESS"
        artifacts_produced: list[dict[str, Any]] = []

        try:
            self.audit.emit(
                AuditEventType.STAGE_START,
                {"stage": stage_def.id, "category": stage_def.category},
                pipeline_id=pipeline_id,
            )

            # Lazy-load KB context with per-pipeline caching
            kb_context = _load_kb_context_lazy(stage_def, pipeline_id)

            for art_name in stage_def.required_artifacts:
                existing = self.state.list_artifacts(pipeline_id)
                found = any(a for a in existing if a.type == art_name)
                if not found:
                    pass

            # Load applicable rules for this stage (cached)
            rules_context = _load_rules_context(stage_def.id)

            if stage_def.subagent:
                task = SubagentTask(
                    agent_id=stage_def.subagent,
                    input=context.get("input", ""),
                    context={"kb": kb_context, "rules": rules_context},
                    pipeline_id=pipeline_id,
                    stage_id=stage_def.id,
                    max_iter=stage_def.timeout // 60 or 10,
                )
                result = await self.subagent_pool.invoke(stage_def.subagent, task)
                total_cost = result.cost_usd
                if not result.success:
                    status = "FAILED"
                    error = result.error or "Subagent failed"
                else:
                    for art_id in stage_def.produces_artifacts:
                        content = result.artifacts.get(art_id, result.output[:500])
                        artifacts_produced.append(
                            {
                                "id": f"{pipeline_id}-{stage_def.id}-{art_id}",
                                "type": "doc",
                                "name": art_id,
                                "content": content if isinstance(content, str) else str(content),
                            }
                        )

            if status == "SUCCESS":
                for art_dict in artifacts_produced:
                    artifact = Artifact(
                        id=art_dict["id"],
                        pipeline_id=pipeline_id,
                        stage_id=stage_def.id,
                        type=art_dict.get("type", "doc"),
                        path=art_dict.get("name"),
                        created_at=now_utc().isoformat(),
                    )
                    self.state.register_artifact(artifact)

            stage_result = StateStageResult(
                id=f"{pipeline_id}-{stage_def.id}",
                pipeline_id=pipeline_id,
                stage_def_id=stage_def.id,
                status=status,
                started_at=started_at,
                finished_at=now_utc().isoformat(),
                error=error,
            )
            self.state.save_stage_result(stage_result)

        except Exception as e:
            status = "FAILED"
            error = str(e)
            self.audit.emit(
                AuditEventType.ERROR,
                {"stage": stage_def.id, "error": error},
                pipeline_id=pipeline_id,
            )

        gate_decision = None
        if self.gate_engine and status == "SUCCESS":
            gate_context = {
                "stage_id": stage_def.id,
                "stage_status": status,
                "pipeline_id": pipeline_id,
                **context,
            }
            gate_decision = self.gate_engine.evaluate(stage_def.id, gate_context)

        self.audit.emit(
            AuditEventType.STAGE_END,
            {"stage": stage_def.id, "status": status, "cost_usd": total_cost, "duration_ms": 0},
            pipeline_id=pipeline_id,
        )

        return {
            "stage_id": stage_def.id,
            "status": status,
            "artifacts": artifacts_produced,
            "cost_usd": total_cost,
            "error": error,
            "gate_decision": gate_decision,
        }

    async def run_pipeline_stages(
        self,
        stage_nodes: list[StageNode],
        pipeline_id: str,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        completed_ids: set[str] = set()

        for node in stage_nodes:
            unmet = [d for d in node.depends_on if d not in completed_ids]
            if unmet:
                results.append(
                    {
                        "stage_id": node.id,
                        "status": "SKIPPED",
                        "artifacts": [],
                        "cost_usd": 0.0,
                        "error": f"Unmet dependencies: {unmet}",
                        "gate_decision": None,
                    }
                )
                continue

            stage_def = node.stage_def or self.catalog.get(node.id)
            result = await self.run_stage(stage_def, pipeline_id, context)
            results.append(result)

            if result["status"] == "SUCCESS":
                completed_ids.add(node.id)
            elif (
                result["gate_decision"] and result["gate_decision"].action == GateAction.BLOCK
            ) or result["status"] == "FAILED":
                break

        return results
