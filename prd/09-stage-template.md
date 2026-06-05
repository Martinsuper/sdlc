# 09. Stage 模板 (v2.0)

> **新增一个 Stage = 写一份 YAML 注册到 `~/.claude/stages/`，无需改主流程**  
> 模板保证一致性

---

## 一、Stage 注册目录

```
~/.claude/
  stages/                       # Stage 库
    01-requirement/
      clarify.yaml
      impact-analysis.yaml
    02-design/
      design.yaml
      adr.yaml
    03-implement/
      implement-backend.yaml
      implement-frontend.yaml
      implement-mobile.yaml
      implement-infra.yaml
    04-test/
      unit-test.yaml
      integration-test.yaml
      regression.yaml
      e2e-test.yaml
    05-review/
      cr.yaml
      security-scan.yaml
    06-deploy/
      package.yaml
      deploy.yaml
    07-operate/
      monitor-setup.yaml
      incident-response.yaml
    08-maintain/
      refactor.yaml
      docs-update.yaml
      migration.yaml
      rollback.yaml
  prompts/                      # Subagent prompt 模板
    requirements-analyst.md
    architect.md
    coder-backend.md
    ...
```

---

## 二、Stage 模板（YAML）

```yaml
# ============================================
# Stage 模板 - 复制此文件并修改
# ============================================

# 必填
id: <kebab-case-id>              # 全局唯一，如 "implement-grpc-server"
name: <中文/英文名>                # "实现 gRPC 服务"
category: <requirement|design|implement|test|review|deploy|operate|maintain>
description: |
  <一句话说明本 Stage 做什么>

# 必填：默认 Subagent
default_subagent: <subagent-id>  # 如 coder-backend

# 选填：Subagent 可选列表（用户/Profile 可选）
subagent_candidates: [<subagent-id>, ...]

# 必填：输入
inputs:
  - artifact_type: <type>
    required: <true|false>
    source_stage: <stage_id>?
    description: |
      <这个输入是什么>

# 必填：输出
outputs:
  - artifact_type: <type>
    format: <markdown|json|yaml|code|sql|...>
    required: <true|false>
    description: |
      <这个输出是什么>

# 选填：依赖的前置 stage
dependencies:
  - <stage_id>                   # 本 stage 必在它们之后

# 选填：Gate
gate:
  trigger: <always|on_severity|on_artifact_missing|on_artifact_contains|manual|never>
  severity_threshold: <P0|P1|P2|P3|P4>?
  artifact_contains: <regex>?
  sla_hours: <int>
  approvers:
    - role: <pm|ba|architect|tl|sre|qa|security|legal|compliance|oncall>
      min_count: <int>
      optional: <true|false>
  checklist:
    - id: <item-id>
      question: <text>
      blocking: <true|false>
      default: <yes|no|n/a>?
      hint: <text>?

# 选填：估算
estimated_minutes: <int>        # 默认 30
estimated_cost_usd: <float>     # 默认 0.2

# 选填：Subagent prompt 模板路径
prompt_template: prompts/<file>.md

# 选填：输入校验
input_validation:
  - artifact_type: <type>
    min_count: <int>?
    schema: <json-schema-or-yaml>?

# 选填：输出校验
output_validation:
  - artifact_type: <type>
    schema: <json-schema-or-yaml>?
    must_contain_keywords: [string]?
    must_not_contain_keywords: [string]?

# 选填：执行前后动作
pre_actions:
  - kind: <mcp|skill|shell|http>
    spec: <map>
    required: <true|false>
    timeout_seconds: <int>?
post_actions:
  - kind: <mcp|skill|shell|http>
    spec: <map>
    required: <true|false>
    on_failure: <warn|fail|skip>

# v2.1 新增：KB 加载与更新
pre_kb_load:                    # 启动前自动加载到 Subagent 上下文
  - doc/kb/rules/MUST.yaml
  - doc/kb/standards/coding-style.md
  - doc/kb/architecture/component-catalog.md
post_kb_update:                 # 完成后自动更新 KB
  files:
    - doc/kb/components.md
    - doc/kb/patterns.md
  additions: [components, patterns, antipatterns]
  auto_generated: true

# 选填：Adapter 特定配置
adapter_specific:
  - adapter_id: <id>
    config: <map>
    override: <map>              # 覆盖默认字段
```

---

## 三、模板示例

### 3.1 `clarify` Stage

