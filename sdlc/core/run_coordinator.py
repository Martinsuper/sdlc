from __future__ import annotations

from typing import Any

from sdlc.adapter import AdapterRegistry
from sdlc.audit import AuditEventType, AuditLogger
from sdlc.core.entry_detector import EntryDetector
from sdlc.core.models import PipelineResult
from sdlc.core.pipeline_builder import PipelineBuilder
from sdlc.gate import GateEngine
from sdlc.llm.cost import CostTracker
from sdlc.profile import ProfileRegistry
from sdlc.stage import StageCatalog, StageRunner
from sdlc.state import StateStore
from sdlc.subagent import SubagentPool


class RunCoordinator:
    def __init__(
        self,
        state: StateStore,
        audit: AuditLogger,
        catalog: StageCatalog,
        subagent_pool: SubagentPool,
        gate_engine: GateEngine | None = None,
        profile_registry: ProfileRegistry | None = None,
        adapter_registry: AdapterRegistry | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        self.state = state
        self.audit = audit
        self.catalog = catalog
        self.subagent_pool = subagent_pool
        self.gate_engine = gate_engine
        self.profile_registry = profile_registry or ProfileRegistry()
        self.adapter_registry = adapter_registry or AdapterRegistry()
        self.cost_tracker = cost_tracker
        self.entry_detector = EntryDetector()
        self.pipeline_builder = PipelineBuilder(catalog)
        self.stage_runner = StageRunner(
            catalog=catalog,
            state=state,
            audit=audit,
            subagent_pool=subagent_pool,
            gate_engine=gate_engine,
        )

    async def run(
        self,
        input_text: str,
        profile_id: str | None = None,
        adapter_id: str | None = None,
        **opts: Any,
    ) -> PipelineResult:
        entry = self.entry_detector.detect(input_text)
        self.audit.emit(
            AuditEventType.ENTRY_DETECTED,
            {"kind": entry.kind.value, "confidence": entry.confidence},
        )

        if profile_id:
            profile = self.profile_registry.get(profile_id)
        else:
            profile = self.profile_registry.resolve(entry.kind.value)
        self.audit.emit(
            AuditEventType.PROFILE_RESOLVED,
            {"profile_id": profile.id, "entry_kind": entry.kind.value},
        )

        pipeline = self.pipeline_builder.build(entry, profile)

        self.state.save_pipeline(
            pipeline_id=pipeline.id,
            entry_kind=entry.kind.value,
            profile_id=profile.id,
            status="RUNNING",
        )
        self.audit.emit(
            AuditEventType.PIPELINE_START,
            {"id": pipeline.id, "entry": entry.raw_input[:100], "profile": profile.id},
            pipeline_id=pipeline.id,
        )

        context = {"input": input_text, "severity": profile.severity, "pipeline_id": pipeline.id}
        stage_results = await self.stage_runner.run_pipeline_stages(
            pipeline.stages, pipeline.id, context
        )

        # Track costs if CostTracker is provided
        total_cost = sum(r.get("cost_usd", 0.0) for r in stage_results)
        if self.cost_tracker is not None:
            for r in stage_results:
                if r.get("cost_usd", 0.0) > 0:
                    stage_def_id = r.get("stage_id", "")
                    model = (self.catalog.has(stage_def_id) and self.catalog.get(stage_def_id).model) or "unknown"
                    self.cost_tracker.record(
                        model=model,
                        input_tokens=0,
                        output_tokens=0,
                        cost_usd=r.get("cost_usd", 0.0),
                    )
            if self.cost_tracker.check_budget():
                self.audit.emit(
                    AuditEventType.COST_EXCEEDED,
                    {
                        "total_usd": self.cost_tracker.total_cost,
                        "budget_usd": self.cost_tracker.max_budget,
                        "pipeline_id": pipeline.id,
                    },
                    pipeline_id=pipeline.id,
                )

        all_success = all(r["status"] == "SUCCESS" for r in stage_results)
        has_failed = any(r["status"] == "FAILED" for r in stage_results)

        if has_failed:
            final_status = "failed"
        elif all_success:
            final_status = "completed"
        else:
            final_status = "paused"

        self.state.update_pipeline_status(pipeline.id, final_status.upper())
        self.audit.emit(
            AuditEventType.PIPELINE_END,
            {"id": pipeline.id, "status": final_status, "cost_usd": total_cost},
            pipeline_id=pipeline.id,
        )

        return PipelineResult(
            pipeline_id=pipeline.id,
            status=final_status,
            stage_results=stage_results,
            total_cost_usd=total_cost,
        )
