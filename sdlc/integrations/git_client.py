"""Git operations client."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitClient:
    """High-level wrapper around common git commands."""

    def __init__(self, cwd: Path | None = None) -> None:
        self.cwd = cwd

    def _run(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run a git subprocess command."""
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=self.cwd,
            check=check,
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
