"""sdlc.rule.enforcer — rule enforcement strategies."""

from __future__ import annotations

import re
from typing import Protocol

from sdlc.rule.models import Rule, Violation


def _glob_match(file_path: str, pattern: str) -> bool:
    """Match a file path against a glob pattern, supporting ``**``.

    ``**/*.py`` matches both ``a.py`` and ``src/a.py``.
    ``*.py`` matches only ``a.py`` (no subdirectories).
    """
    # pathlib.PurePath.match handles ** but requires at least one directory
    # level for **.  We handle the "root-level file" case by also trying
    # the pattern with the **/ prefix stripped.
    from pathlib import PurePosixPath

    path = PurePosixPath(file_path)
    if path.match(pattern):
        return True
    # For patterns starting with **/, also try the remainder without it
    # so that **/*.py matches a.py as well as dir/a.py
    if pattern.startswith("**/"):
        suffix = pattern[3:]
        if path.match(suffix):
            return True
    return False


class Enforcer(Protocol):
    """Protocol for rule enforcement strategies."""

    def check(self, rule: Rule, context: dict[str, object]) -> list[Violation]: ...


class CREnforcer:
    """Code review enforcer — checks files in context against rule patterns."""

    def check(self, rule: Rule, context: dict[str, object]) -> list[Violation]:
        if not rule.pattern:
            return []

        violations: list[Violation] = []
        try:
            compiled = re.compile(rule.pattern)
        except re.error:
            return violations

        files = context.get("files", {})
        # files is a dict mapping file_path -> file_content (str)
        if not isinstance(files, dict):
            return violations

        for file_path, content in files.items():
            # Check applies_to glob filter (supports ** patterns)
            if rule.applies_to and not any(
                _glob_match(str(file_path), glob) for glob in rule.applies_to
            ):
                continue

            if not isinstance(content, str):
                continue

            for match in compiled.finditer(content):
                # Calculate approximate line number
                line = content[:match.start()].count("\n") + 1
                msg = rule.message or f"Rule {rule.id}: pattern matched"
                violations.append(
                    Violation(
                        rule_id=rule.id,
                        file=str(file_path),
                        line=line,
                        message=msg,
                        severity=rule.action.value,
                    )
                )

        return violations


class LintEnforcer:
    """Static lint enforcer — stub that returns empty violations for M2."""

    def check(self, rule: Rule, context: dict[str, object]) -> list[Violation]:
        return []


class CIEnforcer:
    """CI pipeline enforcer — stub for M2."""

    def check(self, rule: Rule, context: dict[str, object]) -> list[Violation]:
        return []


class RuntimeEnforcer:
    """Runtime pre/post hook enforcer — stub for M2."""

    def check(self, rule: Rule, context: dict[str, object]) -> list[Violation]:
        return []
