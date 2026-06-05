# 04. 数据模型 (v1.0)

> SQLite schema + 文件 schema + 关系图

---

## 一、概览

| 存储 | 内容 | 格式 | 位置 |
|---|---|---|---|
| **SQLite** | 运行时状态 | 表 | `<project>/.sdlc/state.db` 或 `~/.sdlc/projects/<id>/state.db` |
| **JSONL** | 审计 | 追加 | `<project>/.sdlc/audit.log` |
| **JSON** | meta.json | 单文件 | `<project>/.sdlc/pipelines/<id>/meta.json` |
| **YAML** | 配置 / 规则 / Adapter | 文件 | 项目 + 全局 |
| **Markdown** | KB | 文件 | `<project>/doc/kb/` |
| **YAML** | KB rules | 文件 | `<project>/doc/kb/rules/*.yaml` |
| **Mermaid** | KB arch | 内嵌 md | `<project>/doc/kb/architecture/*.md` |

---

## 二、SQLite Schema（6 表）

### 2.1 ER 图

```
pipelines (1) ──< (N) stages
   │                  │
   │                  │
   ├──< (N) artifacts ─┤
   │                  │
   ├──< (N) llm_calls ┤
   │                  │
   ├──< (N) kb_deltas ┤
   │                  │
   └─── audit_log_meta (1)
```

### 2.2 DDL（详见 03-module-design.md §12.3）

- `pipelines`：pipeline 主表
- `stages`：每个 stage 一次执行
- `artifacts`：stage 产出
- `llm_calls`：所有 LLM 调用记录（成本可观测）
- `kb_deltas`：KB 写入历史（用于回滚/审计）
- `audit_log_meta`：指向 JSONL 审计 + 计数器

### 2.3 索引

```sql
CREATE INDEX idx_pipelines_status ON pipelines(status);
CREATE INDEX idx_pipelines_created ON pipelines(created_at DESC);
CREATE INDEX idx_stages_pipeline ON stages(pipeline_id);
CREATE INDEX idx_artifacts_pipeline ON artifacts(pipeline_id);
CREATE INDEX idx_artifacts_stage ON artifacts(stage_id);
CREATE INDEX idx_llm_calls_pipeline ON llm_calls(pipeline_id);
CREATE INDEX idx_llm_calls_created ON llm_calls(created_at DESC);
CREATE INDEX idx_kb_deltas_fingerprint ON kb_deltas(fingerprint);
```

### 2.4 视图

```sql
-- pipeline 概览
CREATE VIEW v_pipeline_summary AS
SELECT p.id, p.status, p.entry_kind, p.profile_id,
       p.created_at, p.updated_at,
       (SELECT COUNT(*) FROM stages WHERE pipeline_id = p.id) AS stage_count,
       (SELECT COUNT(*) FROM stages WHERE pipeline_id = p.id AND status='SUCCESS') AS done_count,
       (SELECT COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE pipeline_id = p.id) AS total_cost
FROM pipelines p;

-- 成本按日聚合
CREATE VIEW v_cost_daily AS
SELECT DATE(created_at) AS day,
       model,
       COUNT(*) AS calls,
       SUM(input_tokens) AS in_tok,
       SUM(output_tokens) AS out_tok,
       SUM(cost_usd) AS cost
FROM llm_calls
GROUP BY DATE(created_at), model;
```

---

## 三、meta.json schema

每个 pipeline 一个目录，存 meta.json（**唯一事实源**之一，与 SQLite 对账）。

