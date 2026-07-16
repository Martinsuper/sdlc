"""Stage runner -- executes pipeline stages with caching and lazy loading.

Performance optimizations:
- YAML template caching: stage definitions are parsed once and reused
- Lazy KB context loading: KB files are only read when a stage requires them
- Pre-compiled regex patterns in rule enforcer
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

from sdlc.audit import AuditEventType, AuditLogger
from sdlc.gate import GateAction, GateEngine
from sdlc.kb.memory import MemoryL2
from sdlc.stage.catalog import StageCatalog
from sdlc.stage.models import StageDef, StageNode
from sdlc.state import Artifact, StateStore
from sdlc.state import StageResult as StateStageResult
from sdlc.subagent import SubagentPool, SubagentTask
from sdlc.utils.time import now_utc

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache infrastructure -- TTL + max entries to prevent unbounded growth
# ---------------------------------------------------------------------------

_CACHE_TTL = 3600  # seconds
_CACHE_MAX_ENTRIES = 100


@dataclass
class _CacheEntry:
    value: Any
    timestamp: float


def _cache_get(cache: dict[str, _CacheEntry], key: str) -> Any | None:
    """Retrieve a value from a TTL cache, removing expired entries."""
    entry = cache.get(key)
    if entry is None:
        return None
    if time.monotonic() - entry.timestamp > _CACHE_TTL:
        del cache[key]
        return None
    return entry.value


def _cache_set(cache: dict[str, _CacheEntry], key: str, value: Any) -> None:
    """Store a value in a TTL cache, evicting oldest entries if at capacity."""
    if len(cache) >= _CACHE_MAX_ENTRIES and key not in cache:
        oldest_key = min(cache, key=lambda k: cache[k].timestamp)
        del cache[oldest_key]
    cache[key] = _CacheEntry(value=value, timestamp=time.monotonic())


# ---------------------------------------------------------------------------
# YAML template cache -- avoid re-parsing the same YAML files
# ---------------------------------------------------------------------------

_yaml_cache: dict[str, _CacheEntry] = {}


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
    cached = _cache_get(_yaml_cache, cache_key)
    if cached is not None:
        return cached

    data = load_yaml(p)
    _cache_set(_yaml_cache, cache_key, data)
    return data


def clear_yaml_cache() -> None:
    """Clear the YAML template cache (useful for tests or forced reload)."""
    _yaml_cache.clear()


# ---------------------------------------------------------------------------
# KB context cache -- lazy load + memoize per pipeline run
# ---------------------------------------------------------------------------

_kb_context_cache: dict[str, _CacheEntry] = {}


def _load_kb_context_lazy(stage_def: StageDef, pipeline_id: str) -> dict[str, str]:
    """Load KB context for a stage, with per-pipeline caching.

    The KB files are read at most once per pipeline_id, then reused across
    stages in the same pipeline run.
    """
    if not stage_def.pre_kb_load:
        return {}

    # Check per-pipeline cache
    cache_key = pipeline_id
    cached = _cache_get(_kb_context_cache, cache_key)
    if cached is not None:
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
                    raw = target.read_text(encoding="utf-8")
                    if len(raw) > 5000:
                        logger.warning(
                            "KB file %s truncated from %d to %d chars",
                            kb_file, len(raw), 5000,
                        )
                    kb_context[kb_file] = raw[:5000]
                except Exception:
                    kb_context[kb_file] = f"[KB: {kb_file}] (could not read)"
            else:
                kb_context[kb_file] = f"[KB: {kb_file}] (not found)"

    # Store in per-pipeline cache
    _cache_set(_kb_context_cache, cache_key, kb_context)
    return kb_context


def clear_kb_context_cache() -> None:
    """Clear the KB context cache."""
    _kb_context_cache.clear()


def clear_kb_context_for_pipeline(pipeline_id: str) -> None:
    """Remove a specific pipeline's entry from the KB context cache."""
    _kb_context_cache.pop(pipeline_id, None)


# ---------------------------------------------------------------------------
# Rule context cache with pre-compiled regex
# ---------------------------------------------------------------------------

_rule_context_cache: dict[str, _CacheEntry] = {}
_compiled_patterns: dict[str, re.Pattern[str]] = {}


def _precompile_pattern(pattern: str) -> re.Pattern[str] | None:
    """Pre-compile a regex pattern with caching."""
    if pattern in _compiled_patterns:
        return _compiled_patterns[pattern]
    try:
        compiled = re.compile(pattern)
        _compiled_patterns[pattern] = compiled
        return compiled
    except re.error as e:
        logger.warning("Invalid regex pattern '%s': %s", pattern, e)
        return None


