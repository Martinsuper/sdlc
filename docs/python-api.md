# Python API — SdlcClient

`SdlcClient` provides a synchronous Python API for programmatic access to `sdlc` functionality. It is the recommended way to integrate `sdlc` into scripts, CI/CD pipelines, and other Python applications.

## Installation

```bash
pip install sdlc
```

## Quick Reference

```python
from sdlc import SdlcClient

client = SdlcClient()
```

## Methods

### `SdlcClient(config=None)`

Create a new client instance.

**Parameters:**
- `config` (`SdlcConfig | None`) — Optional configuration. When `None`, loads from the 4-layer config hierarchy (CLI > project > user > defaults).

```python
from sdlc import SdlcClient
from sdlc.utils.config import SdlcConfig, LLMConfig

# Default configuration
client = SdlcClient()

# Custom configuration
config = SdlcConfig(
    llm=LLMConfig(
        provider="anthropic",
        model="claude-opus-4-20250514",
        max_cost_usd=10.0,
    ),
    log_level="DEBUG",
)
client = SdlcClient(config)
```

### `run(input_text, **opts)`

Execute an SDLC pipeline synchronously.

**Parameters:**
- `input_text` (`str`) — Natural language description of the task
- `**opts` — Additional options:
  - `profile_id` (`str | None`) — Override profile selection
  - `adapter_id` (`str | None`) — Override adapter selection

**Returns:** `dict[str, Any]` with keys:
- `pipeline_id` — Unique pipeline identifier
- `status` — `"completed"`, `"failed"`, or `"paused"`
- `stage_results` — List of per-stage result dicts
- `total_cost_usd` — Total LLM cost in USD

```python
result = client.run("Add user authentication with JWT tokens")
print(result["pipeline_id"])    # "abc-123-def"
print(result["status"])         # "completed"
print(result["total_cost_usd"]) # 0.042

# With profile override
result = client.run("Fix login timeout", profile_id="bug-fix")
```

### `init(path=Path("."), **opts)`

Initialize a project. Scans the codebase, detects the technology adapter, and builds the initial knowledge base.

**Parameters:**
- `path` (`Path`) — Project root directory (default: current directory)
- `**opts` — Scanner options

**Returns:** `dict[str, Any]` — Scanner result with detected files, adapter, and KB structure.

```python
result = client.init(path=Path("/path/to/project"))
print(result.keys())  # dict_keys(['files', 'adapter', 'kb_layers', ...])
```

### `status(pipeline_id=None, **filters)`

Query pipeline status.

**Parameters:**
- `pipeline_id` (`str | None`) — Specific pipeline ID. When `None`, returns all pipelines.
- `**filters` — Additional filter arguments passed to state store

**Returns:**
- When `pipeline_id` is provided: `PipelineSummary | None`
- When `pipeline_id` is `None`: `list[PipelineSummary]`

```python
# All pipelines
pipelines = client.status()
for p in pipelines:
    print(p.pipeline_id, p.status)

# Specific pipeline
pipeline = client.status(pipeline_id="abc-123")
if pipeline:
    print(pipeline.status)
```

### `kb_list()`

List knowledge base files.

**Returns:** `list[dict[str, Any]]` — Each dict contains:
- `name` — KB layer name
- `type` — Layer type
- `size` — Size in bytes

```python
layers = client.kb_list()
for layer in layers:
    print(f"{layer['name']} ({layer['type']}, {layer['size']} bytes)")
```

### `rule_list(**filters)`

List rules from the rule engine.

**Parameters:**
- `**filters` — Filter arguments:
  - `category` (`str | None`) — Filter by category (coding, security, performance, etc.)
  - `level` (`RuleLevel | None`) — Filter by level (MUST, SHOULD, MAY, etc.)

**Returns:** `list[dict[str, Any]]` — Each dict contains rule properties.

```python
# All rules
rules = client.rule_list()

# Security rules only
rules = client.rule_list(category="security")

# MUST-level rules
from sdlc.rule.models import RuleLevel
rules = client.rule_list(level=RuleLevel.MUST)
```

### `stage_list()`

List all registered pipeline stages.

**Returns:** `list[dict[str, Any]]` — Each dict contains stage properties.

```python
stages = client.stage_list()
for s in stages:
    print(s["id"], s["name"], s["category"])
```

### `doctor()`

Run environment diagnostics.

**Returns:** `dict[str, bool]` — Diagnostic check results:
- `python_version` — Python 3.11+ installed
- `uv_installed` — uv package manager available
- `sdlc_home_exists` — `~/.sdlc/` directory exists
- `disk_space_ok` — At least 1 GB free disk space

```python
checks = client.doctor()
for check, passed in checks.items():
    status = "OK" if passed else "FAIL"
    print(f"  {check}: {status}")
```

## Complete Example

```python
#!/usr/bin/env python3
"""CI/CD integration example using SdlcClient."""

from pathlib import Path
from sdlc import SdlcClient
from sdlc.utils.config import SdlcConfig, LLMConfig

# Configure client
config = SdlcConfig(
    llm=LLMConfig(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        max_cost_usd=3.0,
    ),
    audit_enabled=True,
)
client = SdlcClient(config)

# Pre-flight checks
checks = client.doctor()
if not all(checks.values()):
    print("Environment check failed:")
    for k, v in checks.items():
        if not v:
            print(f"  {k}: FAIL")
    raise SystemExit(1)

# Initialize project
print("Initializing project...")
init_result = client.init(path=Path("."))
print(f"Detected adapter: {init_result.get('adapter', 'none')}")

# Run pipeline
print("Running pipeline...")
result = client.run(
    "Add health check endpoint at /health that returns service status",
    profile_id="new-feature",
)

# Report results
print(f"Pipeline: {result['pipeline_id']}")
print(f"Status: {result['status']}")
print(f"Cost: ${result['total_cost_usd']:.4f}")
print(f"Stages completed: {len(result['stage_results'])}")

# Check rules
security_rules = client.rule_list(category="security")
must_rules = [r for r in security_rules if r["level"] in ("MUST", "MUST_NOT")]
print(f"Security MUST rules: {len(must_rules)}")
```

## Error Handling

```python
from sdlc import SdlcClient
from sdlc.utils.exceptions import SdlcError

client = SdlcClient()

try:
    result = client.run("Add feature")
except SdlcError as e:
    print(f"SDLC error: {e}")
```

Common error scenarios:
- Missing API keys — LLM calls will fail at request time
- Adapter not found — raised when specifying a non-existent `adapter_id`
- Profile not found — raised when specifying a non-existent `profile_id`
- Budget exceeded — pipeline may pause if cost exceeds `max_cost_usd`