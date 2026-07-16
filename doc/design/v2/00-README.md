# v2.0 开发方案（Development Design）

> 版本：v2.0-dev-design · 日期：2026-07-16
> 定位：把 `roadmap/` 的**战略路线图**落成**工程可执行方案** —— 讲清每个里程碑改哪些文件、加什么接口、扩什么 schema、怎么测、验收标准是什么。
> 读者：接手实现 v2.0 的工程师 / 提 PR 的社区贡献者
> 状态：开发设计稿（可随实现演进）
> **代码基线**：已按 main@`3dc05d0`（fix: thread configured temperature/max_tokens…）复核。该 commit 落地了 Q0 大部分 P0/P1 修复 —— **[01 Q0 方案](./01-q0-mainpath-hardening.md) §一 的核对表已据此更新，净剩工作收敛为 §3.3（400 分流）+ §3.8（pricing 兜底）**。其余支柱方案（02–05）的"现状锚点"行号在该 commit 后仍准确。

---

## 一、这套文档是什么

`roadmap/`（8 份）回答的是 **"下一步做什么、为什么、按什么顺序"**。
本目录（`doc/design/v2/`）回答的是 **"具体怎么造出来"**：

| 维度 | `roadmap/` | `doc/design/v2/`（本目录） |
|---|---|---|
| 关心 | 愿景、北极星、支柱、季度排期、KPI | 文件、类、接口签名、schema、YAML 字段、测试、验收 |
| 粒度 | 里程碑（M-A1…M-D5） | 里程碑内部的模块拆解与落地步骤 |
| 形式 | 产品/战略规划 | 软件工程方案 |
| 读者 | 决策者、maintainer | 实现工程师、贡献者 |
| 与代码 | 描述"能力现状" | 精确到 `sdlc/xxx/yyy.py:行为` |

它也接续 `doc/design/`（00–14，v1.0 GA 的实现设计）：**v1 设计讲地基怎么盖，v2 方案讲在地基上加盖"智能层 + 协作层 + 生态层 + 评估层"**。凡涉及既有模块，本目录直接引用 v1 设计与真实代码路径，不重述。

---

## 二、文档索引

| # | 文档 | 对应 roadmap | 覆盖里程碑 | 季度 |
|---|---|---|---|---|
| **00** | [导航总览](./00-README.md) | 00 | — | — |
| **01** | [Q0 主路径加固开发方案](./01-q0-mainpath-hardening.md) | 07 §三 | P0 稳定性加固 | Q0 前置 |
| **02** | [支柱一 · Agent 智能化开发方案](./02-pillar-agent-intelligence.md) | 03 | M-A1 ~ M-A6 | Q1–Q4 |
| **03** | [支柱二 · 团队协作开发方案](./03-pillar-collaboration.md) | 04 | M-B1 ~ M-B6 | Q2、Q4 |
| **04** | [支柱三 · 生态开放开发方案](./04-pillar-ecosystem.md) | 05 | M-C1 ~ M-C6 | Q3、Q4 |
| **05** | [支柱四 · 评估质量开发方案](./05-pillar-eval-quality.md) | 06 | M-D1 ~ M-D5 | Q1、Q3、Q4 |

> 编号策略：v2 方案自成一套 `00–05`，与 `doc/design/` 的 `00–14`（v1 GA）物理隔离，演进边界清晰。

---

## 三、里程碑 → 文档 → 主要落点速查

| 里程碑 | 一句话 | 主要新增/改动模块 | 文档 |
|---|---|---|---|
| **P0 加固** | 主路径跑通 + 探活不假绿 | `llm/client.py`·`cost.py`·`cli/*_cmd.py` | 01 |
| **M-A1** | Subagent 接 grep/shell/mcp/skill | `subagent/tools/`·`tool_schemas.py` | 02 |
| **M-A2** | Plan-Act-Reflect Runtime | `subagent/runtime.py`（新）·`stage/models.py` | 02 |
| **M-A3** | 结构化澄清（ask_user 异步） | `subagent/pool.py`·`state/`（挂起态） | 02 + 03 |
| **M-A4** | 语义记忆（sqlite-vec） | `kb/vector_store.py`（新）·`kb/memory.py` | 02 |
| **M-A5** | Orchestrator-Worker 多 agent | `subagent/orchestrator.py`（新） | 02 |
| **M-A6** | 反馈学习闭环 | `kb/adr.py`（新）·`kb/memory.py` | 02 + 05 |
| **M-B1** | 异步 Gate 闭环 | `core/run_coordinator.py`·`state/schema.py`·`cli/approve_cmd.py`（新） | 03 |
| **M-B2** | sdlc-server MVP | `server/`（新包） | 03 |
| **M-B3** | Web 控制台只读版 | `server/web/`（新） | 03 |
| **M-B4** | IM 通知闭环 | `integrations/notify/`（新） | 03 |
| **M-B5** | 组织 KB 共享 | `kb/org_kb.py`（新）·4 层加载 | 03 |
| **M-B6** | 轻量权限治理 | `server/auth.py`（新）·`gate/` | 03 |
| **M-C1** | 插件 SDK | `cli/plugin_cmd.py`（新）·`plugin/`（新包） | 04 |
| **M-C2** | 模板/Adapter 市场 | `cli/market_cmd.py`（新）·`market/`（新包） | 04 |
| **M-C3** | CI 集成 | `.github/actions/`·`cli/` 输出格式 | 04 |
| **M-C4** | MCP 工具生态 | `integrations/mcp_client.py`·`market/` | 04 |
| **M-C5** | IDE + IM 集成 | 外部薄壳（调 CLI/server） | 04 |
| **M-C6** | A2A 协议雏形 | `subagent/a2a.py`（新） | 04 |
| **M-D1** | 端到端冒烟门禁 | `tests/smoke/`（新）·CI | 05 |
| **M-D2** | Eval 框架 + 黄金集 | `eval/`（新包）·`cli/eval_cmd.py`（新） | 05 |
| **M-D3** | 跨版本回归 | `eval/regression.py`（新） | 05 |
| **M-D4** | ROI 量化 | `llm/cost.py`·`state/`·`eval/roi.py`（新） | 05 |
| **M-D5** | 反馈回流学习 | `eval/feedback.py`（新）·`kb/adr.py` | 05 + 02 |

