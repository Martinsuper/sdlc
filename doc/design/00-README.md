# 00. 开发设计文档 (README)

> **元项目**：设计如何开发 `sdlc` CLI 工具自身
> **作用**：本目录是 `~/claude-workspace/SDLC/prd/`（v2.2 产品 PRD）的**实现设计**——讲清楚用什么语言/库/架构/模块/接口/测试/发布来落地那个 PRD
> **读者**：自己 / 团队后续接手开发的工程师
> **状态**：设计稿（v1.0），可随实现演进

---

## 一、为什么需要这份设计

`prd/` 目录是"产品长什么样"，`doc/design/` 是"怎么造出来"。

| 维度 | prd/（v2.2） | doc/design/（本目录） |
|---|---|---|
| 关心 | 功能、流程、概念、规则 | 代码、模块、接口、依赖、测试 |
| 形式 | PRD 风格 | 软件设计风格 |
| 读者 | PM/架构师/AI Agent | 工程师 |
| 更新频率 | 需求变更时 | 实现变更时 |

---

## 二、目录

| # | 文档 | 主题 | 行数 |
|---|---|---|---|
| 00 | [README](./00-README.md) | 本页 | - |
| 01 | [架构总览](./01-architecture-overview.md) | 1 张架构图 + 6 大子系统 + 关键时序 | ~250 |
| 02 | [技术栈](./02-tech-stack.md) | Python 3.11+ / uv / 核心库 / 理由 | ~200 |
| 03 | [模块设计](./03-module-design.md) | 13 个包逐个接口/类/职责 | ~600 |
| 04 | [数据模型](./04-data-model.md) | SQLite schema + 文件 schema + 关系图 | ~300 |
| 05 | [CLI 与 API](./05-cli-and-api.md) | 19 个 CLI 命令 + 内部 Python API | ~400 |
| 06 | [Stage 执行流程](./06-stage-execution.md) | stage 生命周期 8 步 + 错误处理 | ~350 |
| 07 | [扩展机制](./07-extension-mechanism.md) | 加 Adapter/Stage/Profile/Rule 的零代码流程 | ~300 |
| 08 | [KB 引擎](./08-kb-engine.md) | sdlc init 扫描 + KB 写入 + rules 强制 | ~450 |
| 09 | [Subagent 与 LLM](./09-subagent-and-llm.md) | Subagent 池 + LLMClient + 缓存 + 回退 | ~400 |
| 10 | [状态与恢复](./10-state-and-recovery.md) | SQLite 状态机 + snapshot + resume | ~300 |
| 11 | [测试策略](./11-testing-strategy.md) | 单元/集成/E2E/性能 + CI | ~300 |
| 12 | [分发与发布](./12-distribution-and-release.md) | uv 打包 + Homebrew + PyPI | ~250 |
| 13 | [开发流程](./13-dev-workflow.md) | sdlc 自身的 git/CI/版本/CHANGELOG | ~250 |
| 14 | [里程碑与任务](./14-milestones.md) | 8 个月 4 阶段细到周的任务 | ~400 |

**总览**：~5000 行设计稿，**无任何可执行代码**（仅 YAML 模板/接口签名示意）。

---

## 三、5 分钟上手

### 3.1 一句话架构

```
sdlc (Python CLI)
  ├── CLI 层 (click + rich)
  ├── 引擎层 (Pipeline Builder / Stage Runner / Entry Detector / Gate Engine)
  ├── 数据层 (SQLite + JSON KB + JSONL 审计)
  ├── 适配层 (Adapter / Stage / Profile / Rule 注册表)
  ├── 知识层 (KB Scanner / KB Writer / Rules Enforcer)
  ├── 智能层 (LLM Client + Subagent Pool + Prompt 模板)
  └── 工具层 (MCP / Skill / Shell / HTTP 调度)
```

### 3.2 4 大子系统

1. **编排引擎**（`core/`）：把需求 → Pipeline → Stage DAG → 跑起来
2. **适配器框架**（`adapter/`, `stage/`, `profile/`）：技术栈/项目类型可插拔
3. **知识引擎**（`kb/`）：3 层记忆 + 规则强制 + 越用越准
4. **智能调度**（`llm/`, `subagent/`）：统一 LLM 调用 + Subagent 池

### 3.3 MVP 路径

按 `prd/12-implementation-roadmap.md` P1 M1-M2 走：

```
M1 Week 1-2: 脚手架 + 核心引擎
  └── sdlc run "做一个订单查询接口"  # 端到端跑通 1 个新功能

M1 Week 3-4: dongboot adapter + 1 个真实需求
  └── dongboot 编码 + 单元测试 + 部署（hot_deploy）

M2 Week 5-8: 3 Profile + 监控 + 1 团队试运行
  └── bug-fix / hotfix / refactor 跑通
```

---

## 四、设计原则

| 原则 | 体现 |
|---|---|
| **配置驱动 > 代码** | 加 Adapter/Stage/Profile/Rules 只需改 YAML |
| **Pydantic 强类型** | 所有数据结构 schema 化 |
| **失败可恢复** | SQLite 事务 + 12h resume + 审计幂等 |
| **观测优先** | 25+ 事件审计 + cost tracking + structured logging |
| **本地优先** | 默认 offline-only，LLM/MCP 可选 |
| **安全优先** | Bash 白名单 + 文件路径校验 + 权限分级 |
| **测试先行** | 关键路径覆盖率 > 80%，golden 文件对比 |
| **渐进交付** | MVP → 扩展 → 完善 → 商业化，4 阶段可独立发布 |

---

## 五、与 prd/ 关系

```
prd/  (产品需求)              doc/design/  (实现设计)
├── 00-README             ←→   00-README (本文件)
├── 01-core-concepts      ←→   01-architecture-overview
├── 02-stage-catalog      ←→   06-stage-execution + 03-module-design#stage
├── 03-entry-points       ←→   03-module-design#entry_detector
├── 04-pipeline-builder   ←→   03-module-design#pipeline_builder
├── 05-adapters           ←→   07-extension-mechanism + 03-module-design#adapter
├── 06-project-profiles   ←→   03-module-design#profile
├── 07-gate-catalog       ←→   03-module-design#gate
├── 08-state-and-meta     ←→   10-state-and-recovery + 04-data-model
├── 09-stage-template     ←→   06-stage-execution
├── 10-running-examples   ←→   11-testing-strategy (E2E 用例)
├── 11-subagent-and-skills ←→  09-subagent-and-llm
├── 12-implementation-roadmap ←→ 14-milestones (细化)
├── 13-memory-and-evolution  ←→ 08-kb-engine
├── 14-init-and-bootstrap    ←→ 08-kb-engine#scanner
└── 15-rule-and-standard-library ←→ 08-kb-engine#enforcer
```

---

## 六、阅读路径建议

- **PM / 架构师**：只看 `prd/`，本目录是工程参考
- **新入职工程师**：01 → 03 → 06 → 09 → 11（架构 → 模块 → 关键流程 → 智能层 → 测试）
- **实现 MVP**：01 → 02 → 03 → 04 → 14（按里程碑走）
- **加 Adapter / Stage**：07 + 03 中对应包
- **调试 / 优化**：10 → 11 → 03 中相关包

---

## 七、版本

- v1.0 (2026-06-05): 初版 15 份设计稿，对应 `prd/` v2.2
