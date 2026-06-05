# Architecture

## Overview

`sdlc` is an AI-driven SDLC orchestration CLI that automates the full software development lifecycle. It classifies user input, selects a workflow profile, builds a pipeline of stages, executes them with AI subagents, enforces quality gates and rules, and tracks all activity through an audit trail.

## Package Map

```
sdlc/
├── adapter/          Technology adapters (18 adapters, auto-detect)
├── audit/            JSONL event logging (27 event types)
├── builtin/          YAML templates
│   ├── gates/        5 quality gate definitions
│   ├── profiles/     Profile registration helpers
│   ├── rules/        9 rule set YAML files (27 rules)
│   ├── stages/       12 stage YAML definitions
│   └── subagents/    11 subagent prompt definitions
├── cli/              Click CLI (19 commands)
├── core/             Pipeline orchestration
│   ├── entry_detector.py    Classify input (feature/bug/hotfix/...)
│   ├── pipeline_builder.py  Assemble stage graph from profile
│   └── run_coordinator.py   Orchestrate execution end-to-end
├── gate/             Quality gates (5 gates, 6 triggers, 4 actions)
├── integrations/     External system clients
│   ├── filesystem.py        File operations
│   ├── git_client.py        Git operations
│   ├── http_client.py       HTTP requests
│   ├── mcp_client.py        Model Context Protocol
│   ├── shell_runner.py      Safe shell execution
│   ├── skill_runner.py      Skill dispatch
│   └── whitelist.py         Command security whitelist
├── kb/               Knowledge base
│   ├── scanner.py            Project file scanner
│   ├── fingerprint.py        Content fingerprinting
│   ├── reconciler.py         KB staleness detection
│   ├── writer.py             KB file writer
│   └── knowledge_base.py     KB layer management
├── llm/              LLM providers
│   ├── anthropic_provider.py  Anthropic API
│   ├── openai_provider.py     OpenAI API
│   ├── client.py              Multi-provider with fallback
│   ├── cache.py               SQLite response cache
│   └── cost.py                CostTracker
├── profile/          Workflow profiles (14 profiles)
├── rule/             Rule engine
│   ├── engine.py     Central engine: load, filter, check
│   ├── enforcer.py   4 enforcers: CR, Lint, CI, Runtime
│   ├── exceptions.py Rule exemption management
│   └── loader.py     YAML rule loader
├── stage/            Pipeline stages
│   ├── catalog.py    Stage registry, YAML loading
│   ├── runner.py     Sequential stage execution
│   └── models.py     StageDef, StageNode
├── state/            State persistence
│   ├── store.py      SQLite state store
│   ├── schema.py     Table definitions
│   └── snapshot.py   Pipeline snapshots
├── subagent/         AI subagents
│   ├── registry.py   Subagent registry
│   ├── pool.py       Pool-based dispatch
│   └── builtin.py    11 built-in agent definitions
├── utils/            Shared utilities
│   ├── config.py           SdlcConfig (Pydantic model)
│   ├── config_loader.py    4-layer config loading
│   ├── paths.py            Path resolution
│   ├── yaml_io.py          YAML read/write
│   ├── git.py              Git helpers
│   ├── fingerprint.py      Content hashing
│   ├── text.py             Text utilities
│   ├── time.py             Time helpers
│   ├── logging.py          Logging setup
│   ├── exceptions.py       Base exception classes
│   └── async_runner.py     Async execution helpers
└── client.py         SdlcClient public Python API
```

## Dependency Graph

```
                    ┌─────────┐
                    │   CLI   │
                    └────┬────┘
                         │
                    ┌────┴────┐
                    │  core   │
                    └────┬────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
    ┌─────┴─────┐  ┌─────┴─────┐  ┌────┴────┐
    │  profile  │  │   stage   │  │  gate   │
    └─────┬─────┘  └─────┬─────┘  └────┬────┘
          │              │              │
          │         ┌────┴────┐        │
          │         │subagent │        │
          │         └────┬────┘        │
          │              │             │
    ┌─────┴─────┐  ┌─────┴─────┐  ┌───┴────┐
    │  adapter  │  │    llm    │  │  rule  │
    └─────┬─────┘  └─────┬─────┘  └───┬────┘
          │              │             │
          │         ┌────┴────┐        │
          │         │integrat.│        │
          │         └────┬────┘        │
          │              │             │
    ┌─────┴──────────────┴─────────────┴──────┐
    │              utils + state + audit       │
    └──────────────────┬──────────────────────┘
                       │
                  ┌────┴────┐
                  │builtin  │
                  └─────────┘
```

## Execution Flow

1. **Input** — User runs `sdlc run "description"` or calls `SdlcClient.run()`
2. **Entry Detection** — `EntryDetector` classifies the input as feature, bug, hotfix, etc.
3. **Profile Resolution** — `ProfileRegistry.resolve()` maps entry kind to a workflow profile
4. **Pipeline Building** — `PipelineBuilder` assembles an ordered list of stages from the profile
5. **State Initialization** — `StateStore` creates a pipeline record with status `RUNNING`
6. **Stage Execution** — `StageRunner` executes stages sequentially:
   - Load stage definition from catalog
   - Dispatch to subagent via `SubagentPool`
   - Subagent calls LLM via `MultiLLMClient`
   - Record results in `StateStore` and `AuditLogger`
   - Evaluate gates via `GateEngine`
   - Check rules via `RuleEngine`
   - Track costs via `CostTracker`
7. **Completion** — Pipeline status updated to `COMPLETED`, `FAILED`, or `PAUSED`
8. **Audit** — All events emitted to JSONL log for traceability

## Data Persistence

- **SQLite** (`~/.sdlc/state.db`): Pipeline state, stage results, snapshots
- **JSONL** (`~/.sdlc/audit.jsonl`): Append-only audit trail
- **SQLite** (LLM cache): Response cache with TTL expiration
- **YAML** (`.sdlc/`): Project-level configuration and KB