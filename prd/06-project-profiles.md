# 06. 项目 Profile (v2.0)

> **Profile = 项目类型，决定默认 Pipeline、默认 Gate、风险等级、回滚策略**  
> 12 种 Profile 覆盖几乎所有 SDLC 场景

---

## 一、12 种 Profile 总览

| ID | 名称 | 风险等级 | 必走 Gate | 必跑 Stage |
|---|---|---|---|---|
| `new-feature` | 新功能 | medium | 1, 2, 3, 4 | clarify → design → impl → test → cr → deploy → monitor |
| `bug-fix` | 缺陷修复 | low | 2, 3 | diagnose → fix → test → cr → deploy |
| `hotfix` | 紧急修复 | high | 3 | diagnose → fix → test → deploy → verify |
| `refactor` | 重构 | medium | 2, 3 | impact → refactor → test → regression → cr → deploy |
| `migration` | 迁移 | high | 1, 2, 3, 4 | impact → design → impl → test → regression → cr → security-scan → deploy → verify |
| `performance` | 性能优化 | medium | 2, 3, 4 | diagnose → design → impl → test → cr → deploy → monitor |
| `security` | 安全加固 | high | 1, 2, 3, 4 | diagnose → design → impl → security-scan → test → cr → deploy → monitor |
| `docs-only` | 文档更新 | low | none | docs-update |
| `test-only` | 测试补充 | low | 3 | test → cr |
| `review-only` | 评审/CR | low | none | cr |
| `deploy-only` | 仅部署 | medium | 4 | package → deploy |
| `monitor-only` | 监控/告警 | low | 4 | monitor-setup |
| `greenfield` | 新项目 | high | 1, 2, 3, 4 | clarify → design → impl → test → cr → deploy → monitor 全套 |
| `poc` | 概念验证 | low | none | clarify → design → impl → test |

---

## 二、Profile Schema

```yaml
id: string                      # kebab-case
name: string
description: string
version: string

default_stages: [string]        # 必跑 stage
optional_stages: [string]       # 可选 stage
skip_stages: [string]           # 必跳 stage
default_gates: [string]         # 必走 Gate
skip_gates: [string]            # 必跳 Gate

risk_class: enum                # low | medium | high
severity_default: enum          # P0 | P1 | P2 | P3 | P4

max_budget_minutes: int
max_budget_usd: float

rollback_required: bool
canary_required: bool
canary_duration_minutes: int?   # 仅 canary_required=true 时用

require_issue: bool             # 必先有 JIRA/GitHub Issue
require_dor: bool               # 必先有 Definition of Ready
require_dod: bool               # 必先有 Definition of Done

advisories:                     # 提醒
  - when: string                # 触发条件
    message: string
    severity: enum              # info | warn | block

checklist:                      # 启动前的检查项
  - question: string
    blocking: bool
    default_answer: enum?       # yes | no | n/a
```

---

## 三、详细 Profile

### 3.1 `new-feature` 新功能

```yaml
id: new-feature
name: 新功能
description: 全新功能/特性，从需求到上线
risk_class: medium
severity_default: P2

default_stages:
  - clarify
  - design
  - implement-backend    # 实际取决于 adapter，可能是 frontend/mobile/infra
  - unit-test
  - cr
  - package
  - deploy
  - monitor-setup
optional_stages:
  - impact-analysis
  - integration-test
  - regression
  - e2e-test
  - security-scan
  - adr
skip_stages: []
default_gates: [gate-1, gate-2, gate-3, gate-4]
skip_gates: []

max_budget_minutes: 1440        # 24h
max_budget_usd: 5.0

rollback_required: true
canary_required: false

require_issue: true
require_dor: true
require_dod: true

advisories:
  - when: feature_contains_db_change
    message: "数据库 Schema 变更需提前通知 DBA + 走 Flyway/Liquibase"
    severity: warn
  - when: feature_touches_critical_api
    message: "改动核心 API 需走 Gate 2 架构评审"
    severity: block

checklist:
  - question: "是否已与依赖方（上下游/QA/UI/PM）对齐？"
    blocking: true
    default_answer: yes
  - question: "是否需要新增监控/SLO？"
    blocking: false
    default_answer: no
  - question: "是否需要 AB 测试？"
    blocking: false
    default_answer: no
```

