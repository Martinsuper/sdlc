"""Git operations client."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


# Known git flags that are safe to pass as arguments.
_KNOWN_GIT_FLAGS = frozenset({
    "--abbrev-ref",
    "--staged",
    "--porcelain",
    "--oneline",
    "-n",
    "-1",
    "-2",
    "-3",
    "-4",
    "-5",
    "-6",
    "-7",
    "-8",
    "-9",
    "-10",
    "-20",
    "-50",
    "--all",
    "--quiet",
    "--verbose",
    "--force",
    "--dry-run",
    "--no-verify",
    "--signoff",
    "-m",
    "-a",
    "-S",
    "-b",
    "-d",
    "-r",
    "-f",
    "-p",
})


class GitClient:
    """High-level wrapper around common git commands."""

    DEFAULT_TIMEOUT = 60

    def __init__(self, cwd: Path | None = None, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.cwd = cwd
        self._timeout = timeout

    def _validate_args(self, args: list[str]) -> None:
        """Reject suspicious arguments that start with ``-`` but are not known flags.

        Short numeric flags like ``-5`` are allowed for ``git log -5`` etc.
        """
        for arg in args:
            if arg.startswith("-") and arg not in _KNOWN_GIT_FLAGS:
                # Allow short numeric flags like -5, -10, -20
                if re.match(r"^-\d+$", arg):
                    continue
                raise ValueError(
                    f"Unrecognized git flag rejected for safety: {arg}"
                )

    def _run(
        self,
        args: list[str],
        check: bool = True,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run a git subprocess command."""
        self._validate_args(args)
        effective_timeout = timeout if timeout is not None else self._timeout
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=self.cwd,
            check=check,
            timeout=effective_timeout,
        )

    def current_branch(self) -> str:
        """Get current git branch name."""
        result = self._run(["rev-parse", "--abbrev-ref", "HEAD"])
        return result.stdout.strip()

    def current_sha(self) -> str:
        """Get current commit SHA."""
        result = self._run(["rev-parse", "HEAD"])
        return result.stdout.strip()

    def is_clean(self) -> bool:
        """Check if working tree is clean."""
        result = self._run(["status", "--porcelain"])
        return result.stdout.strip() == ""

    def diff(self, staged: bool = False) -> str:
        """Get git diff output."""
        args = ["diff"]
        if staged:
            args.append("--staged")
        result = self._run(args)
        return result.stdout

    def log(self, n: int = 10, oneline: bool = True) -> str:
        """Get git log."""
        args = ["log", f"-{n}"]
        if oneline:
            args.append("--oneline")
        result = self._run(args)
        return result.stdout

    def list_files(self) -> list[str]:
        """List tracked files via git ls-files."""
        result = self._run(["ls-files"])
        lines = result.stdout.strip().splitlines()
        return [line for line in lines if line]
