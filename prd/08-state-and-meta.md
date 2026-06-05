# 08. 状态与审计 (v2.0)

> **所有 Pipeline/Stage/Artifact 的状态变更必须留痕**  
> 支持 resume、追溯、合规审计

---

## 一、目录结构

```
prd/
  {feature_id}/
    meta.json                    # 全局元数据（Pipeline 状态、预算、配置）
    pipeline.yaml                # 完整 Pipeline 定义
    audit.log                    # 审计日志（append-only，JSONL 格式）
    artifacts/                   # 所有产物
      {stage_id}-{artifact_type}-{ts}.{ext}
    snapshots/                   # 关键检查点
      after-stage-{stage_id}/
        meta.json
        artifacts/
    feedback/                    # 用户/评审反馈
      {gate_id}-feedback.md
    resume_token.txt             # Resume 凭证（短期有效）
```

---

## 二、meta.json Schema

```yaml
# Pipeline 级元数据
schema_version: "2.0"
feature_id: string              # 全局唯一
feature_name: string
created_at: timestamp
updated_at: timestamp
created_by: user_id

# 入口
entrypoint: string
profile: string
adapter: string
adapter_version: string?

# 用户覆盖
user_overrides:
  enabled_stages: [string]?
  disabled_stages: [string]?
  extra_stages: [stage_spec]?
  max_budget: {minutes: int, cost_usd: float}?
  skip_gates: [string]?

# Pipeline 状态
state: enum                     # draft | active | paused | completed | failed
state_history:                  # 状态机历史
  - state: enum
    at: timestamp
    reason: string
    by: user_id | subagent_id

# 阶段进度
stages:
  - instance_id: string
    stage_id: string
    state: enum                 # pending | active | completed | failed | skipped
    started_at: timestamp?
    completed_at: timestamp?
    duration_seconds: int?
    subagent_id: string?
    attempts: int               # 重试次数
    error: string?
    outputs: [artifact_id]
    cost_usd: float?

# 产物索引
artifacts:
  - artifact_id: string
    type: string
    format: string
    path: string
    hash: string
    created_at: timestamp
    created_by: subagent_id
    stage_instance_id: string
    size_bytes: int
    tags: [string]?

# 预算
budget:
  max_minutes: int?
  max_cost_usd: float?
  spent_minutes: int
  spent_cost_usd: float

# Gate 状态
gates:
  - gate_id: string
    after_stage: string
    state: enum                 # pending | approved | rejected | overdue | skipped
    pending_at: timestamp?
    decided_at: timestamp?
    decided_by: user_id?
    sla_hours: int
    escalation_at: timestamp?
    feedback: string?
    checklist_responses:
      - item_id: string
        answer: enum            # yes | no | n/a
        comment: string?

# 协作
collaborators: [user_id]
reviewers: [user_id]
oncall: user_id?

# 标签
tags: [string]?
labels: map?
severity: enum?                 # P0 | P1 | P2 | P3 | P4

# 风险与合规
risk_class: enum                # low | medium | high
rollback_plan: string?          # 文本描述
data_classification: enum?      # public | internal | confidential | restricted

# Resume 支持
resume_token: string?
resume_expires_at: timestamp?

# KB 更新（v2.1 新增）
kb_updates:
  - stage_id: string
    at: timestamp
    files_changed: [string]      # 改的 KB 文件
    additions:
      components: [string]?
      patterns: [string]?
      antipatterns: [string]?
      adrs: [string]?
      runbooks: [string]?
      lessons: [string]?
    summary: string              # 一句话总结
    auto_generated: bool         # 自动/人工

# 上下文快照（v2.1 新增）
context_snapshot:
  recent_components_used: [string]
  recent_patterns_applied: [string]
  recent_skills_invoked: [string]
  recent_decisions: [string]
  open_questions: [string]
```

---

## 三、audit.log Schema

JSONL 格式，每行一个事件。

