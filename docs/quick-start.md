# Quick Start Guide

## Installation

### With uv (recommended)

```bash
uv tool install -e .
```

### With pip

```bash
pip install -e .
```

### Verify

```bash
sdlc version
sdlc doctor
```

The `doctor` command checks your environment:
- Python version (3.11+)
- uv installation
- `~/.sdlc/` directory
- Available disk space

## Set Up API Keys

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."       # optional fallback
```

Without API keys, `sdlc init` and `sdlc status` work in offline mode. LLM-powered features require at least one provider key.

## Initialize a Project

```bash
cd /path/to/your/project
sdlc init
```

What `init` does:
1. Scans project files using the KB Scanner
2. Auto-detects the technology adapter (e.g., `python-fastapi`, `frontend-react`)
3. Builds the initial knowledge base in `doc/kb/`
4. Creates `.sdlc/` directory with default configuration

## Run a Pipeline

```bash
sdlc run "Add user authentication with JWT tokens"
```

What `run` does:
1. Detects the entry type (feature, bug, hotfix, etc.)
2. Resolves the appropriate workflow profile
3. Builds a pipeline of stages
4. Executes stages sequentially with AI subagents
5. Evaluates quality gates between stages
6. Enforces coding rules
7. Tracks costs and audit events

### With Options

```bash
# Specify a profile
sdlc run "Fix login timeout" --profile bug-fix

# Specify an adapter
sdlc run "Add REST endpoint" --adapter python-fastapi

# Set cost limit
sdlc run "Refactor database layer" --max-cost 2.0
```

## Check Status

```bash
# List all pipelines
sdlc status

# Check a specific pipeline
sdlc status --pipeline abc-123

# Show detailed stage breakdown
sdlc status --pipeline abc-123 --verbose
```

## Browse Resources

```bash
# List available adapters
sdlc adapter list

# Detect which adapter matches the current project
sdlc adapter detect

# List available profiles
sdlc profile list

# List available stages
sdlc stage list

# List subagents
sdlc agent list
```

## Manage Rules

```bash
# List all rules
sdlc rule list

# Filter by category
sdlc rule list --category security

# Filter by level
sdlc rule list --level MUST

# Disable a rule temporarily
sdlc rule disable no-console-log --until 2026-07-01 --reason "Debug sprint"

# Re-enable a rule
sdlc rule enable no-console-log

# Check rules against files
sdlc rule check --stage s-impl-backend
```

## Manage Knowledge Base

```bash
# Scan project and update KB
sdlc kb scan

# List KB files
sdlc kb list

# Show KB file details
sdlc kb show architecture/component-catalog.md
```

## Configuration

### Create a project config

```bash
# Show current configuration
sdlc config show

# Set a value
sdlc config set llm.model claude-opus-4-20250514

# Set profile default
sdlc config set profile.default bug-fix
```

### Config file locations

| Priority | Location | Scope |
|----------|----------|-------|
| 1 (highest) | `--config path.yaml` | Single invocation |
| 2 | `.sdlc/config.yaml` | Project |
| 3 | `~/.sdlc/config.yaml` | User |
| 4 (lowest) | Builtin defaults | System |

### Example `.sdlc/config.yaml`

```yaml
llm:
  provider: anthropic
  model: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY
  max_tokens: 4096
  temperature: 0.7
  max_cost_usd: 5.0
profile:
  auto_detect: true
  default: new-feature
log_level: INFO
cache_enabled: true
audit_enabled: true
```

## Python API

```python
from sdlc import SdlcClient

client = SdlcClient()

# Initialize
result = client.init(path=".")

# Run a pipeline
result = client.run("Add user authentication with JWT")
print(result["pipeline_id"])
print(result["status"])

# Query status
pipelines = client.status()
for p in pipelines:
    print(p.pipeline_id, p.status)

# List resources
stages = client.stage_list()
rules = client.rule_list(category="security")
kb = client.kb_list()

# Diagnostics
checks = client.doctor()
```

## Next Steps

- [Architecture](architecture.md) — detailed package and dependency overview
- [Adapters](adapters.md) — all 18 technology adapters
- [Rules](rules.md) — rule engine, enforcers, and custom rules
- [Python API](python-api.md) — complete SdlcClient reference