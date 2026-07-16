"""Shell tool: run whitelisted build/test/lint commands.

Wraps ``ShellRunner``, which already enforces the command whitelist and blocks
shell operators / path traversal / env expansion (raising ``SecurityError``).
This tool is NOT granted to any built-in subagent by default; an agent must
list "shell" in its YAML ``tools`` to use it (least privilege).
"""

from __future__ import annotations

import shlex
from typing import Any

from sdlc.audit.events import AuditEventType
from sdlc.integrations.shell_runner import ShellRunner
from sdlc.integrations.whitelist import SecurityError
from sdlc.subagent.tools import ToolContext

_MAX_OUTPUT = 4000  # cap captured stdout/stderr fed back to the model


class ShellTool:
    name = "shell"

    def __init__(self, runner: ShellRunner | None = None) -> None:
        # Default runner uses the built-in DEFAULT_WHITELIST.
        self._runner = runner or ShellRunner()

    def schema(self) -> dict[str, Any]:
        return {
            "name": "shell",
            "description": (
                "Run a whitelisted shell command (build/test/lint). Only allow-"
                "listed commands run; shell operators, pipes, redirects, path "
                "traversal, and env expansion are rejected. Provide the command "
                "as a single string."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to run, e.g. 'pytest -q' or 'ruff check .'",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Optional timeout in seconds.",
                    },
                },
                "required": ["command"],
            },
        }

    async def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        command = args.get("command", "")
        if not command or not command.strip():
            return "Error: command must not be empty"
        try:
            cmd = shlex.split(command)
        except ValueError as e:
            return f"Error: cannot parse command: {e}"
        if not cmd:
            return "Error: command must not be empty"

        timeout = args.get("timeout")
        try:
            # Commands run inside the project root, not the caller's cwd.
            result = self._runner.run(cmd, timeout=timeout, cwd=ctx.project_root)
        except SecurityError as e:
            return f"Error: command rejected by security policy: {e}"
        except Exception as e:
            return f"Error running command: {e}"

        if ctx.audit is not None:
            ctx.audit.emit(
                AuditEventType.SHELL_RUN,
                {
                    "agent_id": ctx.agent_id,
                    "command": command,
                    "exit_code": result.exit_code,
                    "duration_ms": result.duration_ms,
                },
                pipeline_id=ctx.pipeline_id or None,
            )

        out = result.stdout[:_MAX_OUTPUT]
        err = result.stderr[:_MAX_OUTPUT]
        parts = [f"exit_code: {result.exit_code}"]
        if out:
            parts.append(f"stdout:\n{out}")
        if err:
            parts.append(f"stderr:\n{err}")
        return "\n".join(parts)
