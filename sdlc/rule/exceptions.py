"""sdlc.rule.exceptions — temporary rule exemption management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sdlc.rule.models import RuleException
from sdlc.utils.time import now_utc


class ExceptionManager:
    """Manage temporary rule exemptions."""

    def __init__(self, kb_root: Path | None = None) -> None:
        self.kb_root = kb_root
        self.exceptions: list[RuleException] = []

    def add(self, exception: RuleException) -> None:
        """Add a rule exception."""
        self.exceptions.append(exception)

    def is_active(self, rule_id: str, context: dict[str, object] | None = None) -> RuleException | None:
        """Check if a rule has an active exception for the given context.

        An exception is active when it has not expired.  If *context* is
        provided, the exception's scope (files / stages) is also checked.
        """
        now = now_utc()
        for exc in self.exceptions:
            if exc.rule_id != rule_id:
                continue

            # Check expiry
            try:
                expires = _parse_iso(exc.expires_at)
            except (ValueError, TypeError):
                continue
            if expires <= now:
                continue

            # Check scope if context provided
            if context and not _scope_matches(exc.scope, context):
                continue

            return exc
        return None

    def expire_check(self) -> list[RuleException]:
        """Return exceptions that have expired."""
        now = now_utc()
        expired: list[RuleException] = []
        for exc in self.exceptions:
            try:
                expires = _parse_iso(exc.expires_at)
            except (ValueError, TypeError):
                continue
            if expires <= now:
                expired.append(exc)
        return expired

    def expiring_soon(self, days: int = 3) -> list[RuleException]:
        """Return exceptions expiring within N days."""
        now = now_utc()
        threshold = now + timedelta(days=days)
        result: list[RuleException] = []
        for exc in self.exceptions:
            try:
                expires = _parse_iso(exc.expires_at)
            except (ValueError, TypeError):
                continue
            if now < expires <= threshold:
                result.append(exc)
        return result

    def remove(self, exception_id: str) -> bool:
        """Remove an exception. Returns True if found."""
        for i, exc in enumerate(self.exceptions):
            if exc.id == exception_id:
                self.exceptions.pop(i)
                return True
        return False


def _parse_iso(s: str) -> datetime:
    """Parse an ISO timestamp string to a datetime for comparison."""
    # Handle trailing Z
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    # If naive, assume UTC
    if dt.tzinfo is None:

        dt = dt.replace(tzinfo=UTC)
    return dt


def _scope_matches(scope: dict[str, list[str]], context: dict[str, object]) -> bool:
    """Check whether the exception scope is compatible with the context.

    A scope like ``{files: ["src/**/*.java"]}`` means the exception only
    applies when the context includes matching files.  If the scope key is
    absent the exception applies broadly for that dimension.
    """

    for key, patterns in scope.items():
        ctx_val = context.get(key)
        if ctx_val is None:
            # Context doesn't provide this dimension — no match
            return False
        if isinstance(ctx_val, str):
            ctx_val = [ctx_val]
        if not isinstance(ctx_val, list):
            ctx_val = [str(ctx_val)]
        # At least one context value must match at least one pattern
        if not any(any(_glob_match(str(v), p) for p in patterns) for v in ctx_val):
            return False
    return True


def _glob_match(file_path: str, pattern: str) -> bool:
    """Match a file path against a glob pattern, supporting ``**``.

    ``**/*.py`` matches both ``a.py`` and ``src/a.py``.
    ``src/legacy/**/*.java`` matches ``src/legacy/OldService.java``.
    ``*.py`` matches only ``a.py`` (no subdirectories).
    """
    from pathlib import PurePosixPath

    path = PurePosixPath(file_path)
    if path.match(pattern):
        return True
    # ``**`` in pathlib.match requires at least one directory level, but
    # conventionally it should also match zero levels.  We progressively
    # replace each ``**/`` with nothing and retry the match.
    while "**/" in pattern:
        pattern = pattern.replace("**/", "", 1)
        if path.match(pattern):
            return True
    return False