### 3.2 `bug-fix` 缺陷修复

```yaml
id: bug-fix
name: 缺陷修复
description: 修复已复现的 bug
risk_class: low
severity_default: P2

default_stages:
  - diagnose
  - fix
  - unit-test
  - cr
  - deploy
optional_stages:
  - integration-test
  - regression
  - e2e-test
skip_stages: [clarify, design, impact-analysis, monitor-setup]
default_gates: [gate-2, gate-3]
skip_gates: [gate-1, gate-4]

max_budget_minutes: 480         # 8h
max_budget_usd: 2.0

rollback_required: true
canary_required: false

require_issue: true             # 必有 JIRA 单
require_dor: false
require_dod: true               # 必有"如何验证"

advisories:
  - when: "diagnose_outputs.severity >= P1"
    message: "P1+ bug 建议升级为 hotfix 流程（自动通知 oncall）"
    severity: warn
  - when: "bug.loc == 'production'"
    message: "生产 bug 必先有 RCA 与缓解措施"
    severity: block

checklist:
  - question: "是否有可复现的测试用例？"
    blocking: true
  - question: "影响范围（用户数/接口数/数据量）已评估？"
    blocking: true
  - question: "是否需要数据修复（脏数据处理）？"
    blocking: false
```

### 3.3 `hotfix` 紧急修复

```yaml
id: hotfix
name: 紧急修复
description: 线上 P0/P1 故障，立刻修
risk_class: high
severity_default: P1

default_stages:
  - diagnose          # 同时跑止血（rollback / feature flag）
  - fix
  - unit-test         # 简版
  - deploy
  - verify            # 监控 + 业务指标
optional_stages:
  - integration-test
skip_stages: [clarify, design, cr, monitor-setup, e2e-test, regression]
default_gates: [gate-3]         # 仅 TL
skip_gates: [gate-1, gate-2, gate-4]

max_budget_minutes: 180         # 3h
max_budget_usd: 1.5

rollback_required: true
canary_required: false

require_issue: true             # 必先有 incident 单
require_dor: false
require_dod: true

advisories:
  - when: always
    message: "HOTFIX：3h 内完成。必先止血（rollback/feature flag），再修因。"
    severity: block
  - when: post_deploy
    message: "修复后 1h 内必出 post_mortem（5 Whys + action items）"
    severity: block

checklist:
  - question: "已通知 oncall 和相关方？"
    blocking: true
  - question: "止血措施（rollback/feature flag/限流）已就位？"
    blocking: true
  - question: "Root cause 初步定位？"
    blocking: false               # 可后续补
  - question: "修复后 1h 内必出 post_mortem"
    blocking: true
```

### 3.4 `refactor` 重构

```yaml
id: refactor
name: 重构
description: 保持行为不变前提下改善代码结构
risk_class: medium
severity_default: P2

default_stages:
  - impact-analysis
  - design
  - refactor
  - unit-test
  - integration-test
  - regression
  - cr
  - deploy
optional_stages:
  - security-scan
skip_stages: [clarify, monitor-setup, e2e-test]
default_gates: [gate-2, gate-3]
skip_gates: [gate-1, gate-4]

max_budget_minutes: 2880        # 48h
max_budget_usd: 8.0

rollback_required: true
canary_required: false

require_issue: true
require_dor: true
require_dod: true

advisories:
  - when: refactor_touches_more_than_X_files
    message: "改动超过 50 文件建议拆 PR"
    severity: warn
  - when: refactor_changes_public_api
    message: "公开 API 变更需走 Gate 2 架构评审 + 上下游同步"
    severity: block

checklist:
  - question: "现有测试覆盖率 ≥ 70%？"
    blocking: true
  - question: "行为不变（功能等价）已明确？"
    blocking: true
  - question: "回滚方案明确？"
    blocking: true
  - question: "性能基线已记录（重构后需对比）？"
    blocking: false
```

### 3.5 `migration` 迁移

