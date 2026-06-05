# 01. 核心概念 (v2.0)

> 7 抽象层是 SDLC 系统一切能力的来源：**Stage / Artifact / Gate / Pipeline / EntryPoint / Adapter / Profile**  
> 本文档定义这 7 抽象的 Schema、关系与最小可执行示例。

---

## 一、7 抽象总览

```
                        ┌──────────────┐
                        │   Profile    │   "什么类型的项目"
                        └──────┬───────┘
                               │ 影响
                               ↓
┌──────────┐    触发      ┌──────────────┐
│EntryPoint│────────────→│  Pipeline    │   "按什么顺序跑"
└──────────┘             └──────┬───────┘
                               │ 由 … 组成
                               ↓
                        ┌──────────────┐
                   ┌───→│    Stage     │   "原子工作单元"
                   │    └──────┬───────┘
                   │           │ 产生 / 消费
                   │           ↓
                   │    ┌──────────────┐
                   └───│   Artifact   │   "产物/中间品"
                        └──────┬───────┘
                               │ 触发
                               ↓
                        ┌──────────────┐
                        │     Gate     │   "人工把关"
                        └──────────────┘

   横向：
   ┌──────────────┐                    ┌──────────────┐
   │   Adapter    │←─── 装备给 ───────→│  Subagent    │
   └──────────────┘   Stage/Profile    └──────────────┘
```

---

## 二、Stage（阶段 / 原子工作单元）

> **一个 Stage = 一次 Subagent 调度 + 一份输入 → 一份输出 + 一道 Gate（可选）**

### 2.1 Schema

```yaml
id: string                      # 唯一标识，kebab-case
name: string                    # 中文/英文展示名
description: string             # 一句话说明
category: enum                  # requirement | design | implement | test | review | deploy | operate | maintain
default_subagent: string        # 默认调度哪个 Subagent
subagent_override: string?     # 用户/Profile 可临时覆盖

inputs:                         # 入参 Artifact 类型列表
  - artifact_type: string       # 如 prd, design_doc, code
    required: bool
    source_stage: string?       # 从哪个 stage 取（可省略，由 Builder 自动接）

outputs:                        # 出参 Artifact 类型列表
  - artifact_type: string
    format: enum                # markdown | json | yaml | code | sql | ...

gate:                           # 是否需要人工 Gate
  trigger: enum                 # always | on_severity | on_artifact_missing | never | manual
  severity_threshold: enum?     # P0 | P1 | P2
  sla_hours: int?               # 超时升级时间
  approvers: [string]?          # role 列表，如 ["pm", "architect"]

estimated_minutes: int          # 期望耗时（用于超时检测和资源估算）
estimated_cost_usd: float       # 期望成本（用于预算估算）

adapter_specific:               # Adapter 可覆盖的配置
  - adapter_id: string          # 如 "dongboot"
    config: map                 # adapter 特定的参数
```

### 2.2 最小示例

```yaml
# Stage: implement-backend
id: implement-backend
name: 后端编码
category: implement
default_subagent: coder-backend

inputs:
  - artifact_type: design_doc
    required: true
  - artifact_type: api_contract
    required: true

outputs:
  - artifact_type: code
    format: code
  - artifact_type: db_schema_diff
    format: sql

gate:
  trigger: never                # 编码不强制 Gate（CR 在后续 Stage）

estimated_minutes: 60
estimated_cost_usd: 0.30
```

### 2.3 Stage 库（18+ 详细见 02-stage-catalog.md）

| Category | Stage | 默认 Subagent | Gate |
|---|---|---|---|
| requirement | clarify | requirements-analyst | always |
| requirement | impact-analysis | architect | manual |
| design | design | architect | always |
| design | adr | architect | never |
| implement | implement-backend | coder-backend | never |
| implement | implement-frontend | coder-frontend | never |
| implement | implement-mobile | coder-mobile | never |
| implement | implement-infra | coder-infra | never |
| test | unit-test | tester-unit | never |
| test | integration-test | tester-integration | on_artifact_missing |
| test | regression | tester-regression | manual |
| review | cr | reviewer | on_severity(P1) |
| deploy | package | deployer | never |
| deploy | deploy | deployer | always |
| operate | monitor-setup | sre-writer | always |
| operate | runbook | sre-writer | never |
| maintain | refactor | architect | manual |
| maintain | docs-update | docs-writer | never |

---

## 三、Artifact（产物）

> 任何在 Pipeline 中产生、消费、归档的内容都是 Artifact

### 3.1 Schema

