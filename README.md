# `sdlc` — AI-Driven SDLC Orchestration CLI

> Automate your entire software development lifecycle — from idea to production — with AI-powered pipeline orchestration.

**Status:** ![Alpha](https://img.shields.io/badge/status-alpha-orange) ![v0.1.0](https://img.shields.io/badge/version-0.1.0-blue) ![M1](https://img.shields.io/badge/milestone-M1-cyan)

---

## Features (M1 Milestone)

| Area | Detail |
|------|--------|
| **CLI Commands** | 19 commands: `init`, `run`, `status`, `resume`, `stage`, `profile`, `adapter`, `kb`, `rule`, `agent`, `config`, `doctor`, `export`, `import`, `replay`, `trace`, `stats`, `version`, `completion` |
| **Pipeline Stages** | 12 stages across an 8-step lifecycle (ideation → analysis → design → implementation → testing → review → deployment → monitoring) |
| **Gate Triggers** | 6 modes: `auto-pass`, `auto-block`, `manual`, `conditional`, `timeout`, `retry` |
| **Built-in Profiles** | 14 profiles: `new-feature`, `bugfix`, `refactor`, `hotfix`, `experiment`, `release`, `docs`, `security`, `perf`, `test`, `migration`, `infra`, `dongboot`, `legacy` |
| **dongboot Adapter** | JD microservice framework adapter (8 components) |
| **LLM Cache** | SQLite backend with TTL-based expiration |
| **Dual LLM Provider** | Anthropic + OpenAI with automatic fallback |
| **Audit Trail** | 27 event types, JSONL format, full traceability |
| **State Management** | SQLite (6 tables + 2 views), snapshots, pause/resume |
| **4-Layer Config** | CLI `--config` > project `.sdlc/` > user `~/.sdlc/` > builtin defaults |

---

## Quick Start

```bash
# Install with uv
uv tool install -e .

# Or with pip
pip install -e .

# Verify installation
sdlc doctor
sdlc version

# Initialize a project
sdlc init

# Run a pipeline
sdlc run

# Check status
sdlc status
```

---

## Architecture

```
CLI (Click)
 └── Engine (core)
      ├── Adapter layer   — framework integrations (dongboot, …)
      ├── Stage layer      — 12 pipeline stages, 8-step lifecycle
      ├── Profile layer    — 14 built-in workflow profiles
      └── Rule layer       — gate rules & trigger policies
      │
      └─ Supporting services
         ├── KB            — knowledge base
         ├── LLM           — dual-provider + cache
         ├── Subagent      — task delegation
         ├── Gate          — quality gates & triggers
         ├── Audit         — JSONL event logging (27 types)
         └── State         — SQLite persistence & snapshots
```

13 packages: `adapter`, `audit`, `builtin`, `cli`, `core`, `gate`, `integrations`, `kb`, `llm`, `profile`, `rule`, `stage`, `state`, `subagent`, `utils`

---

## Development

```bash
# Clone and install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/ -q

# Lint
uv run ruff check sdlc/ tests/

# Type check
uv run mypy sdlc/
```

---

## Tech Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.11+ |
| CLI framework | Click 8.1+ |
| Data models | Pydantic v2.6+ |
| YAML handling | ruamel.yaml |
| Persistence | SQLite |
| Build system | hatchling |
| Linting | ruff |
| Type checking | mypy (strict) |
| Package manager | uv |

---

## License

MIT
