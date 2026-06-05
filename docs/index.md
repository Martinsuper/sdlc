# SDLC Documentation

AI-driven full-lifecycle SDLC orchestration CLI tool.

SDLC automates the complete software development lifecycle using AI subagents,
from requirements analysis through implementation, testing, and deployment.

## Quick Links

- [Tutorial](tutorial.md) -- step-by-step guide to get started
- [Configuration](configuration.md) -- full config reference
- [API Reference](api-reference.md) -- Python API and CLI docs
- [Changelog](changelog.md) -- release history

## Features

- **18 technology adapters** with auto-detection (Python, Node.js, Go, Rust, Java, etc.)
- **14 workflow profiles** for features, bug fixes, hotfixes, refactoring, and more
- **12 pipeline stages** from clarify to security scan
- **4 rule enforcers** (CR, Lint, CI, Runtime) with 27 built-in rules
- **5 quality gates** including PM Review, TL Review, and Security Gate
- **Dual LLM provider** support (Anthropic + OpenAI) with cost tracking
- **Python API** for programmatic access via `SdlcClient`
- **Audit trail** with 27 event types and full traceability

## Installation

```bash
# With uv (recommended)
uv tool install sdlc

# With pip
pip install sdlc

# With Homebrew
brew install your-org/sdlc/sdlc
```

## Verify

```bash
sdlc version
sdlc doctor
```
