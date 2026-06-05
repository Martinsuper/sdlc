"""MCP SDK wrapper - stub for M2."""

from __future__ import annotations


class MCPClient:
    """Client for calling MCP server tools.

    This is a stub implementation that will be completed in milestone M2.
    """

    async def call(self, server: str, tool: str, args: dict[str, object]) -> dict[str, object]:
        """Call an MCP server tool - stub for M2."""
        raise NotImplementedError("MCPClient will be implemented in M2")
