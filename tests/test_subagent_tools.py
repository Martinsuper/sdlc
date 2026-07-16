"""Tests for M-A1 subagent tool ecosystem (sdlc/subagent/tools/).

Covers the security boundaries that make a wider toolset safe to grant:
path confinement (fs/grep/glob), shell command whitelisting, and MCP/skill
whitelists — plus registry schema resolution and pool backward-compat.
"""

from __future__ import annotations

import pytest

from sdlc.subagent.tools import ToolContext, ToolRegistry, default_registry
from sdlc.subagent.tools.fs_tools import (
    GlobTool,
    GrepTool,
    ListTool,
    ReadTool,
    WriteTool,
    validate_path,
)
from sdlc.subagent.tools.mcp_tool import MCPCallTool
from sdlc.subagent.tools.shell_tool import ShellTool
from sdlc.subagent.tools.skill_tool import SkillTool


@pytest.fixture
def project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def hello():\n    return 'world'\n")
    (tmp_path / "README.md").write_text("# Demo\nTODO: write docs\n")
    return tmp_path


def _ctx(root, **kw) -> ToolContext:
    return ToolContext(project_root=root, agent_id="SA-test", **kw)


# --------------------------------------------------------------------------- #
# Path confinement
# --------------------------------------------------------------------------- #

def test_validate_path_rejects_absolute(project):
    with pytest.raises(ValueError, match="Absolute"):
        validate_path("/etc/passwd", project)


def test_validate_path_rejects_traversal(project):
    with pytest.raises(ValueError, match="escapes project root"):
        validate_path("../../etc/passwd", project)


def test_validate_path_rejects_home(project):
    with pytest.raises(ValueError, match="Home directory"):
        validate_path("~/secrets", project)


@pytest.mark.asyncio
async def test_read_confined_to_project(project):
    out = await ReadTool().run({"path": "../../../etc/passwd"}, _ctx(project))
    assert out.startswith("Error")


@pytest.mark.asyncio
async def test_read_write_roundtrip(project):
    w = await WriteTool().run({"path": "note.txt", "content": "hi"}, _ctx(project))
    assert "Successfully wrote" in w
    r = await ReadTool().run({"path": "note.txt"}, _ctx(project))
    assert r == "hi"


@pytest.mark.asyncio
async def test_list_directory(project):
    out = await ListTool().run({"path": "src"}, _ctx(project))
    assert "src/app.py" in out


# --------------------------------------------------------------------------- #
# grep / glob (read-only)
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_grep_finds_matches(project):
    out = await GrepTool().run({"pattern": "TODO"}, _ctx(project))
    assert "README.md" in out and "TODO" in out


@pytest.mark.asyncio
async def test_grep_invalid_regex_errors(project):
    out = await GrepTool().run({"pattern": "([unclosed"}, _ctx(project))
    assert out.startswith("Error")


@pytest.mark.asyncio
async def test_glob_matches_pattern(project):
    out = await GlobTool().run({"pattern": "src/*.py"}, _ctx(project))
    assert "src/app.py" in out


@pytest.mark.asyncio
async def test_glob_rejects_traversal(project):
    out = await GlobTool().run({"pattern": "../*"}, _ctx(project))
    assert out.startswith("Error")


# --------------------------------------------------------------------------- #
# shell (whitelist + safety)
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_shell_blocks_dangerous_command(project):
    out = await ShellTool().run({"command": "rm -rf /"}, _ctx(project))
    assert out.startswith("Error")  # rm not whitelisted


@pytest.mark.asyncio
async def test_shell_blocks_shell_operators(project):
    out = await ShellTool().run({"command": "ls; cat /etc/passwd"}, _ctx(project))
    assert out.startswith("Error")  # ';' rejected by validate_command_safety


@pytest.mark.asyncio
async def test_shell_allows_whitelisted(project):
    out = await ShellTool().run({"command": "echo hello"}, _ctx(project))
    assert "exit_code: 0" in out
    assert "hello" in out


# --------------------------------------------------------------------------- #
# mcp / skill whitelists (deny by default)
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_mcp_denied_when_not_whitelisted(project):
    out = await MCPCallTool().run(
        {"server": "http://evil.example", "tool": "x"}, _ctx(project)
    )
    assert "not whitelisted" in out


@pytest.mark.asyncio
async def test_skill_denied_when_not_whitelisted(project):
    out = await SkillTool().run({"skill": "analyze_code"}, _ctx(project))
    assert "not whitelisted" in out


@pytest.mark.asyncio
async def test_skill_runs_when_whitelisted(project):
    ctx = _ctx(project, skill_whitelist={"analyze_code"})
    out = await SkillTool().run(
        {"skill": "analyze_code", "context": {"source": "a\nb\n"}}, ctx
    )
    assert "analyze_code" in out


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

def test_default_registry_has_all_tools():
    names = set(default_registry().names())
    assert {"read", "write", "list", "grep", "glob", "shell", "mcp_call", "skill"} <= names


def test_resolve_schemas_only_granted():
    reg = default_registry()
    schemas = reg.resolve_schemas(["read", "grep"])
    assert {s["name"] for s in schemas} == {"read", "grep"}


def test_resolve_schemas_skips_unknown():
    reg = default_registry()
    schemas = reg.resolve_schemas(["read", "nonexistent"])
    assert {s["name"] for s in schemas} == {"read"}


@pytest.mark.asyncio
async def test_registry_execute_rejects_ungranted(project):
    reg = default_registry()
    out = await reg.execute("shell", {"command": "echo hi"}, _ctx(project), allowed=["read"])
    assert "not allowed" in out


@pytest.mark.asyncio
async def test_registry_execute_unknown_tool(project):
    reg = ToolRegistry()  # empty
    out = await reg.execute("read", {}, _ctx(project), allowed=["read"])
    assert "not implemented" in out