```yaml
type: string                    # 见 3.2 类型清单
id: string                      # uuid
feature_id: string              # 所属 feature
stage_id: string                # 由哪个 stage 产生
created_at: timestamp
created_by: subagent_id
hash: string                    # 内容 hash
format: enum                    # markdown | json | yaml | code | sql | image | binary
path: string                    # 相对路径
metadata: map                   # 类型特定的元数据
```

### 3.2 类型清单（18+）

| Type | 格式 | 产生于 | 消费于 |
|---|---|---|---|
| `idea` | md | 用户输入 / clarify | clarify, impact-analysis |
| `prd` | md | clarify | design, adr |
| `user_story` | md | clarify | design, test |
| `acceptance` | md | clarify | test, review |
| `impact_report` | md | impact-analysis | design, pm-gate |
| `design_doc` | md | design | implement-*, review |
| `adr` | md | design | implement-*, docs-update |
| `api_contract` | yaml/openapi | design | implement-backend, test |
| `db_schema` | sql | design | implement-backend, test |
| `sequence_diagram` | plantuml/mermaid | design | implement-*, review |
| `risk_register` | md | design | pm-gate, architect-gate |
| `code` | code（按语言） | implement-* | unit-test, review |
| `db_schema_diff` | sql | implement-* | review, deploy |
| `unit_test_report` | md | unit-test | review |
| `integration_test_report` | md | integration-test | review |
| `regression_report` | md | regression | deploy-gate, qa-gate |
| `review_report` | md | cr | tl-gate |
| `config` | yaml/json | design / implement-* | deploy |
| `deploy_manifest` | yaml | package | deploy, review |
| `deploy_record` | md | deploy | monitor-setup |
| `dashboard` | json/grafana | monitor-setup | operate |
| `alert` | yaml/prometheus | monitor-setup | operate |
| `runbook` | md | monitor-setup | operate |
| `slo` | yaml | monitor-setup | qa-gate |
| `incident` | md | operate / hotfix | post-mortem |
| `metric_definition` | yaml | monitor-setup | operate |
| `migration_plan` | md | refactor / migration | design, deploy |

### 3.3 存储

```
prd/
  {feature_id}/
    meta.json                    # 全局元数据
    audit.log                    # 审计日志（append-only）
    artifacts/                   # 所有 artifact
      01-clarify-20260605-prd.md
      02-design-20260605-design_doc.md
      03-impl-20260605-code-UserController.java
      ...
    snapshots/                   # 关键检查点（用于 resume）
      after-gate-1/
      after-gate-2/
```

---

## 四、Gate（人工把关点）

> Pipeline 默认自动跑全流程；Gate 是流程中**显式停下来等人工批准/补充/决策**的点

### 4.1 Schema

```yaml
id: string                      # gate-1-clarify, gate-2-design, ...
name: string
when:                           # 在哪个 stage 后
  after_stage: string
trigger: enum                   # 见 4.2
severity_threshold: enum?       # 仅 on_severity 模式
sla_hours: int
approvers: [role]               # 通过谁的角色放行
  - role: pm | ba | architect | tl | sre | qa | security
    min_count: int              # 至少几个
    optional: bool              # 是否可跳过

checklist:                      # 放行前的检查项
  - id: string
    question: string
    blocking: bool              # 必须勾才能放行

notifications:                  # 通知渠道
  - channel: feishu | email | slack | im
    on: pending | overdue | approved | rejected
```

### 4.2 触发模式

| 模式 | 说明 |
|---|---|
| `always` | 每个 feature 都必走 |
| `on_severity` | 当 artifact 严重度 ≥ 阈值时触发（如 P0/P1 必评审） |
| `on_artifact_missing` | 某些产出缺失时触发（如缺 test report） |
| `manual` | 由用户/Profile 显式指定 |
| `never` | 跳过（实际等同"无 Gate"） |

### 4.3 默认 4 Gate（v1.0 沿用，可配）

| Gate | 位置 | 角色 | SLA | 何时跳过 |
|---|---|---|---|---|
| Gate 1 | clarify 后 | PM / BA | 4h | hotfix / docs-only |
| Gate 2 | design 后 | 架构师 / TL | 8h | simple bug-fix / refactor |
| Gate 3 | cr 后 | TL | 4h | docs-only / test-only |
| Gate 4 | deploy + monitor 后 | SRE / QA | 4h | docs-only |

更多详见 [07-gate-catalog.md](./07-gate-catalog.md)。

---

## 五、Pipeline（流水线）

### 5.1 Schema

