"""Tool JSON schemas for sub-agent tool definitions.

These schemas are provided to the LLM so it knows how to invoke tools.
Path arguments must be relative to the project root directory.
"""

from typing import Any

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "read": {
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
    },
    "write": {
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
    },
    "list": {
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
    },
    "ask_user": {
        "name": "ask_user",
        "description": "Ask the user a question and wait for a response.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user.",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of option strings for the user to choose from.",
                },
            },
            "required": ["question"],
        },
    },
    # --- M-A1 tool ecosystem: grep/glob (read-only), shell/mcp_call/skill
    # (security-gated). Authoritative schemas live on each Tool class in
    # sdlc/subagent/tools/; these mirror them for reference/documentation. ---
    "grep": {
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
                    "description": "Directory to search (relative to project root).",
                },
                "glob": {"type": "string", "description": "Optional filename glob, e.g. '*.py'."},
            },
            "required": ["pattern"],
        },
    },
    "glob": {
        "name": "glob",
        "description": (
            "Find files matching a glob pattern (e.g. 'src/**/*.py'). Read-only."
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
    },
    "shell": {
        "name": "shell",
        "description": (
            "Run a whitelisted shell command (build/test/lint). Only allow-listed "
            "commands run; shell operators, redirects, and traversal are rejected."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command, e.g. 'pytest -q'."},
                "timeout": {"type": "integer", "description": "Optional timeout in seconds."},
            },
            "required": ["command"],
        },
    },
    "mcp_call": {
        "name": "mcp_call",
        "description": (
            "Call a tool on an external MCP server (server must be whitelisted)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "server": {"type": "string", "description": "MCP server (must be whitelisted)."},
                "tool": {"type": "string", "description": "Tool name on the server."},
                "args": {"type": "object", "description": "Arguments for the tool."},
            },
            "required": ["server", "tool"],
        },
    },
    "skill": {
        "name": "skill",
        "description": "Run a registered built-in skill by name (skill must be whitelisted).",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill": {"type": "string", "description": "Skill name to run."},
                "context": {"type": "object", "description": "Context dict for the skill."},
            },
            "required": ["skill"],
        },
    },
}
