# Tutorial

This tutorial walks you through installing, configuring, and running SDLC
end-to-end on a sample project.

## Prerequisites

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- At least one LLM API key (Anthropic or OpenAI)

## Step 1: Install SDLC

```bash
# With uv (recommended)
uv tool install sdlc

# With pip
pip install sdlc
```

Verify the installation:

```bash
sdlc version
# 0.4.0
```

## Step 2: Run Environment Check

```bash
sdlc doctor
```

This checks:

- Python version (3.11+)
- uv installation
- `~/.sdlc/` directory
- Available disk space

## Step 3: Set Up API Keys

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Optional fallback:
export OPENAI_API_KEY="sk-..."
```

Without API keys, `sdlc init` and `sdlc status` work in offline mode.
LLM-powered features require at least one provider key.

## Step 4: Initialize a Project

Navigate to your project directory and run:

```bash
cd /path/to/your/project
sdlc init
```

What `init` does:

1. Scans project files using the KB Scanner
2. Auto-detects the technology adapter (e.g., `python-fastapi`, `frontend-react`)
3. Builds the initial knowledge base in `doc/kb/`
4. Creates `.sdlc/` directory with default configuration

## Step 5: Run a Pipeline

Execute a feature pipeline with a natural language description:

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

## Step 6: Check Pipeline Status

```bash
# List all pipelines
sdlc status

# Check a specific pipeline
sdlc status --pipeline abc-123

# Show detailed stage breakdown
sdlc status --pipeline abc-123 --verbose
```

## Step 7: Browse Resources

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

## Step 8: Manage Rules

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

## Step 9: Use the Python API

```python
from sdlc import SdlcClient

client = SdlcClient()

# Initialize a project
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

- [Configuration](configuration.md) -- customize profiles, LLM settings, and rules
- [API Reference](api-reference.md) -- complete Python API and CLI documentation