```yaml
id: clarify
name: 需求澄清
category: requirement
description: |
  从用户模糊输入中提取结构化需求（PRD/用户故事/验收标准/风险）。
default_subagent: requirements-analyst
subagent_candidates: [requirements-analyst, architect]

inputs:
  - artifact_type: idea
    required: false
    description: 用户原始输入
  - artifact_type: prd
    required: false
    description: 已有的 PRD（若有则验证完整性）
  - artifact_type: repo_context
    required: true
    source: auto
    description: 工程上下文（自动扫描）

outputs:
  - artifact_type: prd
    format: markdown
    required: true
  - artifact_type: user_story
    format: markdown
    required: true
  - artifact_type: acceptance
    format: markdown
    required: true
  - artifact_type: risk_register
    format: markdown
    required: false

dependencies: []

gate:
  trigger: always
  sla_hours: 4
  approvers:
    - role: pm
      min_count: 1
    - role: ba
      min_count: 1
      optional: true
  checklist:
    - id: dor
      question: DoR（Definition of Ready）已就位？
      blocking: true
    - id: scope
      question: 范围边界已明确？
      blocking: true

estimated_minutes: 15
estimated_cost_usd: 0.10

prompt_template: prompts/requirements-analyst.md

output_validation:
  - artifact_type: prd
    must_contain_keywords: [背景, 用户故事, 验收标准, 范围]
  - artifact_type: user_story
    must_contain_keywords: [As a, I want, so that]

pre_actions:
  - kind: mcp
    spec:
      tool: repo_context.scanner
      args: { include: [package_files, readme, configs] }
    required: false
post_actions:
  - kind: skill
    spec:
      skill: DongLog
      when: prd_mentions_business_logic
    required: false
```

### 3.2 `implement-backend` Stage

```yaml
id: implement-backend
name: 后端编码
category: implement
description: |
  根据设计文档实现后端业务逻辑、API、DB Schema 变更。
default_subagent: coder-backend
subagent_candidates: [coder-backend, coder-jvm-dongboot, coder-python-flask, coder-go-gin, coder-nodejs]

inputs:
  - artifact_type: design_doc
    required: true
  - artifact_type: api_contract
    required: true
  - artifact_type: db_schema
    required: false
  - artifact_type: sequence_diagram
    required: false
  - artifact_type: adr
    required: false
  - artifact_type: repo_context
    required: true
    source: auto

outputs:
  - artifact_type: code
    format: code
    required: true
  - artifact_type: db_schema_diff
    format: sql
    required: false
  - artifact_type: dongboot_anchors
    format: yaml
    required: false

dependencies: [design]

gate:
  trigger: never

estimated_minutes: 90
estimated_cost_usd: 0.50

prompt_template: prompts/coder-backend.md

output_validation:
  - artifact_type: code
    must_contain_keywords: [@sdlc-feature, @sdlc-stage, @sdlc-requirement, @sdlc-generated-by, @sdlc-timestamp]
    must_not_contain_keywords: [TODO, FIXME, System.out.println, print(]
  - artifact_type: db_schema_diff
    must_contain_keywords: [CREATE TABLE, ALTER TABLE]

post_actions:
  - kind: mcp
    spec:
      tool: dongboot_analyzer.check_dongboot_status
    required: false
    on_failure: warn
  - kind: skill
    spec:
      skill: MultiSkillCoordination
    required: false
    on_failure: warn

adapter_specific:
  - adapter_id: dongboot
    subagent: coder-jvm-dongboot
    extra_outputs: [dongboot_anchors, donglog_audit]
  - adapter_id: spring-boot
    subagent: coder-jvm-spring
  - adapter_id: python-flask
    subagent: coder-python-flask
  - adapter_id: go-gin
    subagent: coder-go-gin
```

### 3.3 `cr` Stage

```yaml
id: cr
name: Code Review
category: review
description: |
  评审代码质量、设计一致、安全、性能、可观测性。
default_subagent: reviewer
subagent_candidates: [reviewer, reviewer-jvm-dongboot]

inputs:
  - artifact_type: code
    required: true
  - artifact_type: db_schema_diff
    required: false
  - artifact_type: design_doc
    required: true

outputs:
  - artifact_type: review_report
    format: markdown
    required: true

dependencies: [implement-backend, implement-frontend, implement-mobile, implement-infra]

gate:
  trigger: on_severity
  severity_threshold: P1
  sla_hours: 4
  approvers:
    - role: tl
      min_count: 1

estimated_minutes: 30
estimated_cost_usd: 0.30

prompt_template: prompts/reviewer.md

output_validation:
  - artifact_type: review_report
    must_contain_keywords: [严重度, P0, P1, 修改建议, 通过/不通过]
```

### 3.4 `monitor-setup` Stage

```yaml
id: monitor-setup
name: 监控/告警/Runbook
category: operate
description: |
  配置黄金信号、业务指标、告警阈值、Runbook、SLO。
default_subagent: sre-writer
subagent_candidates: [sre-writer, sre-writer-jvm-dongboot]

inputs:
  - artifact_type: deploy_record
    required: true
  - artifact_type: api_contract
    required: true
  - artifact_type: slo
    required: false

outputs:
  - artifact_type: dashboard
    format: json
    required: true
  - artifact_type: alert
    format: yaml
    required: true
  - artifact_type: runbook
    format: markdown
    required: true
  - artifact_type: slo
    format: yaml
    required: true
  - artifact_type: metric_definition
    format: yaml
    required: true

dependencies: [deploy]

gate:
  trigger: always
  sla_hours: 4
  approvers:
    - role: sre
      min_count: 1
    - role: qa
      min_count: 1
      optional: true

estimated_minutes: 45
estimated_cost_usd: 0.40

prompt_template: prompts/sre-writer.md

post_actions:
  - kind: skill
    spec:
      skill: DongMonitorDashboard
      when: adapter == dongboot
    required: false
```