```yaml
id: string                      # "{entrypoint}-{profile}-{ts}"
entrypoint: string              # 见 EntryPoint
profile: string                 # 见 Profile
adapter: string                 # 见 Adapter

stages:                         # DAG 节点
  - stage_id: string
    instance_id: string         # 同 stage 可多次实例化
    inputs_override: [string]?
    outputs_override: [string]?
    enabled: bool               # 是否启用（false 跳过）
    gate_override: gate?

edges:                          # DAG 边（默认由 Builder 推）
  - from: instance_id
    to: instance_id
    on: success | failure | always

state: enum                     # draft | active | paused | completed | failed
state_history:                  # 状态机历史
  - state: enum
    at: timestamp
    reason: string

budget:
  max_minutes: int?
  max_cost_usd: float?
  max_retries_per_stage: int

created_at: timestamp
updated_at: timestamp
```

### 5.2 状态机

```
       ┌──────┐
       │draft│
       └──┬───┘
          │ start
          ↓
       ┌──────┐ ←─pause─ ┌──────┐
       │active│──────────→│paused│
       └──┬───┘           └──┬───┘
          │                  │ resume
          │                  ↓
          │              (active)
          │
   ┌──────┴──────┐
   ↓             ↓
┌────────┐  ┌────────┐
│complete│  │ failed │
└────────┘  └────────┘
```

### 5.3 最小示例（new-feature, java-dongboot）

```yaml
id: idea-newfeature-dongboot-20260605-001
entrypoint: idea
profile: new-feature
adapter: dongboot

stages:
  - instance_id: s-clarify
    stage_id: clarify
    enabled: true
  - instance_id: s-impact
    stage_id: impact-analysis
    enabled: false                # 简单功能跳过
  - instance_id: s-design
    stage_id: design
    enabled: true
  - instance_id: s-impl
    stage_id: implement-backend
    enabled: true
  - instance_id: s-unit
    stage_id: unit-test
    enabled: true
  - instance_id: s-cr
    stage_id: cr
    enabled: true
  - instance_id: s-pkg
    stage_id: package
    enabled: true
  - instance_id: s-deploy
    stage_id: deploy
    enabled: true
  - instance_id: s-mon
    stage_id: monitor-setup
    enabled: true

edges:
  - from: s-clarify
    to: s-design
  - from: s-design
    to: s-impl
  - from: s-impl
    to: s-unit
  - from: s-unit
    to: s-cr
  - from: s-cr
    to: s-pkg
  - from: s-pkg
    to: s-deploy
  - from: s-deploy
    to: s-mon

state: draft
budget:
  max_minutes: 1440             # 24h
  max_cost_usd: 5.0
```

---

## 六、EntryPoint（入口点）

> 回答"用户从哪个阶段进入"

### 6.1 Schema

```yaml
id: string                      # idea | prd | design | code | bug | refactor | test | review | deploy | monitor | doc | hotfix
name: string
detection_keywords: [string]    # 用于自动检测的正向关键词
detection_patterns:             # 用于结构化检测
  - kind: enum                  # file | url | branch | text | tag
    regex: string
example_user_inputs: [string]   # few-shot 提示
default_profile: string?        # 默认 Profile（可被用户覆盖）
default_stages: [string]?       # 必跑的 stage 集合（其余由 Profile 决定）
skip_stages: [string]?          # 必跳的 stage
```

### 6.2 12 种入口（详细见 03-entry-points.md）

| ID | 用户典型输入 | 默认 Profile | 必跑 Stage |
|---|---|---|---|
| `idea` | "我想做..." | new-feature | clarify → design → ... |
| `prd` | [贴 PRD] | new-feature | design → ... |
| `design` | [贴设计] | new-feature | design-validate → ... |
| `code` | [贴代码] | review-only | review → ... |
| `bug` | "有个 bug" | bug-fix | diagnose → fix → test → ... |
| `refactor` | "重构..." | refactor | impact-analysis → refactor → ... |
| `test` | "写测试" | test-only | test → review → ... |
| `review` | "评审..." | review-only | review |
| `deploy` | "部署..." | deploy-only | package → deploy |
| `monitor` | "加监控" | monitor-only | monitor-setup |
| `doc` | "写文档" | docs-only | docs-update |
| `hotfix` | "线上 P0" | hotfix | diagnose → fix → test → deploy → verify |

### 6.3 检测算法

