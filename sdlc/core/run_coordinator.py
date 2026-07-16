from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from sdlc.adapter import AdapterRegistry
from sdlc.audit import AuditEventType, AuditLogger
from sdlc.core.entry_detector import EntryDetector
from sdlc.core.models import PipelineResult
from sdlc.core.pipeline_builder import PipelineBuilder
from sdlc.gate import GateAction, GateDecision, GateEngine
from sdlc.kb.memory import MemoryL2
from sdlc.llm.cost import CostTracker
from sdlc.profile import ProfileRegistry
from sdlc.stage import StageCatalog, StageRunner
from sdlc.stage.models import StageNode
from sdlc.state import StateStore
from sdlc.subagent import SubagentPool

MAX_CONCURRENCY_CAP = 5

logger = logging.getLogger(__name__)


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
        memory_l2: MemoryL2 | None = None,
    ) -> None:
        self.state = state
        self.audit = audit
        self.catalog = catalog
        self.subagent_pool = subagent_pool
        self.gate_engine = gate_engine
        self.profile_registry = profile_registry or ProfileRegistry()
        self.adapter_registry = adapter_registry or AdapterRegistry()
        self.cost_tracker = cost_tracker
        self.memory_l2 = memory_l2
        self.entry_detector = EntryDetector()
        self.pipeline_builder = PipelineBuilder(catalog)
        self.stage_runner = StageRunner(
            catalog=catalog,
            state=state,
            audit=audit,
            subagent_pool=subagent_pool,
            gate_engine=gate_engine,
            memory_l2=memory_l2,
        )

    async def run(
        self,
        input_text: str,
        profile_id: str | None = None,
        adapter_id: str | None = None,
        concurrency: int = 1,
        **opts: Any,
    ) -> PipelineResult:
        # --- Input validation (P1-输入验证) ---
        if not input_text or not input_text.strip():
            raise ValueError("input_text must not be empty or whitespace-only")
        if concurrency < 1:
            raise ValueError("concurrency must be >= 1")
        if len(input_text) > 10000:
            logger.warning("input_text exceeds 10000 chars, truncating to 10000")
            input_text = input_text[:10000]

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

        # Filter stages based on only_stages / skip_stages options
        only_stages = opts.get("only_stages")
        skip_stages = opts.get("skip_stages")
        stages_to_run = pipeline.stages
        if only_stages:
            stages_to_run = [s for s in stages_to_run if s.id in only_stages]
        if skip_stages:
            stages_to_run = [s for s in stages_to_run if s.id not in skip_stages]

        try:
            # Choose execution mode based on concurrency
            if concurrency > 1:
                stage_results = await self._run_pipeline_stages_concurrent(
                    stages_to_run, pipeline.id, context, concurrency
                )
            else:
                stage_results = await self.stage_runner.run_pipeline_stages(
                    stages_to_run, pipeline.id, context
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

            all_success = all(r["status"] == "COMPLETED" for r in stage_results)
            has_failed = any(r["status"] == "FAILED" for r in stage_results)

            if has_failed:
                final_status = "failed"
            elif all_success:
                final_status = "completed"
            else:
                final_status = "paused"
        except Exception as exc:
            # P0-37: Pipeline exception state leak — mark as FAILED if still RUNNING
            final_status = "failed"
            total_cost = 0.0
            stage_results = []
            meta_json = json.dinternal-monitorings({"error": str(exc), "error_type": type(exc).__name__})
            self.state.save_pipeline(
                pipeline_id=pipeline.id,
                entry_kind=entry.kind.value,
                profile_id=profile.id,
                status="FAILED",
                meta_json=meta_json,
            )
            self.audit.emit(
                AuditEventType.PIPELINE_END,
                {"id": pipeline.id, "status": "failed", "error": str(exc)},
                pipeline_id=pipeline.id,
            )
            return PipelineResult(
                pipeline_id=pipeline.id,
                status="failed",
                stage_results=stage_results,
                total_cost_usd=total_cost,
                error=str(exc),
            )

        # Map logical final_status to valid pipeline state transitions
        pipeline_status_map = {
            "completed": "COMPLETED",
            "failed": "FAILED",
            "paused": "PAUSED",
        }
        pipeline_status = pipeline_status_map.get(final_status, final_status.upper())
        self.state.update_pipeline_status(pipeline.id, pipeline_status)
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

    async def _run_pipeline_stages_concurrent(
        self,
        stage_nodes: list[StageNode],
        pipeline_id: str,
        context: dict[str, Any],
        concurrency: int,
    ) -> list[dict[str, Any]]:
        """Run pipeline stages with concurrency for independent stages.

        Stages that have no unmet dependencies can run in parallel,
        respecting the concurrency limit. Per-stage timing is tracked.
        """
        max_concurrency = min(concurrency, MAX_CONCURRENCY_CAP)
        semaphore = asyncio.Semaphore(max_concurrency)

        results: list[dict[str, Any]] = [None] * len(stage_nodes)  # type: ignore[list-item]
        completed_ids: set[str] = set()
        # Track index for each task so we can map results back
        task_index: dict[asyncio.Task[Any], int] = {}

        # Track which stages are ready, running, or done
        pending = set(range(len(stage_nodes)))
        should_stop = False

        async def _run_one(idx: int, node: StageNode) -> dict[str, Any]:
            """Run a single stage with semaphore-based concurrency control."""
            async with semaphore:
                start = time.monotonic()
                stage_def = node.stage_def
                if stage_def is None and self.stage_runner.catalog.has(node.id):
                    stage_def = self.stage_runner.catalog.get(node.id)
                if stage_def is None:
                    return {
                        "stage_id": node.id,
                        "status": "FAILED",
                        "artifacts": [],
                        "cost_usd": 0.0,
                        "error": f"Stage definition not found for '{node.id}'",
                        "gate_decision": None,
                        "duration_ms": 0,
                    }
                result = await self.stage_runner.run_stage(stage_def, pipeline_id, context)
                elapsed_ms = (time.monotonic() - start) * 1000
                result["duration_ms"] = round(elapsed_ms, 2)
                return result

        # Iterative scheduling: keep launching stages as their deps are met
        running: set[asyncio.Task[Any]] = set()

        while (pending or running) and not should_stop:
            # Find stages whose dependencies are all satisfied
            ready: list[int] = []
            for idx in list(pending):
                node = stage_nodes[idx]
                if all(d in completed_ids for d in node.depends_on):
                    ready.append(idx)

            # Launch ready stages
            for idx in ready:
                pending.remove(idx)
                node = stage_nodes[idx]
                task = asyncio.create_task(_run_one(idx, node))
                task_index[task] = idx
                running.add(task)

            if not running:
                # Nothing running and nothing ready -- remaining stages have unmet deps
                for idx in pending:
                    node = stage_nodes[idx]
                    unmet = [d for d in node.depends_on if d not in completed_ids]
                    results[idx] = {
                        "stage_id": node.id,
                        "status": "SKIPPED",
                        "artifacts": [],
                        "cost_usd": 0.0,
                        "error": f"Unmet dependencies: {unmet}",
                        "gate_decision": None,
                        "duration_ms": 0,
                    }
                pending.clear()
                break

            # Wait for at least one running task to complete
            done, running = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                idx = task_index.pop(task, -1)
                try:
                    result = task.result()
                except Exception as exc:
                    node = stage_nodes[idx] if idx >= 0 else None  # type: ignore[assignment]
                    result = {
                        "stage_id": node.id if node else "unknown",
                        "status": "FAILED",
                        "artifacts": [],
                        "cost_usd": 0.0,
                        "error": str(exc),
                        "gate_decision": None,
                        "duration_ms": 0,
                    }

                results[idx] = result

                # Check for failure / gate block
                # Normalize gate_decision to GateDecision object if it's a dict
                gate_decision = result.get("gate_decision")
                if gate_decision and isinstance(gate_decision, dict):
                    try:
                        gate_decision = GateDecision(
                            gate_id=gate_decision.get("gate_id", ""),
                            action=GateAction(gate_decision.get("action", "")),
                            reason=gate_decision.get("reason", ""),
                            reviewer=gate_decision.get("reviewer", ""),
                            deadline=gate_decision.get("deadline", ""),
                            metadata=gate_decision.get("metadata", {}),
                        )
                        result["gate_decision"] = gate_decision
                    except (ValueError, KeyError):
                        gate_decision = None
                is_block = False
                if gate_decision and isinstance(gate_decision, GateDecision):
                    is_block = gate_decision.action == GateAction.BLOCK

                if result["status"] == "COMPLETED" and not is_block:
                    completed_ids.add(result["stage_id"])
                else:
                    # Failure or gate block: skip remaining pending stages
                    should_stop = True
                    for p_idx in list(pending):
                        p_node = stage_nodes[p_idx]
                        results[p_idx] = {
                            "stage_id": p_node.id,
                            "status": "SKIPPED",
                            "artifacts": [],
                            "cost_usd": 0.0,
                            "error": "Blocked by gate decision" if is_block else "Skipped due to prior stage failure",
                            "gate_decision": None,
                            "duration_ms": 0,
                        }
                    pending.clear()
                    # Cancel any still-running tasks and await their completion
                    for t in running:
                        t.cancel()
                    if running:
                        await asyncio.gather(*running, return_exceptions=True)

        # Fill any remaining None slots (shouldn't happen, but defensive)
        for i, r in enumerate(results):
            if r is None:
                results[i] = {
                    "stage_id": stage_nodes[i].id,
                    "status": "SKIPPED",
                    "artifacts": [],
                    "cost_usd": 0.0,
                    "error": "Not executed",
                    "gate_decision": None,
                    "duration_ms": 0,
                }

        return results
