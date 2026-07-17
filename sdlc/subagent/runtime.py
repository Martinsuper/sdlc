"""Plan-Act-Reflect runtime (M-A2).

Upgrades a subagent from a single bounded tool-loop to an explicit
Plan → (Act → Reflect)* loop, for complex stages (design/impl/impact) that
benefit from decomposition and self-checking. Lightweight stages stay single
(``runtime="single"``) to control cost.

Wiring: ``SubagentPool.run_agent`` dispatches to this runtime when the agent's
``runtime == "par"``; otherwise it calls the original ``invoke``. Each subtask
is executed by reusing ``pool.invoke`` (the M-A1 tool-loop), so tool access and
security are inherited unchanged.

Cost is bounded three ways: ``max_reflect`` caps retries per subtask; the
optional ``CostTracker`` short-circuits when the budget would be exceeded; and
reflection is skipped entirely for single-mode agents.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sdlc.audit.events import AuditEventType
from sdlc.llm.models import CompletionRequest, Message, Role
from sdlc.subagent.models import Subagent, SubagentResult, SubagentTask

if TYPE_CHECKING:
    from sdlc.audit.logger import AuditLogger
    from sdlc.llm.client import MultiLLMClient
    from sdlc.llm.cost import CostTracker
    from sdlc.subagent.pool import SubagentPool


@dataclass
class SubTask:
    description: str
    acceptance_criteria: list[str] = field(default_factory=list)
    budget_usd: float = 0.0


@dataclass
class ReflectVerdict:
    passed: bool
    score: float  # 0..1
    unmet: list[str] = field(default_factory=list)
    fix_hint: str = ""


def _extract_json(text: str) -> Any:
    """Pull the first JSON object/array out of an LLM reply.

    Models wrap JSON in prose or ```json fences; be tolerant. Returns None when
    nothing parses so callers can fall back rather than crash a stage."""
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    candidates = []
    if fence:
        candidates.append(fence.group(1))
    candidates.append(text)
    # Also try the outermost {...} / [...] span.
    brace = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if brace:
        candidates.append(brace.group(1))
    for c in candidates:
        try:
            return json.loads(c)
        except (json.JSONDecodeError, TypeError):
            continue
    return None


class PlanActReflectRuntime:
    def __init__(
        self,
        pool: SubagentPool,
        llm: MultiLLMClient,
        max_reflect: int = 2,
        reflect_model: str = "",
        audit: AuditLogger | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        self.pool = pool
        self.llm = llm
        self.max_reflect = max_reflect
        self.reflect_model = reflect_model
        self.audit = audit
        self.cost_tracker = cost_tracker
        self._spent = 0.0

    async def run(
        self, agent: Subagent, task: SubagentTask, criteria: list[str] | None = None
    ) -> SubagentResult:
        criteria = criteria or []
        plan = await self._plan(agent, task)
        trace: list[dict[str, Any]] = []
        outputs: list[str] = []
        artifacts: dict[str, Any] = {}
        all_tool_calls: list[dict[str, Any]] = []
        total_iters = 0
        last_score = 0.0

        for sub in plan:
            sub_criteria = sub.acceptance_criteria or criteria
            for attempt in range(self.max_reflect + 1):
                if self._budget_exhausted():
                    trace.append(
                        {"sub": sub.description, "attempt": attempt, "stopped": "budget"}
                    )
                    break

                act = await self.pool.invoke(agent.id, self._subtask_task(task, sub))
                self._spent += act.cost_usd
                total_iters += act.iterations
                all_tool_calls.extend(act.tool_calls)

                verdict = await self._reflect(agent, sub, act, sub_criteria)
                last_score = verdict.score
                trace.append(
                    {
                        "sub": sub.description,
                        "attempt": attempt,
                        "score": verdict.score,
                        "passed": verdict.passed,
                        "unmet": verdict.unmet,
                    }
                )
                if self.audit is not None:
                    self.audit.emit(
                        AuditEventType.REFLECT_STEP,
                        {
                            "agent_id": agent.id,
                            "subtask": sub.description,
                            "attempt": attempt,
                            "score": verdict.score,
                            "passed": verdict.passed,
                        },
                        pipeline_id=task.pipeline_id or None,
                    )

                if verdict.passed:
                    outputs.append(act.output)
                    artifacts.update(act.artifacts)
                    break
                # Not passed: feed the fix hint back into the next attempt.
                task = self._inject_fix(task, verdict.fix_hint)
            else:
                # Ran out of attempts without passing — keep the last output.
                outputs.append(act.output)
                artifacts.update(act.artifacts)

        # Reflection trace is persisted as an artifact so it is queryable and
        # can feed eval (M-D2). Kept under a stable key.
        artifacts["_reflection_trace"] = trace
        artifacts["_self_score"] = last_score
        return SubagentResult(
            success=True,
            output="\n\n".join(o for o in outputs if o),
            artifacts=artifacts,
            tool_calls=all_tool_calls,
            iterations=total_iters,
            cost_usd=self._spent,
        )

    # --- internals -------------------------------------------------------- #

    def _budget_exhausted(self) -> bool:
        if self.cost_tracker is None:
            return False
        # The runtime tracks its own spend in self._spent (it does not call
        # tracker.record), so compare that against the configured ceiling.
        max_budget: float = self.cost_tracker.max_budget
        return self._spent >= max_budget

    def _subtask_task(self, task: SubagentTask, sub: SubTask) -> SubagentTask:
        crit = ""
        if sub.acceptance_criteria:
            crit = "\n\nAcceptance criteria:\n" + "\n".join(
                f"- {c}" for c in sub.acceptance_criteria
            )
        return SubagentTask(
            agent_id=task.agent_id,
            input=f"{task.input}\n\nSubtask: {sub.description}{crit}",
            context=task.context,
            artifacts_required=task.artifacts_required,
            pipeline_id=task.pipeline_id,
            stage_id=task.stage_id,
            max_iter=task.max_iter,
        )

    def _inject_fix(self, task: SubagentTask, fix_hint: str) -> SubagentTask:
        if not fix_hint:
            return task
        return SubagentTask(
            agent_id=task.agent_id,
            input=f"{task.input}\n\nPrevious attempt fell short. Fix: {fix_hint}",
            context=task.context,
            artifacts_required=task.artifacts_required,
            pipeline_id=task.pipeline_id,
            stage_id=task.stage_id,
            max_iter=task.max_iter,
        )

    async def _plan(self, agent: Subagent, task: SubagentTask) -> list[SubTask]:
        """Ask the model to decompose the task into subtasks with criteria.

        On any parse failure, fall back to a single subtask covering the whole
        task — so planning never makes a stage worse than single mode."""
        prompt = (
            "Decompose the following task into an ordered list of concrete "
            "subtasks. Reply with JSON: a list of objects, each with "
            '"description" (string) and "acceptance_criteria" (list of strings). '
            "Keep it minimal — only the subtasks truly needed.\n\n"
            f"Task: {task.input}"
        )
        req = CompletionRequest(
            model=agent.model,
            messages=[Message(role=Role.USER, content=prompt)],
            metadata={
                "pipeline_id": task.pipeline_id,
                "stage_id": task.stage_id,
                "agent_id": agent.id,
                "phase": "plan",
            },
        )
        try:
            resp = await self.llm.complete(req)
            self._spent += resp.cost_usd
            data = _extract_json(self._text(resp))
        except Exception:
            data = None

        if isinstance(data, list) and data:
            plan: list[SubTask] = []
            for item in data:
                if isinstance(item, dict) and item.get("description"):
                    plan.append(
                        SubTask(
                            description=str(item["description"]),
                            acceptance_criteria=[
                                str(c) for c in item.get("acceptance_criteria", []) or []
                            ],
                        )
                    )
            if plan:
                return plan
        return [SubTask(description=task.input)]

    async def _reflect(
        self, agent: Subagent, sub: SubTask, act: SubagentResult, criteria: list[str]
    ) -> ReflectVerdict:
        """Self-check the produced output against the acceptance criteria.

        Uses reflect_model if configured (a stronger judge over a weaker
        producer — the LLM-as-judge seed shared with M-D2). Parse failure is
        treated as "passed" so a flaky judge never blocks forever."""
        checks = sub.acceptance_criteria or criteria
        if not checks:
            return ReflectVerdict(passed=True, score=1.0)

        prompt = (
            "You are reviewing whether an output meets its acceptance criteria. "
            "Reply with JSON: {\"passed\": bool, \"score\": 0..1, "
            '"unmet": [strings], "fix_hint": string}.\n\n'
            "Criteria:\n" + "\n".join(f"- {c}" for c in checks) + "\n\n"
            f"Output to review:\n{act.output[:6000]}"
        )
        model = self.reflect_model or agent.model
        req = CompletionRequest(
            model=model,
            messages=[Message(role=Role.USER, content=prompt)],
            metadata={"agent_id": agent.id, "phase": "reflect"},
        )
        try:
            resp = await self.llm.complete(req)
            self._spent += resp.cost_usd
            data = _extract_json(self._text(resp))
        except Exception:
            data = None

        if isinstance(data, dict):
            return ReflectVerdict(
                passed=bool(data.get("passed", False)),
                score=float(data.get("score", 0.0) or 0.0),
                unmet=[str(u) for u in data.get("unmet", []) or []],
                fix_hint=str(data.get("fix_hint", "") or ""),
            )
        # Unparseable judgment: don't block the pipeline on a flaky judge.
        return ReflectVerdict(passed=True, score=0.5, fix_hint="")

    @staticmethod
    def _text(resp: Any) -> str:
        return "\n".join(b.text for b in resp.content if b.type == "text" and b.text)