```yaml
id: migration
name: 迁移
description: 数据库/服务/中间件迁移
risk_class: high
severity_default: P1

default_stages:
  - clarify
  - impact-analysis
  - design
  - implement-backend
  - unit-test
  - integration-test
  - regression
  - cr
  - security-scan
  - package
  - deploy
  - verify
skip_stages: []
default_gates: [gate-1, gate-2, gate-3, gate-4]

max_budget_minutes: 4320        # 72h
max_budget_usd: 15.0

rollback_required: true         # 强制
canary_required: true           # 强制灰度
canary_duration_minutes: 1440   # 24h

require_issue: true
require_dor: true
require_dod: true

advisories:
  - when: db_migration
    message: "DB 迁移必走双写 + 数据校验 + 回滚预案"
    severity: block
  - when: cross_team_migration
    message: "跨团队迁移需提前 1 周通知 + 上下游联调"
    severity: warn
```

### 3.6 `performance` 性能优化

```yaml
id: performance
name: 性能优化
description: 性能瓶颈优化
risk_class: medium
severity_default: P2

default_stages:
  - diagnose            # 性能基线测量
  - design
  - implement-backend
  - unit-test
  - integration-test
  - regression
  - cr
  - deploy
  - monitor-setup       # 必看性能指标
skip_stages: [clarify]
default_gates: [gate-2, gate-3, gate-4]
skip_gates: [gate-1]

max_budget_minutes: 2880
max_budget_usd: 8.0

rollback_required: true
canary_required: false

advisories:
  - when: optimize_db_query
    message: "DB 优化必看执行计划 + 索引影响"
    severity: warn
  - when: optimize_hot_path
    message: "热点路径优化必先有基线数据 + 灰度对比"
    severity: block
```

### 3.7 `security` 安全加固

```yaml
id: security
name: 安全加固
description: 修复安全漏洞
risk_class: high
severity_default: P0

default_stages:
  - diagnose            # 漏洞复现 + 风险评估
  - design
  - implement-backend
  - security-scan
  - unit-test
  - integration-test
  - cr
  - deploy
  - monitor-setup
default_gates: [gate-1, gate-2, gate-3, gate-4]

max_budget_minutes: 1440
max_budget_usd: 5.0

rollback_required: true
canary_required: false

advisories:
  - when: severity_CVE_high
    message: "高危 CVE 建议升级到 hotfix 流程"
    severity: block
  - when: data_leak_risk
    message: "数据泄露风险需法务 + 安全团队介入"
    severity: block
```

### 3.8 `docs-only` 文档更新

```yaml
id: docs-only
name: 文档更新
description: 仅文档变更（README/API doc/ADR）
risk_class: low
severity_default: P3

default_stages: [docs-update]
skip_stages: [几乎所有]
default_gates: []
skip_gates: [gate-1, gate-2, gate-3, gate-4]

max_budget_minutes: 60
max_budget_usd: 0.3

rollback_required: false
canary_required: false

require_issue: false
```

### 3.9 `test-only` 测试补充

```yaml
id: test-only
name: 测试补充
description: 仅补充测试用例
risk_class: low
severity_default: P3

default_stages:
  - unit-test
  - cr
skip_stages: [clarify, design, implement, deploy, monitor]
default_gates: [gate-3]
skip_gates: [gate-1, gate-2, gate-4]

max_budget_minutes: 240
max_budget_usd: 1.0

require_issue: false
```

### 3.10 `review-only` 评审/CR

```yaml
id: review-only
name: 评审/CR
description: 仅评审代码，不实现
risk_class: low
severity_default: P3

default_stages: [cr]
skip_stages: [几乎所有]
default_gates: []
skip_gates: [全部]

max_budget_minutes: 30
max_budget_usd: 0.2

require_issue: false
```

### 3.11 `deploy-only` 仅部署

```yaml
id: deploy-only
name: 仅部署
description: 把已构建好的版本部署到目标环境
risk_class: medium
severity_default: P2

default_stages:
  - package             # 仅校验镜像
  - deploy
skip_stages: [几乎所有]
default_gates: [gate-4]
skip_gates: [gate-1, gate-2, gate-3]

max_budget_minutes: 60
max_budget_usd: 0.5

require_issue: false
```

### 3.12 `monitor-only` 监控/告警

```yaml
id: monitor-only
name: 监控/告警
description: 仅新增/调整监控/告警/Runbook
risk_class: low
severity_default: P3

default_stages: [monitor-setup]
skip_stages: [几乎所有]
default_gates: [gate-4]
skip_gates: [gate-1, gate-2, gate-3]

max_budget_minutes: 60
max_budget_usd: 0.3

require_issue: false
```

### 3.13 `greenfield` 新项目

