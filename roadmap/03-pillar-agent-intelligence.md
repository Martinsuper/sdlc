# 03. 支柱一：Agent 智能化深化

> 版本：v2.0-planning（2026-07-16）
> 一句话：把 Subagent 从"带工具的单轮 prompt"升级为具备 **规划 → 执行 → 反思 → 协作** 的完整智能体，把记忆从"文件柜"升级为"语义大脑"。
> 对应瓶颈：[01](./01-product-assessment.md) 瓶颈 1（半个 agent）、瓶颈 3（记忆是文件柜）
> 北极星贡献：**产物采纳率**（质量因子）

---

## 一、为什么这是第一支柱

产物采纳率是北极星（可信 Pipeline 数）的质量因子，而**采纳率的天花板由 agent 智能决定**：

- 一个 design Stage 如果产出的设计漏了关键约束，人类不会采纳 → Pipeline 不可信。
- 一个 impl Stage 如果不会自检、不会调用项目已有工具，产物质量就是"单次 prompt 的运气"。

这是 sdlc 与"通用 copilot"的**根本差异点**：sdlc 不是补全代码片段，而是**编排一支懂上下文、会自省的 AI 梯队**。这个差异，只有把 agent 真正做智能才成立。

---

## 二、现状 → 目标

| 能力 | 现状（代码验证） | v2.0 目标 |
|---|---|---|
| 工具 | 仅 `read`/`write`/`ask_user`（后者返回"不可用） | 完整工具集：文件/shell/grep/MCP/skill/子agent派发 |
| 规划 | 无，直接进 tool-loop | 复杂 Stage 先 Plan（分解子任务 + 成功标准） |
| 反思 | 无，产物即最终 | Reflect：自检产物 → 不达标自动重试/修正 |
| 求助 | `ask_user` 直接失败 | 结构化 clarification：挂起 → 收集答案 → 恢复 |
| 多 agent | Pool 只顺序 invoke 单 agent | Orchestrator-Worker：主 agent 派发子 agent |
| 记忆检索 | 路径/fingerprint 匹配 | 语义检索（本地向量）+ 相关性排序注入 |
| 记忆学习 | 反模式计数入 MUST | 效果反馈回流：上线结果 → 强化/弱化决策 |

---

## 三、能力地图（5 个子方向）

```
支柱一 Agent 智能化
├── A. Agent Runtime 升级（Plan-Act-Reflect 循环）      ← 最高优先级
├── B. 工具生态接入（MCP / Skill / Shell / 子agent）
├── C. 多 Agent 协作（Orchestrator-Worker + A2A 雏形）
├── D. 语义记忆引擎（向量检索 + 相关性注入）
└── E. 反馈学习闭环（效果 → 决策强化）  ← 与支柱四共建
```

---

## 四、子方向 A：Agent Runtime 升级（Plan-Act-Reflect）

### 4.1 目标状态机

把当前"裸 tool-loop"升级为显式的三阶段循环。对**复杂 Stage**（design / impl / impact-analysis）默认启用，对**轻量 Stage**（docs / clarify）保持单轮以控成本。

```
        ┌──────────────────────────────────────────┐
        │  Stage 输入 + 注入的 KB context            │
        └───────────────────┬──────────────────────┘
                            ▼
                    ┌───────────────┐
                    │  PLAN 规划      │  产出：子任务清单 + 每步成功标准 + 预算
                    └───────┬───────┘
                            ▼
             ┌──────────────────────────┐
        ┌───▶│  ACT 执行（tool-loop）     │  调用工具完成一个子任务
        │    └───────────┬──────────────┘
        │                ▼
        │        ┌───────────────┐
        │        │ REFLECT 反思    │  对照成功标准自检产物
        │        └───────┬───────┘
        │                ▼
        │         达标？ ──No──┐
        │           │Yes       │ 修正提示回灌
        └───────────┘          │（≤ N 次）
              还有子任务？──Yes──┘
                   │No
                   ▼
            ┌───────────────┐
            │ 产物 + 自评分   │ → Artifact Store（含 reflection trace）
            └───────────────┘
```

### 4.2 关键设计决策

| 决策点 | 方案 | 理由 |
|---|---|---|
| 规划是否强制 | 按 Stage 配置 `planning: required/optional/off` | design 类必须规划，docs 类跳过省成本 |
| 反思几轮 | `max_reflect` 默认 2，可配 + 预算门控 | 防止反思死循环烧钱，回扣成本护栏 |
| 反思判据来源 | Stage 的 `acceptance_criteria` + Rule 库 MUST | 复用已有 548 规则，不重造标准 |
| 反思用什么模型 | 可配独立 `reflect_model`（可用更强模型评弱模型产物） | LLM-as-judge 的雏形，与支柱四打通 |
| trace 是否留存 | reflection trace 存 Artifact + 审计 | 可观测 + 可作为 eval 数据 |

### 4.3 落地要点