```json
{
  "schema_version": "1.0",
  "id": "feat-2026-06-05-001",
  "entry": {
    "kind": "feature",
    "raw_input": "做一个订单查询接口",
    "attachments": [],
    "detected_at": "2026-06-05T10:00:00Z",
    "confidence": 0.95
  },
  "profile": {
    "id": "new-feature",
    "resolved_at": "2026-06-05T10:00:01Z",
    "context": { "severity": "P2", "domain": "backend" }
  },
  "adapters": [
    {
      "id": "dongboot",
      "version": "1.0",
      "detected": true,
      "matched_patterns": ["pom.xml:com.jd.*", "dongboot-starter"]
    }
  ],
  "pipeline": {
    "stages": [
      {
        "id": "s-clarify",
        "def_id": "s-clarify",
        "depends_on": [],
        "artifacts_in": [],
        "artifacts_out": ["prd.md"]
      },
      {
        "id": "s-design",
        "def_id": "s-design",
        "depends_on": ["s-clarify"],
        "artifacts_in": ["prd.md"],
        "artifacts_out": ["arch.md", "interfaces.yaml"]
      }
    ],
    "gates": [
      {
        "after": "s-clarify",
        "trigger": "always",
        "reviewer": "PM",
        "deadline_hours": 4
      }
    ]
  },
  "state": {
    "status": "running",
    "current_stage": "s-impl-backend",
    "completed_stages": ["s-clarify", "s-design", "s-impl-backend", ...],
    "paused_at": null
  },
  "cost": {
    "total_usd": 0.42,
    "by_model": {
      "claude-opus-4-7": 0.32,
      "claude-sonnet-4-6": 0.10
    }
  },
  "kb_updates": [
    {
      "stage": "s-impl-backend",
      "target": "doc/kb/architecture/component-catalog.md",
      "operation": "append",
      "delta_hash": "sha256:abc...",
      "at": "2026-06-05T10:30:00Z"
    }
  ],
  "context_snapshot": {
    "git_sha": "abc1234",
    "kb_fingerprint": "sha256:xyz...",
    "rules_snapshot_hash": "sha256:def..."
  },
  "resume": {
    "token": "uuid-or-jwt",
    "expires_at": "2026-06-05T22:00:00Z"
  },
  "created_at": "2026-06-05T10:00:00Z",
  "updated_at": "2026-06-05T10:30:00Z"
}
```

---

## 四、audit.log schema（JSONL）

每行一个 JSON 对象：

```json
{"ts":"2026-06-05T10:00:00.123Z","type":"pipeline_start","payload":{"id":"feat-...","entry":"做一个订单查询接口","profile":"new-feature"}}
{"ts":"2026-06-05T10:00:01.456Z","type":"entry_detected","payload":{"id":"feat-...","kind":"feature","confidence":0.95}}
{"ts":"2026-06-05T10:00:02.789Z","type":"adapter_detected","payload":{"adapters":["dongboot"]}}
{"ts":"2026-06-05T10:00:05.012Z","type":"pipeline_built","payload":{"stage_count":7,"gate_count":3}}
{"ts":"2026-06-05T10:00:10.345Z","type":"stage_start","payload":{"stage":"s-clarify","subagent":"SA-1"}}
{"ts":"2026-06-05T10:01:30.678Z","type":"llm_called","payload":{"model":"claude-opus-4-7","in_tok":1200,"out_tok":850,"cost":0.045,"duration_ms":2300}}
{"ts":"2026-06-05T10:02:00.901Z","type":"subagent_invoked","payload":{"agent":"SA-1","stage":"s-clarify","iter":1}}
{"ts":"2026-06-05T10:03:00.234Z","type":"artifact_created","payload":{"stage":"s-clarify","type":"doc","path":"feat-.../artifacts/prd.md","hash":"sha256:..."}}
{"ts":"2026-06-05T10:03:01.567Z","type":"kb_updated","payload":{"stage":"s-clarify","target":"doc/kb/architecture/context-map.md","op":"append","delta_hash":"sha256:..."}}
{"ts":"2026-06-05T10:03:30.890Z","type":"stage_end","payload":{"stage":"s-clarify","status":"success","duration_ms":210}}
{"ts":"2026-06-05T10:03:31.123Z","type":"gate_triggered","payload":{"after":"s-clarify","gate":"G1","decision":"manual_review","reviewer":"PM","deadline":"2026-06-05T14:00:00Z"}}
```

**25+ 事件类型**：见 03-module-design.md §11.2。

---

## 五、KB 文件 Schema

### 5.1 doc/kb/ 主目录 11 文件