---

## 四、贯穿全套的工程约束（每份方案都遵守）

这些约束来自 [roadmap/02 §六](../../../roadmap/02-vision-strategy.md) 的取舍原则，落到工程层：

1. **不破坏 7 抽象 / 13 包契约**：新能力优先以"新模块 + 扩展点"加入，改既有文件时保持签名向后兼容。每份方案含**"向后兼容策略"**小节。
2. **本地可跑优先**：任何新依赖必须能在 Ollama + 单机 + SQLite 下工作（如语义记忆锁定 `sqlite-vec`，不引 Milvus）。新依赖进 `pyproject.toml` 的 `optional-dependencies`，核心零新增重依赖。
3. **CLI 独立可跑**：server / 市场 / Web 全为**可选增强**，server 不可达时 CLI 降级本地。
4. **全程审计**：新增行为复用 `audit/events.py` 的 `AuditEventType`（不足时扩枚举），工具调用/审批/派发均可回放。
5. **可度量**：每个 agent 能力改动必须配 eval（支柱四），新特性附文档 —— 对齐健康度护栏。
6. **成本门控**：反思/多 agent/派发等增调用的能力，一律接 `CostTracker` 预算校验（`llm/cost.py`）。

---

## 五、跨里程碑复用点（一次投入多处受益）

方案设计刻意让以下机制**共用一套实现**，避免重复造轮子（对应 [roadmap/07 §九](../../../roadmap/07-roadmap-4q.md)）：

| 复用机制 | 落地模块 | 服务的里程碑 |
|---|---|---|
| **异步挂起 / 通知 / resume** | `state/`（挂起态）+ `core/run_coordinator.py` | M-A3 澄清 + M-B1 异步 Gate |
| **acceptance_criteria + Rule 判据** | `stage/models.py` + `rule/` | M-A2 reflect + M-D2 judge |
| **并发调度骨架** | `run_coordinator._run_pipeline_stages_concurrent` 的 `asyncio.Semaphore` | M-A5 子 agent 并发（下沉一层） |
| **SQLite + 审计数据源** | `state/store.py` + `audit/` | M-B3 控制台 + M-D4 ROI |
| **4 层加载覆盖** | `utils/config*` + 加载器 | M-B5 组织 KB + M-C2 私有 registry |
| **integrations 集成层** | `integrations/{mcp_client,skill_runner,shell_runner}` | M-A1 工具接入 + M-C4 MCP 生态 |
| **whitelist 安全底线** | `integrations/whitelist.py` | M-A1 shell 工具 + M-C4 MCP 白名单 |

---

## 六、每份支柱方案的统一结构

为便于并行开发与评审，02–05 四份支柱方案采用统一骨架：

```
一、方案目标与对应里程碑（回扣 roadmap）
二、现状锚点（真实代码：文件:行 / 现有接口）
三、逐里程碑工程方案
    对每个 M-xx：
      3.x.1 目标状态机 / 架构图
      3.x.2 新增/改动文件清单（精确路径）
      3.x.3 关键接口签名（Python/Pydantic/dataclass）
      3.x.4 数据 / schema / YAML 字段变更
      3.x.5 向后兼容策略
      3.x.6 测试要点
      3.x.7 验收标准（可勾选）
四、依赖与顺序（本支柱内 + 跨支柱）
五、风险与缓解（工程视角）
```

---

## 七、阅读路径建议

- **立即动手（Q0）**：01 → 直接转 issue。P0 加固不依赖任何其他方案。
- **实现支柱一（Q1 主线）**：02 §三 M-A1 → M-A2，配合 05 §三 M-D1/M-D2（守门）。
- **实现支柱二（Q2 主线）**：03 §三 M-B1 → M-B2 → M-B3，注意 M-A3 与 M-B1 共用挂起机制。
- **实现支柱三（Q3 主线）**：04 §三 M-C1 → M-C2。
- **实现支柱四（贯穿）**：05 全文；M-D1 与 Q0 并行启动。
- **评审方案**：任一方案的 §五（向后兼容）+ §七（验收）+ 本页 §四（工程约束）。

---

## 八、版本

| 版本 | 日期 | 变更 |
|---|---|---|
| v2.0-dev-design | 2026-07-16 | 首版：1 导航 + 1 Q0 加固 + 4 支柱工程方案，承接 `roadmap/` v2.0-planning |
