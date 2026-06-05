"""Integrations package - external system adapters with security gating."""

from sdlc.integrations.filesystem import FileSystem
from sdlc.integrations.git_client import GitClient
from sdlc.integrations.http_client import HTTPClient
from sdlc.integrations.mcp_client import MCPClient
from sdlc.integrations.shell_runner import ShellResult, ShellRunner
from sdlc.integrations.skill_runner import SkillRunner
from sdlc.integrations.whitelist import SecurityError, is_command_allowed, validate_command_safety

__all__ = [
    "FileSystem",
    "GitClient",
    "HTTPClient",
    "MCPClient",
    "SecurityError",
    "ShellResult",
    "ShellRunner",
    "SkillRunner",
    "is_command_allowed",
    "validate_command_safety",
]
