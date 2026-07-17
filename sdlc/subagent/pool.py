import json
import re
from pathlib import Path
from typing import Any

from sdlc.audit.events import AuditEventType
from sdlc.audit.logger import AuditLogger
from sdlc.llm.client import MultiLLMClient
from sdlc.llm.cost import CostTracker
from sdlc.llm.models import CompletionRequest, ContentBlock, Message, Role, Tool
from sdlc.subagent.models import Subagent, SubagentResult, SubagentTask
from sdlc.subagent.registry import SubagentRegistry
from sdlc.subagent.tools import ToolContext, ToolRegistry, default_registry

_DANGEROUS_ASK_KEYWORDS = frozenset({
    "deploy", "delete", "remove", "destroy", "drop", "truncate",
    "reset", "force", "overwrite", "purge", "wipe",
})

# ask_user is handled inline (it needs the pool's interaction policy), so it is
# not part of ToolRegistry. Its schema is still offered to agents that grant it.
_ASK_USER_SCHEMA = {
    "name": "ask_user",
    "description": "Ask the user a question and wait for a response.",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question to ask the user."},
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of option strings for the user to choose from.",
            },
        },
        "required": ["question"],
    },
}


class SubagentPool:
    def __init__(
        self,
        registry: SubagentRegistry,
        llm: MultiLLMClient,
        audit: AuditLogger | None = None,
        tools: ToolRegistry | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        self.registry = registry
        self.llm = llm
        self.audit = audit
        # Default registry gives every agent access to the built-in toolset,
        # still gated per-agent by its `tools` allow-list at execution time.
        self.tools = tools if tools is not None else default_registry()
        self.cost_tracker = cost_tracker

    def _resolve_tool_schemas(self, agent: Subagent) -> list[Tool]:
        """Build the LLM tool list from the agent's granted tool names.

        Combines registry-backed tools with the inline ask_user schema, so the
        model is offered exactly the tools the agent is allowed to call."""
        schemas = self.tools.resolve_schemas(agent.tools)
        if "ask_user" in agent.tools:
            schemas.append(_ASK_USER_SCHEMA)
        return [Tool(**s) for s in schemas]

    async def run_agent(
        self,
        agent_id: str,
        task: SubagentTask,
        criteria: list[str] | None = None,
        runtime: str | None = None,
    ) -> SubagentResult:
        """Dispatch to the requested execution mode.

        ``runtime`` (usually the stage's) takes precedence over the agent's own
        ``runtime`` field; "par" runs the Plan-Act-Reflect loop (M-A2), anything
        else uses the single bounded tool-loop (``invoke``). This preserves GA
        behavior for every stage/agent that has not opted in.
        """
        agent = self.registry.get(agent_id)
        mode = runtime or getattr(agent, "runtime", "single")
        if mode == "par":
            from sdlc.subagent.runtime import PlanActReflectRuntime

            par_runtime = PlanActReflectRuntime(
                pool=self,
                llm=self.llm,
                audit=self.audit,
                cost_tracker=self.cost_tracker,
            )
            return await par_runtime.run(agent, task, criteria)
        return await self.invoke(agent_id, task)

    async def invoke(self, agent_id: str, task: SubagentTask) -> SubagentResult:
        agent = self.registry.get(agent_id)
        messages = self._build_initial_messages(agent, task)
        total_cost = 0.0
        iterations = 0
        max_iter = task.max_iter or agent.max_iter
        all_tool_calls: list[dict[str, Any]] = []

        for i in range(max_iter):
            iterations += 1
            req = CompletionRequest(
                model=agent.model,
                messages=messages,
                tools=self._resolve_tool_schemas(agent),
                system=agent.system_addon or None,
                metadata={
                    "pipeline_id": task.pipeline_id,
                    "stage_id": task.stage_id,
                    "agent_id": agent.id,
                    "tier": "high" if "opus" in agent.model else "medium",
                    "iter": i,
                },
            )
            resp = await self.llm.complete(req)
            total_cost += resp.cost_usd

            if self.audit:
                self.audit.emit(
                    AuditEventType.LLM_CALLED,
                    {
                        "agent_id": agent.id,
                        "model": resp.model,
                        "cost_usd": resp.cost_usd,
                        "iter": i,
                    },
                    pipeline_id=task.pipeline_id or None,
                )

            tool_calls = [b for b in resp.content if b.type == "tool_use"]
            if not tool_calls:
                final_text = self._extract_text(resp.content)
                return SubagentResult(
                    success=True,
                    output=final_text,
                    artifacts=self._parse_artifacts(final_text),
                    tool_calls=all_tool_calls,
                    iterations=iterations,
                    cost_usd=total_cost,
                )

            for tc in tool_calls:
                all_tool_calls.append({"name": tc.name, "id": tc.id, "input": tc.input})
                tool_result = await self._execute_tool(tc, task, agent)
                messages.append(
                    Message(
                        role=Role.TOOL,
                        content=tool_result,
                        tool_call_id=tc.id,
                    )
                )

            messages.append(Message(role=Role.ASSISTANT, content=resp.content))

        return SubagentResult(
            success=False,
            output="",
            artifacts={},
            tool_calls=all_tool_calls,
            iterations=iterations,
            cost_usd=total_cost,
            error=f"Max iterations ({max_iter}) exceeded",
        )

    def _build_initial_messages(self, agent: Subagent, task: SubagentTask) -> list[Message]:
        parts = []
        if agent.prompt:
            parts.append(agent.prompt)
        if task.input:
            parts.append(task.input)
        if task.context:
            parts.append(f"Context:\n{json.dinternal-monitorings(task.context, indent=2, default=str)}")
        content = "\n\n".join(parts)
        return [Message(role=Role.USER, content=content)]

    def _extract_text(self, content: list[ContentBlock]) -> str:
        texts = [b.text for b in content if b.type == "text" and b.text]
        return "\n".join(texts)

    def _parse_artifacts(self, text: str) -> dict[str, Any]:
        artifacts: dict[str, Any] = {}
        pattern = r"```json\s*\n(.*?)\n```"
        for i, match in enumerate(re.finditer(pattern, text, re.DOTALL)):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict):
                    artifacts.update(data)
                else:
                    artifacts[f"block_{i}"] = data
            except json.JSONDecodeError:
                continue
        return artifacts

    @staticmethod
    def _get_project_root(task: SubagentTask) -> Path:
        """Resolve project root from task context or fall back to cwd."""
        ctx = task.context or {}
        root = ctx.get("project_root") or ctx.get("project_dir")
        if root:
            p = Path(root).resolve()
            if p.is_dir():
                return p
        return Path.cwd().resolve()

    def _validate_path(self, path_str: str, project_root: Path) -> Path:
        """Validate that *path_str* resolves inside *project_root*.

        Rejects:
          - Paths that resolve outside the project root (including via ``..``)
          - Absolute paths
          - Paths containing ``~`` (home directory expansion)
        """
        if not path_str:
            raise ValueError("Path must not be empty")
        if path_str.startswith("/"):
            raise ValueError(f"Absolute paths are not allowed: {path_str}")
        if "~" in path_str:
            raise ValueError(f"Home directory paths (~/) are not allowed: {path_str}")

        resolved = (project_root / path_str).resolve()
        try:
            resolved.relative_to(project_root)
        except ValueError:
            raise ValueError(
                f"Path escapes project root: {path_str} (resolved to {resolved}, "
                f"root is {project_root})"
            ) from None
        return resolved

    def _build_tool_context(self, task: SubagentTask, agent: Subagent) -> ToolContext:
        """Assemble the security/observability context for a tool call.

        MCP-server and skill whitelists are read from the agent config first
        (per-agent grants) and then the task context, defaulting to empty
        (deny-all) so shell/mcp/skill stay least-privilege."""
        ctx_data = task.context or {}
        servers = set(getattr(agent, "mcp_servers", None) or [])
        servers |= set(ctx_data.get("mcp_servers", []) or [])
        skills = set(getattr(agent, "skills", None) or [])
        skills |= set(ctx_data.get("skills", []) or [])
        return ToolContext(
            project_root=self._get_project_root(task),
            pipeline_id=task.pipeline_id,
            stage_id=task.stage_id,
            agent_id=agent.id,
            audit=self.audit,
            cost_tracker=self.cost_tracker,
            server_whitelist=servers,
            skill_whitelist=skills,
        )

    async def _execute_tool(
        self, tool_call: ContentBlock, task: SubagentTask, agent: Subagent
    ) -> str:
        tool_name = tool_call.name or ""
        tool_input = tool_call.input or {}
        if tool_name not in agent.tools:
            return f"Error: tool '{tool_name}' is not allowed for agent {agent.id}"

        # ask_user is handled inline: it needs the pool's non-interactive policy
        # (dangerous-keyword guard), not a registry tool.
        if tool_name == "ask_user":
            return self._handle_ask_user(tool_input)

        ctx = self._build_tool_context(task, agent)
        return await self.tools.execute(tool_name, tool_input, ctx, agent.tools)

    def _handle_ask_user(self, tool_input: dict[str, Any]) -> str:
        question = tool_input.get("question", "")
        options = tool_input.get("options", [])
        # In non-interactive mode, do NOT auto-select dangerous options
        if options and isinstance(options, list):
            question_lower = question.lower()
            has_dangerous = any(kw in question_lower for kw in _DANGEROUS_ASK_KEYWORDS)
            if has_dangerous:
                return (
                    f"[Interaction paused: {question}]\n"
                    "Options: " + " | ".join(str(o) for o in options) + "\n"
                    "WARNING: This question involves a potentially destructive "
                    "operation. Auto-selection is disabled for safety. "
                    "Please provide the answer in the task context."
                )
            return (
                f"[Interaction paused: {question}]\n"
                "Options: " + " | ".join(str(o) for o in options) + "\n"
                "Interactive user input is not available in this mode. "
                "Please select the most appropriate option and proceed."
            )
        return (
            f"[Interaction paused: {question}]\n"
            "Note: Interactive user input is not available in this mode. "
            "Please provide the answer in the task context."
        )
