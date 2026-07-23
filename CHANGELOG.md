# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-07-21

### Changed

- **重大转向：从 Python 编排引擎收敛为纯提示词 Claude Code Skill。** 研发流程的核心价值（编排逻辑 + 阶段模板 + 检查清单）现以提示词形式存放于 `skills/sdlc/`，由 Claude Code 本体能力驱动，不再需要独立 CLI。

### Removed

- 移除 Python 编排引擎（`sdlc/` 源码、`tests/` 测试套件）及其打包/分发/CI 配置（`pyproject.toml`、Homebrew formula、Dockerfile、mkdocs、PyPI/CI workflows）。
- 移除引擎相关文档（`prd/`、`doc/`、`docs/`）与过程性文件。
- 下列 v1.x 条目为 Python CLI 的历史记录，保留仅作追溯。

## [1.1.0] - 2026-06-12

### Fixed

- Resolved 59 production issues across 7 modules (input validation, pipeline exception-state leaks, path-traversal hardening, cost-tracking edge cases)
- Unified terminal pipeline/stage state on `COMPLETED` (previously split between `SUCCESS` and `COMPLETED`), with an idempotent DB migration for legacy rows

### Added

- Custom `base_url` support for OpenAI-compatible providers, with tier-routing automatically disabled for proxy endpoints
- `only_stages` / `skip_stages` filtering on `sdlc run`
- Init auto-detection improvements and lazy stage-catalog loading

## [1.0.0] - 2026-06-06

### Added

- **First GA release** — AI-driven full-lifecycle SDLC orchestration CLI
- Third-party LLM API support: DeepSeek, Qwen, Moonshot, GLM, Ollama, SiliconFlow (8 provider presets total)
- 10 quality gates and expanded rule sets
- `MCPClient` + `SkillRunner` integrations
- Memory L2: post-stage KB auto-update engine
- Concurrent stage execution
- LICENSE (MIT), PyPI publish workflow, Homebrew formula, comprehensive tutorial docs

## [0.3.0-rc] - 2026-06-05

### Added

- **18 technology adapters** with auto-detection: dongboot, jd-spring-boot, python-flask, python-django, python-fastapi, node-express, node-nestjs, frontend-react, frontend-vue, go-gin, go-kratos, rust-axum, infra-terraform, mobile-android, mobile-flutter, mobile-ios, data-spark, no-tech
- **27 rules** across 9 rule sets: coding-must, python-must, node-must, go-must, rust-must, frontend-must, mobile-must, data-must, infra-must
- **4 rule enforcers**: CREnforcer (code review), LintEnforcer (static lint), CIEnforcer (CI pipeline), RuntimeEnforcer (runtime hooks)
- **5 quality gates**: PM Review, TL Review, Security Gate, Deploy Approval, Hotfix Emergency
- **11 subagent prompts**: requirements-analyst, architect, coder-backend, coder-frontend, tester-unit, reviewer, sre-writer, doc-writer, migration-engineer, security-auditor, devops-engineer
- **SdlcClient Python API**: synchronous programmatic access (`run`, `init`, `status`, `kb_list`, `rule_list`, `stage_list`, `doctor`)
- **Real pipeline execution**: RunCoordinator orchestrates entry detection, profile resolution, pipeline building, stage execution, gate evaluation, and cost tracking end-to-end
- **3 enforcer strategies**: CR (regex pattern matching on files), Lint (static analysis), CI (workflow status checks), Runtime (pre/post hooks)
- **Rule exception management**: temporary exemptions with expiry, scope filtering, auto-renewal
- **DependencyContainer**: unified assembly of all subsystems (state, audit, catalog, profiles, adapters, gates, subagent pool, LLM client, cost tracker)
- **Security whitelist**: command allowlist with shell operator, command substitution, path traversal, and env var access blocking
- **965 tests** with 92% code coverage

### Changed

- Expanded adapter registry from 1 (dongboot) to 18 adapters
- Expanded rule engine from basic to 4-enforcer architecture with exception management
- Profile registry expanded with `frontend`, `full-stack`, `revert`, `audit`, `idea`, `migrate` profiles

## [0.2.0] - 2026-05-15

### Added

- **KB Scanner**: scans project files and builds knowledge base with fingerprinting
- **KB Reconciler**: detects stale and missing KB entries, reconciles with current state
- **Stage YAML templates**: all 12 stages defined as YAML files in `builtin/stages/`
- **Gate YAML templates**: 5 quality gates defined in `builtin/gates/`
- **Subagent YAML templates**: 11 subagent prompts in `builtin/subagents/`
- **CostTracker**: tracks LLM call costs per model with budget thresholds and `COST_EXCEEDED` audit events
- **E2E tests**: end-to-end pipeline execution tests
- **Stage runner**: executes stages sequentially with gate evaluation between stages
- **Gate triggers**: 6 trigger types — `always`, `on_severity`, `on_artifact`, `on_rule_violation`, `on_failure`, `on_stage_end`
- **Gate actions**: `auto_pass`, `manual_review`, `block`, `escalate`

### Changed

- CLI command structure organized into 3 groups: core flow (5), auxiliary (7), management (7)
- Audit event types expanded to 27

## [0.1.0] - 2026-04-01

### Added

- **13 packages**: `adapter`, `audit`, `builtin`, `cli`, `core`, `gate`, `integrations`, `kb`, `llm`, `profile`, `rule`, `stage`, `state`, `subagent`, `utils`
- **19 CLI commands**: `init`, `run`, `status`, `resume`, `stage`, `profile`, `adapter`, `kb`, `rule`, `agent`, `config`, `doctor`, `export`, `import`, `replay`, `trace`, `stats`, `version`, `completion`
- **dongboot adapter**: JD microservice framework adapter with 8 components
- **14 profiles**: `new-feature`, `bug-fix`, `hotfix`, `refactor`, `test`, `infra`, `release`, `revert`, `doc`, `migrate`, `audit`, `idea`, `frontend`, `full-stack`
- **12 pipeline stages**: clarify, design, impl-backend, impl-frontend, unit-test, cr, package, deploy, monitor-setup, docs, impact-analysis, security-scan
- **Dual LLM provider**: Anthropic (primary) + OpenAI (fallback) with automatic routing
- **LLM cache**: SQLite backend with TTL-based expiration
- **Audit trail**: JSONL format with 27 event types and full traceability
- **State management**: SQLite persistence (6 tables + 2 views), snapshots, pause/resume
- **4-layer config**: CLI `--config` > project `.sdlc/` > user `~/.sdlc/` > builtin defaults
- **Entry detector**: classifies input text as feature, bug, hotfix, refactor, etc.
- **Pipeline builder**: assembles stage graph from profile and entry type
- **Integrations**: filesystem, git, http, MCP, shell runner, skill runner, whitelist