```yaml
id: greenfield
name: 新项目
description: 全新项目从 0 到 1
risk_class: high
severity_default: P1

default_stages:
  - clarify
  - impact-analysis
  - design
  - adr
  - implement-backend
  - implement-frontend
  - implement-infra
  - implement-mobile          # 可选
  - unit-test
  - integration-test
  - cr
  - security-scan
  - package
  - deploy
  - monitor-setup
default_gates: [gate-1, gate-2, gate-3, gate-4]

max_budget_minutes: 10080     # 7 天
max_budget_usd: 50.0

rollback_required: true
canary_required: false
```

### 3.14 `poc` 概念验证

```yaml
id: poc
name: 概念验证
description: 验证某技术/方案是否可行
risk_class: low
severity_default: P3

default_stages:
  - clarify
  - design
  - implement-backend
  - unit-test
skip_stages: [cr, deploy, monitor-setup]
default_gates: []
skip_gates: [全部]

max_budget_minutes: 480
max_budget_usd: 1.0

require_issue: false

advisories:
  - when: always
    message: "POC 产物不进生产，必重建"
    severity: block
```

---

## 四、Profile 选择算法

```python
def select_profile(user_input, entrypoint, context) -> Profile:
    # 1. 用户显式指定
    if context.explicit_profile:
        return PROFILES[context.explicit_profile]
    
    # 2. 基于 EntryPoint 默认
    default = ENTRYPOINTS[entrypoint.id].default_profile
    if default:
        return PROFILES[default]
    
    # 3. 关键词增强
    text = user_input.lower()
    if "hotfix" in text or "p0" in text or "线上" in text and ("故障" in text or "挂了" in text):
        return PROFILES["hotfix"]
    if "refactor" in text or "重构" in text:
        return PROFILES["refactor"]
    if "迁移" in text and ("mysql" in text or "tidb" in text or "http" in text or "grpc" in text):
        return PROFILES["migration"]
    if "性能" in text or "慢" in text or "p99" in text or "rt" in text:
        return PROFILES["performance"]
    if "安全" in text or "cve" in text or "漏洞" in text:
        return PROFILES["security"]
    if "bug" in text or "缺陷" in text:
        return PROFILES["bug-fix"]
    if "文档" in text and "实现" not in text and "代码" not in text:
        return PROFILES["docs-only"]
    if "测试" in text and "补" in text:
        return PROFILES["test-only"]
    if "监控" in text or "告警" in text:
        return PROFILES["monitor-only"]
    if "部署" in text and "实现" not in text:
        return PROFILES["deploy-only"]
    
    # 4. 兜底
    return PROFILES[entrypoint.default_profile]
```

---

## 五、Profile 与 EntryPoint 的对应矩阵

| EntryPoint \ Profile | new-feature | bug-fix | hotfix | refactor | migration | performance | security | docs-only | test-only | review-only | deploy-only | monitor-only | greenfield | poc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| idea | ✓ | | | | | | | | | | | | ✓ | ✓ |
| prd | ✓ | | | | | | | | | | | | ✓ | |
| design | ✓ | | | | | | | | | | | | ✓ | |
| code | | | | ✓ | | | | | | ✓ | | | | |
| bug | | ✓ | | | | | | | | | | | | |
| refactor | | | | ✓ | | | | | | | | | | |
| test | | | | | | | | | ✓ | | | | | |
| review | | | | | | | | | | ✓ | | | | |
| deploy | | | | | | | | | | | ✓ | | | |
| monitor | | | | | | | | | | | | ✓ | | |
| doc | | | | | | | | ✓ | | | | | | |
| hotfix | | | ✓ | | | | | | | | | | | |

---

## 六、Profile 扩展

新增 Profile = 写一份 YAML 注册到 `~/.claude/profiles/`。

例如新增 `compliance-audit`（合规审计）：
```yaml
id: compliance-audit
name: 合规审计
default_stages: [clarify, design, security-scan, cr, deploy, monitor-setup]
default_gates: [gate-2, gate-3, gate-4]
risk_class: high
advisories:
  - when: data_involves_pii
    message: "涉及 PII 数据需走 GDPR/PIPL 评估"
    severity: block
```

---

## 七、版本

- v2.0 (2026-06-05): 12+ Profile 库（取代 v1.0 的隐式 new-feature）