```
detect_entrypoint(user_input, repo_context) → EntryPoint
  1. 关键词匹配
     - 含 "hotfix|紧急|线上 P0|故障" → hotfix
     - 含 "评审|review|CR" → review
     - 含 "重构|refactor" → refactor
     - 含 "监控|告警|dashboard" → monitor
     - 含 "PRD|需求文档" → prd
     - 含 "代码|code" 且有代码块 → code
     - 含 "bug|缺陷|故障"（非 hotfix） → bug
     - 含 "测试" → test
     - 含 "部署" → deploy
     - 含 "文档|README" → doc
     - 含 "设计|架构" → design
     - 兜底：含 "我想做|新增|添加" → idea
  2. 结构化检测
     - 贴入 OpenAPI/YAML → design
     - 贴入 git diff/branch → code
     - 贴入 PR link → review
  3. LLM 二次判定
     - 用 claude-sonnet 对输入分类，强制选 1 个 EntryPoint
  4. 模糊则询问用户
```

---

## 七、Adapter（技术栈适配器）

> 一切"只在某技术栈下有效"的能力，封装在 Adapter 中；主流程零技术栈知识

### 7.1 Schema

```yaml
id: string                      # dongboot | spring-boot | python-flask | node-express | ...
name: string
language: enum                  # java | go | python | node | ts | rust | kotlin | swift | ...
framework: string?

detection:                      # 在工程中检测本 adapter 是否适用
  file_globs: [string]          # 如 ["pom.xml:jd-dongboot*", "**/DongBootApplication.java"]
  package_patterns: [string]    # 如 ["com.jd.dongboot*"]
  import_patterns: [string]     # 如 ["import com.jd.dongboot"]

stages:                         # 覆盖默认 stage 行为
  - stage_id: string
    subagent: string?           # 用哪个 subagent
    prompt_template: string?    # prompt 模板路径
    extra_inputs: [artifact_type]?
    extra_outputs: [artifact_type]?
    post_actions:               # stage 跑完后做的事
      - kind: shell | http | mcp
        spec: map

components:                     # 强制 / 推荐使用的组件
  cache: dongcache | guava | caffeine | redis | memcached?
  http: donghttp | okhttp | feign | axios | requests | stdlib?
  lock: donglock | redlock | zookeeper | db_lock?
  log: donglog_biz | log4j | slf4j | loguru | pino?
  threadpool: dongthread | executors | asyncio | tokio?
  database: dongdal | jdbc | sqlalchemy | prisma | gorm?
  test: dongmock | junit | pytest | jest | go_test?

build:
  command: string?              # mvn package, npm run build, go build, ...
  artifact_pattern: string?     # target/*.jar, dist/*.js, bin/*
test:
  command: string?              # mvn test, pytest, npm test, go test, ...
deploy:
  command: string?              # mvn deploy, kubectl apply, scp, ...
```

### 7.2 详细示例：DongBoot

```yaml
id: dongboot
name: 企业 DongBoot 框架
language: java
framework: Spring Boot (DongBoot 扩展)

detection:
  file_globs:
    - "**/pom.xml"
  package_patterns:
    - "com.jd.**.dongboot.*"
  import_patterns:
    - "com.jd.dongboot"

stages:
  - stage_id: implement-backend
    subagent: coder-jvm-dongboot
    extra_outputs: [db_schema_diff, dongboot_anchors]
    post_actions:
      - kind: mcp
        spec: { tool: dongboot_analyzer.check_dongboot_status }
      - kind: skill
        spec: { skill: MultiSkillCoordination }

components:
  cache: dongcache
  http: donghttp
  lock: donglock
  log: donglog_biz
  threadpool: dongthread
  database: dongdal
  test: dongmock
  sequence: dongsequence
  schedule: dongschedule

build:
  command: mvn -DskipTests package
  artifact_pattern: "target/*.jar"
test:
  command: mvn test
deploy:
  command: image_deploy_from_pod
```

### 7.3 内置 Adapter

| ID | 语言/框架 | 状态 |
|---|---|---|
| `dongboot` | Java / DongBoot | 完整 |
| `spring-boot` | Java / Spring Boot | 完整 |
| `python-flask` | Python / Flask | 完整 |
| `python-django` | Python / Django | 完整 |
| `node-express` | Node / Express | 完整 |
| `node-nest` | Node / NestJS | 完整 |
| `frontend-react` | TS / React | 完整 |
| `frontend-vue` | TS / Vue | 完整 |
| `go-gin` | Go / Gin | 完整 |
| `go-kratos` | Go / Kratos | 完整 |
| `mobile-android` | Kotlin / Android | 完整 |
| `mobile-ios` | Swift / iOS | 完整 |
| `infra-terraform` | HCL | 完整 |
| `data-spark` | Scala/PySpark | 完整 |
| `library-publish` | 任意 | 完整 |
| `no-tech` | 纯文档 / 纯配置 | 完整 |

