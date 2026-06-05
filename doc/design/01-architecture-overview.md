# 01. 架构总览 (v1.0)

> 1 张架构图 + 6 大子系统 + 关键时序

---

## 一、系统架构图

```
┌────────────────────────────────────────────────────────────────────┐
│                       User / IDE / CI                              │
│              sdlc run / init / status / resume / rule              │
└───────────────────────────┬────────────────────────────────────────┘
                            │ CLI (click)
┌───────────────────────────▼────────────────────────────────────────┐
│                       CLI 层 (cli/)                                │
│  run / init / status / resume / trace / rule / kb / stage / agent  │
└───────────────────────────┬────────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────────┐
│                      引擎层 (core/)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │ Entry       │  │ Pipeline    │  │ Stage       │  │ Gate       │  │
│  │ Detector    │→ │ Builder     │→ │ Runner      │→ │ Engine     │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │
│         ↑                ↑                ↑              ↑          │
│         │                │                │              │          │
│         └────────────────┴────────────────┴──────────────┘          │
│                       State Store (SQLite)                         │
└──────┬─────────────┬─────────────┬─────────────┬──────────────────┘
       │             │             │             │
┌──────▼────┐  ┌─────▼─────┐  ┌────▼─────┐  ┌────▼─────────────┐
│ 适配器框架 │  │  知识引擎  │  │ 智能调度 │  │   工具与外部      │
│ adapter/  │  │   kb/     │  │ subagent │  │   adapters/      │
│ stage/    │  │ scanner   │  │ + llm/   │  │   integrations/  │
│ profile/  │  │ writer    │  │ client   │  │   mcp/ skill/    │
│ rule/     │  │ enforcer  │  │ pool     │  │   shell/ http    │
└───────────┘  └───────────┘  └──────────┘  └──────────────────┘
       │             │             │             │
       └─────────────┴─────────────┴─────────────┘
                     │
         ┌───────────▼───────────┐
         │   Audit / Logging    │
         │   (JSONL + rich)     │
         └───────────────────────┘
```

---

## 二、6 大子系统

### 2.1 编排引擎（`core/`）

**职责**：把用户输入变成可执行的 Pipeline，再执行。

| 组件 | 输入 | 输出 | 关键算法 |
|---|---|---|---|
| `EntryDetector` | 用户原始文本 / 文件 | `EntryPoint` | 关键词 + 结构化检测 |
| `PipelineBuilder` | `EntryPoint` + `Profile` + Adapter 检测结果 | `Pipeline` (DAG) | 7 步算法（见 03） |
| `StageRunner` | `Pipeline` | 执行结果 + artifacts | 状态机 + 8 步生命周期 |
| `GateEngine` | 完成的 stage + 触发条件 | `GateDecision` | 6 触发模式 |

**数据流**：
```
input → EntryDetector → PipelineBuilder → Stage DAG
                                           ↓
                                    StageRunner (循环)
                                           ↓
                                      artifacts
                                           ↓
                                       GateEngine
                                           ↓
                                    下一 stage / 暂停
```

### 2.2 适配器框架（`adapter/`, `stage/`, `profile/`, `rule/`）

**职责**：把"通用能力"映射到"具体技术栈"。

| 组件 | 加载对象 | 存储位置 |
|---|---|---|
| `AdapterRegistry` | adapter YAML | `~/.sdlc/adapters/` 或 `stages/dongboot.yaml` |
| `StageCatalog` | stage YAML | `~/.sdlc/stages/` |
| `ProfileRegistry` | profile YAML | `~/.sdlc/profiles/` |
| `RuleEngine` | rules YAML | `doc/kb/rules/*.yaml` |

**零代码扩展**：加新 Adapter/Stage/Profile/Rule 只写 YAML，不碰 Python。

### 2.3 知识引擎（`kb/`）

**职责**：3 层记忆 + 自动更新 + 规则强制。

| 组件 | 作用 |
|---|---|
| `Scanner` | 扫描项目代码/文件/配置，生成 KB 骨架 |
| `KnowledgeBase` | 读/写/查询 11 个 KB 文件 + 子目录 |
| `Writer` | 接收 stage 输出，diff-only 写入 KB |
| `RuleEnforcer` | 在 stage 前后注入规则 + CR/lint 校验 |
| `ExceptionManager` | 临时豁免 + 过期告警 |

**v2.1 / v2.2 核心**，详见 `08-kb-engine.md`。

### 2.4 智能调度（`llm/`, `subagent/`）

**职责**：统一调用 LLM + 调度 Subagent。

| 组件 | 作用 |
|---|---|
| `LLMClient` | Anthropic 主 + OpenAI 回退 + 多模型路由 |
| `PromptRenderer` | Jinja2 模板 + 上下文注入 |
| `Cache` | prompt+context → response 缓存 |
| `SubagentPool` | 11 个 Subagent 注册 + 调度 |
| `ClaudeCaller` | 调用外部 Claude/Codex 进程 |

详见 `09-subagent-and-llm.md`。

### 2.5 状态与恢复（`state/`）

**职责**：持久化 Pipeline 状态 + 12h resume。

| 组件 | 作用 |
|---|---|
| `StateStore` | SQLite 封装（pipelines / stages / artifacts） |
| `Snapshotter` | 每 stage 完成后生成可恢复快照 |
| `ResumeManager` | 12h token 验证 + 状态恢复 |
| `AuditLogger` | JSONL append-only + 25+ 事件类型 |

详见 `10-state-and-recovery.md`。

### 2.6 工具与外部集成（`integrations/`）

**职责**：与外部世界交互。

