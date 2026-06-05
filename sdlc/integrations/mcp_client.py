"""MCP SDK wrapper - client for calling MCP server tools."""

from __future__ import annotations

import asyncio
import json
import subprocess
import time
from typing import Any

import httpx


class MCPClient:
    """Client for calling MCP server tools.

    Supports both HTTP and stdio transports for MCP servers.
    Includes timeout handling, retry logic, and tool listing cache.
    """

    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRIES = 3
    CACHE_TTL_SECONDS = 300  # 5 minutes

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        cache_ttl: int = CACHE_TTL_SECONDS,
    ) -> None:
        self._timeout = timeout
        self._retries = retries
        self._cache_ttl = cache_ttl
        self._tools_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._http_client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http_client.aclose()

    async def __aenter__(self) -> MCPClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def call(self, server: str, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP server tool.

        Parameters
        ----------
        server : str
            Either an HTTP URL (``http://`` or ``https://``) or a stdio command
            string (e.g. ``npx @modelcontextprotocol/server-filesystem /tmp``).
        tool : str
            The name of the tool to invoke on the server.
        args : dict
            Arguments to pass to the tool.

        Returns
        -------
        dict
            The tool result.
        """
        if self._is_http(server):
            return await self._call_http(server, tool, args)
        return await self._call_stdio(server, tool, args)

    async def list_tools(self, server: str) -> list[dict[str, Any]]:
        """List available tools from an MCP server.

        Results are cached for ``cache_ttl`` seconds (default 5 minutes).

        Parameters
        ----------
        server : str
            Server identifier (HTTP URL or stdio command).

        Returns
        -------
        list[dict]
            List of tool descriptors.
        """
        now = time.monotonic()
        cached = self._tools_cache.get(server)
        if cached is not None:
            cached_at, tools = cached
            if now - cached_at < self._cache_ttl:
                return tools

        if self._is_http(server):
            tools = await self._list_tools_http(server)
        else:
            tools = await self._list_tools_stdio(server)

        self._tools_cache[server] = (now, tools)
        return tools

    async def health_check(self, server: str) -> bool:
        """Check if an MCP server is reachable.

        Parameters
        ----------
        server : str
            Server identifier (HTTP URL or stdio command).

        Returns
        -------
        bool
            ``True`` if the server responded successfully.
        """
        try:
            if self._is_http(server):
                return await self._health_check_http(server)
            return await self._health_check_stdio(server)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # HTTP transport helpers
    # ------------------------------------------------------------------

    async def _call_http(self, server: str, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """Call a tool via HTTP transport with retry logic."""
        url = f"{server.rstrip('/')}/tools/call"
        payload = {"name": tool, "arguments": args}

        last_exc: Exception | None = None
        for attempt in range(self._retries):
            try:
                resp = await self._http_client.post(url, json=payload, timeout=self._timeout)
                resp.raise_for_status()
                return dict(resp.json())
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_exc = exc
                if attempt < self._retries - 1:
                    await asyncio.sleep(2**attempt)
        raise last_exc  # type: ignore[misc]

    async def _list_tools_http(self, server: str) -> list[dict[str, Any]]:
        """List tools via HTTP transport with retry logic."""
        url = f"{server.rstrip('/')}/tools/list"

        last_exc: Exception | None = None
        for attempt in range(self._retries):
            try:
                resp = await self._http_client.get(url, timeout=self._timeout)
                resp.raise_for_status()
                data = dict(resp.json())
                return list(data.get("tools", []))
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_exc = exc
                if attempt < self._retries - 1:
                    await asyncio.sleep(2**attempt)
        raise last_exc  # type: ignore[misc]

    async def _health_check_http(self, server: str) -> bool:
        """Health check via HTTP transport."""
        url = f"{server.rstrip('/')}/health"
        try:
            resp = await self._http_client.get(url, timeout=self._timeout)
            return resp.status_code == 200
        except httpx.RequestError:
            return False

    # ------------------------------------------------------------------
    # stdio transport helpers
    # ------------------------------------------------------------------

    async def _call_stdio(self, server: str, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """Call a tool via stdio transport with retry logic."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        }

        last_exc: Exception | None = None
        for attempt in range(self._retries):
            try:
                return await self._run_stdio_command(server, request)
            except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as exc:
                last_exc = exc
                if attempt < self._retries - 1:
                    await asyncio.sleep(2**attempt)
        raise last_exc  # type: ignore[misc]

    async def _list_tools_stdio(self, server: str) -> list[dict[str, Any]]:
        """List tools via stdio transport with retry logic."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        last_exc: Exception | None = None
        for attempt in range(self._retries):
            try:
                result = await self._run_stdio_command(server, request)
                return list(result.get("tools", []))
            except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as exc:
                last_exc = exc
                if attempt < self._retries - 1:
                    await asyncio.sleep(2**attempt)
        raise last_exc  # type: ignore[misc]

    async def _health_check_stdio(self, server: str) -> bool:
        """Health check via stdio transport -- just try listing tools."""
        try:
            result = await self._list_tools_stdio(server)
            return isinstance(result, list)
        except Exception:
            return False

    async def _run_stdio_command(
        self, server: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Run a stdio MCP server subprocess and return the JSON response."""
        cmd = server.split()
        loop = asyncio.get_running_loop()

        def _run() -> dict[str, Any]:
            proc = subprocess.run(
                cmd,
                input=json.dinternal-monitorings(request),
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if proc.returncode != 0:
                raise subprocess.SubprocessError(
                    f"MCP server exited with code {proc.returncode}: {proc.stderr}"
                )
            data = json.loads(proc.stdout)
            if "error" in data:
                raise subprocess.SubprocessError(
                    f"MCP server error: {data['error']}"
                )
            return dict(data.get("result", {}))

        return await loop.run_in_executor(None, _run)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _is_http(server: str) -> bool:
        """Return True if *server* looks like an HTTP URL."""
        return server.startswith(("http://", "https://"))
