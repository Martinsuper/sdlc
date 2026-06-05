# AI 驱动的 SDLC 详细设计方案 (v2.2 - 通用版)

> 版本：v2.2  
> 适用：任意技术栈、任意项目类型、任意入口点  
> 核心思想：7 抽象层 + 可插拔 Stage 库 + 自动 Pipeline 构建 + 3 层记忆 + 结构化规则/规范/架构知识库

---

## 目录

| # | 文档 | 主题 |
|---|---|---|
| 00 | [README](./00-README.md) | 总览与导航 |
| **01** | **[核心概念](./01-core-concepts.md)** | **7 抽象：Stage / Artifact / Gate / Pipeline / EntryPoint / Adapter / Profile** |
| 02 | [Stage 库](./02-stage-catalog.md) | 22 标准阶段（需求/设计/编码/测试/部署/运维/维护） |
| 03 | [入口点](./03-entry-points.md) | 12 种入口模式：从任意阶段开始 |
| 04 | [Pipeline 构建器](./04-pipeline-builder.md) | 从 EntryPoint + Profile 自动构建 Pipeline |
| 05 | [适配器](./05-adapters.md) | 18 技术栈适配器：DongBoot / Spring / Django / Node / Go / Frontend ... |
| 06 | [项目 Profile](./06-project-profiles.md) | 14 种项目类型：new-feature / bug-fix / refactor / hotfix / migration / ... |
| 07 | [Gate 库](./07-gate-catalog.md) | 10+ 人工 Gate 模板与编排 |
| 08 | [状态与审计](./08-state-and-meta.md) | meta.json / 审计日志 / 追溯 / resume |
| 09 | [Stage 模板](./09-stage-template.md) | 如何新增一个 Stage（不写代码） |
| 10 | [运行示例](./10-running-examples.md) | 10 个真实场景：idea / PRD / code / bug / hotfix / ... |
| 11 | [Subagent 与 Skill](./11-subagent-and-skills.md) | 通用 Subagent 设计 + Skill 调用机制 |
| 12 | [落地路线图](./12-implementation-roadmap.md) | 8 个月四阶段（含 P2 记忆层），适配任意规模团队 |
| **13** | **[记忆与进化](./13-memory-and-evolution.md)** | **3 层记忆架构 + 项目 KB + 越用越好用** |
| **14** | **[项目初始化与引导](./14-init-and-bootstrap.md)** | **`sdlc init` 一行命令自动分析项目 + 生成 KB 骨架** |
| **15** | **[规则/规范/架构知识库](./15-rule-and-standard-library.md)** | **结构化强约束规则 + 流程规范 + 架构知识库（v2.2）** |

**推荐阅读**：01（必读）→ 03/04（理解入口与构建）→ 05/06（按需选 Adapter 和 Profile）→ 10（看示例）→ 其他按需。

---

## 一、设计目标（v2.0）

| 目标 | 说明 |
|---|---|
| **任意技术栈** | Java/Go/Python/Node/前端/移动/数据/基础设施全覆盖 |
| **任意项目类型** | 新功能 / Bug 修复 / 重构 / 迁移 / 性能优化 / 安全 / 文档 / 测试 / 部署 / 监控 / 紧急修复 |
| **任意入口点** | 从 idea / PRD / 设计 / 代码 / bug / 任何阶段开始 |
| **任意规模** | 1 人项目到 100 人团队 |
| **任意 Gate 策略** | 严格（4 Gate）到宽松（0 Gate）可配 |
| **记忆与进化** | **3 层 KB + 经验自动沉淀，越用越好用** |
| **自动项目引导** | **`sdlc init` 一行命令让 SDLC 系统读懂你的项目** |
| **上下文自动更新** | **每 stage 完成后自动更新 KB / components / patterns / antipatterns** |

## 二、与 v1.0 的差异

| 维度 | v1.0 | v2.0 |
|---|---|---|
| 阶段数 | 固定 7 阶段 | 18+ 可选阶段，按需组合 |
| 技术栈 | 硬编码 DongBoot | Adapter 机制（多语言） |
| 项目类型 | 隐式（new feature） | 12 种 Profile 显式 |
| 入口 | 必须从 Stage 1 | 12 种 EntryPoint，自动检测 |
| Pipeline | 固定 DAG | 运行时构建 |
| Gate | 固定 4 个 | 10+ 可选 + 自定义 |
| 适配新场景 | 改主流程 | 加 Profile / Stage / Adapter（不破坏） |