---

## 四、Subagent Prompt 模板

每个 Subagent 对应一份 prompt 模板，引用 Stage 元数据。

### 4.1 prompt 模板（`prompts/requirements-analyst.md`）

```markdown
# Requirements Analyst

你是 SDLC 系统的需求分析师 Subagent。
工作：根据用户输入与工程上下文，产出结构化 PRD/用户故事/验收标准/风险。

## 输入
- 用户输入：{{user_input}}
- 工程上下文：{{repo_context}}
- 已有 PRD：{{existing_prd}}（可空）

## 输出要求
1. **PRD**（必出）含：
   - 背景与目标
   - 用户故事（至少 1 条）
   - 功能需求（Must/Should/Could/Won't）
   - 非功能需求
   - 验收标准（Given/When/Then）
   - 风险与依赖
   - 范围边界

2. **用户故事**（必出）格式：As a [角色] / I want [需求] / So that [价值]

3. **验收标准**（必出）格式：Given/When/Then

4. **风险登记**（必出）含：风险描述、影响、概率、缓解

## 必须遵守
- 锚点注释（按 Adapter）
- 引用现有代码（用文件路径+行号）
- 不确定的地方明确写"待确认"而非臆测
- 调用 Skill `DongLog` 在涉及业务逻辑时
```

### 4.2 prompt 模板（`prompts/coder-backend.md`）

```markdown
# Backend Coder

你是 SDLC 系统的后端编码 Subagent。
工作：根据设计文档/API 契约/DB Schema 实现后端代码。

## 输入
- 设计文档：{{design_doc}}
- API 契约：{{api_contract}}
- DB Schema：{{db_schema}}
- 现有代码：{{repo_context}}

## 输出要求
1. **代码**（必出）：
   - 业务方法 + 单元测试骨架
   - 锚点注释（按 Adapter）
   - 错误码规范
   - 日志埋点（按 adapter 推荐）
   - 必用 adapter 推荐组件（cache/http/lock/log/threadpool/db）

2. **DB Schema Diff**（若涉及 schema 变更）：
   - Flyway/Liquibase 格式
   - 含前向/回滚脚本

3. **DongBoot 锚点**（若 adapter=dongboot）

## 必须遵守
- 任何线程池/异步/数据库/缓存/锁/分布式/internal-rpc 调用 → 触发 `MultiSkillCoordination` 协同
- 业务方法 → 必用 DongLog/BizLogger
- 错误处理 → Result 模型 / 异常 + BizLogger
- 测试骨架 → mock + happy path + edge case
```

---

## 五、新增 Stage 流程

### 5.1 简单 Stage（仅配置）

```
1. 复制一份 yaml 模板
2. 改 id / name / category / description
3. 改 inputs / outputs / dependencies
4. （可选）配 gate
5. 保存到 ~/.claude/stages/{category}/{id}.yaml
6. 重新加载（CLI: `sdlc stage reload`）
7. 写 contract test（在 ~/.claude/stages/{category}/tests/）
```

### 5.2 复杂 Stage（带自定义 Subagent）

```
1. 写 stage yaml（同上）
2. 写 prompt 模板 prompts/{subagent}.md
3. 在 subagent 池中注册 subagent（通过 skills.yaml 或编程方式）
4. 写 contract test
5. 端到端测试：选一个真实需求跑全流程
```

### 5.3 测试 contract

```python
# ~/.claude/stages/03-implement/tests/implement-backend_test.py
def test_inputs():
    stage = load_stage("implement-backend")
    assert "design_doc" in [i.artifact_type for i in stage.inputs if i.required]

def test_outputs():
    stage = load_stage("implement-backend")
    assert "code" in [o.artifact_type for o in stage.outputs if o.required]

def test_gate():
    stage = load_stage("implement-backend")
    assert stage.gate.trigger == "never"

def test_adapter_override():
    stage = load_stage("implement-backend")
    overrides = {a.adapter_id: a for a in stage.adapter_specific}
    assert "dongboot" in overrides
    assert overrides["dongboot"].subagent == "coder-jvm-dongboot"
```

---

## 六、Stage 库版本管理

```yaml
# ~/.claude/stages/VERSION
schema_version: "2.0"
stages_version: "2.0.1"
released_at: 2026-06-05
breaking_changes: []
```

升级时：
- 增量更新：老 stage 保留，新 stage 加 `--version=experimental` 标识
- 灰度：通过 Profile 选 version
- 回滚：切换回老 version

---

## 七、版本

- v2.0 (2026-06-05): Stage 模板与注册机制
- v2.1 (2026-06-05): 新增 `pre_kb_load` + `post_kb_update` 字段
- v2.2 (2026-06-05): pre_kb_load 支持 `rules/` `standards/` `architecture/` 三类 KB
