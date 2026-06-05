from typing import Any

from sdlc.audit import AuditEventType, AuditLogger
from sdlc.gate import GateAction, GateEngine
from sdlc.stage.catalog import StageCatalog
from sdlc.stage.models import StageDef, StageNode
from sdlc.state import Artifact, StateStore
from sdlc.state import StageResult as StateStageResult
from sdlc.subagent import SubagentPool, SubagentTask
from sdlc.utils.time import now_utc


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

            kb_context: dict[str, str] = {}
            for kb_file in stage_def.pre_kb_load:
                # Try to load KB content for this file
                from sdlc.utils.paths import project_root

                try:
                    kb_root = project_root() / "doc" / "kb"
                except Exception:
                    kb_root = None
                if kb_root and (kb_root / kb_file).exists():
                    try:
                        kb_context[kb_file] = (kb_root / kb_file).read_text(encoding="utf-8")[
                            :5000
                        ]  # Truncate to avoid context overflow
                    except Exception:
                        kb_context[kb_file] = f"[KB: {kb_file}] (could not read)"
                else:
                    kb_context[kb_file] = f"[KB: {kb_file}] (not found)"

            for art_name in stage_def.required_artifacts:
                existing = self.state.list_artifacts(pipeline_id)
                found = any(a for a in existing if a.type == art_name)
                if not found:
                    pass

            # Load applicable rules for this stage
            rules_context: list[dict[str, str]] = []
            try:
                from sdlc.rule.engine import RuleEngine
                from sdlc.rule.models import RuleLevel
                from sdlc.utils.paths import project_root as _project_root

                rule_engine = RuleEngine()
                rules_dir = _project_root() / "doc" / "kb" / "rules"
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
                    for r in rule_engine.for_stage(stage_def.id)
                    if r.level
                    in (RuleLevel.MUST, RuleLevel.MUST_NOT, RuleLevel.SHOULD, RuleLevel.SHOULD_NOT)
                ]
            except Exception:
                # If rule loading fails, continue with empty rules context
                pass

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
