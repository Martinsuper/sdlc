"""Subagent tool registry and execution (M-A1: tool ecosystem).

The Subagent tool-loop was previously hard-wired to read/write/list/ask_user
in ``pool.py``. This package extracts tools behind a small ``Tool`` protocol and
a ``ToolRegistry`` so agents can be granted a wider, security-gated toolset
(grep/glob/shell/mcp_call/skill) purely via their ``tools`` allow-list — no
changes to the tool-loop per new tool.

Security is per-tool and enforced inside each tool's ``run``:
  - fs tools:  paths confined to project_root (no absolute/``..``/``~``)
  - shell:     command whitelist + shell-operator/traversal blocking
  - mcp_call:  MCP server must be in ctx.server_whitelist
  - skill:     skill name must be in ctx.skill_whitelist
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from sdlc.audit.events import AuditEventType

if TYPE_CHECKING:
    from sdlc.audit.logger import AuditLogger
    from sdlc.llm.cost import CostTracker


@dataclass
class ToolContext:
    """Per-invocation context handed to every tool.

    Carries the security boundaries (project_root, whitelists) and the
    observability/accounting hooks (audit, cost_tracker). Whitelists default to
    empty sets — i.e. shell/mcp/skill are *denied* unless a caller explicitly
    grants servers/skills — so the safe default is least privilege.
    """

    project_root: Path
    pipeline_id: str = ""
    stage_id: str = ""
    agent_id: str = ""
    audit: AuditLogger | None = None
    cost_tracker: CostTracker | None = None
    server_whitelist: set[str] = field(default_factory=set)
    skill_whitelist: set[str] = field(default_factory=set)


@runtime_checkable
class Tool(Protocol):
    """A subagent tool. ``schema()`` feeds the LLM the tool definition;
    ``run()`` executes it and returns a string result for the tool-loop."""

    name: str

    def schema(self) -> dict[str, Any]: ...

    async def run(self, args: dict[str, Any], ctx: ToolContext) -> str: ...


class ToolRegistry:
    """Holds the available tools and mediates schema exposure + execution.

    ``resolve_schemas`` narrows to the agent's granted tools (so the model only
    sees what it may call); ``execute`` re-checks the allow-list at call time
    (defense in depth) and emits a ``TOOL_CALLED`` audit event per invocation.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def register_all(self, tools: list[Tool]) -> None:
        for t in tools:
            self.register(t)

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return sorted(self._tools)

    def resolve_schemas(self, names: list[str]) -> list[dict[str, Any]]:
        """Map an agent's granted tool names to JSON schemas for the LLM.

        Unknown names are silently skipped (an agent granting a tool the build
        doesn't provide should not crash the run — it just won't be offered)."""
        return [self._tools[n].schema() for n in names if n in self._tools]

    async def execute(
        self, name: str, args: dict[str, Any], ctx: ToolContext, allowed: list[str]
    ) -> str:
        """Execute a tool by name, enforcing the agent's allow-list.

        Returns an ``Error: ...`` string (rather than raising) for policy
        rejections and unknown tools, so the tool-loop can feed the message
        back to the model instead of aborting the stage.
        """
        if name not in allowed:
            return f"Error: tool '{name}' is not allowed for agent {ctx.agent_id}"
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: tool '{name}' is not implemented"

        if ctx.audit is not None:
            ctx.audit.emit(
                AuditEventType.TOOL_CALLED,
                {"agent_id": ctx.agent_id, "tool": name, "stage_id": ctx.stage_id},
                pipeline_id=ctx.pipeline_id or None,
            )
        return await tool.run(args, ctx)


def default_registry() -> ToolRegistry:
    """Build a registry with all built-in tools registered.

    shell/mcp_call/skill are registered here (so any agent *may* be granted
    them) but remain denied at execution time unless the agent's YAML lists
    them AND — for mcp/skill — the relevant whitelist is populated.
    """
    from sdlc.subagent.tools.fs_tools import (
        GlobTool,
        GrepTool,
        ListTool,
        ReadTool,
        WriteTool,
    )
    from sdlc.subagent.tools.mcp_tool import MCPCallTool
    from sdlc.subagent.tools.shell_tool import ShellTool
    from sdlc.subagent.tools.skill_tool import SkillTool

    reg = ToolRegistry()
    reg.register_all(
        [
            ReadTool(),
            WriteTool(),
            ListTool(),
            GrepTool(),
            GlobTool(),
            ShellTool(),
            MCPCallTool(),
            SkillTool(),
        ]
    )
    return reg
