# 07. Gate 库 (v2.0)

> **Gate = 流程中显式停下来等人工批准/补充/决策的点**  
> 10+ Gate 模板，覆盖各种业务场景

---

## 一、Gate 总览

| ID | 位置 | 角色 | SLA | 触发模式 |
|---|---|---|---|---|
| `gate-1-clarify` | clarify 后 | PM / BA | 4h | always |
| `gate-2-design` | design 后 | 架构师 / TL | 8h | always |
| `gate-3-cr` | cr 后 | TL | 4h | on_severity(P1) |
| `gate-4-monitor` | monitor-setup 后 | SRE / QA | 4h | always |
| `gate-5-security` | security-scan 后 | 安全工程师 | 8h | always（high risk） |
| `gate-6-impact` | impact-analysis 后 | 架构师 / DBA | 8h | manual |
| `gate-7-customer` | 涉及客户数据后 | 法务 | 24h | on_artifact_contains_pii |
| `gate-8-compliance` | 涉及合规项后 | 合规官 | 24h | manual |
| `gate-9-rollback-decision` | incident 触发后 | TL | 1h | on_incident |
| `gate-10-postmortem` | hotfix 后 24h | 团队负责人 | 24h | always（hotfix） |

---

## 二、Gate Schema

```yaml
id: string
name: string
description: string

when:
  after_stage: string           # 在哪个 stage 后
  trigger: enum                 # always | on_severity | on_artifact_missing | on_artifact_contains | manual | never
  severity_threshold: enum?     # P0 | P1 | P2 | P3
  artifact_contains: string?    # 关键词，如 "PII" / "GDPR" / "AB实验"
  
sla_hours: int
escalation_after_hours: int?

approvers:
  - role: enum                  # pm | ba | architect | tl | sre | qa | security | legal | compliance | oncall
    min_count: int
    optional: bool

checklist:
  - id: string
    question: string
    blocking: bool
    default: enum?              # yes | no | n/a
    hint: string?

notifications:
  - channel: enum               # feishu | email | slack | im | webhook
    on: enum                    # pending | overdue | approved | rejected
    template: string?

actions_on_approve:             # 放行后做的事
  - kind: string                # create_jira | send_message | trigger_stage | ...
    spec: map

actions_on_reject:
  - kind: string                # rollback_stage | escalate | ...
    spec: map

actions_on_overdue:
  - kind: string                # escalate_to_lead | post_to_channel
    spec: map
```

---

## 三、详细 Gate

### 3.1 `gate-1-clarify` 需求评审

```yaml
id: gate-1-clarify
name: 需求评审
description: PM/BA 评审需求完整性与合理性

when:
  after_stage: clarify
  trigger: always

sla_hours: 4
escalation_after_hours: 2

approvers:
  - role: pm
    min_count: 1
  - role: ba
    min_count: 1
    optional: true              # 小项目可只 PM

checklist:
  - id: dor
    question: "DoR（Definition of Ready）已就位：背景/目标/用户故事/验收标准/范围边界？"
    blocking: true
  - id: scope
    question: "范围边界已明确（in scope / out of scope）？"
    blocking: true
  - id: priority
    question: "优先级 P0-P4 已标注？"
    blocking: true
  - id: dependency
    question: "依赖方（上下游/设计/QA/UI/PM）已对齐？"
    blocking: false
  - id: data
    question: "涉及数据变更？是否通知 DBA？"
    blocking: false

notifications:
  - channel: feishu
    on: pending
    template: "需求评审待办：{feature_id} - {feature_name}"

actions_on_approve:
  - kind: trigger_stage
    spec: { next_stage: design }
  - kind: create_jira
    spec: { type: task, assignee: architect }

actions_on_reject:
  - kind: rollback_stage
    spec: { to: clarify }
```

### 3.2 `gate-2-design` 设计评审

```yaml
id: gate-2-design
name: 设计评审
description: 架构师/TL 评审技术方案

when:
  after_stage: design
  trigger: always

sla_hours: 8
escalation_after_hours: 4

approvers:
  - role: architect
    min_count: 1
  - role: tl
    min_count: 1
    optional: true

checklist:
  - id: contract
    question: "API Contract / DB Schema 已定义？"
    blocking: true
  - id: nonfunctional
    question: "非功能需求（性能/可用性/安全/合规）已考虑？"
    blocking: true
  - id: rollback
    question: "回滚方案明确？"
    blocking: true
  - id: data-migration
    question: "如涉及数据迁移，双写/校验/回滚预案齐备？"
    blocking: false
  - id: observability
    question: "可观测性（日志/指标/Trace）已规划？"
    blocking: true
  - id: dependency
    question: "下游/上游团队已同步？"
    blocking: false

actions_on_approve:
  - kind: trigger_stage
    spec: { next_stage: implement-backend }
```

### 3.3 `gate-3-cr` Code Review 放行