```jsonl
{"ts": "2026-06-05T10:00:00.123Z", "event": "pipeline_created", "actor": "user:duanluyao1", "feature_id": "feat-001", "pipeline": {...}}
{"ts": "2026-06-05T10:01:00.456Z", "event": "stage_started", "actor": "subagent:requirements-analyst", "feature_id": "feat-001", "stage_id": "clarify", "instance_id": "s-clarify"}
{"ts": "2026-06-05T10:15:00.789Z", "event": "stage_completed", "actor": "subagent:requirements-analyst", "feature_id": "feat-001", "stage_id": "clarify", "instance_id": "s-clarify", "duration_seconds": 840, "artifacts": ["a-001", "a-002"]}
{"ts": "2026-06-05T10:15:00.890Z", "event": "gate_pending", "actor": "system", "feature_id": "feat-001", "gate_id": "gate-1-clarify", "approvers": ["user:pm-zhang"]}
{"ts": "2026-06-05T10:20:00.123Z", "event": "gate_approved", "actor": "user:pm-zhang", "feature_id": "feat-001", "gate_id": "gate-1-clarify", "comment": "OK"}
{"ts": "2026-06-05T10:20:00.234Z", "event": "stage_started", "actor": "subagent:architect", "feature_id": "feat-001", "stage_id": "design", "instance_id": "s-design"}
```

### 3.1 事件类型清单

| Event | Actor | 触发时机 | Payload |
|---|---|---|---|
| `pipeline_created` | user | 用户启动 pipeline | pipeline 完整定义 |
| `pipeline_started` | user / system | draft → active | - |
| `pipeline_paused` | user | user 请求暂停 | reason |
| `pipeline_resumed` | user | user 请求恢复 | - |
| `pipeline_completed` | system | 全部 stage 完成 | - |
| `pipeline_failed` | system | 致命错误 | error |
| `stage_started` | system | 进入 stage | subagent_id |
| `stage_completed` | subagent | stage 跑完 | duration, artifacts, cost |
| `stage_failed` | subagent | stage 出错 | error, retry_count |
| `stage_retried` | system | 重试 | attempt |
| `stage_skipped` | user / system | 跳过 | reason |
| `kb_updated` | system | KB 文件更新 | files, additions, summary |
| `kb_init` | system | sdlc init 触发 | project, detected, recommended |
| `kb_reconciled` | system | 周/季度 reconcile | drift_count, fixed_count |
| `pattern_extracted` | system | 从代码抽象新模式 | pattern_id, occurrences |
| `antipattern_detected` | system | CR/测试发现反模式 | antipattern_id, source |
| `lesson_captured` | system | hotfix/incident 总结 | lesson_id, source |
| `subagent_adapted` | system | Subagent 学习新偏好 | agent_id, learned_prefs |
| `artifact_created` | subagent | 产物生成 | artifact 完整信息 |
| `artifact_updated` | subagent | 产物更新 | diff |
| `artifact_consumed` | subagent | 产物被消费 | consumer_stage_id |
| `gate_pending` | system | Gate 触发 | approvers, sla |
| `gate_approved` | user | 放行 | checklist, comment |
| `gate_rejected` | user | 拒绝 | comment, reasons |
| `gate_overdue` | system | 超时 | escalated_to |
| `gate_escalated` | system | 升级 | new_owner |
| `subagent_invoked` | system | 调度 subagent | subagent_id, prompt_hash |
| `subagent_completed` | subagent | subagent 返回 | tokens, cost |
| `tool_used` | subagent | 工具调用 | tool_name, args_hash, result_hash |
| `budget_warning` | system | 预算 80% | remaining |
| `budget_exceeded` | system | 预算 100% | action |
| `override_applied` | user | 用户覆盖 | field, old, new |
| `error` | any | 任何错误 | error_type, stack |
| `rollback` | user / system | 回滚 | from_state, to_state, reason |

### 3.2 事件通用结构

```json
{
  "ts": "2026-06-05T10:00:00.123Z",
  "event": "stage_started",
  "actor": "subagent:architect",
  "feature_id": "feat-001",
  "instance_id": "s-design",
  "session_id": "uuid",
  "parent_event_id": "uuid",    # 关联父事件
  "metadata": {
    "tokens": 1234,
    "cost_usd": 0.05
  }
}
```

---

## 四、Snapshot 机制

### 4.1 何时打 Snapshot

- 每个 stage 完成后
- 每个 gate 决策后
- Pipeline 进入 paused
- 失败重试前
- 用户显式请求 `snapshot`

### 4.2 Snapshot 内容