def _load_rules_context(stage_id: str) -> list[dict[str, str]]:
    """Load rules context for a stage, with caching by stage_id."""
    cached = _cache_get(_rule_context_cache, stage_id)
    if cached is not None:
        return cached

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
    except Exception as e:
        logger.warning("Rule loading failed for stage %s: %s", stage_id, e)

    _cache_set(_rule_context_cache, stage_id, rules_context)
    return rules_context


def clear_rule_context_cache() -> None:
    """Clear the rule context cache."""
    _rule_context_cache.clear()


def clear_all_caches() -> None:
    """Clear all module-level caches."""
    _yaml_cache.clear()
    _kb_context_cache.clear()
    _rule_context_cache.clear()
    _compiled_patterns.clear()


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
        memory_l2: MemoryL2 | None = None,
        strict_deps: bool = False,
    ) -> None:
        self.catalog = catalog
        self.state = state
        self.audit = audit
        self.subagent_pool = subagent_pool
        self.gate_engine = gate_engine
        self.memory_l2 = memory_l2
        self.strict_deps = strict_deps

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
        status = "COMPLETED"
        artifacts_produced: list[dict[str, Any]] = []

        try:
            self.audit.emit(
                AuditEventType.STAGE_START,
                {"stage": stage_def.id, "category": stage_def.category},
                pipeline_id=pipeline_id,
            )

            # Lazy-load KB context with per-pipeline caching
            kb_context = _load_kb_context_lazy(stage_def, pipeline_id)

            # Check required artifacts
            for art_name in stage_def.required_artifacts:
                existing = self.state.list_artifacts(pipeline_id)
                found = any(a for a in existing if a.type == art_name)
                if not found:
                    logger.warning(
                        "Required artifact '%s' missing for stage '%s'",
                        art_name,
                        stage_def.id,
                    )
                    if self.strict_deps:
                        status = "SKIPPED"
                        error = f"Required artifact '{art_name}' not found"
                        break

            if status == "SKIPPED":
                # Short-circuit when strict_deps is True and artifacts are missing
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
                return {
                    "stage_id": stage_def.id,
                    "status": status,
                    "artifacts": [],
                    "cost_usd": 0.0,
                    "error": error,
                    "gate_decision": None,
                }

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
                timeout_seconds = stage_def.timeout or 1800
                try:
                    result = await asyncio.wait_for(
                        self.subagent_pool.invoke(stage_def.subagent, task),
                        timeout=timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    status = "FAILED"
                    error = (
                        f"Stage '{stage_def.id}' timed out after {timeout_seconds}s"
                    )
                    result = None

                if result is not None:
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

            if status == "COMPLETED":
                for art_dict in artifacts_produced:
                    artifact = Artifact(
                        id=art_dict["id"],
                        pipeline_id=pipeline_id,
                        stage_id=stage_def.id,
                        type=art_dict.get("type", "doc"),
                        path=art_dict.get("path") or art_dict.get("name"),
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
        if self.gate_engine and status == "COMPLETED":
            gate_context = {
                "stage_id": stage_def.id,
                "stage_status": status,
                "pipeline_id": pipeline_id,
                **context,
            }
            gate_decision = self.gate_engine.evaluate(stage_def.id, gate_context)

        # Memory L2: auto-update KB with learnings after stage completes
        result_dict = {
            "stage_id": stage_def.id,
            "status": status,
            "artifacts": artifacts_produced,
            "cost_usd": total_cost,
            "error": error,
            "gate_decision": gate_decision,
        }
        if self.memory_l2:
            self.memory_l2.on_stage_complete(
                stage_id=stage_def.id,
                result=result_dict,
                pipeline_id=pipeline_id,
            )

        self.audit.emit(
            AuditEventType.STAGE_END,
            {"stage": stage_def.id, "status": status, "cost_usd": total_cost, "duration_ms": 0},
            pipeline_id=pipeline_id,
        )

        return result_dict

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

            if result["status"] == "COMPLETED":
                completed_ids.add(node.id)
            elif (
                result.get("gate_decision") and result["gate_decision"].action == GateAction.BLOCK
            ) or result["status"] == "FAILED":
                # Design decision: in sequential mode, stop on first
                # BLOCK gate or FAILED stage.  Independent stages that
                # could still run are intentionally skipped.
                break

        # Pipeline finished; clean up KB context cache for this pipeline
        clear_kb_context_for_pipeline(pipeline_id)

        return results
