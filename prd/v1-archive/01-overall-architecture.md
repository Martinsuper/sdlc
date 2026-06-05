# 01 - 整体架构与流水线总览

## 一、设计目标与约束

### 1.1 目标

| 维度 | 目标值 |
|---|---|
| 人工介入次数 | ≤ 4 次/需求（4 个 Gate） |
| 单条业务线从 PRD 到上线 | ≤ 5 工作日 |
| 代码可追溯率 | 100%（每个文件有 AI 生成记录） |
| CR 误报率 | ≤ 10%（人工驳回 AI review 中 ≤ 10% 为非真问题） |
| 测试覆盖率 | 核心链路 ≥ 80%，边缘 ≥ 60% |
| 部署回滚率 | ≤ 5% |

### 1.2 约束

- 不允许单个 Agent 跑完全流程（context 必爆、不可控）
- 不允许跳过人工 Gate（事故后必须可追溯）
- 不允许 CR 与编码使用同一 context（自我合理化）
- 不允许 Subagent 直接修改主分支（必须经人类 review 或 PR）

## 二、流水线总体架构

### 2.1 7 阶段流水线

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│  │ Stage 1  │ →  │ Stage 2  │ →  │ Stage 3  │ →  │ Stage 4  │               │
│  │需求拆解  │    │架构设计  │    │  编码    │    │   CR     │               │
│  │          │    │          │    │          │    │          │               │
│  │ PRD      │    │ ADR      │    │ 业务代码 │    │ review.md│               │
│  │ 用户故事 │    │ API契约  │    │ 单测骨架 │    │ 风险清单 │               │
│  │ 验收标准 │    │ 库表DDL  │    │          │    │          │               │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘               │
│       ↓               ↓               ↓               ↓                    │
│     Gate 1          Gate 2         (自动)         Gate 3*                  │
│                                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                                │
│  │ Stage 5  │ →  │ Stage 6  │ →  │ Stage 7  │                                │
│  │  测试    │    │  部署    │    │ 监控准备 │                                │
│  │          │    │          │    │          │                                │
│  │ 覆盖率   │    │ 镜像/包  │    │ 监控盘   │                                │
│  │ 用例报告 │    │ 变更单   │    │ Runbook  │                                │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘                                │
│       ↓               ↓               ↓                                       │
│    (自动)          (自动)          Gate 4                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

* Gate 3 只在 Stage 4 标 P0/P1 时触发
```

### 2.2 阶段-产物-Gate 对应表

| Stage | 输入 | 产物 | Gate | Gate 角色 | 放行 SLA |
|---|---|---|---|---|---|
| 1 需求拆解 | PRD/用户故事 | `01-requirements.md` | Gate 1 | PM/BA | 4h |
| 2 架构设计 | 01-requirements.md | `02-design/` (ADR + API + DDL) | Gate 2 | 架构师/TL | 8h |
| 3 编码 | 02-design/ | 业务代码 + 单测骨架 | - | - | - |
| 4 CR | Git diff | `04-review.md` | Gate 3* | Tech Lead | 4h |
| 5 测试 | 业务代码 | `05-test-report.md` | - | - | - |
| 6 部署 | 业务代码 + 配置 | 镜像/包 + 变更单 | - | - | - |
| 7 监控准备 | 业务代码 | 监控盘 + Runbook | Gate 4 | SRE/QA | 4h |

## 三、Agent 分层架构

### 3.1 三层 Agent 模型

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Orchestrator（编排层）                  │
│  - 主对话窗口，掌控全局                           │
│  - 决定哪个 Stage 启动、是否放行 Gate              │
│  - 调用 Subagent、读产物、写 Gate 记录             │
└────────────────────┬────────────────────────────┘
                     │ 派发任务
                     ↓
┌─────────────────────────────────────────────────┐
│  Layer 2: Stage Worker（阶段执行层）              │
│  - 每个 Stage 启动一个独立 Subagent               │
│  - 拥有独立 context，避免污染主对话               │
│  - 调用 Layer 3 的 Skill 完成具体工作             │
└────────────────────┬────────────────────────────┘
                     │ 调用 Skill / 工具
                     ↓
┌─────────────────────────────────────────────────┐
│  Layer 3: Skill/MCP（原子能力层）                 │
│  - 已有的 ~500 个 Skill                          │
│  - MCP 工具（DongBoot 系列、HotServer、DUCC 等）  │
│  - 文件读写、Bash 等基础工具                     │
└─────────────────────────────────────────────────┘
```

### 3.2 Subagent 类型清单

