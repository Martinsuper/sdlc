import json
import re
from pathlib import Path
from typing import Any

from sdlc.audit.events import AuditEventType
from sdlc.audit.logger import AuditLogger
from sdlc.llm.client import MultiLLMClient
from sdlc.llm.models import CompletionRequest, ContentBlock, Message, Role
from sdlc.subagent.models import Subagent, SubagentResult, SubagentTask
from sdlc.subagent.registry import SubagentRegistry
from sdlc.utils.paths import ensure_dir

_DANGEROUS_ASK_KEYWORDS = frozenset({
    "deploy", "delete", "remove", "destroy", "drop", "truncate",
    "reset", "force", "overwrite", "purge", "wipe",
})


class SubagentPool:
    def __init__(
        self,
        registry: SubagentRegistry,
        llm: MultiLLMClient,
        audit: AuditLogger | None = None,
    ) -> None:
        self.registry = registry
        self.llm = llm
        self.audit = audit

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

    async def _execute_tool(
        self, tool_call: ContentBlock, task: SubagentTask, agent: Subagent
    ) -> str:
        tool_name = tool_call.name or ""
        tool_input = tool_call.input or {}
        if tool_name not in agent.tools:
            return f"Error: tool '{tool_name}' is not allowed for agent {agent.id}"

        project_root = self._get_project_root(task)

        if tool_name == "read":
            path = tool_input.get("path", "")
            try:
                safe_path = self._validate_path(path, project_root)
                return safe_path.read_text(encoding="utf-8")
            except ValueError as e:
                return f"Error: {e}"
            except Exception as e:
                return f"Error reading {path}: {e}"
        elif tool_name == "write":
            path = tool_input.get("path", "")
            content = tool_input.get("content", "")
            try:
                safe_path = self._validate_path(path, project_root)
                ensure_dir(safe_path.parent)
                safe_path.write_text(content, encoding="utf-8")
                return f"Successfully wrote to {path}"
            except ValueError as e:
                return f"Error: {e}"
            except Exception as e:
                return f"Error writing {path}: {e}"
        elif tool_name == "list":
            path = tool_input.get("path", "")
            try:
                safe_path = self._validate_path(path, project_root)
                if not safe_path.is_dir():
                    return f"Error: {path} is not a directory"
                entries = sorted(
                    p.relative_to(project_root).as_posix()
                    for p in safe_path.iterdir()
                )
                return "\n".join(entries) if entries else "(empty directory)"
            except ValueError as e:
                return f"Error: {e}"
            except Exception as e:
                return f"Error listing {path}: {e}"
        elif tool_name == "ask_user":
            question = tool_input.get("question", "")
            options = tool_input.get("options", [])
            # In non-interactive mode, do NOT auto-select dangerous options
            if options and isinstance(options, list):
                question_lower = question.lower()
                has_dangerous = any(
                    kw in question_lower for kw in _DANGEROUS_ASK_KEYWORDS
                )
                if has_dangerous:
                    return (
                        f"[Interaction paused: {question}]\n"
                        "Options: " + " | ".join(str(o) for o in options) + "\n"
                        "WARNING: This question involves a potentially destructive "
                        "operation. Auto-selection is disabled for safety. "
                        "Please provide the answer in the task context."
                    )
                # For non-dangerous questions, return all options and let LLM decide
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
        else:
            return f"Error: tool '{tool_name}' not implemented yet"