```yaml
# snapshots/after-stage-s-design/snapshot.json
schema_version: "2.0"
feature_id: feat-001
created_at: 2026-06-05T10:20:00Z
trigger: stage_completed
triggered_by: stage s-design

# 复制关键文件
files:
  - meta.json                    # 主 meta
  - pipeline.yaml                # pipeline 定义
  - artifacts/                   # 截至当前的产物

# 状态摘要
state:
  pipeline: active
  stages_completed: [s-clarify, s-design]
  stages_remaining: [s-impl, s-unit, s-cr, s-pkg, s-deploy, s-mon]
  gates_approved: [gate-1]
  gates_pending: [gate-2]

# Resume 信息
resume:
  next_stage: s-impl
  token: "..."
  expires_at: ...
```

---

## 五、Resume 机制

### 5.1 Resume Token

```json
{
  "token": "rt_abc123def456",
  "feature_id": "feat-001",
  "issued_at": "2026-06-05T10:00:00Z",
  "expires_at": "2026-06-05T22:00:00Z",   # 12h 有效
  "next_stage": "s-impl",
  "snapshot_path": "snapshots/after-stage-s-design/"
}
```

### 5.2 Resume 流程

```
1. 用户："继续 feat-001"
2. 系统：
   a. 加载 meta.json + 最新 snapshot
   b. 校验 resume_token 未过期
   c. 校验产物完整性（hash）
   d. 标记已完成的 stage 为 completed
   e. 返回当前 Pipeline 状态
   f. 提示用户：
      "feat-001 已运行到 s-design（s-clarify 完成、gate-1 通过）
       下一步：s-impl（implement-backend）
       输入：
         - '继续'：从 s-impl 跑
         - '修改 s-impl 的输入'：先编辑再跑
         - '重跑 s-design'：从 s-design 跑
         - '查看产物'：列产物清单"
```

### 5.3 跨设备 Resume

- 凭证存在服务端 + 本地两份
- 服务端作权威，本地缓存
- 断网/换设备时，服务端仍能 resume

---

## 六、追溯 (Trace)

### 6.1 追溯一个产物

```
用户："feat-001 的 UserController.java 是怎么来的？"
→ 系统回答：
  - 由 subagent coder-jvm-dongboot 于 2026-06-05 10:30 生成
  - 在 stage s-impl (instance_id=s-impl)
  - 输入来自：
    - artifacts/02-design-.../design_doc.md (a-005)
    - artifacts/02-design-.../api_contract.yaml (a-006)
  - 关联的 review report: artifacts/04-cr-.../review_report.md
  - 关联的 commit: abc123def
  - 关联的 PR: #1234
  - 关联的 ADR: adr-0007
```

### 6.2 追溯一个 Gate

```
用户："gate-2 是谁批的？"
→ 系统回答：
  - gate-2-design，决策时间 2026-06-05 14:00
  - 决策人：user:architect-li
  - checklist 全部通过
  - 关联 PRD：feat-001
  - 关联 design_doc：a-005
```

### 6.3 追溯一个故障

```
用户："上周 OOM 是哪个 feature 引起的？"
→ 关联分析：
  - 时间窗：2026-05-30 13:00-15:00
  - 同时段部署：feat-005, feat-008
  - 监控指标：feat-005 部署后 1h 内存飙升
  - 自动关联到 feat-005
  - 关联 post_mortem：pm-001
```

---

## 七、Retention 与归档

```yaml
retention:
  artifacts: 90d                 # 产物保留 90 天
  audit_log: 365d                # 审计日志 1 年
  snapshots: 30d                 # 快照 30 天
  meta: 永久

archive:
  - 将 90d 前的产物压缩归档到冷存储
  - audit_log 可选归档

purge:
  - 超过 retention 的按策略删除
  - meta 永久保留
```

---

## 八、合规审计

### 8.1 不可篡改

- audit.log 用 append-only 文件
- 关键事件加 hash chain（前一条 hash + 本条内容）
- 可选：定期把 hash 提交到区块链/可信赖存储

### 8.2 监管报告

支持一键导出：
- 某时间段所有 feature 的状态
- 某用户的 Gate 决策历史
- 某 feature 的完整事件链
- 某 Profile 的平均耗时/通过率

格式：JSON / CSV / PDF

---

## 九、版本

- v2.0 (2026-06-05): 状态/审计/追溯/Resume 体系
