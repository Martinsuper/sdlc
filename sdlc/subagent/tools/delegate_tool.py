"""Delegate tool (M-A5): let a lead agent fan out subtasks to worker agents.

The tool wraps an Orchestrator. It is deny-by-default: an agent must be granted
"delegate" in its YAML, and the depth guard in Orchestrator prevents workers
from delegating again (no runaway trees).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from sdlc.subagent.orchestrator import DelegationDepthError, Orchestrator, WorkerSpec
from sdlc.subagent.tools import ToolContext

if TYPE_CHECKING:
    from sdlc.subagent.pool import SubagentPool

_MAX_OUTPUT = 6000


class DelegateTool:
    name = "delegate"

    def __init__(self, pool: SubagentPool | None = None) -> None:
        # Pool is injected at registration; without it the tool reports an error
        # (it cannot dispatch workers on its own).
        self._pool = pool

    def schema(self) -> dict[str, Any]:
        return {
            "name": "delegate",
            "description": (
                "Dispatch independent subtasks to worker agents in parallel and "
                "get back a merged result. Use for decomposable work (e.g. design "
                "split into DB / API / risk). Workers cannot themselves delegate."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "subtasks": {
                        "type": "array",
                        "description": "Subtasks to dispatch.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "worker_agent_id": {"type": "string"},
                                "description": {"type": "string"},
                                "acceptance_criteria": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["worker_agent_id", "description"],
                        },
                    },
                },
                "required": ["subtasks"],
            },
        }

    async def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        if self._pool is None:
            return "Error: delegation is not available (no pool bound)"
        raw = args.get("subtasks", [])
        if not isinstance(raw, list) or not raw:
            return "Error: 'subtasks' must be a non-empty list"
        specs = [
            WorkerSpec(
                worker_agent_id=str(s.get("worker_agent_id", "")),
                description=str(s.get("description", "")),
                acceptance_criteria=[str(c) for c in s.get("acceptance_criteria", []) or []],
            )
            for s in raw
            if isinstance(s, dict) and s.get("worker_agent_id") and s.get("description")
        ]
        if not specs:
            return "Error: no valid subtasks provided"

        from sdlc.subagent.models import Subagent, SubagentTask

        orch = Orchestrator(self._pool)
        lead = Subagent(id=ctx.agent_id, name=ctx.agent_id, role="orchestrator", model="")
        task = SubagentTask(
            agent_id=ctx.agent_id,
            input="",
            context={"_delegate_depth": 0},
            pipeline_id=ctx.pipeline_id,
            stage_id=ctx.stage_id,
        )
        try:
            result = await orch.run(lead, task, specs)
        except DelegationDepthError as e:
            return f"Error: {e}"

        payload = {"output": result.output, "artifacts": result.artifacts}
        if result.error:
            payload["error"] = result.error
        return json.dinternal-monitorings(payload, ensure_ascii=False, default=str)[:_MAX_OUTPUT]
