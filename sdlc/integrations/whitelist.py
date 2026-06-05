"""Command whitelist for security-gated shell execution."""

from __future__ import annotations

import re

from sdlc.utils.exceptions import SdlcError


class SecurityError(SdlcError):
    """Raised when a command violates security policies."""


DEFAULT_WHITELIST: dict[str, set[str]] = {
    "git": {
        "commit",
        "diff",
        "log",
        "show",
        "status",
        "add",
        "branch",
        "checkout",
        "pull",
        "push",
        "fetch",
        "merge",
        "rebase",
    },
    "ls": set(),
    "cat": set(),
    "head": set(),
    "tail": set(),
    "grep": set(),
    "find": set(),
    "wc": set(),
    "sort": set(),
    "uniq": set(),
    "echo": set(),
    "mkdir": set(),
    "cp": set(),
    "mv": set(),
    "python": {"-m", "-c", "-V"},
    "pip": {"install", "list", "show"},
    "uv": {"run", "pip", "sync"},
    "mvn": {"compile", "test", "package", "install", "clean"},
    "npm": {"install", "test", "run", "build", "lint"},
    "go": {"build", "test", "mod", "fmt", "vet"},
    "kubectl": {"get", "logs", "describe", "apply"},
    "docker": {"build", "run", "ps", "logs"},
}

# Patterns that are never allowed in any command argument
_SHELL_OPERATORS = {"|", ";", "&&", "||", ">", ">>", "<"}
_COMMAND_SUBSTITUTION_RE = re.compile(r"\$\(|`")
_ENV_VAR_RE = re.compile(r"\$\{|\$[A-Za-z_]")
_PATH_TRAVERSAL_RE = re.compile(r"\.\.")


def is_command_allowed(cmd: list[str], whitelist: dict[str, set[str]] | None = None) -> bool:
    """Check if a command is in the whitelist.

    Rules:
      - cmd[0] must be in whitelist keys
      - if whitelist[cmd[0]] is an empty set, any subcommand is allowed
      - if whitelist[cmd[0]] is non-empty, cmd[1] (if present) must be in that set
      - commands with no subcommand are allowed when the base command is whitelisted
    """
    if not cmd:
        return False

    wl = whitelist if whitelist is not None else DEFAULT_WHITELIST
    base = cmd[0]

    if base not in wl:
        return False

    allowed_subcmds = wl[base]
    # Empty set means all subcommands are allowed
    if allowed_subcmds == set():
        return True

    # If there is a subcommand (cmd[1]), it must be in the allowed set
    if len(cmd) > 1:
        return cmd[1] in allowed_subcmds

    # No subcommand present; base command alone is allowed
    return True


def validate_command_safety(cmd: list[str]) -> None:
    """Raise SecurityError if command contains dangerous patterns.

    Detects:
      - Shell operators: |, ;, &&, ||, >, >>, <
      - Command substitution: $(...), `...`
      - Path traversal: ..
      - Environment variable access: $VAR, ${VAR}
    """
    for part in cmd:
        # Check shell operators
        for op in _SHELL_OPERATORS:
            if op in part:
                raise SecurityError(f"Shell operator '{op}' is not allowed in commands")

        # Check command substitution
        if _COMMAND_SUBSTITUTION_RE.search(part):
            raise SecurityError("Command substitution ($() or backticks) is not allowed in commands")

        # Check path traversal
        if _PATH_TRAVERSAL_RE.search(part):
            raise SecurityError("Path traversal (..) is not allowed in commands")

        # Check environment variable access
        if _ENV_VAR_RE.search(part):
            raise SecurityError(
                "Environment variable access ($VAR or ${VAR}) is not allowed in commands"
            )