## 三、最小可执行示例

**用户输入**（任意技术栈、任意入口、任意项目）：

```
"我有一个 Python Flask 项目，加一个新接口：
POST /api/orders，接受 {user_id, items}，返回订单详情。
DBA 说：先评估影响面再写代码。"
```

**AI 自动处理**：

```
1. 检测 EntryPoint = "prd"（用户给了接口定义）
2. 检测 Adapter = "python-flask"（基于工程文件）
3. 选择 Profile = "new-feature"
4. 构建 Pipeline（依据"先评估影响面"）：
   - clarify (轻量) → impact-analysis → design → implement → test → review → deploy → monitor
5. 派发 Subagent 执行
6. 在 4 个关键 Gate 等待人工放行
```

**用户输入**（不同入口）：

```
"线上 OOM，紧急修复"
```
→ EntryPoint=`hotfix`, Adapter=自动检测, Profile=`hotfix`, Pipeline = 5 阶段精简版

```
"帮我评审这段代码：[code]"
```
→ EntryPoint=`review`, Pipeline = 1 阶段（仅 review）

```
"加个监控，订单创建错误率超 1% 告警"
```
→ EntryPoint=`monitor`, Pipeline = 1-2 阶段

## 四、核心架构

```
                          ┌─────────────────┐
                          │  用户输入/请求  │
                          └────────┬────────┘
                                   ↓
                          ┌─────────────────┐
                          │  EntryPoint     │   ← 检测"用户从哪来"
                          │  Detection      │
                          └────────┬────────┘
                                   ↓
                          ┌─────────────────┐
                          │  Profile        │   ← 选"项目类型"
                          │  Selection      │
                          └────────┬────────┘
                                   ↓
                          ┌─────────────────┐
                          │  Adapter        │   ← 选"技术栈"
                          │  Detection      │
                          └────────┬────────┘
                                   ↓
                          ┌─────────────────┐
                          │  Pipeline       │   ← 自动构建"流水线"
                          │  Builder        │
                          └────────┬────────┘
                                   ↓
                          ┌─────────────────┐
                          │  Stage DAG      │   ← 跑阶段
                          │  Execution      │
                          └────────┬────────┘
                                   ↓
                          ┌─────────────────┐
                          │  Artifact Store │   ← 产物归档
                          │  + Audit Log    │
                          └─────────────────┘
```

详见 [01-core-concepts.md](./01-core-concepts.md)。

## 五、3 分钟上手

### 场景 A：我想做一个新功能

```
你：我想做一个新功能：[描述]
AI：
  1. 检测：EntryPoint=idea, Profile=new-feature
  2. 询问技术栈/项目类型
  3. 自动构建 Pipeline
  4. 开始跑 Stage 1（clarify）
```

### 场景 B：我有 PRD，直接开发

```
你：[贴 PRD 或 PRD 链接]
AI：
  1. EntryPoint=prd
  2. 直接跳到 Stage design
  3. 跑后续
```

### 场景 C：我有代码，帮我 CR + 测试 + 部署

```
你：[贴代码或代码路径]
AI：
  1. EntryPoint=code, 检测 Adapter
  2. Pipeline = [review, test, deploy]
  3. 跑
```

### 场景 D：紧急 hotfix

```
你：线上 P0 故障：[描述]
AI：
  1. EntryPoint=hotfix
  2. 精简 Pipeline = [diagnose, fix, test, deploy, verify]
  3. 全自动，3h 内完成
```

更多场景见 [10-running-examples.md](./10-running-examples.md)。

## 六、关键约束

- **不绑死技术栈**：所有技术栈特定逻辑在 Adapter 中，主流程零技术栈知识
- **不绑死阶段顺序**：Pipeline 是 DAG，不是固定顺序
- **不绑死入口**：用户从任何阶段开始都可以
- **不绑死 Gate 数量**：根据 Profile / 用户偏好配置