- 新增 `subagent/runtime.py`：`PlanActReflectRuntime`，与现有 `pool.py` 的 `invoke` 并存，通过 Subagent YAML 的 `runtime: single | par`（Plan-Act-Reflect）选择。
- Stage YAML 扩展字段：`planning`、`max_reflect`、`reflect_model`、`acceptance_criteria`。
- **向后兼容**：默认 `runtime: single`，存量 11 Subagent 行为不变；显式开启才升级。

---

## 五、子方向 B：工具生态接入

现状 `integrations/` 里已有 `mcp_client` / `skill_runner` / `shell_runner` / `git_client`，但**没暴露给 Subagent 的工具白名单**。这是"低垂的果实"——集成层已存在，只差把它接进 agent 的工具循环。

### 5.1 目标工具集

| 工具 | 来源 | 用途 | 安全约束 |
|---|---|---|---|
| `read` / `write` | 已有 | 文件读写 | 路径白名单（限项目内） |
| `grep` / `glob` | 新增（薄封装） | 代码检索定位 | 只读 |
| `shell` | `shell_runner` + `whitelist` | 跑 build/test/lint | **复用已有命令白名单**（allowlist + 阻断 shell 操作符/路径穿越） |
| `mcp_call` | `mcp_client` | 调用外部 MCP 工具（如 dongboot_analyzer） | MCP server 白名单 |
| `skill` | `skill_runner` | 调用已装 Skill | Skill 白名单 |
| `ask_user` | 重做（见子方向 C 的 clarification） | 向人求助 | 异步挂起，不再直接失败 |
| `delegate` | 新增 | 派发子 agent | 见子方向 C |

### 5.2 关键要点

- **安全是前提**：`shell`/`mcp_call` 必须走已有 `whitelist.py` 与配置的 server 白名单，默认最小权限。这是开源工具的信任底线。
- **工具授权分级**：Subagent YAML 的 `tools:` 字段决定该 agent 能用哪些工具（reviewer 不需要 write，coder 需要 shell）。已有字段，只需扩充可选值。
- **成本/审计**：每次工具调用记审计事件，`shell`/`mcp_call` 的耗时纳入 stage 预算。

---

## 六、子方向 C：多 Agent 协作

### 6.1 Orchestrator-Worker 模式

把 SubagentPool 从"顺序调用单 agent"升级为"主 agent 可派发多个子 agent 并汇总"。这是复杂 Stage 提质的关键（如 design 可派发"数据库设计"+"接口设计"+"风险评估"三个子 agent 并行）。

```
              ┌────────────────────────┐
              │  Orchestrator (architect)│  规划 → 拆成 3 个独立子任务
              └───────────┬────────────┘
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌─────────┐ ┌─────────┐ ┌─────────┐
        │ Worker: │ │ Worker: │ │ Worker: │  并行执行（复用已有并发调度）
        │ DB设计   │ │ 接口设计 │ │ 风险评估 │
        └────┬────┘ └────┬────┘ └────┬────┘
             └───────────┼───────────┘
                         ▼
              ┌────────────────────────┐
              │ Orchestrator 汇总 + 一致性│  合并 + 交叉校验 → 统一产物
              └────────────────────────┘
```

### 6.2 设计要点

- 复用 `run_coordinator` 已有的 `asyncio.Semaphore` 并发骨架，把"stage 级并发"下沉一层到"子 agent 级并发"。
- `delegate` 工具：主 agent 通过它派发，参数含子 agent id + 子任务 + 成功标准。
- **防失控**：子 agent 不能再无限派发（`max_delegate_depth` 默认 1），预算在派发时按比例分配。
- **A2A 雏形**：先做进程内的 agent 协作，把交互契约（任务/结果/成功标准）标准化为 schema，为支柱三的 A2A 跨进程协议打基础（见 [05](./05-pillar-ecosystem.md)）。

### 6.3 结构化澄清（重做 ask_user）

当前 `ask_user` 直接返回"不可用"，是断裂点。重做为**异步澄清**，与支柱二的异步 Gate 共用机制：

```
agent 调用 ask_user(question)
        ▼
Pipeline 进入 WAITING_CLARIFICATION 状态（持久化）
        ▼
问题推送到通知渠道（终端 / Web / IM —— 见支柱二）
        ▼
人类回答 → 写回 → Pipeline 自动 resume，答案注入 context
```

---

## 七、子方向 D：语义记忆引擎

### 7.1 现状痛点

L2 KB（`doc/kb/`）检索靠路径与 fingerprint，注入 Subagent 的 context 是"关键词/路径匹配"，长 KB 下噪声大、相关性差。

### 7.2 目标：本地向量语义检索

