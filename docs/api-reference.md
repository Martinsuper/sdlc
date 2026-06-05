# API Reference

Auto-generated documentation from source docstrings.

## Python API

### SdlcClient

::: sdlc.client.SdlcClient
    options:
      show_root_heading: true
      show_source: true
      members: true

## CLI Commands

### Core Flow

| Command | Description |
|---------|-------------|
| `sdlc init` | Initialize a project with KB scan and adapter detection |
| `sdlc run` | Execute a pipeline with natural language input |
| `sdlc status` | Query pipeline status |
| `sdlc resume` | Resume a paused or failed pipeline |
| `sdlc stage` | Manage pipeline stages |

### Auxiliary

| Command | Description |
|---------|-------------|
| `sdlc adapter` | List and detect technology adapters |
| `sdlc profile` | List workflow profiles |
| `sdlc kb` | Manage the knowledge base |
| `sdlc rule` | List, check, enable, and disable rules |
| `sdlc agent` | List subagents |
| `sdlc config` | View and modify configuration |
| `sdlc doctor` | Run environment diagnostics |

### Management

| Command | Description |
|---------|-------------|
| `sdlc export` | Export pipeline data |
| `sdlc import` | Import pipeline data |
| `sdlc replay` | Replay a pipeline |
| `sdlc trace` | Trace pipeline execution |
| `sdlc stats` | Show usage statistics |
| `sdlc version` | Show version information |
| `sdlc completion` | Generate shell completion script |

## Core Modules

### Entry Detector

::: sdlc.core.entry_detector
    options:
      show_root_heading: true
      show_source: true

### Pipeline Builder

::: sdlc.core.pipeline_builder
    options:
      show_root_heading: true
      show_source: true

### Run Coordinator

::: sdlc.core.run_coordinator
    options:
      show_root_heading: true
      show_source: true

## Adapter System

### Base Adapter

::: sdlc.adapter.models
    options:
      show_root_heading: true
      show_source: true

### Adapter Registry

::: sdlc.adapter.registry
    options:
      show_root_heading: true
      show_source: true

### Adapter Detector

::: sdlc.adapter.detector
    options:
      show_root_heading: true
      show_source: true

## Rule Engine

### Rule Models

::: sdlc.rule.models
    options:
      show_root_heading: true
      show_source: true

### Rule Engine

::: sdlc.rule.engine
    options:
      show_root_heading: true
      show_source: true

### Rule Enforcer

::: sdlc.rule.enforcer
    options:
      show_root_heading: true
      show_source: true

## Quality Gates

### Gate Engine

::: sdlc.gate.engine
    options:
      show_root_heading: true
      show_source: true

### Gate Models

::: sdlc.gate.models
    options:
      show_root_heading: true
      show_source: true

## LLM Integration

### LLM Client

::: sdlc.llm.client
    options:
      show_root_heading: true
      show_source: true

### Cost Tracker

::: sdlc.llm.cost
    options:
      show_root_heading: true
      show_source: true

## Knowledge Base

### KB Scanner

::: sdlc.kb.scanner
    options:
      show_root_heading: true
      show_source: true

### Knowledge Base

::: sdlc.kb.knowledge_base
    options:
      show_root_heading: true
      show_source: true

## State Management

### State Store

::: sdlc.state.store
    options:
      show_root_heading: true
      show_source: true

## Audit Trail

### Audit Logger

::: sdlc.audit.logger
    options:
      show_root_heading: true
      show_source: true

## Subagents

### Subagent Pool

::: sdlc.subagent.pool
    options:
      show_root_heading: true
      show_source: true
