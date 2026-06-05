# Configuration Reference

SDLC uses a 4-layer configuration system with increasing priority:

| Priority | Location | Scope |
|----------|----------|-------|
| 1 (highest) | `--config path.yaml` | Single invocation |
| 2 | `.sdlc/config.yaml` | Project |
| 3 | `~/.sdlc/config.yaml` | User |
| 4 (lowest) | Builtin defaults | System |

## CLI Configuration Commands

```bash
# Show current configuration
sdlc config show

# Set a value
sdlc config set llm.model claude-opus-4-20250514

# Set profile default
sdlc config set profile.default bug-fix
```

## Full Configuration File

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

## LLM Configuration

### `llm.provider`

- **Type**: `string`
- **Default**: `"anthropic"`
- **Options**: `"anthropic"`, `"openai"`
- **Description**: Primary LLM provider. SDLC supports Anthropic (primary) and
  OpenAI (fallback) with automatic routing.

### `llm.model`

- **Type**: `string`
- **Default**: `"claude-sonnet-4-20250514"`
- **Description**: Model identifier for the chosen provider.

### `llm.api_key_env`

- **Type**: `string`
- **Default**: `"ANTHROPIC_API_KEY"` (for Anthropic), `"OPENAI_API_KEY"` (for OpenAI)
- **Description**: Environment variable name holding the API key.

### `llm.max_tokens`

- **Type**: `integer`
- **Default**: `4096`
- **Description**: Maximum tokens per LLM response.

### `llm.temperature`

- **Type**: `float`
- **Default**: `0.7`
- **Range**: 0.0 - 2.0
- **Description**: Sampling temperature for LLM responses.

### `llm.max_cost_usd`

- **Type**: `float`
- **Default**: `5.0`
- **Description**: Maximum cost in USD per pipeline run. Exceeding this triggers
  a `COST_EXCEEDED` audit event and halts the pipeline.

## Profile Configuration

### `profile.auto_detect`

- **Type**: `boolean`
- **Default**: `true`
- **Description**: Whether to auto-detect the workflow profile based on the
  entry type (feature, bug, hotfix, etc.).

### `profile.default`

- **Type**: `string`
- **Default**: `"new-feature"`
- **Options**: `new-feature`, `bug-fix`, `hotfix`, `refactor`, `test`,
  `infra`, `release`, `revert`, `doc`, `migrate`, `audit`, `idea`,
  `frontend`, `full-stack`
- **Description**: Default workflow profile when auto-detection is disabled or
  fails.

## General Settings

### `log_level`

- **Type**: `string`
- **Default**: `"INFO"`
- **Options**: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`
- **Description**: Logging verbosity.

### `cache_enabled`

- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable LLM response caching (SQLite backend with TTL-based
  expiration).

### `audit_enabled`

- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable audit trail recording (JSONL format with 27 event
  types).

## Available Adapters

SDLC includes 18 technology adapters with auto-detection:

| Adapter | Identifier |
|---------|-----------|
| Dongboot | `dongboot` |
| JD Spring Boot | `jd-spring-boot` |
| Python Flask | `python-flask` |
| Python Django | `python-django` |
| Python FastAPI | `python-fastapi` |
| Node Express | `node-express` |
| Node NestJS | `node-nestjs` |
| Frontend React | `frontend-react` |
| Frontend Vue | `frontend-vue` |
| Go Gin | `go-gin` |
| Go Kratos | `go-kratos` |
| Rust Axum | `rust-axum` |
| Infra Terraform | `infra-terraform` |
| Mobile Android | `mobile-android` |
| Mobile Flutter | `mobile-flutter` |
| Mobile iOS | `mobile-ios` |
| Data Spark | `data-spark` |
| No Tech | `no-tech` |

## Available Profiles

| Profile | Identifier | Description |
|---------|-----------|-------------|
| New Feature | `new-feature` | Full feature development cycle |
| Bug Fix | `bug-fix` | Targeted bug resolution |
| Hotfix | `hotfix` | Emergency production fix |
| Refactor | `refactor` | Code refactoring |
| Test | `test` | Test writing and coverage |
| Infra | `infra` | Infrastructure changes |
| Release | `release` | Release preparation |
| Revert | `revert` | Revert previous changes |
| Doc | `doc` | Documentation updates |
| Migrate | `migrate` | Technology migration |
| Audit | `audit` | Code audit and review |
| Idea | `idea` | Exploratory prototyping |
| Frontend | `frontend` | Frontend-only development |
| Full-stack | `full-stack` | Full-stack development |

## Pipeline Stages

| Stage | Identifier |
|-------|-----------|
| Clarify | `s-clarify` |
| Design | `s-design` |
| Implement Backend | `s-impl-backend` |
| Implement Frontend | `s-impl-frontend` |
| Unit Test | `s-unit-test` |
| Code Review | `s-cr` |
| Package | `s-package` |
| Deploy | `s-deploy` |
| Monitor Setup | `s-monitor-setup` |
| Docs | `s-docs` |
| Impact Analysis | `s-impact-analysis` |
| Security Scan | `s-security-scan` |

## Quality Gates

| Gate | Identifier | Action |
|------|-----------|--------|
| PM Review | `g1-pm-review` | `manual_review` |
| TL Review | `g2-tl-review` | `manual_review` |
| Security Gate | `g3-security-gate` | `block` |
| Deploy Approval | `g4-deploy-approval` | `manual_review` |
| Hotfix Emergency | `g5-hotfix-emergency` | `auto_pass` |