| 类型 | 触发 Stage | 工具权限 | 上下文 |
|---|---|---|---|
| `requirements-analyst` | 1 | 只读：PRD/规范；可写：01-requirements.md | 独立 |
| `architect` | 2 | 只读：01-requirements.md、pom.xml；可写：02-design/ | 独立 |
| `coder-backend` | 3 | 全权限（含 git、mvn） | 独立 |
| `coder-test` | 3（单测） | 全权限 | 独立 |
| `reviewer` | 4 | **只读**（禁止修改代码） | 独立 |
| `tester` | 5 | 全权限（含 mvn test、hot_deploy） | 独立 |
| `deployer` | 6 | 受限（仅 deploy 类 MCP） | 独立 |
| `sre-writer` | 7 | 部分（监控盘、Runbook） | 独立 |

详细 system prompt 与 I/O schema 见 [10-subagent-spec.md](./10-subagent-spec.md)。

## 四、工具链选型

### 4.1 主控：opencode vs claude code

| 维度 | opencode | claude code |
|---|---|---|
| 多 Agent 派发 | 原生支持（`task` 工具） | 支持（Task tool） |
| Skill 加载 | 通过 `~/.claude/skills/` 自动发现 | 需手动配置 |
| 上下文管理 | 独立 context | 共享主 context |
| 适合场景 | **本方案首选** | 备选 |
| MCP 集成 | 完善 | 完善 |

**选型结论**：**优先使用 opencode**，因其 Subagent 隔离更彻底、与已有 Skill 生态无缝集成。

### 4.2 模型选择

| 阶段 | 推荐模型 | 理由 |
|---|---|---|
| 1 需求拆解 | Sonnet 4.x | 长文本理解 + 结构化输出 |
| 2 架构设计 | Opus 4.x | 决策质量优先 |
| 3 编码 | Sonnet 4.x | 速度 + 成本平衡 |
| 4 CR | Opus 4.x | 严谨性优先 |
| 5 测试 | Sonnet 4.x | 重复模板化 |
| 6 部署 | Sonnet 4.x | 流程化 |
| 7 监控 | Sonnet 4.x | 模板化 |

**降级策略**：Opus 不可用时降级为 Sonnet，但 Gate 2 / Gate 3 仍必须人工兜底。

## 五、上下文管理策略

### 5.1 三大原则

1. **隔离**：每个 Subagent 独立 context，不读主对话历史
2. **最小**：Subagent 只接收必要输入（PRD 摘录 + 上一阶段产物）
3. **可丢弃**：Subagent 输出后即丢弃，不在主对话保留完整历史

### 5.2 主对话的"超薄状态"

主对话只维护：

```yaml
current_stage: 3
current_feature: feat-2024-001-优惠券核销
gate_status:
  gate1: approved (by PM张三 at 2026-06-05 10:00)
  gate2: approved (by TL李四 at 2026-06-05 14:00)
  gate3: pending
  gate4: pending
artifacts:
  - 02-design/adr-001-coupon-architecture.md
  - 02-design/api-coupon.yaml
  - 03-code/CouponServiceImpl.java
subagents_dispatched:
  - requirements-analyst: completed (10 min)
  - architect: completed (45 min)
  - coder-backend: in_progress (15 min)
```

## 六、错误处理与降级

### 6.1 错误分类

| 错误类型 | 表现 | 处理 |
|---|---|---|
| **A 类：产物缺失** | Subagent 没生成期望文件 | 重派同一 Subagent，加重试 prompt |
| **B 类：产物质量低** | 文件存在但不符合模板 | 回退到上一 Stage 重新执行 |
| **C 类：环境异常** | MCP/工具不可用 | 降级为手动模式 + 标记异常 |
| **D 类：超出能力** | 多次重试仍失败 | 升级到人工处理 |

### 6.2 降级路径

```
A 类：自动重试（最多 2 次）→ 仍失败则降为 B 类
B 类：标记回退 → 通知 Gate 评审人 + 提供修复建议
C 类：自动切换备用 MCP → 仍不可用则暂停流水线
D 类：暂停流水线 → 分配工程师人工完成该 Stage
```

## 七、与现有流程的兼容性

### 7.1 与传统开发的兼容

- 任意 Stage 都可"切回"纯人工模式
- 人工已写的代码可直接进入 Stage 4（跳过 2/3）
- 紧急修复（hotfix）走精简版（详见 09-gates.md §5）

### 7.2 与现有工具的兼容

| 现有工具 | 兼容方式 |
|---|---|
| Git | Subagent 使用 git 工具生成 commit |
| Confluence/internal-docs | 产物导出为 md，自动同步 |
| 行云/DongBoot | 通过 MCP 集成 |
| JMeter/压测 | Stage 5 可选集成 |
| 监控/告警 | 通过 DongMonitorDashboard |

## 八、安全与合规

### 8.1 数据安全

- 禁止 Subagent 直接访问生产 DB（通过 MCP 鉴权控制）
- 禁止 Subagent 上传代码到非公司仓库
- 敏感字段（身份证、手机号）在 PRD 中脱敏后再输入

### 8.2 审计

- 所有 Subagent 调用记录日志（输入/输出/耗时）
- 所有 Gate 放行/驳回记录到审计表
- AI 生成的代码必须可追溯到 PRD 段落（通过注释锚点）