## 七、3 大新功能（v2.1 增强）

### 1. 记忆与进化（`13-memory-and-evolution.md`）

- **3 层记忆架构**：短期（Pipeline 内）/ 中期（项目 KB `doc/kb/`）/ 长期（全局 `~/.sdlc/kb/`）
- **项目知识库**：每个项目自动维护架构/组件/规范/模式/反模式/ADR/Runbook/经验
- **越用越好用**：CR/测试/事故每次拒绝自动入反模式库，重复实现自动抽象为模式
- **Subagent 自适应**：根据历史学习每个项目的偏好

### 2. 自动项目引导（`14-init-and-bootstrap.md`）

```bash
cd my-project
sdlc init          # 一行命令自动分析 + 生成 KB 骨架
```

- 扫描技术栈、组件、规范、知识资产
- 生成 `doc/kb/` 全套（11 文件）
- 推荐 Adapter + Profile
- 生成 `CLAUDE.md` / `AGENTS.md` 供任何 AI 读懂
- 支持模板复用（`--template=team-java-dongboot`）

### 3. 上下文自动更新（每 stage 必更）

| Stage | 自动更新 |
|-------|----------|
| s-clarify | glossary.md, conventions.md |
| s-design | architecture.md, decisions/ |
| s-impl | components.md, patterns.md, antipatterns.md |
| s-cr | antipatterns.md |
| s-test | patterns.md, antipatterns.md |
| s-deploy | runbook/ |
| s-mon | runbook/, components.md |
| hotfix | lessons-learned.md, antipatterns.md |

## 八、版本

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-06-05 | 初版（7 阶段 + DongBoot） |
| v2.0 | 2026-06-05 | 重构为通用版（7 抽象 + 22 Stage + 14 Profile + 18 Adapter） |
| v2.1 | 2026-06-05 | + 3 层记忆/KB + sdlc init + 上下文自动更新 |
| v2.2 | 2026-06-05 | + 结构化规则/规范/架构知识库（`doc/kb/rules/` + `standards/` + `architecture/`） |

---

## 九、3 大新功能（v2.2 增强）

### 1. 结构化强约束规则库（`15-rule-and-standard-library.md` §三）

```yaml
# doc/kb/rules/MUST.yaml
- id: NO-THREAD-SLEEP
  level: MUST
  pattern: "java\\.lang\\.Thread\\.sleep"
  message: "禁止 Thread.sleep；用 DongThread"
  enforcer: [cr, lint]
  since: 2026-01-01
```

- 强制级别：**MUST / SHOULD / MAY**（RFC 2119）
- 强制器：**cr / lint / ci / runtime** 4 种
- 例外管理：临时 override 带 `expires_at`，自动过期告警
- 自动抽象：同反模式被拒 ≥3 次自动入 MUST

### 2. 流程级开发规范（`15-rule-and-standard-library.md` §四）

```
doc/kb/standards/
├── coding-style.md     # 命名/注释/工具
├── git-workflow.md     # 分支/commit/PR
├── review-process.md   # CR 流程/SLA
├── testing.md          # TDD/覆盖率/E2E
├── security.md         # 安全开发
├── release.md          # 发布流程
└── oncall.md           # 值班规范
```

### 3. 结构化架构知识库（`15-rule-and-standard-library.md` §五）

```
doc/kb/architecture/
├── component-catalog.md   # 组件清单（表）
├── dependency-graph.md    # 依赖图（Mermaid）
├── tech-radar.md          # adopt/trial/hold 矩阵
├── non-functional.md      # 可用性/性能/RTO/RPO
├── threats.md             # STRIDE 威胁模型
└── ...
```

- Subagent 启动时**按角色**自动注入（如 reviewer 加载全部 MUST，coder-backend 加载 component-catalog）
- Adapter 配置 `enforce_rules: true` 开启规则强制
- 例外管理 + 漂移防护 + 自动同步

**关联**：`05-adapters.md` 新增 `enforce_rules`/`rule_sets`/`required_kb` 字段；`09-stage-template.md` 新增 `pre_kb_load`/`post_kb_update` 字段；`13-memory-and-evolution.md` L2 KB 目录结构同步。
