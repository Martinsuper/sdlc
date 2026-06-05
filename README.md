# `sdlc` — AI-Driven SDLC Orchestration CLI

> Automate your entire software development lifecycle — from idea to production — with AI-powered pipeline orchestration.

**Status:** ![RC](https://img.shields.io/badge/status-rc-blue) ![v0.3.0](https://img.shields.io/badge/version-0.3.0--rc-blue) ![M3](https://img.shields.io/badge/milestone-M3-cyan)

---

## Features

| Area | Detail |
|------|--------|
| **CLI Commands** | 19 commands: `init`, `run`, `status`, `resume`, `stage`, `profile`, `adapter`, `kb`, `rule`, `agent`, `config`, `doctor`, `export`, `import`, `replay`, `trace`, `stats`, `version`, `completion` |
| **Pipeline Stages** | 12 stages across an 8-step lifecycle (ideation → analysis → design → implementation → testing → review → deployment → monitoring) |
| **Quality Gates** | 5 gates: PM Review, TL Review, Security Gate, Deploy Approval, Hotfix Emergency |
| **Rule Engine** | 27 rules across 9 rule sets (coding, python, node, go, rust, frontend, mobile, data, infra) with 4 enforcers |
| **Built-in Adapters** | 18 technology adapters with auto-detection |
| **Workflow Profiles** | 14 profiles: `new-feature`, `bug-fix`, `hotfix`, `refactor`, `test`, `infra`, `release`, `revert`, `doc`, `migrate`, `audit`, `idea`, `frontend`, `full-stack` |
| **Subagents** | 11 built-in AI agents with role-specific prompts |
| **LLM Providers** | Anthropic + OpenAI with automatic fallback, SQLite cache, cost tracking |
| **Audit Trail** | 27 event types, JSONL format, full traceability |
| **State Management** | SQLite (6 tables + 2 views), snapshots, pause/resume |
| **Python API** | `SdlcClient` for programmatic access |
| **4-Layer Config** | CLI `--config` > project `.sdlc/` > user `~/.sdlc/` > builtin defaults |
| **Security** | Command whitelist, no hardcoded secrets, API keys from env vars |

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

# Initialize a project (scans codebase, detects adapter, builds KB)
sdlc init

# Run a pipeline
sdlc run "Add user authentication with JWT"

# Check pipeline status
sdlc status
sdlc status --pipeline <id>
```

---

## Architecture

```
CLI (Click, 19 commands)
 └── DependencyContainer
      ├── RunCoordinator (core)
      │    ├── EntryDetector    — classify input as feature/bug/hotfix/...
      │    ├── PipelineBuilder  — assemble stage graph from profile
      │    └── StageRunner      — execute stages, enforce gates
      │
      ├── Adapter layer         — 18 adapters, auto-detect via glob+contains
      ├── Stage layer           — 12 stages, YAML-defined, catalog-driven
      ├── Profile layer         — 14 workflow profiles, entry-kind routing
      ├── Gate layer            — 5 quality gates, trigger-based evaluation
      ├── Rule layer            — 27 rules, 4 enforcers, exception management
      │
      └─ Supporting services
         ├── KB                 — knowledge base (scanner, fingerprint, reconciler)
         ├── LLM                — dual-provider (Anthropic+OpenAI) + SQLite cache + CostTracker
         ├── Subagent           — 11 agents, pool-based dispatch, tool access
         ├── Audit              — JSONL event logging (27 event types)
         ├── State              — SQLite persistence, snapshots, pause/resume
         ├── Integrations       — filesystem, git, http, MCP, shell, skills, whitelist
         └── Builtin            — YAML templates for stages, rules, gates, subagents
```

13 packages: `adapter`, `audit`, `builtin`, `cli`, `core`, `gate`, `integrations`, `kb`, `llm`, `profile`, `rule`, `stage`, `state`, `subagent`, `utils`

---

## Adapters

18 built-in technology adapters with auto-detection:

| Adapter | ID | Detect Pattern | Components |
|---------|----|---------------|------------|
| DongBoot | `dongboot` | `**/pom.xml` contains `dong-boot-starter` | 8 components (dong-log, dong-thread, dong-dal, dong-cache, dong-mq, dong-web, dong-config, dong-hot-deploy) |
| JD Spring Boot | `jd-spring-boot` | `**/pom.xml` contains `spring-boot-starter` | 4 components (spring-mvc, spring-data, spring-security, spring-actuator) |
| Python Flask | `python-flask` | `**/requirements.txt` contains `flask` | 3 components (flask-restful, flask-sqlalchemy, flask-caching) |
| Python Django | `python-django` | `**/requirements.txt` contains `django` | 4 components (django-rest, django-orm, django-admin, django-auth) |
| Python FastAPI | `python-fastapi` | `**/requirements.txt` or `**/pyproject.toml` contains `fastapi` | 4 components (uvicorn, pydantic, sqlalchemy, redis) |
| Node Express | `node-express` | `**/package.json` contains `express` | 3 components (express-router, express-middleware, body-parser) |
| Node NestJS | `node-nestjs` | `**/package.json` contains `@nestjs/core` | 4 components (nest-modules, nest-guards, nest-interceptors, typeorm) |
| React | `frontend-react` | `**/package.json` contains `react` | 4 components (react-router, redux, axios, jest) |
| Vue | `frontend-vue` | `**/package.json` contains `vue` | 4 components (vue-router, vuex, axios, vitest) |
| Go Gin | `go-gin` | `**/go.mod` contains `gin-gonic/gin` | 3 components (gin-router, gin-middleware, gorm) |
| Go Kratos | `go-kratos` | `**/go.mod` contains `go-kratos/kratos` | 3 components (kratos-proto, kratos-wire, kratos-config) |
| Rust Axum | `rust-axum` | `**/Cargo.toml` contains `axum` | 3 components (axum-router, tokio-runtime, sqlx) |
| Terraform | `infra-terraform` | `**/*.tf` | 2 components (terraform-aws, terraform-k8s) |
| Android | `mobile-android` | `**/build.gradle` contains `com.android.application` | 4 components (android-activity, android-fragment, retrofit, room) |
| Flutter | `mobile-flutter` | `**/pubspec.yaml` contains `flutter` | 3 components (flutter-bloc, dio, hive) |
| iOS | `mobile-ios` | `**/Package.swift` or `**/*.xcodeproj` | 3 components (uikit, alamofire, coredata) |
| Apache Spark | `data-spark` | `**/pom.xml` contains `spark-core` or `**/requirements.txt` contains `pyspark` | 3 components (spark-sql, spark-streaming, spark-ml) |
| No Tech | `no-tech` | (none) | 0 components |

---

## Profiles

14 built-in workflow profiles:

| Profile | ID | Entry Kinds | Stages | Severity |
|---------|----|-------------|--------|----------|
| New Feature | `new-feature` | feature, idea | clarify → design → impl-backend → unit-test → cr → package → deploy → monitor-setup | P2 |
| Bug Fix | `bug-fix` | bug | clarify → impl-backend → unit-test → cr → package → deploy | P1 |
| Hotfix | `hotfix` | hotfix | clarify → impl-backend → unit-test → deploy | P0 |
| Refactor | `refactor` | refactor | clarify → design → impl-backend → unit-test → cr → package → deploy | P2 |
| Test | `test` | test | clarify → unit-test → cr | P3 |
| Infra | `infra` | infra | clarify → design → impl-backend → unit-test → deploy → monitor-setup | P1 |
| Release | `release` | release | clarify → package → deploy → monitor-setup | P1 |
| Revert | `revert` | revert | clarify → deploy | P0 |
| Doc | `doc` | doc | clarify | P3 |
| Migrate | `migrate` | migrate | clarify → design → impl-backend → unit-test → cr → deploy | P1 |
| Audit | `audit` | audit | clarify → cr | P1 |
| Idea | `idea` | idea | clarify | P3 |
| Frontend | `frontend` | feature | clarify → design → impl-frontend → unit-test → cr → deploy | P2 |
| Full Stack | `full-stack` | feature | clarify → design → impl-backend → impl-frontend → unit-test → cr → package → deploy → monitor-setup | P2 |

---

## Configuration

### 4-Layer Config Hierarchy

1. **CLI flag** `--config path/to/config.yaml` (highest priority)
2. **Project** `.sdlc/config.yaml`
3. **User** `~/.sdlc/config.yaml`
4. **Builtin defaults** (lowest priority)

### Config Schema

```yaml
llm:
  provider: anthropic          # anthropic | openai
  model: claude-sonnet-4-20250514
  api_key_env: ANTHROPIC_API_KEY  # environment variable name
  base_url: null               # custom endpoint
  max_tokens: 4096
  temperature: 0.7
  timeout: 120.0
  max_cost_usd: 5.0
profile:
  auto_detect: true
  default: new-feature
log_level: INFO
cache_enabled: true
cache_dir: null
audit_enabled: true
no_color: false
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `SDLC_HOME` | Override default `~/.sdlc/` directory |

---

## Python API

```python
from sdlc import SdlcClient

client = SdlcClient()

# Initialize a project
result = client.init(path=".")

# Run a pipeline
result = client.run("Add user authentication with JWT")

# Check status
status = client.status()
status = client.status(pipeline_id="abc-123")

# List KB files
kb = client.kb_list()

# List rules
rules = client.rule_list(category="security")

# List stages
stages = client.stage_list()

# Run diagnostics
checks = client.doctor()
```

---

## Development

```bash
# Clone and install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/ -q

# Run with coverage
uv run pytest tests/ --cov=sdlc --cov-report=term-missing

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
