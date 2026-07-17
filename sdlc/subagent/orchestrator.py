"""Orchestrator-Worker multi-agent execution (M-A5).

Lets a complex stage's lead agent fan out independent subtasks to worker agents
in parallel, then merge their outputs — e.g. a design stage dispatching
"DB design", "API design", "risk assessment" concurrently.

Runaway protection (roadmap §6.2):
  - max_delegate_depth (default 1): workers cannot themselves delegate, so the
    tree can't explode. Depth is carried in the task context.
  - concurrency cap via asyncio.Semaphore (reuses the coordinator's pattern,
    pushed down one level to sub-agents).
  - per-worker budget = remaining budget / worker count, enforced via a
    CostTracker check before each dispatch.
  - every dispatch emits a DELEGATE_SPAWNED audit event.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sdlc.audit.events import AuditEventType
from sdlc.subagent.models import Subagent, SubagentResult, SubagentTask

if TYPE_CHECKING:
    from sdlc.subagent.pool import SubagentPool

_CONTEXT_DEPTH_KEY = "_delegate_depth"


@dataclass
class WorkerSpec:
    """One delegated subtask: which worker agent runs what, to what bar."""

    worker_agent_id: str
    description: str
    acceptance_criteria: list[str] = field(default_factory=list)


class DelegationDepthError(Exception):
    """Raised when a worker tries to delegate beyond max_delegate_depth."""


class Orchestrator:
    def __init__(
        self,
        pool: SubagentPool,
        max_delegate_depth: int = 1,
        concurrency: int = 3,
    ) -> None:
        self.pool = pool
        self.max_delegate_depth = max_delegate_depth
        self.concurrency = concurrency

    async def run(
        self, agent: Subagent, task: SubagentTask, subtasks: list[WorkerSpec]
    ) -> SubagentResult:
        """Dispatch subtasks to workers in parallel, then merge.

        Refuses to delegate past max_delegate_depth (the current depth is read
        from the task context). Never partially fails: a worker that errors
        contributes an error note to the merge rather than aborting siblings.
        """
        depth = int((task.context or {}).get(_CONTEXT_DEPTH_KEY, 0))
        if depth >= self.max_delegate_depth:
            raise DelegationDepthError(
                f"delegation depth {depth} >= max {self.max_delegate_depth}"
            )
        if not subtasks:
            return SubagentResult(success=True, output="", artifacts={})

        sem = asyncio.Semaphore(self.concurrency)
        # Split remaining budget evenly across workers (proportional allocation).
        per_worker_budget = self._per_worker_budget(len(subtasks))

        async def _one(spec: WorkerSpec) -> tuple[WorkerSpec, SubagentResult]:
            async with sem:
                if self._over_budget():
                    return spec, SubagentResult(
                        success=False, output="", error="budget exhausted before dispatch"
                    )
                if self.pool.audit is not None:
                    self.pool.audit.emit(
                        AuditEventType.DELEGATE_SPAWNED,
                        {
                            "orchestrator": agent.id,
                            "worker": spec.worker_agent_id,
                            "subtask": spec.description,
                            "budget_usd": per_worker_budget,
                        },
                        pipeline_id=task.pipeline_id or None,
                    )
                worker_task = self._worker_task(task, spec, depth + 1)
                try:
                    return spec, await self.pool.invoke(spec.worker_agent_id, worker_task)
                except Exception as e:
                    return spec, SubagentResult(success=False, output="", error=str(e))

        results = await asyncio.gather(*[_one(s) for s in subtasks])
        return self._merge(agent, results)

    def _per_worker_budget(self, n: int) -> float:
        ct = getattr(self.pool, "cost_tracker", None)
        if ct is None or n == 0:
            return 0.0
        remaining = max(0.0, float(ct.max_budget) - float(ct.total_cost))
        return remaining / n

    def _over_budget(self) -> bool:
        ct = getattr(self.pool, "cost_tracker", None)
        return ct is not None and ct.check_budget()

    def _worker_task(self, task: SubagentTask, spec: WorkerSpec, depth: int) -> SubagentTask:
        ctx = dict(task.context or {})
        ctx[_CONTEXT_DEPTH_KEY] = depth  # workers see incremented depth => cannot re-delegate
        crit = ""
        if spec.acceptance_criteria:
            crit = "\n\nAcceptance criteria:\n" + "\n".join(
                f"- {c}" for c in spec.acceptance_criteria
            )
        return SubagentTask(
            agent_id=spec.worker_agent_id,
            input=f"{spec.description}{crit}",
            context=ctx,
            pipeline_id=task.pipeline_id,
            stage_id=task.stage_id,
        )

    def _merge(
        self, agent: Subagent, results: list[tuple[WorkerSpec, SubagentResult]]
    ) -> SubagentResult:
        """Combine worker outputs into one artifact set, tagged by subtask.

        Cross-worker consistency review is left to the lead agent downstream;
        here we aggregate outputs, artifacts, cost, and surface any failures."""
        sections: list[str] = []
        artifacts: dict[str, object] = {}
        total_cost = 0.0
        all_tool_calls: list[dict[str, object]] = []
        failures: list[str] = []

        for spec, res in results:
            total_cost += res.cost_usd
            all_tool_calls.extend(res.tool_calls)
            if res.success:
                sections.append(f"## {spec.description}\n{res.output}")
                for k, v in res.artifacts.items():
                    artifacts[f"{spec.worker_agent_id}.{k}"] = v
            else:
                failures.append(f"{spec.worker_agent_id}: {res.error}")

        artifacts["_delegated_workers"] = [s.worker_agent_id for s, _ in results]
        if failures:
            artifacts["_delegate_failures"] = failures
        return SubagentResult(
            success=not failures or len(failures) < len(results),
            output="\n\n".join(sections),
            artifacts=artifacts,
            tool_calls=all_tool_calls,
            cost_usd=total_cost,
            error="; ".join(failures) if failures else None,
        )
