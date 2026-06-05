"""Restricted shell command execution with whitelist security."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from sdlc.integrations.whitelist import SecurityError, is_command_allowed, validate_command_safety


@dataclass
class ShellResult:
    """Result of a shell command execution."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


class ShellRunner:
    """Execute shell commands with whitelist-based security gating."""

    def __init__(
        self,
        whitelist: dict[str, set[str]] | None = None,
        default_timeout: int = 60,
    ) -> None:
        self.whitelist = whitelist
        self.default_timeout = default_timeout

    def run(
        self,
        cmd: list[str],
        timeout: int | None = None,
        cwd: Path | None = None,
    ) -> ShellResult:
        """Execute a whitelisted command.

        - Validates command safety first
        - Checks against whitelist
        - Runs with subprocess.run
        - Captures stdout/stderr
        - Times out after specified seconds

        Raises:
            SecurityError: If the command is not allowed or is unsafe.
            subprocess.TimeoutExpired: If the command times out.
        """
        validate_command_safety(cmd)

        if not is_command_allowed(cmd, self.whitelist):
            raise SecurityError(f"Command not allowed: {' '.join(cmd)}")

        effective_timeout = timeout if timeout is not None else self.default_timeout

        start = time.monotonic()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=effective_timeout,
            cwd=cwd,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        return ShellResult(
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_ms=elapsed_ms,
        )