| 文件 | 类型 | Schema |
|---|---|---|
| `conventions.md` | Markdown | 自由格式，人工维护 |
| `glossary.md` | Markdown | 表格：术语 / 定义 / 出处 |
| `tech-stack.md` | Markdown | 表格：技术 / 版本 / 用途 / 责任人 |
| `dependencies.md` | Markdown | 表格：依赖 / 版本 / 用途 / 风险 |
| `commands.md` | Markdown | 表格：命令 / 用途 / 示例 |
| `api-catalog.md` | Markdown | 接口列表 + 责任人 |
| `data-catalog.md` | Markdown | 表 / 字段 / 生命周期 |
| `runbook.md` | Markdown | 故障 → 排查步骤 |
| `lessons-learned.md` | Markdown | 时间 / 问题 / 根因 / 修复 / 启示 |
| `patterns.md` | Markdown | 模式 / 示例代码 / 适用场景 |
| `antipatterns.md` | Markdown | 反模式 / 后果 / 正确做法 |

### 5.2 子目录 3 类

**doc/kb/rules/**
- `MUST.yaml` — MUST 强约束
- `SHOULD.yaml` — SHOULD 推荐
- `MAY.yaml` — MAY 可选
- `enforcer.yaml` — enforcer 配置
- `exceptions/active.yaml` — 当前生效豁免
- `custom/*.yaml` — 自定义规则

**doc/kb/standards/**（10 个流程规范 Markdown）
- `coding-style.md`, `git-workflow.md`, `review-process.md`, `testing.md`, `security.md`, `release.md`, `oncall.md`, `observability.md`, `doc.md`, `incident.md`

**doc/kb/architecture/**（10 个架构 Markdown + Mermaid）
- `context-map.md`, `component-catalog.md`, `dependency-graph.md`, `data-flow.md`, `tech-radar.md`, `api-style.md`, `schema-evolution.md`, `non-functional.md`, `threats.md`, `adr/`

### 5.3 MUST.yaml Schema

```yaml
- id: dongboot-hot-deploy-only-in-dev
  level: MUST
  category: deployment
  description: |
    hot_deploy 仅允许在 dev/staging 环境。
    pre 强制 image_deploy，prod 强制人工 review。
  enforcer: cr  # cr | lint | ci | runtime
  scope:
    stages: [s-deploy]
    adapters: [dongboot]
  detection:
    type: file_check
    paths: [".sdlc/state.db"]
    query: "SELECT environment FROM active_deploy WHERE type='hot_deploy'"
  action: block  # block | warn
  message: "hot_deploy not allowed in {environment}"
  exceptions: []
  references:
    - prd/12-implementation-roadmap.md#p1
```

### 5.4 enforcer.yaml Schema

```yaml
enforcers:
  cr:
    type: code_review
    config:
      cr_template: .sdlc/templates/cr.md
      min_reviewers: 1
      require_p1_approval: true
  lint:
    type: static_lint
    config:
      tools: [ruff, mypy, eslint]
      fail_on: error
  ci:
    type: pipeline
    config:
      workflows: [.github/workflows/test.yml]
      required_status: success
  runtime:
    type: pre_action
    config:
      timeout: 30
```

---

## 六、Stage YAML Schema

```yaml
id: s-clarify
name: 需求澄清
category: requirement
description: |
  通过与用户多轮对话，澄清需求边界与验收标准。
subagent: SA-1
model: claude-opus-4-7
required_artifacts: []
produces_artifacts:
  - prd.md
pre_kb_load:
  - conventions.md
  - glossary.md
post_kb_update:
  - target: architecture/context-map.md
    op: append
    template: |
      ## {{ stage_id }} ({{ ts }})
      - 需求：{{ input }}
      - 关键决策：{{ decisions }}
gates:
  - after: always
    reviewer: PM
    deadline_hours: 4
timeout: 1800  # 30min
retry:
  max: 2
  backoff: exponential
```

---

## 七、Adapter YAML Schema

```yaml
id: dongboot
name: DongBoot 企业微服务框架
version: 1.0
detect_patterns:
  - glob: "**/pom.xml"
    contains: "<artifactId>dong-boot-starter"
  - glob: "**/application.yml"
    contains: "dongboot"