详见 [05-adapters.md](./05-adapters.md)。

---

## 八、Profile（项目类型）

> 回答"这个任务属于哪类工作"，决定默认 Pipeline、默认 Gate、默认 Adapter

### 8.1 Schema

```yaml
id: string                      # new-feature | bug-fix | hotfix | refactor | migration | ...
name: string
description: string

default_stages: [string]        # 必跑 stage
optional_stages: [string]       # 可选 stage
skip_stages: [string]           # 必跳 stage
default_gates: [gate_id]        # 必走 Gate
max_budget_minutes: int
severity_default: enum          # 默认严重度（P0-P4）

risk_class: enum                # low | medium | high
rollback_required: bool
canary_required: bool
```

### 8.2 12 种 Profile

| ID | 必跑 Stage | 必走 Gate | 风险等级 |
|---|---|---|---|
| `new-feature` | clarify→design→impl→test→cr→deploy→monitor | 1, 2, 3, 4 | medium |
| `bug-fix` | diagnose→fix→test→cr→deploy | 2, 3 | low |
| `hotfix` | diagnose→fix→test→deploy→verify | 3 | high |
| `refactor` | impact→design→impl→test→cr→deploy | 2, 3 | medium |
| `migration` | impact→design→impl→test→cr→deploy→verify | 1, 2, 3, 4 | high |
| `performance` | diagnose→design→impl→test→cr→deploy→monitor | 2, 3, 4 | medium |
| `security` | diagnose→design→impl→test→cr→deploy→monitor | 1, 2, 3, 4 | high |
| `docs-only` | docs-update | none | low |
| `test-only` | test→cr | 3 | low |
| `review-only` | cr | none | low |
| `deploy-only` | package→deploy | 4 | medium |
| `monitor-only` | monitor-setup | 4 | low |
| `greenfield` | clarify→design→...→monitor 全套 | 1, 2, 3, 4 | high |
| `poc` | clarify→design→impl→test | none | low |

详见 [06-project-profiles.md](./06-project-profiles.md)。

---

## 九、7 抽象的协作关系

```
                    用户输入
                       ↓
              [EntryPoint Detection]
                       ↓ 选
                  EntryPoint
                       ↓
              [Profile Selection]
                       ↓ 选
                   Profile ──→ default_stages / default_gates
                       ↓
              [Adapter Detection]
                       ↓ 选
                    Adapter ──→ stage 行为 / 组件 / 构建
                       ↓
              [Pipeline Builder]
                       ↓ 构造
                   Pipeline (DAG of Stages)
                       ↓ 执行
              ┌────────┴────────┐
              ↓                 ↓
         [Subagent]  ←──装备──  [Adapter]
              ↓ 产生
          Artifact ──→ 触发
              ↓
            Gate (人工放行)
              ↓
         下一个 Stage ...
              ↓ 结束
         Audit Log / Resume Point
```

---

## 十、最小可执行 Schema 例子

```yaml
# 用户: "用 Java DongBoot 加个新接口：POST /api/orders"
# 自动检测结果:
entrypoint: idea
profile: new-feature
adapter: dongboot

# Pipeline Builder 输出:
pipeline:
  id: idea-newfeature-dongboot-20260605-001
  entrypoint: idea
  profile: new-feature
  adapter: dongboot
  stages:
    - {instance_id: s-clarify, stage_id: clarify, enabled: true}
    - {instance_id: s-design, stage_id: design, enabled: true}
    - {instance_id: s-impl, stage_id: implement-backend, enabled: true}
    - {instance_id: s-unit, stage_id: unit-test, enabled: true}
    - {instance_id: s-cr, stage_id: cr, enabled: true}
    - {instance_id: s-pkg, stage_id: package, enabled: true}
    - {instance_id: s-deploy, stage_id: deploy, enabled: true}
    - {instance_id: s-mon, stage_id: monitor-setup, enabled: true}
  edges: [线性的 7 条]
  state: draft
  budget: {max_minutes: 1440, max_cost_usd: 5.0}
  gates:
    - {id: gate-1, after_stage: s-clarify, trigger: always, sla: 4h, approvers: [pm]}
    - {id: gate-2, after_stage: s-design, trigger: always, sla: 8h, approvers: [architect]}
    - {id: gate-3, after_stage: s-cr, trigger: on_severity(P1), sla: 4h, approvers: [tl]}
    - {id: gate-4, after_stage: s-mon, trigger: always, sla: 4h, approvers: [sre, qa]}
```

---

## 十一、版本

- v2.0 (2026-06-05): 引入 7 抽象，取代 v1.0 的固定 7 阶段