| 设计点 | 方案 | 理由（回扣开源约束） |
|---|---|---|
| 向量存储 | **sqlite-vec**（SQLite 扩展） | 复用已有 SQLite 基建，**零外部依赖、本地可跑**，不违反"本地可跑"原则 |
| Embedding | 可配：本地（Ollama embedding）/ 云（可选） | 默认本地零成本，云为增强 |
| 检索单元 | KB 文档切块（section 级）+ 元数据（类型/时间/来源 stage） | 细粒度召回 |
| 注入策略 | 按 stage 角色 + 语义相关性 top-k + 时间衰减 | reviewer 召回 MUST，coder 召回 component-catalog，相关性排序 |
| 增量更新 | KB 写入时增量 embed（复用 Reconciler 的 diff-only） | 性能，不全量重算 |

### 7.3 关键要点

- **不引入重型向量服务**（如 Milvus/独立向量 DB）—— 违反本地可跑。sqlite-vec 是嵌入式的正解。
- 语义检索是"增强"而非"替换"：路径/fingerprint 匹配保留作为兜底和精确命中。
- 检索质量本身要进 eval（支柱四）：度量"注入的 context 是否真的相关" = KB 相关上下文命中率 KPI。

---

## 八、子方向 E：反馈学习闭环（与支柱四共建）

这是"越用越好用"从口号变数据的核心，也是支柱一与支柱四的交汇点。详细评估机制见 [06](./06-pillar-eval-quality.md)，此处只讲 agent 侧如何**消费**反馈。

### 8.1 反馈信号来源

```
上线后信号（客观）          人类信号（主观）
├── 部署成功率              ├── Gate 通过/拒绝 + 理由
├── 上线后错误率变化         ├── 产物是否被采纳/改动幅度
├── 回滚事件               └── CR 中被指出的问题
└── 监控告警
        │                        │
        └────────┬───────────────┘
                 ▼
         反馈归因到"哪个决策/模式/agent"
                 ▼
    ┌────────────────────────────┐
    │ L2/L3 KB 决策记录带上"效果分" │
    └────────────────────────────┘
                 ▼
    下次同类任务：高分决策/模式优先注入，低分反模式主动规避
```

### 8.2 与现有机制的衔接

- 现有"反模式被拒 ≥3 次入 MUST"是**计数式**学习，升级为**效果加权**：一次拒绝 + 一次线上事故的权重 > 三次无后果的拒绝。
- ADR（决策记录）扩展 `outcome` 字段：记录该决策上线后的效果，形成"决策 → 效果"的可学习数据。
- **闭环验证**：反馈学习是否真的让产物变好，由支柱四的跨版本回归证明，避免"自我强化了错误偏好"。

---

## 九、里程碑与验收（本支柱视角，季度归属见 [07](./07-roadmap-4q.md)）

| 里程碑 | 内容 | 验收标准 |
|---|---|---|
| **M-A1** | 工具生态接入（子方向 B） | Subagent 可安全调用 grep/shell/mcp/skill；全走白名单；有审计 |
| **M-A2** | Plan-Act-Reflect Runtime（子方向 A） | design/impl Stage 默认启用；reflection trace 可查；eval 显示采纳率↑ |
| **M-A3** | 结构化澄清（子方向 C 前半） | `ask_user` 触发异步挂起 → 回答 → resume，全链路通 |
| **M-A4** | 语义记忆引擎（子方向 D） | sqlite-vec 落地；本地 embedding 可跑；KB 相关命中率 ≥ 75% |
| **M-A5** | Orchestrator-Worker（子方向 C 后半） | design 可派发并行子 agent 并汇总；有防失控护栏 |
| **M-A6** | 反馈学习闭环（子方向 E） | ADR 带 outcome；效果加权生效；回归证明产物质量不退化 |

### 关键 KPI

| 指标 | 基线 | 目标 |
|---|---|---|
| Stage 产物一次通过率（eval 判定） | 未度量 | ≥ 85% |
| KB 相关上下文命中率 | 未度量 | ≥ 75% |
| 复杂 Stage 采纳率（人类合入/放行） | 未度量 | ≥ 80% |
| 单次复杂 Stage 成本 | GA 基线 | ≤ 1.5×（反思/协作会增调用，用预算门控） |

---

## 十、风险

| 风险 | 缓解 |
|---|---|
| 反思/多 agent 大幅增加成本与时延 | 按 Stage 分级启用；预算门控；轻量 Stage 保持单轮 |
| 语义检索引入依赖违反"本地可跑" | 锁定 sqlite-vec + 本地 embedding，云端仅可选增强 |
| agent 自主性提升带来不可控行为 | 工具全走白名单；派发深度受限；全程审计可回放 |
| 反馈学习强化了错误偏好 | 支柱四回归把关；效果分需足够样本才生效 |
| 提升不达预期（模型天花板） | 每子方向独立可交付、独立 eval，不押单一大改 |

---

## 十一、小结

支柱一是差异化护城河：让每个 Subagent 会规划、会用工具、会反思、会协作、有语义记忆、能从效果学习。它直接抬升北极星的质量因子（采纳率）。落地遵循**分级启用 + 预算门控 + 全程审计 + eval 验证**，在提升智能的同时守住成本与安全。

下一篇：[04-支柱二 团队协作与企业化](./04-pillar-collaboration.md)。