| 工具 | 用途 |
|---|---|
| `MCPClient` | dongboot_analyzer / dongboothotserver 等 |
| `SkillRunner` | 调 opencode/claude 内置 skill |
| `ShellRunner` | 受限 shell 命令（白名单） |
| `HTTPClient` | 异步 HTTP/httpx（带重试+限流） |
| `GitClient` | git diff/commit/PR |

---

## 三、关键时序

### 3.1 `sdlc run "做一个订单查询接口"` 端到端

```
User
  ↓
CLI 接收 input
  ↓
EntryDetector.detect(input) → EntryPoint(idea/new-feature)
  ↓
AdapterDetector.detect() → Adapter(dongboot)
  ↓
ProfileResolver.resolve() → Profile(new-feature)
  ↓
PipelineBuilder.build() → Pipeline(7 stages)
  ↓
StageRunner.run(pipeline) loop:
  ├─ s-clarify → SubAgent(requirements-analyst) → LLM → artifact(prd)
  ├─ Gate-1 (PM/BA, 4h, always)
  ├─ s-design → SubAgent(architect) → LLM → artifact(architecture)
  ├─ Gate-2 (Architect, 8h, always)
  ├─ s-impl-backend → SubAgent(coder-jvm-dongboot) → LLM + Skills → artifact(code)
  ├─ s-unit-test → SubAgent(tester-unit) → LLM + DongMock → artifact(tests)
  ├─ s-cr → SubAgent(reviewer) → LLM + RuleEnforcer → artifact(review-report)
  ├─ Gate-3 (TL, on_severity P1)
  ├─ s-package → deployer → artifact(jar)
  ├─ s-deploy → deployer + MCP(hot_deploy) → artifact(deployment)
  └─ s-monitor-setup → sre-writer → LLM → artifact(runbook)
  ↓
  每 stage 后:
  ├─ StateStore.commit()
  ├─ AuditLogger.emit()
  └─ KBWriter.update()
  ↓
Pipeline.completed
  ↓
CLI 输出回放历史链接
```

### 3.2 `sdlc init` 端到端

```
User 在项目根目录运行 sdlc init
  ↓
Scanner.scan() 7 阶段:
  ├─ Stage 1: 基础扫描 (文件树 + manifest)
  ├─ Stage 2: 技术栈检测 (package.json/pom.xml/...)
  ├─ Stage 3: 组件提取 (依赖图)
  ├─ Stage 4: 规范反推 (lint/format/CI)
  ├─ Stage 5: 知识导入 (读已有 doc/)
  ├─ Stage 6: AI 深度分析 (调 LLM)
  └─ Stage 7: 写入 doc/kb/ (11 文件)
  ↓
AdapterDetector → 推荐 Adapter
ProfileResolver → 推荐 Profile
  ↓
生成 CLAUDE.md / AGENTS.md
  ↓
输出摘要 + 待确认项
  ↓
Human review conventions.md
  ↓
完成
```

### 3.3 `sdlc resume <id>` 恢复

```
User: sdlc resume feat-001-2026-06-05
  ↓
ResumeManager.load(id)
  ↓
验证 token + expires_at
  ↓
StateStore.load(id) → snapshot
  ↓
找到 last_completed_stage
  ↓
重算 DAG next stages
  ↓
StageRunner.resume() 继续
```

---

## 四、数据流概览

```
外部输入                内存对象                    持久化
────────                ───────                    ──────
用户文本    ──→  EntryPoint   ──→  Pipeline meta (SQLite)
                              ──→  audit log (JSONL)
                              ──→  meta.json
代码文件    ──→  RepoContext  ──→  cache/*.json
                              ──→  KB fingerprint

Adapter 检测 ──→  AdapterDef  ──→  registry 内存
Stage 加载   ──→  StageDef    ──→  registry 内存
Profile 解析 ──→  ProfileDef  ──→  registry 内存

Stage 执行  ──→  StageRun     ──→  stages table (SQLite)
                              ──→  artifact_id → artifacts table
                              ──→  KB 文件 (doc/kb/*.md)
                              ──→  audit event

Subagent    ──→  LLMRequest   ──→  cache (SQLite)
                              ──→  cost 表 (SQLite)
```

---

## 五、依赖方向（强约束）

```
CLI ──→ Engine ──→ Adapter/Stage/Profile/Rule
                  ↓
                 KB / Subagent / LLM
                  ↓
                 Integrations (MCP/Skill/Shell/HTTP)
                  ↓
                 State / Audit

禁止反向依赖：
- KB 不能 import Adapter
- Adapter 不能 import CLI
- Integrations 不能 import Engine

允许的横切：
- 所有层可 import utils/
- Audit 可被任意层调用
- 错误统一在 utils/exceptions.py 定义
```

---

## 六、关键不变量（永远成立的约束）

1. **单一事实源**：`meta.json` + SQLite 两份必须一致
2. **审计完整**：每个状态变更必有 audit event
3. **KB 写入幂等**：相同 stage 输出写两次结果相同
4. **Stage 失败不留半成品**：用 SQLite 事务保证 atomic
5. **Subagent 隔离**：每个 stage 的 LLM call 独立，不共享 context
6. **配置可重现**：相同 Pipeline 配置文件 + 相同 KB 状态 → 相同结果

---

## 七、扩展点

| 想加什么 | 改哪 |
|---|---|
| 新技术栈（Rust/Go） | `adapters/rust.yaml`（零代码） |
| 新项目类型 | `profiles/security.yaml` |
| 新 Stage | `stages/extra/x.yaml` |
| 新 Subagent | `subagents/registry.yaml` + `prompts/x.md` |
| 新规则 | `doc/kb/rules/MUST.yaml` 加一条 |
| 新 Gate | `gates/x.yaml` |
| 新 Skill | `~/.claude/skills/x`（依赖外部） |

详见 `07-extension-mechanism.md`。

---

## 八、版本

- v1.0 (2026-06-05): 初版