```yaml
id: gate-3-cr
name: Code Review 放行
description: TL 决定是否合并

when:
  after_stage: cr
  trigger: on_severity
  severity_threshold: P1

sla_hours: 4
escalation_after_hours: 2

approvers:
  - role: tl
    min_count: 1

checklist:
  - id: p0
    question: "P0-Blocker 问题已全部修复？"
    blocking: true
  - id: p1
    question: "P1-Critical 问题已修复或承诺？"
    blocking: true
  - id: test
    question: "单元测试覆盖率 ≥ 80%？"
    blocking: true
  - id: integration
    question: "集成测试通过？"
    blocking: false
  - id: regression
    question: "回归测试通过？"
    blocking: false
  - id: anchor
    question: "代码锚点（@sdlc-*）完整？"
    blocking: true
  - id: observability
    question: "可观测性埋点已加？"
    blocking: true

actions_on_approve:
  - kind: trigger_stage
    spec: { next_stage: package }

actions_on_reject:
  - kind: rollback_stage
    spec: { to: implement-backend, mode: revise }
```

### 3.4 `gate-4-monitor` 监控/SLO 放行

```yaml
id: gate-4-monitor
name: 监控/SLO 放行
description: SRE/QA 确认监控/告警/SLO 齐备

when:
  after_stage: monitor-setup
  trigger: always

sla_hours: 4
escalation_after_hours: 2

approvers:
  - role: sre
    min_count: 1
  - role: qa
    min_count: 1
    optional: true

checklist:
  - id: golden-signal
    question: "黄金信号（Latency/Traffic/Errors/Saturation）已配？"
    blocking: true
  - id: business-metric
    question: "业务关键指标（订单/支付/转化）已配？"
    blocking: true
  - id: alert
    question: "告警阈值合理（无告警风暴）？"
    blocking: true
  - id: runbook
    question: "Runbook 完整？值班 oncall 已知？"
    blocking: true
  - id: slo
    question: "SLO 已定义（可用性/性能目标）？"
    blocking: false
  - id: postmortem
    question: "如为 hotfix，post_mortem 链接已附？"
    blocking: false

actions_on_approve:
  - kind: send_message
    spec:
      channel: feishu
      template: "🎉 {feature_id} 已上线！监控/SLO 见 {monitor_url}"
```

### 3.5 `gate-5-security` 安全评审

```yaml
id: gate-5-security
name: 安全评审
description: 安全工程师评审

when:
  after_stage: security-scan
  trigger: always
  severity_threshold: high

sla_hours: 8
escalation_after_hours: 4

approvers:
  - role: security
    min_count: 1

checklist:
  - id: sast
    question: "SAST 工具扫描通过（无 high）？"
    blocking: true
  - id: dependency
    question: "依赖扫描通过（无高危 CVE）？"
    blocking: true
  - id: auth
    question: "认证/鉴权设计正确？"
    blocking: true
  - id: data-protection
    question: "敏感数据已加密/脱敏？"
    blocking: true
  - id: owasp
    question: "OWASP Top 10 已自查？"
    blocking: true

actions_on_reject:
  - kind: rollback_stage
    spec: { to: implement-backend, mode: revise_with_security_fix }
```

### 3.6 `gate-6-impact` 影响面放行

```yaml
id: gate-6-impact
name: 影响面放行
description: 架构师/DBA 评审影响面

when:
  after_stage: impact-analysis
  trigger: manual

sla_hours: 8
escalation_after_hours: 4

approvers:
  - role: architect
    min_count: 1
  - role: dba
    min_count: 1
    optional: true

checklist:
  - id: schema
    question: "DB Schema 变更已评估（Flyway/Liquibase）？"
    blocking: true
  - id: cache
    question: "缓存失效/穿透已评估？"
    blocking: true
  - id: api
    question: "API 兼容性已评估（v1/v2 共存）？"
    blocking: true
  - id: data-volume
    question: "数据量/迁移量已评估（行数/容量）？"
    blocking: false
  - id: upstream
    question: "上游调用方已通知？"
    blocking: true
```

### 3.7 `gate-7-customer` 客户数据评审

```yaml
id: gate-7-customer
name: 客户数据/法务评审
description: 涉及 PII/客户数据时法务介入

when:
  after_stage: design
  trigger: on_artifact_contains
  artifact_contains: "PII|GDPR|PIPL|用户隐私|跨境"

sla_hours: 24
escalation_after_hours: 12

approvers:
  - role: legal
    min_count: 1

checklist:
  - id: privacy
    question: "用户隐私影响评估（DPIA）已做？"
    blocking: true
  - id: consent
    question: "用户同意机制已具备？"
    blocking: true
  - id: retention
    question: "数据保留期限合规？"
    blocking: true
  - id: cross-border
    question: "跨境数据传输合规？"
    blocking: false
```

### 3.8 `gate-8-compliance` 合规评审

```yaml
id: gate-8-compliance
name: 合规评审
description: 合规官评审（金融/医疗/特殊行业）

when:
  after_stage: design
  trigger: manual

sla_hours: 24
escalation_after_hours: 12

approvers:
  - role: compliance
    min_count: 1

checklist:
  - id: regulation
    question: "相关法规已识别（PCI-DSS/HIPAA/SOX）？"
    blocking: true
  - id: audit
    question: "审计日志已规划？"
    blocking: true
  - id: data
    question: "数据分类分级已标注？"
    blocking: true
```

