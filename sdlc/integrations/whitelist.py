"""Command whitelist for security-gated shell execution."""

from __future__ import annotations

import re

from sdlc.utils.exceptions import SdlcError


class SecurityError(SdlcError):
    """Raised when a command violates security policies."""


# Sentinel value: when a command's allowed-subcommand set equals ALL,
# any subcommand/argument is permitted.  An empty set now means
# *no* subcommands are allowed.
ALL = {"__ALL__"}

# Modules that are dangerous when invoked via ``python -m``
_PYTHON_DANGER_MODULES = frozenset({
    "http.server",
    "pdb",
    "socketserver",
    "telnetlib",
    "xmlrpc.server",
    "asyncio",
    "code",
    "codeop",
    "compileall",
    "cProfile",
    "profile",
    "pydoc",
    "site",
    "zipapp",
})


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
        "fetch",
    },
    "ls": ALL,
    "cat": ALL,
    "head": ALL,
    "tail": ALL,
    "grep": ALL,
    "find": ALL,
    "wc": ALL,
    "sort": ALL,
    "uniq": ALL,
    "echo": ALL,
    "mkdir": ALL,
    "python": {"-m", "-V"},
    "pip": {"install", "list", "show"},
    "uv": {"run", "pip", "sync"},
    "mvn": {"compile", "test", "package", "install", "clean"},
    "npm": {"install", "test", "run", "build", "lint"},
    "go": {"build", "test", "mod", "fmt", "vet"},
    "kubectl": {"get", "logs", "describe"},
    "docker": {"build", "ps", "logs"},
}

# Patterns that are never allowed in any command argument
_SHELL_OPERATORS = {"|", ";", "&&", "||", ">", ">>", "<"}
_COMMAND_SUBSTITUTION_RE = re.compile(r"\$\(|`")
_ENV_VAR_RE = re.compile(r"\$\{|\$[A-Za-z_]")
_PATH_TRAVERSAL_RE = re.compile(r"\.\.")
_ABSOLUTE_PATH_RE = re.compile(r"^/")
_HOME_DIR_RE = re.compile(r"^~")


def is_command_allowed(cmd: list[str], whitelist: dict[str, set[str]] | None = None) -> bool:
    """Check if a command is in the whitelist.

    Rules:
      - cmd[0] must be in whitelist keys
      - if whitelist[cmd[0]] equals the ALL sentinel, any subcommand is allowed
      - if whitelist[cmd[0]] is an empty set, no subcommands are allowed
      - if whitelist[cmd[0]] is non-empty, cmd[1] (if present) must be in that set
      - commands with no subcommand are allowed when the base command is whitelisted
      - for ``python -m <module>``, the module must not be in the danger list
    """
    if not cmd:
        return False

    wl = whitelist if whitelist is not None else DEFAULT_WHITELIST
    base = cmd[0]

    if base not in wl:
        return False

    allowed_subcmds = wl[base]
    # ALL sentinel means any subcommand is allowed
    if allowed_subcmds is ALL:
        return True

    # Empty set means no subcommands are allowed
    if allowed_subcmds == set():
        # Base command alone (no args) is allowed
        return len(cmd) == 1

    # If there is a subcommand (cmd[1]), it must be in the allowed set
    if len(cmd) > 1:
        if cmd[1] not in allowed_subcmds:
            return False
        # Extra safety: block dangerous python modules
        if base == "python" and cmd[1] == "-m" and len(cmd) > 2:
            module = cmd[2]
            if module in _PYTHON_DANGER_MODULES:
                return False
        return True

    # No subcommand present; base command alone is allowed
    return True


def validate_command_safety(cmd: list[str]) -> None:
    """Raise SecurityError if command contains dangerous patterns.

    Detects:
      - Shell operators: |, ;, &&, ||, >, >>, <
      - Command substitution: $(...), `...`
      - Path traversal: ..
      - Absolute paths: /...
      - Home directory expansion: ~...
      - Environment variable access: $VAR, ${VAR}
    """
    for i, part in enumerate(cmd):
        # Skip the base command itself (cmd[0]) for path-like checks
        is_base = i == 0

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

        # Check absolute paths (skip base command which may be /usr/bin/git etc.)
        if not is_base and _ABSOLUTE_PATH_RE.search(part):
            raise SecurityError("Absolute paths are not allowed in command arguments")

        # Check home directory expansion
        if _HOME_DIR_RE.search(part):
            raise SecurityError("Home directory paths (~/) are not allowed in commands")

        # Check environment variable access
        if _ENV_VAR_RE.search(part):
            raise SecurityError(
                "Environment variable access ($VAR or ${VAR}) is not allowed in commands"
            )
