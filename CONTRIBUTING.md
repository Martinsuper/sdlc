# Contributing to sdlc

Thank you for your interest in contributing to `sdlc`. This document outlines the development setup, code style, and contribution workflow.

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Install

```bash
# Clone the repository
git clone https://github.com/sdlc-team/sdlc.git
cd sdlc

# Install with dev dependencies
uv sync --extra dev

# Verify setup
uv run sdlc doctor
uv run pytest tests/ -q
```

## Code Style

### Linting (ruff)

```bash
# Check
uv run ruff check sdlc/ tests/

# Auto-fix
uv run ruff check --fix sdlc/ tests/
```

Configuration in `pyproject.toml`:
- Target: Python 3.11
- Line length: 100
- Rules: E, F, W, I, N, UP, B, A, SIM, RUF

### Type Checking (mypy)

```bash
uv run mypy sdlc/
```

Configuration: strict mode with `disallow_untyped_defs = false` and `ignore_missing_imports = true`.

### Formatting

Follow ruff's formatting rules. Key conventions:
- Use `from __future__ import annotations` in all source files
- Use dataclasses for internal models, Pydantic for config and rule models
- Use `StrEnum` for enumeration types
- Keep imports sorted (isort via ruff)

## How to Add Extensions

### Add a New Adapter

1. Create `sdlc/adapter/<name>.py`:

```python
from __future__ import annotations
from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

MY_ADAPTER = AdapterDef(
    id="my-tech",
    name="My Tech Framework",
    version="1.0",
    detect_patterns=[{"glob": "**/package.json", "contains": "my-tech"}],
    components=[
        ComponentDef(id="my-component", type="web", detect="MyComponent", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["my-tech-must"],
    required_kb=["rules/my-tech-must.yaml"],
)

def register_my_tech(registry: AdapterRegistry) -> None:
    registry.register(MY_ADAPTER)
```

2. Register in `sdlc/adapter/__init__.py` and `sdlc/cli/deps.py`.
3. Add tests in `tests/test_adapter.py`.
4. Add rule set in `sdlc/builtin/rules/my-tech-must.yaml` (3 rules per set: MUST, SHOULD, MAY).

### Add a New Stage

1. Create `sdlc/builtin/stages/s-<name>.yaml`:

```yaml
id: s-my-stage
name: My Stage
category: my-category
description: "Description of the stage purpose"
subagent: SA-1
model: claude-sonnet-4-20250514
required_artifacts: []
produces_artifacts:
  - output.md
pre_kb_load:
  - conventions.md
post_kb_update:
  - target: kb/output.md
    op: append
timeout: 1800
retry:
  max: 2
  backoff: exponential
```

2. Reference the stage ID in profile definitions.
3. Add tests for stage catalog loading.

### Add a New Rule

1. Add rule entries to the appropriate rule set YAML in `sdlc/builtin/rules/`:

```yaml
- id: my-rule-id
  level: MUST          # MUST | SHOULD | MAY
  category: security   # coding | security | performance | error-handling | ...
  description: "Rule description"
  enforcer: cr         # cr | lint | ci | runtime
  pattern: "regex_pattern"
  message: "Violation message"
  action: block        # block | warn
  severity: P1         # P0 | P1 | P2 | P3
  applies_to: ["**/*.py"]
  references: []
```

2. Add test cases in `tests/test_rule.py`.

## PR Workflow

1. **Fork** the repository and create a feature branch from `main`.
2. **Develop** with clear commit messages.
3. **Test** — all PRs must pass the full test suite:
   ```bash
   uv run pytest tests/ -q
   uv run ruff check sdlc/ tests/
   uv run mypy sdlc/
   ```
4. **Submit** a pull request with:
   - Description of the change
   - Reference to any related issue
   - Evidence that tests pass

## Testing Requirements

- All new features must include unit tests
- Bug fixes must include regression tests
- Target coverage: 92%+ (current baseline)
- Run the full suite before submitting:

```bash
uv run pytest tests/ -v --cov=sdlc --cov-report=term-missing
```

### Test Structure

Tests are organized by package in `tests/`:
- `test_adapter.py` — adapter registry, detection, definitions
- `test_adapters_extended.py` — individual adapter definitions
- `test_audit.py` — audit logger, event types, queries
- `test_cli_core.py` — CLI core commands
- `test_cli_browse.py` — browse commands
- `test_cli_kb_rule_config.py` — KB, rule, config commands
- `test_cli_deps.py` — dependency container
- `test_core.py` — entry detection, pipeline building, run coordinator
- `test_gate.py` — gate engine, triggers, models
- `test_kb.py` — knowledge base, scanner, reconciler
- `test_llm_*.py` — LLM providers, cache, cost tracking, router
- `test_profile.py` — profile registry, detection
- `test_rule.py` — rule engine, enforcers, exceptions, loader
- `test_stage.py` — stage catalog, runner
- `test_state.py` — state store, snapshots
- `test_subagent.py` — subagent pool, registry
- `test_e2e.py` — end-to-end pipeline execution
- `test_client.py` — SdlcClient Python API
- `test_utils_*.py` — utility modules