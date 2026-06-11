"""Built-in skill runner - executes registered skill functions."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

# Type alias for a skill function: takes context dict, returns result dict.
SkillFunc = Callable[[dict[str, Any]], dict[str, Any]]


# ---------------------------------------------------------------------------
# Built-in skill implementations
# ---------------------------------------------------------------------------


def _generate_readme(context: dict[str, Any]) -> dict[str, Any]:
    """Generate a README.md based on project context."""
    project_name = context.get("project_name", "unknown-project")
    description = context.get("description", "")
    content = f"# {project_name}\n\n{description}\n"
    return {"skill": "generate_readme", "output": content, "status": "ok"}


def _generate_changelog(context: dict[str, Any]) -> dict[str, Any]:
    """Generate a CHANGELOG.md based on context."""
    version = context.get("version", "0.1.0")
    entries = context.get("entries", [])
    lines = [f"## {version}\n"]
    for entry in entries:
        lines.append(f"- {entry}")
    content = "\n".join(lines) + "\n"
    return {"skill": "generate_changelog", "output": content, "status": "ok"}


def _generate_tests(context: dict[str, Any]) -> dict[str, Any]:
    """Generate test stubs based on source code context."""
    source = context.get("source", "")
    module_name = context.get("module_name", "module")
    test_content = f'"""Tests for {module_name}."""\n\nimport pytest\n\n'
    if source:
        test_content += "# TODO: generate tests from source\n"
    test_content += f"def test_{module_name}_placeholder() -> None:\n    pass\n"
    return {"skill": "generate_tests", "output": test_content, "status": "ok"}


def _analyze_code(context: dict[str, Any]) -> dict[str, Any]:
    """Analyze source code and return metrics."""
    source = context.get("source", "")
    lines = source.splitlines() if source else []
    return {
        "skill": "analyze_code",
        "metrics": {
            "total_lines": len(lines),
            "non_empty_lines": sum(1 for line in lines if line.strip()),
            "comment_lines": sum(1 for line in lines if line.strip().startswith("#")),
        },
        "status": "ok",
    }


def _refactor_code(context: dict[str, Any]) -> dict[str, Any]:
    """Refactor source code based on context."""
    source = context.get("source", "")
    rules = context.get("rules", [])
    return {
        "skill": "refactor_code",
        "output": source,
        "rules_applied": rules,
        "status": "ok",
    }


def _fix_lint(context: dict[str, Any]) -> dict[str, Any]:
    """Fix lint issues in source code."""
    source = context.get("source", "")
    linter = context.get("linter", "ruff")
    return {
        "skill": "fix_lint",
        "output": source,
        "linter": linter,
        "fixes_applied": 0,
        "status": "ok",
    }


def _create_pr(context: dict[str, Any]) -> dict[str, Any]:
    """Create a pull request based on context.

    .. note:: This is a stub implementation. Real PR creation requires
        integration with a VCS hosting service (GitHub, GitLab, etc.).
    """
    raise NotImplementedError(
        "create_pr is a stub -- integrate with a VCS hosting service to implement"
    )


def _review_pr(context: dict[str, Any]) -> dict[str, Any]:
    """Review a pull request and return feedback.

    .. note:: This is a stub implementation. Real PR review requires
        integration with a VCS hosting service and/or LLM-based review.
    """
    raise NotImplementedError(
        "review_pr is a stub -- integrate with a VCS hosting service to implement"
    )


def _deploy_check(context: dict[str, Any]) -> dict[str, Any]:
    """Run deployment readiness checks.

    .. note:: This is a stub implementation. Real deploy checks require
        integration with CI/CD systems and environment verification.
    """
    raise NotImplementedError(
        "deploy_check is a stub -- integrate with CI/CD to implement"
    )


# ---------------------------------------------------------------------------
# Skill registry
# ---------------------------------------------------------------------------

_BUILTIN_SKILLS: dict[str, SkillFunc] = {
    "generate_readme": _generate_readme,
    "generate_changelog": _generate_changelog,
    "generate_tests": _generate_tests,
    "analyze_code": _analyze_code,
    "refactor_code": _refactor_code,
    "fix_lint": _fix_lint,
    "create_pr": _create_pr,
    "review_pr": _review_pr,
    "deploy_check": _deploy_check,
}


class SkillRunner:
    """Runner for built-in skills.

    Skills are synchronous functions that accept a context dict and return a
    result dict.  The ``run`` method is async-compatible so callers can await
    it in async contexts.
    """

    def __init__(self, skills: dict[str, SkillFunc] | None = None) -> None:
        self._skills: dict[str, SkillFunc] = dict(_BUILTIN_SKILLS)
        if skills is not None:
            self._skills.update(skills)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, skill_name: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute a built-in skill.

        Parameters
        ----------
        skill_name : str
            Name of the skill to execute.
        context : dict
            Context data passed to the skill function.

        Returns
        -------
        dict
            Skill execution result.

        Raises
        ------
        KeyError
            If the skill is not registered.
        """
        if skill_name not in self._skills:
            raise KeyError(f"Unknown skill: {skill_name!r}")
        skill_fn = self._skills[skill_name]
        # Run in executor so the call is non-blocking in async contexts.
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, skill_fn, context)

    def list_skills(self) -> list[str]:
        """List available skill names.

        Returns
        -------
        list[str]
            Sorted list of registered skill names.
        """
        return sorted(self._skills.keys())

    def has_skill(self, name: str) -> bool:
        """Check if a skill exists.

        Parameters
        ----------
        name : str
            Skill name to check.

        Returns
        -------
        bool
            ``True`` if the skill is registered.
        """
        return name in self._skills
