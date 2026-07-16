"""MCP tool: call an external MCP server tool, gated by a server whitelist.

Wraps ``MCPClient.call``. The target server must appear in
``ctx.server_whitelist`` — an empty whitelist (the default) denies all MCP
calls, so an agent granted "mcp_call" still cannot reach any server until a
caller explicitly populates the whitelist.
"""

from __future__ import annotations

from typing import Any

from sdlc.audit.events import AuditEventType
from sdlc.integrations.mcp_client import MCPClient
from sdlc.subagent.tools import ToolContext

_MAX_OUTPUT = 4000


class MCPCallTool:
    name = "mcp_call"

    def __init__(self, client: MCPClient | None = None) -> None:
        self._client = client

    def schema(self) -> dict[str, Any]:
        return {
            "name": "mcp_call",
            "description": (
                "Call a tool on an external MCP server. The server must be "
                "explicitly allow-listed for this agent."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "server": {
                        "type": "string",
                        "description": "MCP server identifier (must be whitelisted).",
                    },
                    "tool": {"type": "string", "description": "Tool name on the server."},
                    "args": {
                        "type": "object",
                        "description": "Arguments to pass to the tool.",
                    },
                },
                "required": ["server", "tool"],
            },
        }

    async def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        server = args.get("server", "")
        tool = args.get("tool", "")
        call_args = args.get("args", {}) or {}
        if not server or not tool:
            return "Error: 'server' and 'tool' are required"
        if server not in ctx.server_whitelist:
            return (
                f"Error: MCP server '{server}' is not whitelisted for agent "
                f"{ctx.agent_id}. Allowed: {sorted(ctx.server_whitelist) or '(none)'}"
            )

        client = self._client or MCPClient()
        try:
            result = await client.call(server, tool, call_args)
        except Exception as e:
            return f"Error calling MCP {server}/{tool}: {e}"
        finally:
            if self._client is None:
                await client.close()

        if ctx.audit is not None:
            ctx.audit.emit(
                AuditEventType.MCP_CALLED,
                {"agent_id": ctx.agent_id, "server": server, "tool": tool},
                pipeline_id=ctx.pipeline_id or None,
            )
        return str(result)[:_MAX_OUTPUT]
