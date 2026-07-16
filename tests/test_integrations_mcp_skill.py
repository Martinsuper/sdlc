"""Tests for MCPClient and SkillRunner real implementations."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx

from sdlc.integrations.mcp_client import MCPClient
from sdlc.integrations.skill_runner import SkillRunner

# ============================================================================
# MCPClient tests
# ============================================================================


class TestMCPClientHTTPCall:
    """Tests for MCPClient.call with HTTP transport."""

    @respx.mock
    def test_call_http_success(self) -> None:
        respx.post("https://mcp.example.com/tools/call").mock(
            return_value=httpx.Response(200, json={"result": "hello"})
        )

        async def _go() -> None:
            async with MCPClient() as client:
                result = await client.call(
                    "https://mcp.example.com", "greet", {"name": "world"}
                )
                assert result == {"result": "hello"}

        asyncio.run(_go())

    @respx.mock
    def test_call_http_sends_correct_payload(self) -> None:
        route = respx.post("https://mcp.example.com/tools/call").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        async def _go() -> None:
            async with MCPClient() as client:
                await client.call("https://mcp.example.com", "my_tool", {"a": 1})

        asyncio.run(_go())
        assert route.called
        request = route.calls[0].request
        body = json.loads(request.content)
        assert body["name"] == "my_tool"
        assert body["arguments"] == {"a": 1}


class TestMCPClientHTTPListTools:
    """Tests for MCPClient.list_tools with HTTP transport."""

    @respx.mock
    def test_list_tools_http(self) -> None:
        tools = [
            {"name": "tool_a", "description": "Does A"},
            {"name": "tool_b", "description": "Does B"},
        ]
        respx.get("https://mcp.example.com/tools/list").mock(
            return_value=httpx.Response(200, json={"tools": tools})
        )

        async def _go() -> None:
            async with MCPClient() as client:
                result = await client.list_tools("https://mcp.example.com")
                assert result == tools

        asyncio.run(_go())

    @respx.mock
    def test_list_tools_caching(self) -> None:
        """Tool listings are cached for 5 minutes."""
        route = respx.get("https://mcp.example.com/tools/list").mock(
            return_value=httpx.Response(200, json={"tools": [{"name": "t"}]})
        )

        async def _go() -> None:
            client = MCPClient(cache_ttl=60)
            await client.list_tools("https://mcp.example.com")
            await client.list_tools("https://mcp.example.com")
            # Second call should hit cache, so route is called only once.
            assert route.call_count == 1
            await client.close()

        asyncio.run(_go())

    @respx.mock
    def test_list_tools_cache_expires(self) -> None:
        """Cache expires after cache_ttl seconds."""
        route = respx.get("https://mcp.example.com/tools/list").mock(
            return_value=httpx.Response(200, json={"tools": []})
        )

        async def _go() -> None:
            # Very short TTL so cache expires immediately.
            client = MCPClient(cache_ttl=0)
            await client.list_tools("https://mcp.example.com")
            await client.list_tools("https://mcp.example.com")
            # Both calls should go to the server.
            assert route.call_count == 2
            await client.close()

        asyncio.run(_go())


class TestMCPClientHTTPHealthCheck:
    """Tests for MCPClient.health_check with HTTP transport."""

    @respx.mock
    def test_health_check_ok(self) -> None:
        respx.get("https://mcp.example.com/health").mock(
            return_value=httpx.Response(200)
        )

        async def _go() -> None:
            async with MCPClient() as client:
                assert await client.health_check("https://mcp.example.com") is True

        asyncio.run(_go())

    @respx.mock
    def test_health_check_server_error(self) -> None:
        respx.get("https://mcp.example.com/health").mock(
            return_value=httpx.Response(500)
        )

        async def _go() -> None:
            async with MCPClient() as client:
                assert await client.health_check("https://mcp.example.com") is False

        asyncio.run(_go())

    @respx.mock
    def test_health_check_connection_error(self) -> None:
        respx.get("https://mcp.example.com/health").mock(
            side_effect=httpx.ConnectError("refused")
        )

        async def _go() -> None:
            async with MCPClient() as client:
                assert await client.health_check("https://mcp.example.com") is False

        asyncio.run(_go())


class TestMCPClientRetry:
    """Tests for MCPClient retry logic."""

    @respx.mock
    def test_retries_on_transient_error(self) -> None:
        """Succeeds after a transient error on first attempt."""
        route = respx.post("https://mcp.example.com/tools/call").mock(
            side_effect=[
                httpx.ConnectError("transient"),
                httpx.Response(200, json={"result": "ok"}),
            ]
        )

        async def _go() -> None:
            async with MCPClient(retries=3) as client:
                # Patch sleep to avoid waiting.
                with patch("sdlc.integrations.mcp_client.asyncio.sleep", new_callable=AsyncMock):
                    result = await client.call("https://mcp.example.com", "tool", {})
                    assert result == {"result": "ok"}

        asyncio.run(_go())
        assert route.call_count == 2

    @respx.mock
    def test_raises_after_exhausting_retries(self) -> None:
        """Raises after all retries are exhausted."""
        respx.post("https://mcp.example.com/tools/call").mock(
            side_effect=httpx.ConnectError("unreachable")
        )

        async def _go() -> None:
            async with MCPClient(retries=2) as client:
                with patch("sdlc.integrations.mcp_client.asyncio.sleep", new_callable=AsyncMock):
                    with pytest.raises(httpx.ConnectError):
                        await client.call("https://mcp.example.com", "tool", {})

        asyncio.run(_go())


class TestMCPClientTimeout:
    """Tests for MCPClient timeout handling."""

    @respx.mock
    def test_timeout_on_slow_response(self) -> None:
        """A timeout error is raised when the server is too slow."""
        respx.post("https://mcp.example.com/tools/call").mock(
            side_effect=httpx.ReadTimeout("read timeout")
        )

        async def _go() -> None:
            async with MCPClient(timeout=1, retries=1) as client:
                with pytest.raises(httpx.ReadTimeout):
                    await client.call("https://mcp.example.com", "tool", {})

        asyncio.run(_go())


class TestMCPClientStdio:
    """Tests for MCPClient stdio transport."""

    def test_call_stdio_success(self) -> None:
        mock_result = {"output": "hello from stdio"}

        async def _go() -> None:
            client = MCPClient(retries=1)
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = json.dinternal-monitorings({"result": mock_result})
            mock_proc.stderr = ""

            with patch("sdlc.integrations.mcp_client.subprocess.run", return_value=mock_proc):
                result = await client.call("npx my-mcp-server", "tool", {"a": 1})
                assert result == mock_result
            await client.close()

        asyncio.run(_go())

    def test_list_tools_stdio(self) -> None:
        tools = [{"name": "tool1"}, {"name": "tool2"}]

        async def _go() -> None:
            client = MCPClient(retries=1)
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = json.dinternal-monitorings({"result": {"tools": tools}})
            mock_proc.stderr = ""

            with patch("sdlc.integrations.mcp_client.subprocess.run", return_value=mock_proc):
                result = await client.list_tools("npx my-mcp-server")
                assert result == tools
            await client.close()

        asyncio.run(_go())

    def test_health_check_stdio_ok(self) -> None:
        async def _go() -> None:
            client = MCPClient(retries=1)
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = json.dinternal-monitorings({"result": {"tools": []}})
            mock_proc.stderr = ""

            with patch("sdlc.integrations.mcp_client.subprocess.run", return_value=mock_proc):
                assert await client.health_check("npx my-mcp-server") is True
            await client.close()

        asyncio.run(_go())

    def test_health_check_stdio_fail(self) -> None:
        async def _go() -> None:
            client = MCPClient(retries=1)
            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.stdout = ""
            mock_proc.stderr = "error"

            with patch("sdlc.integrations.mcp_client.subprocess.run", return_value=mock_proc):
                assert await client.health_check("npx my-mcp-server") is False
            await client.close()

        asyncio.run(_go())

    def test_call_stdio_server_error(self) -> None:
        async def _go() -> None:
            client = MCPClient(retries=1)
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = json.dinternal-monitorings({"error": {"message": "bad tool"}})
            mock_proc.stderr = ""

            with (
                patch("sdlc.integrations.mcp_client.subprocess.run", return_value=mock_proc),
                pytest.raises(Exception, match="MCP server error"),
            ):
                await client.call("npx my-mcp-server", "bad_tool", {})
            await client.close()

        asyncio.run(_go())

    def test_call_stdio_nonzero_exit(self) -> None:
        async def _go() -> None:
            client = MCPClient(retries=1)
            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.stdout = ""
            mock_proc.stderr = "crashed"

            with (
                patch("sdlc.integrations.mcp_client.subprocess.run", return_value=mock_proc),
                pytest.raises(Exception, match="exited with code 1"),
            ):
                await client.call("npx my-mcp-server", "tool", {})
            await client.close()

        asyncio.run(_go())


class TestMCPClientTransportDetection:
    """Tests for HTTP vs stdio transport detection."""

    def test_http_server_detected(self) -> None:
        assert MCPClient._is_http("http://localhost:8080") is True
        assert MCPClient._is_http("https://mcp.example.com") is True

    def test_stdio_server_detected(self) -> None:
        assert MCPClient._is_http("npx @mcp/server") is False
        assert MCPClient._is_http("python -m mcp_server") is False


# ============================================================================
# SkillRunner tests
# ============================================================================


class TestSkillRunnerRun:
    """Tests for SkillRunner.run."""

    def test_run_generate_readme(self) -> None:
        runner = SkillRunner()
        result = asyncio.run(
            runner.run("generate_readme", {"project_name": "myapp", "description": "cool"})
        )
        assert result["skill"] == "generate_readme"
        assert result["status"] == "ok"
        assert "# myapp" in result["output"]
        assert "cool" in result["output"]

    def test_run_generate_changelog(self) -> None:
        runner = SkillRunner()
        result = asyncio.run(
            runner.run("generate_changelog", {"version": "1.0.0", "entries": ["Added X"]})
        )
        assert result["skill"] == "generate_changelog"
        assert "1.0.0" in result["output"]
        assert "Added X" in result["output"]

    def test_run_generate_tests(self) -> None:
        runner = SkillRunner()
        result = asyncio.run(
            runner.run("generate_tests", {"module_name": "utils", "source": "def foo(): pass"})
        )
        assert result["skill"] == "generate_tests"
        assert "utils" in result["output"]

    def test_run_analyze_code(self) -> None:
        runner = SkillRunner()
        source = "line1\n# comment\n\nline4\n"
        result = asyncio.run(runner.run("analyze_code", {"source": source}))
        assert result["skill"] == "analyze_code"
        assert result["metrics"]["total_lines"] == 4
        assert result["metrics"]["comment_lines"] == 1
        assert result["metrics"]["non_empty_lines"] == 3

    def test_run_refactor_code(self) -> None:
        runner = SkillRunner()
        result = asyncio.run(
            runner.run("refactor_code", {"source": "x=1", "rules": ["ruff"]})
        )
        assert result["skill"] == "refactor_code"
        assert result["rules_applied"] == ["ruff"]

    def test_run_fix_lint(self) -> None:
        runner = SkillRunner()
        result = asyncio.run(runner.run("fix_lint", {"source": "x=1"}))
        assert result["skill"] == "fix_lint"
        assert result["linter"] == "ruff"

    def test_run_create_pr(self) -> None:
        runner = SkillRunner()
        with pytest.raises(NotImplementedError):
            asyncio.run(
                runner.run("create_pr", {"title": "My PR", "branch": "feature"})
            )

    def test_run_review_pr(self) -> None:
        runner = SkillRunner()
        with pytest.raises(NotImplementedError):
            asyncio.run(
                runner.run("review_pr", {"pr_url": "https://github.com/x/pull/1", "diff": "abc"})
            )

    def test_run_deploy_check(self) -> None:
        runner = SkillRunner()
        with pytest.raises(NotImplementedError):
            asyncio.run(
                runner.run("deploy_check", {"env": "staging", "checks": ["tests_pass"]})
            )

    def test_run_unknown_skill_raises(self) -> None:
        runner = SkillRunner()
        with pytest.raises(KeyError, match="Unknown skill"):
            asyncio.run(runner.run("nonexistent_skill", {}))


class TestSkillRunnerListSkills:
    """Tests for SkillRunner.list_skills."""

    def test_lists_all_builtin_skills(self) -> None:
        runner = SkillRunner()
        skills = runner.list_skills()
        expected = [
            "analyze_code",
            "create_pr",
            "deploy_check",
            "fix_lint",
            "generate_changelog",
            "generate_readme",
            "generate_tests",
            "refactor_code",
            "review_pr",
        ]
        assert skills == expected

    def test_list_skills_sorted(self) -> None:
        runner = SkillRunner()
        skills = runner.list_skills()
        assert skills == sorted(skills)

    def test_custom_skill_appears(self) -> None:
        runner = SkillRunner(skills={"my_custom": lambda ctx: {"ok": True}})
        skills = runner.list_skills()
        assert "my_custom" in skills


class TestSkillRunnerHasSkill:
    """Tests for SkillRunner.has_skill."""

    def test_has_builtin_skill(self) -> None:
        runner = SkillRunner()
        assert runner.has_skill("generate_readme") is True
        assert runner.has_skill("deploy_check") is True

    def test_missing_skill(self) -> None:
        runner = SkillRunner()
        assert runner.has_skill("does_not_exist") is False

    def test_custom_skill(self) -> None:
        runner = SkillRunner(skills={"custom_one": lambda ctx: {}})
        assert runner.has_skill("custom_one") is True
        assert runner.has_skill("generate_readme") is True


class TestSkillRunnerCustom:
    """Tests for SkillRunner with custom skills."""

    def test_custom_skill_overrides_builtin(self) -> None:
        custom_fn = MagicMock(return_value={"custom": True})

        runner = SkillRunner(skills={"generate_readme": custom_fn})
        result = asyncio.run(runner.run("generate_readme", {"project_name": "x"}))
        assert result == {"custom": True}
        custom_fn.assert_called_once_with({"project_name": "x"})

    def test_custom_skill_runs(self) -> None:
        def my_skill(ctx: dict) -> dict:
            return {"echo": ctx.get("msg", "")}

        runner = SkillRunner(skills={"echo_skill": my_skill})
        result = asyncio.run(runner.run("echo_skill", {"msg": "hi"}))
        assert result == {"echo": "hi"}