### 3.9 `gate-9-rollback-decision` 回滚决策

```yaml
id: gate-9-rollback-decision
name: 回滚决策
description: 故障触发回滚时的快速决策

when:
  trigger: on_incident

sla_hours: 1
escalation_after_hours: 0.5

approvers:
  - role: oncall
    min_count: 1
  - role: tl
    min_count: 1
    optional: true

checklist:
  - id: impact
    question: "故障影响范围已评估？"
    blocking: true
  - id: rollback-safe
    question: "回滚安全（无数据迁移）？"
    blocking: true
  - id: alternative
    question: "是否尝试过非回滚方案（feature flag/限流/热修复）？"
    blocking: false

actions_on_approve:
  - kind: trigger_stage
    spec: { next_stage: rollback, urgent: true }
```

### 3.10 `gate-10-postmortem` 复盘

```yaml
id: gate-10-postmortem
name: Post-mortem 复盘
description: 故障后 24h 必出复盘

when:
  trigger: always
  # 实际触发：hotfix profile + deploy 完成后 24h

sla_hours: 24
escalation_after_hours: 12

approvers:
  - role: tl
    min_count: 1

checklist:
  - id: timeline
    question: "事件时间线完整（发现/响应/止血/定位/修复/恢复）？"
    blocking: true
  - id: root-cause
    question: "Root Cause 已定位（5 Whys）？"
    blocking: true
  - id: impact
    question: "影响范围已量化（用户数/订单数/收入损失）？"
    blocking: true
  - id: action-items
    question: "Action items 已列（每条带 owner + deadline）？"
    blocking: true
  - id: lesson
    question: "教训与改进项已记录？"
    blocking: false

actions_on_approve:
  - kind: send_message
    spec:
      channel: feishu
      template: "📝 Post-mortem 已出：{pm_url}"
```

---

## 四、Gate 触发模式详解

### 4.1 `always` 总是触发

```yaml
trigger: always
```

最严格。适用于核心环节（如设计评审）。

### 4.2 `on_severity` 按严重度

```yaml
trigger: on_severity
severity_threshold: P1
```

只有产物严重度 ≥ 阈值时触发。P1 意味着"还有 P2/P3 不必走 Gate"。

### 4.3 `on_artifact_missing` 产物缺失

```yaml
trigger: on_artifact_missing
```

如 unit-test 报告缺失 → 阻断。

### 4.4 `on_artifact_contains` 内容包含

```yaml
trigger: on_artifact_contains
artifact_contains: "PII|GDPR"
```

如设计文档提到 PII → 触发法务 Gate。

### 4.5 `manual` 手动指定

```yaml
trigger: manual
```

用户或 Profile 显式启用。

### 4.6 `never` 关闭

等同于"无 Gate"。

---

## 五、Gate 的可配置项

### 5.1 跳过 Gate

```
用户："跳过 Gate 1"
→ user_overrides.skip_gates: [gate-1]
```

### 5.2 加 Gate

```
用户："加个安全 Gate"
→ user_overrides.extra_gates: [{after_stage: cr, role: security}]
```

### 5.3 改变 SLA

```
用户："Gate 2 给 24h"
→ pipeline.gates[gate-2].sla_hours: 24
```

---

## 六、Gate 与 Profile 的关系

| Profile | 必走 Gate | 必跳 Gate |
|---|---|---|
| new-feature | 1, 2, 3, 4 | - |
| bug-fix | 2, 3 | 1, 4 |
| hotfix | 3 | 1, 2, 4 |
| refactor | 2, 3 | 1, 4 |
| migration | 1, 2, 3, 4 | - |
| performance | 2, 3, 4 | 1 |
| security | 1, 2, 3, 4, 5 | - |
| docs-only | - | 全部 |
| test-only | 3 | 1, 2, 4 |
| review-only | - | 全部 |
| deploy-only | 4 | 1, 2, 3 |
| monitor-only | 4 | 1, 2, 3 |
| greenfield | 1, 2, 3, 4, 5 | - |
| poc | - | 全部 |

---

## 七、Gate 流程的 4 步

```
1. Pending
   - 触发条件命中
   - 通知 approvers
   - 启动 SLA 计时

2. In Review
   - approver 收到 checklist
   - 在 UI/IM 中逐项检查
   - 可 ask author 补充

3. Decision
   - 全部 blocking 通过 → Approved
   - 任意 blocking 失败 → Rejected
   - 超时 → Escalation

4. Action
   - Approved: 触发 actions_on_approve
   - Rejected: 触发 actions_on_reject（通常回滚到上一 stage）
   - Escalated: 触发 actions_on_overdue
```

---

## 八、版本

- v2.0 (2026-06-05): 10+ Gate 库（取代 v1.0 的固定 4 Gate）
