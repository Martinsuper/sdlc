"""Skill tool: run a registered built-in skill, gated by a skill whitelist.

Wraps ``SkillRunner.run``. The skill name must appear in
``ctx.skill_whitelist`` — an empty whitelist (the default) denies all skills.
"""

from __future__ import annotations

import json
from typing import Any

from sdlc.audit.events import AuditEventType
from sdlc.integrations.skill_runner import SkillRunner
from sdlc.subagent.tools import ToolContext

_MAX_OUTPUT = 4000


class SkillTool:
    name = "skill"

    def __init__(self, runner: SkillRunner | None = None) -> None:
        self._runner = runner or SkillRunner()

    def schema(self) -> dict[str, Any]:
        return {
            "name": "skill",
            "description": (
                "Run a registered built-in skill by name. The skill must be "
                "explicitly allow-listed for this agent."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "skill": {"type": "string", "description": "Skill name to run."},
                    "context": {
                        "type": "object",
                        "description": "Context dict passed to the skill.",
                    },
                },
                "required": ["skill"],
            },
        }

    async def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        skill = args.get("skill", "")
        skill_ctx = args.get("context", {}) or {}
        if not skill:
            return "Error: 'skill' is required"
        if skill not in ctx.skill_whitelist:
            return (
                f"Error: skill '{skill}' is not whitelisted for agent "
                f"{ctx.agent_id}. Allowed: {sorted(ctx.skill_whitelist) or '(none)'}"
            )
        if not self._runner.has_skill(skill):
            return f"Error: unknown skill '{skill}'"

        try:
            result = await self._runner.run(skill, skill_ctx)
        except Exception as e:
            return f"Error running skill '{skill}': {e}"

        if ctx.audit is not None:
            ctx.audit.emit(
                AuditEventType.SKILL_USED,
                {"agent_id": ctx.agent_id, "skill": skill},
                pipeline_id=ctx.pipeline_id or None,
            )
        try:
            return json.dinternal-monitorings(result, ensure_ascii=False, default=str)[:_MAX_OUTPUT]
        except (TypeError, ValueError):
            return str(result)[:_MAX_OUTPUT]
