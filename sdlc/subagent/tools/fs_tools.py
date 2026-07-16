"""Filesystem tools: read / write / list / grep / glob.

read/write/list preserve the exact behavior previously inlined in
``SubagentPool._execute_tool``. grep/glob are new, read-only. Every path is
validated against the project root — absolute paths, ``..`` traversal, and
``~`` expansion are rejected — so an agent cannot read or write outside the
project it was invoked on.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any

from sdlc.audit.events import AuditEventType
from sdlc.subagent.tools import ToolContext
from sdlc.utils.paths import ensure_dir

# Cap grep/glob output so a broad pattern can't flood the model context.
_MAX_MATCHES = 200
_MAX_GREP_LINE = 300


def validate_path(path_str: str, project_root: Path) -> Path:
    """Resolve *path_str* under *project_root*, rejecting escapes.

    Mirrors the original SubagentPool._validate_path contract:
      - empty → error
      - absolute paths → rejected
      - ``~`` (home expansion) → rejected
      - anything resolving outside project_root (incl. via ``..``) → rejected
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


class ReadTool:
    name = "read"

    def schema(self) -> dict[str, Any]:
        return {
            "name": "read",
            "description": "Read the contents of a file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Path to the file to read. Must be relative to the "
                            "project root directory. Absolute paths and paths "
                            "containing '..' or '~' are not allowed."
                        ),
                    },
                },
                "required": ["path"],
            },
        }

    async def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        path = args.get("path", "")
        try:
            safe = validate_path(path, ctx.project_root)
            return safe.read_text(encoding="utf-8")
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error reading {path}: {e}"


class WriteTool:
    name = "write"

    def schema(self) -> dict[str, Any]:
        return {
            "name": "write",
            "description": "Write content to a file.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Path to the file to write. Must be relative to the "
                            "project root directory. Absolute paths and paths "
                            "containing '..' or '~' are not allowed."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file.",
                    },
                },
                "required": ["path", "content"],
            },
        }

    async def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        path = args.get("path", "")
        content = args.get("content", "")
        try:
            safe = validate_path(path, ctx.project_root)
            ensure_dir(safe.parent)
            safe.write_text(content, encoding="utf-8")
            if ctx.audit is not None:
                ctx.audit.emit(
                    AuditEventType.FILE_WRITTEN,
                    {"agent_id": ctx.agent_id, "path": path},
                    pipeline_id=ctx.pipeline_id or None,
                )
            return f"Successfully wrote to {path}"
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error writing {path}: {e}"


class ListTool:
    name = "list"

    def schema(self) -> dict[str, Any]:
        return {
            "name": "list",
            "description": "List files and directories at a given path.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Path to the directory to list. Must be relative to "
                            "the project root directory. Absolute paths and paths "
                            "containing '..' or '~' are not allowed."
                        ),
                    },
                },
                "required": ["path"],
            },
        }

    async def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        path = args.get("path", "")
        try:
            safe = validate_path(path, ctx.project_root)
            if not safe.is_dir():
                return f"Error: {path} is not a directory"
            entries = sorted(
                p.relative_to(ctx.project_root).as_posix() for p in safe.iterdir()
            )
            return "\n".join(entries) if entries else "(empty directory)"
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error listing {path}: {e}"


class GrepTool:
    """Read-only content search (regex) over project files."""

    name = "grep"

    def schema(self) -> dict[str, Any]:
        return {
            "name": "grep",
            "description": (
                "Search file contents for a regular expression. Read-only. "
                "Returns matching 'path:lineno: line' entries."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex to search for."},
                    "path": {
                        "type": "string",
                        "description": (
                            "Directory to search under (relative to project root). "
                            "Defaults to project root."
                        ),
                    },
                    "glob": {
                        "type": "string",
                        "description": "Optional filename glob filter, e.g. '*.py'.",
                    },
                },
                "required": ["pattern"],
            },
        }

    async def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        pattern = args.get("pattern", "")
        if not pattern:
            return "Error: pattern must not be empty"
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"Error: invalid regex: {e}"
        base_arg = args.get("path", "") or "."
        name_glob = args.get("glob", "")
        try:
            base = validate_path(base_arg, ctx.project_root)
        except ValueError as e:
            return f"Error: {e}"
        if not base.exists():
            return f"Error: {base_arg} does not exist"

        matches: list[str] = []
        files = base.rglob("*") if base.is_dir() else [base]
        for f in files:
            if not f.is_file():
                continue
            if name_glob and not fnmatch.fnmatch(f.name, name_glob):
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # skip binary/unreadable files
            for i, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    rel = f.relative_to(ctx.project_root).as_posix()
                    matches.append(f"{rel}:{i}: {line.strip()[:_MAX_GREP_LINE]}")
                    if len(matches) >= _MAX_MATCHES:
                        matches.append(f"... (truncated at {_MAX_MATCHES} matches)")
                        return "\n".join(matches)
        return "\n".join(matches) if matches else "(no matches)"


class GlobTool:
    """Read-only filename search by glob pattern."""

    name = "glob"

    def schema(self) -> dict[str, Any]:
        return {
            "name": "glob",
            "description": (
                "Find files matching a glob pattern (e.g. 'src/**/*.py'). "
                "Read-only. Returns project-relative paths."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern relative to project root.",
                    },
                },
                "required": ["pattern"],
            },
        }

    async def run(self, args: dict[str, Any], ctx: ToolContext) -> str:
        pattern = args.get("pattern", "")
        if not pattern:
            return "Error: pattern must not be empty"
        if pattern.startswith("/") or "~" in pattern or ".." in pattern:
            return f"Error: unsafe glob pattern: {pattern}"
        results: list[str] = []
        for p in ctx.project_root.glob(pattern):
            try:
                rel = p.resolve().relative_to(ctx.project_root)
            except ValueError:
                continue  # defensive: skip anything resolving outside root
            results.append(rel.as_posix())
            if len(results) >= _MAX_MATCHES:
                results.append(f"... (truncated at {_MAX_MATCHES} matches)")
                break
        return "\n".join(sorted(results)) if results else "(no matches)"