components:
  - id: dong-log
    type: logging
    detect: "BizLogger"
    enforce: true
  - id: dong-thread
    type: threadpool
    detect: "DongThread"
    enforce: true
  - id: dong-dal
    type: db
    detect: "DongDAL"
    enforce: true
  # ... 共 18
enforce_rules: true
rule_sets:
  - dongboot-must
  - jd-coding-must
required_kb:
  - rules/MUST.yaml
  - standards/coding-style.md
  - architecture/component-catalog.md
```

---

## 八、Profile YAML Schema

```yaml
id: new-feature
name: 新功能
entry_kinds: [feature, idea]
base_stages:
  - s-clarify
  - s-design
  - s-impl-backend
  - s-impl-frontend
  - s-unit-test
  - s-cr
  - s-package
  - s-deploy
  - s-monitor-setup
skip_stages: []
extra_stages:
  - s-docs
gates:
  - after: s-clarify
    trigger: always
    reviewer: PM
  - after: s-cr
    trigger: on_severity
    severities: [P0, P1]
    reviewer: TL
severity: P2
subagent_overrides: {}
```

---

## 九、Subagent 注册表 schema

```yaml
# ~/.sdlc/agents/agents.yaml
subagents:
  - id: SA-1
    name: requirements-analyst
    role: requirements-analyst
    model: claude-opus-4-7
    tools: [read, write, ask_user]
    kb_inject:
      - conventions.md
      - glossary.md
    prompt_file: prompts/sa-1-requirements-analyst.md
    max_iter: 5

  - id: SA-2
    name: architect
    role: architect
    model: claude-opus-4-7
    tools: [read, write, skill, mcp]
    kb_inject:
      - architecture/component-catalog.md
      - architecture/dependency-graph.md
      - architecture/tech-radar.md
      - standards/coding-style.md
    prompt_file: prompts/sa-2-architect.md
    max_iter: 8

  # ... 共 11 个 SA-1 ~ SA-11
```

---

## 十、对账与一致性

### 10.1 meta.json vs SQLite

每 stage 完成后：
1. 更新 SQLite（state stage status）
2. 更新 meta.json
3. 比较关键字段（status, completed_stages, cost, kb_updates）
4. 不一致 → 审计告警 + 人工介入

### 10.2 meta.json vs audit.log

- 审计日志不可变
- meta.json 反映最新快照
- 校验：`audit.log` 最后事件 ts ≈ meta.json `updated_at`

### 10.3 KB 文件 vs fingerprint

- 每个 KB 文件有 fingerprint（hash）
- stage 开始时记录 `kb_fingerprint_before`
- 完成后记录 `kb_fingerprint_after`
- KB deltas 表存每次 delta 的 hash
- 重复 delta 自动去重

---

## 十一、配置 Schema（sdlc config）

```toml
# ~/.sdlc/config.toml
[llm]
provider = "anthropic"  # anthropic|openai
primary_model = "claude-opus-4-7"
fallback_model = "gpt-4o"
api_key_env = "ANTHROPIC_API_KEY"
timeout_seconds = 60
max_retries = 3

[cache]
enabled = true
backend = "sqlite"  # sqlite|redis
ttl_seconds = 86400  # 24h
max_size_mb = 500

[state]
db_path = "~/.sdlc/state.db"
backup_enabled = true
backup_interval_hours = 24

[audit]
log_path = "~/.sdlc/audit.log"
max_size_mb = 100
rotation = "size"  # size|time

[kb]
auto_update = true
fingerprint_check = true
batch_writes = true
batch_window_seconds = 30
rollback_window_hours = 24

[security]
shell_whitelist_strict = true
path_validation_strict = true
encrypt_secrets = true

[ui]
color = "auto"  # auto|always|never
progress = true
verbosity = 1  # 0..3
```

---

## 十二、版本

- v1.0 (2026-06-05): 初版
