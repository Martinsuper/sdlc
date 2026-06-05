from typing import Any

from sdlc.subagent.models import Subagent
from sdlc.subagent.registry import SubagentRegistry

BUILTIN_SUBAGENTS: list[dict[str, Any]] = [
    {
        "id": "SA-1",
        "name": "requirements-analyst",
        "role": "requirements",
        "model": "claude-opus-4-20250514",
        "tools": ["read", "write", "ask_user"],
        "kb_inject": ["conventions.md", "glossary.md"],
        "max_iter": 5,
    },
    {
        "id": "SA-2",
        "name": "architect",
        "role": "architect",
        "model": "claude-opus-4-20250514",
        "tools": ["read", "write", "ask_user"],
        "kb_inject": ["architecture/component-catalog.md", "architecture/dependency-graph.md"],
        "max_iter": 8,
    },
    {
        "id": "SA-3",
        "name": "coder-backend",
        "role": "impl",
        "model": "claude-sonnet-4-20250514",
        "tools": ["read", "write", "ask_user"],
        "kb_inject": ["conventions.md", "tech-stack.md"],
        "max_iter": 10,
    },
    {
        "id": "SA-4",
        "name": "coder-frontend",
        "role": "impl",
        "model": "claude-sonnet-4-20250514",
        "tools": ["read", "write", "ask_user"],
        "kb_inject": ["conventions.md", "tech-stack.md"],
        "max_iter": 10,
    },
    {
        "id": "SA-5",
        "name": "tester-unit",
        "role": "test",
        "model": "claude-sonnet-4-20250514",
        "tools": ["read", "write"],
        "kb_inject": ["conventions.md", "patterns.md"],
        "max_iter": 10,
    },
    {
        "id": "SA-6",
        "name": "reviewer",
        "role": "review",
        "model": "claude-opus-4-20250514",
        "tools": ["read"],
        "kb_inject": ["conventions.md", "antipatterns.md"],
        "max_iter": 5,
    },
    {
        "id": "SA-7",
        "name": "sre-writer",
        "role": "monitor",
        "model": "claude-sonnet-4-20250514",
        "tools": ["read", "write"],
        "kb_inject": ["commands.md", "runbook.md"],
        "max_iter": 5,
    },
    {
        "id": "SA-8",
        "name": "doc-writer",
        "role": "doc",
        "model": "claude-haiku-4-5-20251001",
        "tools": ["read", "write"],
        "kb_inject": ["conventions.md"],
        "max_iter": 5,
    },
    {
        "id": "SA-9",
        "name": "migration-engineer",
        "role": "migration",
        "model": "claude-sonnet-4-20250514",
        "tools": ["read", "write", "ask_user"],
        "kb_inject": ["tech-stack.md", "dependencies.md"],
        "max_iter": 10,
    },
    {
        "id": "SA-10",
        "name": "security-auditor",
        "role": "audit",
        "model": "claude-opus-4-20250514",
        "tools": ["read"],
        "kb_inject": ["conventions.md", "antipatterns.md"],
        "max_iter": 5,
    },
    {
        "id": "SA-11",
        "name": "devops-engineer",
        "role": "infra",
        "model": "claude-sonnet-4-20250514",
        "tools": ["read", "write"],
        "kb_inject": ["commands.md", "dependencies.md"],
        "max_iter": 8,
    },
]


def register_builtins(registry: SubagentRegistry) -> int:
    count = 0
    for item in BUILTIN_SUBAGENTS:
        agent = Subagent(**item)
        registry.register(agent)
        count += 1
    # Load from YAML files, overriding hardcoded definitions
    count += registry.load_builtin()
    return count
