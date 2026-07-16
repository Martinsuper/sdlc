# 02. 支柱一 · Agent 智能化开发方案

> 版本：v2.0-dev-design（2026-07-16）
> 承接：[roadmap/03 支柱一](../../../roadmap/03-pillar-agent-intelligence.md)
> 覆盖里程碑：M-A1（工具生态）、M-A2（Plan-Act-Reflect）、M-A3（结构化澄清）、M-A4（语义记忆）、M-A5（Orchestrator-Worker）、M-A6（反馈学习）
> 一句话：把 `SubagentPool` 从"带 3 个工具的单轮 tool-loop"升级为会规划、会用工具、会反思、会协作、有语义记忆、能从效果学习的智能体。

---

## 一、方案目标与对应里程碑

| 里程碑 | 目标 | 季度 | 主要落点 |
|---|---|---|---|
| M-A1 | Subagent 安全调用 grep/glob/shell/mcp/skill | Q1 | `subagent/tools/`（新）·`tool_schemas.py`·`pool.py` |
| M-A2 | 复杂 Stage 默认 Plan→Act→Reflect | Q1 | `subagent/runtime.py`（新）·`stage/models.py` |
| M-A3 | ask_user 异步挂起→回答→resume | Q2 | `pool.py`·`state/`·与 [03 M-B1] 共用机制 |
| M-A4 | sqlite-vec 语义检索注入 | Q2 | `kb/vector_store.py`（新）·`kb/memory.py` |
| M-A5 | 主 agent 派发并行子 agent | Q3 | `subagent/orchestrator.py`（新） |
| M-A6 | 上线效果→决策效果分→agent 消费 | Q4 | `kb/adr.py`（新）·与 [05 M-D5] 共建 |

---

## 二、现状锚点（真实代码）

| 关注点 | 文件:行 | 现状 |
|---|---|---|
| tool-loop | `sdlc/subagent/pool.py:31-101` `invoke()` | for i in range(max_iter)：调 LLM → 若有 tool_use 则执行 → 追加 messages → 循环 |
| 工具执行 | `pool.py:168-244` `_execute_tool` | 仅 `read`/`write`/`list`/`ask_user`；`ask_user` 返回"交互不可用" |
| 工具 schema | `subagent/tool_schemas.py:9` `TOOL_SCHEMAS` | 只定义 4 个工具；**注意 `invoke` 目前未把 schema 传给 `CompletionRequest.tools`** |
| 路径安全 | `pool.py:143-166` `_validate_path` | 拒绝绝对路径/`..`/`~`，限项目内 |
| Subagent 模型 | `subagent/models.py:6` `Subagent` | `tools: list[str]`（授权工具名）、`max_iter=10` |
| Stage 定义 | `stage/models.py:22` `StageDef` | 无 planning/reflect 字段 |
| 集成层（现成） | `integrations/{mcp_client,skill_runner,shell_runner,whitelist}.py` | 已实现，未接入 agent 工具循环 |
| 记忆 | `kb/memory.py` `MemoryL2` | `on_stage_complete` 写 KB；检索靠路径/fingerprint |
| 并发骨架 | `core/run_coordinator.py:221` `_run_pipeline_stages_concurrent` | `asyncio.Semaphore` stage 级并发，可下沉复用 |

> **重要现状**：`pool.py:41-52` 构造 `CompletionRequest` 时**没有传 `tools=`**——即当前 tool-loop 实际拿不到工具定义。M-A1 的第一步是把工具 schema 真正接进请求。

---

## 三、逐里程碑工程方案

### 3.1 M-A1：工具生态接入

#### 3.1.1 目标

`integrations/` 已有 `mcp_client`/`skill_runner`/`shell_runner`/`whitelist`，只差"暴露给 agent 的工具白名单 + 接进 tool-loop"。这是最低垂的果实。

```
Subagent(tools=[read,write,grep,shell,mcp_call,skill])
        ▼
pool.invoke → CompletionRequest(tools=resolve_schemas(agent.tools))  ← 现状缺失，补上
        ▼
LLM 返回 tool_use → ToolRegistry.execute(name, input, ctx)
        ▼          每个 tool 走各自安全约束（whitelist / server 白名单 / 路径校验）
        └── 审计事件（MCP_CALLED / SKILL_USED / FILE_WRITTEN / 新增 SHELL_RUN / TOOL_CALLED）
```

#### 3.1.2 新增/改动文件

| 文件 | 动作 | 职责 |
|---|---|---|
| `sdlc/subagent/tools/__init__.py` | 新增 | `ToolRegistry` + `Tool` 协议 |
| `sdlc/subagent/tools/fs_tools.py` | 新增 | `read`/`write`/`list`/`grep`/`glob`（grep/glob 只读，薄封装） |
| `sdlc/subagent/tools/shell_tool.py` | 新增 | 包 `shell_runner` + `whitelist.validate_command_safety` |
| `sdlc/subagent/tools/mcp_tool.py` | 新增 | 包 `mcp_client`，server 白名单 |
| `sdlc/subagent/tools/skill_tool.py` | 新增 | 包 `skill_runner`，skill 白名单 |
| `sdlc/subagent/tool_schemas.py` | 扩展 | 增 grep/glob/shell/mcp_call/skill 的 JSON schema |
| `sdlc/subagent/pool.py` | 改 | `invoke` 传 `tools=`；`_execute_tool` 委派 `ToolRegistry` |
| `sdlc/audit/events.py` | 扩展 | 增 `SHELL_RUN`、`TOOL_CALLED` 事件 |

#### 3.1.3 关键接口

```python
# subagent/tools/__init__.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class ToolContext:
    project_root: Path
    pipeline_id: str
    stage_id: str
    agent_id: str
    audit: AuditLogger | None
    cost_tracker: CostTracker | None      # shell/mcp 耗时计入预算
    server_whitelist: set[str]            # 允许的 MCP server
    skill_whitelist: set[str]

class Tool(Protocol):
    name: str
    def schema(self) -> dict: ...
    async def run(self, args: dict, ctx: ToolContext) -> str: ...

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
    def register(self, tool: Tool) -> None: ...
    def resolve_schemas(self, names: list[str]) -> list[dict]:
        """把 agent.tools 里授权的工具名 → JSON schema 列表，喂给 CompletionRequest.tools"""
        return [self._tools[n].schema() for n in names if n in self._tools]
    async def execute(self, name: str, args: dict, ctx: ToolContext, allowed: list[str]) -> str:
        if name not in allowed:
            return f"Error: tool '{name}' not allowed for agent {ctx.agent_id}"
        if name not in self._tools:
            return f"Error: tool '{name}' not implemented"
        # 审计 + 执行
        ...
```

`pool.invoke` 改动（`pool.py:41`）：

```python
req = CompletionRequest(
    model=agent.model,
    messages=messages,
    tools=self.tools.resolve_schemas(agent.tools),   # ← 新增：真正带上工具
    system=agent.system_addon or None,
    metadata={...},
)
```

`pool._execute_tool` 改为薄委派：`return await self.tools.execute(tc.name, tc.input, ctx, agent.tools)`。保留 `read/write/list` 的既有实现（迁进 `fs_tools.py`，逻辑不变）。

#### 3.1.4 安全约束（工程落点）

| 工具 | 约束 | 复用 |
|---|---|---|
| grep/glob | 只读，路径限项目内 | `pool._validate_path` 迁到 `fs_tools` |
| shell | allowlist + 阻断 shell 操作符/路径穿越/env 展开 | `whitelist.is_command_allowed` + `validate_command_safety`（`integrations/whitelist.py:81,126`） |
| mcp_call | server 必须在 `ctx.server_whitelist` | `mcp_client` + 配置项 `agent.mcp_servers` |
| skill | skill 名必须在 `ctx.skill_whitelist` | `skill_runner` |

> shell/mcp 默认**不在**任何内置 Subagent 的 `tools` 里；需在 Subagent YAML 显式授权（如 `coder-backend` 授 shell 跑 test，`reviewer` 不授 write）。最小权限原则。

#### 3.1.5 向后兼容

- 存量 Subagent 的 `tools=[read,write]` 行为完全不变（只是现在 schema 真的传给 LLM 了，能力增强而非破坏）。
- `TOOL_SCHEMAS` 只增不改既有 4 项。

#### 3.1.6 测试要点

- 单测每个 tool 的安全边界：shell 传 `rm -rf /` → 被 `validate_command_safety` 拒；mcp_call 未授权 server → 拒。
- 集成测：给一个授 `grep`+`shell` 的 agent 跑"找到 X 并运行测试"，断言审计里有 `TOOL_CALLED`/`SHELL_RUN`。
- 回归：只授 read/write 的 agent 行为与 GA 一致。

#### 3.1.7 验收

- [ ] Subagent 能安全调用 grep/glob/shell/mcp/skill，全走白名单。
- [ ] 每次工具调用有审计事件，可回放。
- [ ] shell/mcp 耗时计入 stage 预算（接 `CostTracker`）。

---

### 3.2 M-A2：Plan-Act-Reflect Runtime

#### 3.2.1 目标状态机

对 **复杂 Stage**（design/impl/impact-analysis）默认启用；**轻量 Stage**（docs/clarify）保持单轮控成本。

```
Stage 输入 + KB context
      ▼
  ┌─ PLAN ─┐  产出：子任务清单 + 每步 acceptance_criteria + 预算分配
  └───┬────┘
      ▼   ┌──────────────┐
  ┌──▶│ ACT (tool-loop) │ 复用 M-A1 的工具循环完成一个子任务
  │   └───────┬─────────┘
  │           ▼
  │      ┌─ REFLECT ─┐  对照 acceptance_criteria + Rule 库自检
  │      └────┬──────┘
  │      达标? ─No─┐ 修正提示回灌（≤ max_reflect）
  └───Yes───┐     │
     还有子任务?─Yes┘
        │No
        ▼
   产物 + 自评分 → Artifact（含 reflection trace）
```

#### 3.2.2 新增/改动文件

| 文件 | 动作 | 职责 |
|---|---|---|
| `sdlc/subagent/runtime.py` | 新增 | `PlanActReflectRuntime`，与 `pool.invoke` 并存 |
| `sdlc/subagent/pool.py` | 改 | `invoke` 按 `agent.runtime` 分派到 single/par |
| `sdlc/subagent/models.py` | 扩展 | `Subagent` 增 `runtime: str = "single"` |
| `sdlc/stage/models.py` | 扩展 | `StageDef` 增 `planning`/`max_reflect`/`reflect_model`/`acceptance_criteria` |
| `sdlc/builtin/stages/*.yaml` | 改 | design/impl 类填 `planning: required` + acceptance_criteria |

#### 3.2.3 关键接口

```python
# subagent/runtime.py
@dataclass
class SubTask:
    description: str
    acceptance_criteria: list[str]
    budget_usd: float

@dataclass
class ReflectVerdict:
    passed: bool
    score: float                 # 0..1
    unmet: list[str]             # 未达标的准则
    fix_hint: str                # 回灌给下一轮 ACT 的修正提示

class PlanActReflectRuntime:
    def __init__(self, pool: "SubagentPool", llm: MultiLLMClient,
                 max_reflect: int = 2, reflect_model: str | None = None): ...

    async def run(self, agent: Subagent, task: SubagentTask,
                  criteria: list[str]) -> SubagentResult:
        plan = await self._plan(agent, task)                 # → list[SubTask]
        trace: list[dict] = []
        for sub in plan:
            for attempt in range(self.max_reflect + 1):
                act = await self.pool.invoke_once(agent, task, sub)   # 复用 M-A1 tool-loop
                verdict = await self._reflect(agent, sub, act, criteria)
                trace.append({"sub": sub.description, "attempt": attempt,
                              "score": verdict.score, "unmet": verdict.unmet})
                if verdict.passed or self._budget_exhausted():
                    break
                task = self._inject_fix(task, verdict.fix_hint)
        return self._assemble(plan, trace)   # artifacts + reflection trace + 自评分
```

- `_plan` / `_reflect` 是独立 LLM 调用；`_reflect` 用 `reflect_model`（可配更强模型评弱模型产物 —— LLM-as-judge 雏形，与 [05 M-D2] 共用判据）。
- `invoke_once`：把现有 `pool.invoke` 的单趟 tool-loop 抽成可复用方法，Runtime 每个子任务调一次。

#### 3.2.4 YAML / schema 变更

```yaml
# builtin/stages/design.yaml 追加
runtime: par            # single | par(Plan-Act-Reflect)
planning: required      # required | optional | off
max_reflect: 2
reflect_model: ""       # 空=用 agent.model；可指定更强模型
acceptance_criteria:
  - "接口设计覆盖所有需求点，无遗漏"
  - "数据库设计符合 MUST 规则（引用 rule 库）"
  - "风险点已识别并给出缓解"
```

`StageDef` 新增字段（`stage/models.py:22`，全部带默认值）：

```python
runtime: str = "single"
planning: str = "off"
max_reflect: int = 2
reflect_model: str = ""
acceptance_criteria: list[str] = field(default_factory=list)
```

#### 3.2.5 向后兼容

- 默认 `runtime="single"` / `planning="off"` → 存量 11 Subagent、12 Stage 行为**完全不变**。
- 只有显式在 YAML 开启的 Stage 才升级。分级启用是硬约束（[roadmap/03 §4.2](../../../roadmap/03-pillar-agent-intelligence.md)）。

#### 3.2.6 测试要点

- 反思触发：mock 一个"首轮不达标、二轮达标"的场景，断言恰好 2 次 ACT + reflection trace 落 Artifact。
- 预算门控：`max_reflect=5` 但预算只够 2 轮 → 断言在预算耗尽时停止（接 `CostTracker.would_exceed_budget`）。
- 单轮回归：`runtime="single"` 的 Stage 走原 `invoke`，成本/行为与 GA 一致。

#### 3.2.7 验收

- [ ] design/impl 开启后，[05 M-D2] eval 判定的一次通过率相对基线 +15pp 起步。
- [ ] reflection trace 存 Artifact + 审计，可查。
- [ ] 单次复杂 Stage 成本 ≤ 1.5× 基线（预算门控生效）。

---

### 3.3 M-A3：结构化澄清（重做 ask_user，异步挂起）

#### 3.3.1 目标

当前 `pool.py:214` `ask_user` 返回"交互不可用"死路。重做为**异步挂起**，与 [03 M-B1 异步 Gate](./03-pillar-collaboration.md) **共用同一套挂起/通知/resume 机制**（[roadmap/07 §九](../../../roadmap/07-roadmap-4q.md) 复用点）。

```
agent 调 ask_user(question, options)
      ▼
抛 ClarificationNeeded(question, options) → 冒泡到 coordinator
      ▼
Pipeline 存 WAITING_CLARIFICATION（复用 §3.3.3 的挂起态，与 Gate 同机制）
      ▼
问题推通知渠道（终端/Web/IM —— 见 [03]）
      ▼
人答 → 写回 answers → resume → 答案注入 task.context → 从挂起点续跑
```

#### 3.3.2 新增/改动文件

| 文件 | 动作 | 职责 |
|---|---|---|
| `sdlc/subagent/pool.py` | 改 | `_tool_ask_user` 改为抛 `ClarificationNeeded` |
| `sdlc/utils/exceptions.py` | 扩展 | 增 `ClarificationNeeded(SdlcError)` |
| `sdlc/core/run_coordinator.py` | 改 | 捕获 `ClarificationNeeded` → 挂起（复用 [03 M-B1] 的挂起写入） |
| `sdlc/cli/answer_cmd.py` | 新增 | `sdlc answer <pipeline> --q <id> --a <text>` 本地回答 |

#### 3.3.3 共用挂起机制（与 M-B1 定义在 [03]，此处只引用）

- Pipeline 状态扩展、`waiting_context` 表、resume 触发 —— **实现归属 [03 §3.1]**，M-A3 复用其"挂起原因 = clarification"分支。
- 契约：挂起记录含 `kind ∈ {approval, clarification}`、`payload`（问题/选项）、`answer` 回写字段。

#### 3.3.4 向后兼容

- 非交互场景（CI/无回答渠道）：保留"超时→按策略默认/失败"退路，不再静默返回假答案。
- 危险关键词（`pool.py:14` `_DANGEROUS_ASK_KEYWORDS`）逻辑保留：涉及 deploy/delete 等的澄清默认不自动放行。

#### 3.3.5 测试要点

- ask_user → 断言 Pipeline 进入 WAITING_CLARIFICATION、可关闭进程。
- `sdlc answer` 回写 → 断言 resume 后答案出现在 `task.context`、Stage 续跑。

#### 3.3.6 验收

- [ ] ask_user 触发异步挂起→回答→resume 全链路通。
- [ ] 与 M-B1 共用一套挂起表（无重复实现）。

---

### 3.4 M-A4：语义记忆引擎（sqlite-vec）

#### 3.4.1 目标

L2 KB（`doc/kb/`）检索现靠路径/fingerprint，长 KB 噪声大。升级为**本地向量语义检索**，锁定 `sqlite-vec`（嵌入式、复用 SQLite、本地可跑，**不引 Milvus/独立向量库**）。

#### 3.4.2 新增/改动文件

| 文件 | 动作 | 职责 |
|---|---|---|
| `sdlc/kb/vector_store.py` | 新增 | sqlite-vec 封装：建表/embed/检索 |
| `sdlc/kb/embedding.py` | 新增 | embedding provider：本地(Ollama)默认，云可选 |
| `sdlc/kb/memory.py` | 改 | 检索路径增加"语义 top-k"分支，保留 fingerprint 兜底 |
| `sdlc/kb/reconciler.py` | 改 | KB 写入时增量 embed（复用 diff-only） |
| `pyproject.toml` | 改 | `optional-dependencies` 增 `semantic = ["sqlite-vec>=0.1"]` |

#### 3.4.3 关键接口

```python
# kb/vector_store.py
class VectorStore:
    def __init__(self, db_path: Path, embedder: "Embedder", dim: int = 768): ...
    def upsert(self, doc_id: str, text: str, meta: dict) -> None: ...
    def search(self, query: str, top_k: int = 5,
               where: dict | None = None) -> list["Hit"]: ...
    # Hit = (doc_id, score, text, meta)  meta 含 type/来源 stage/时间

# kb/embedding.py
class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

class OllamaEmbedder:  # 默认，本地零成本
    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"): ...
```

注入策略（`memory.py`）：按 **stage 角色 + 语义相关性 top-k + 时间衰减**。reviewer 召回 MUST 规则，coder 召回 component-catalog。

#### 3.4.4 数据 / schema

- 独立 `kb_vectors.db`（不污染 `state.db`），表由 sqlite-vec 的 `vec0` 虚拟表 + 元数据表组成。
- section 级切块（非整文档），元数据含 `{type, source_stage, created_at}`。

#### 3.4.5 向后兼容

- `sqlite-vec` 是 **optional 依赖**；未安装时 `memory.py` 回退到现有 fingerprint 检索（能力降级不报错）。
- 语义检索是"增强"非"替换"：路径/fingerprint 精确命中保留。

#### 3.4.6 测试要点

- 有/无 sqlite-vec 两条路径都能出结果（降级验证）。
- 召回质量进 eval（[05]）：度量 KB 相关命中率。

#### 3.4.7 验收

- [ ] sqlite-vec 落地，本地 Ollama embedding 可跑。
- [ ] KB 相关上下文命中率 ≥ 75%（由 [05] eval 度量）。
- [ ] 未装 sqlite-vec 时优雅降级。

---

### 3.5 M-A5：Orchestrator-Worker 多 Agent

#### 3.5.1 目标

`SubagentPool` 现只顺序 invoke 单 agent。升级为主 agent 可派发多个子 agent 并汇总（如 design 派发 DB 设计/接口设计/风险评估三个 worker 并行）。

```
Orchestrator(architect) ── plan → 3 独立子任务
      ├──▶ Worker: DB设计   ┐
      ├──▶ Worker: 接口设计  ├ 并行（复用 run_coordinator 的 Semaphore，下沉一层）
      └──▶ Worker: 风险评估  ┘
              ▼
      Orchestrator 汇总 + 交叉一致性校验 → 统一产物
```

#### 3.5.2 新增/改动文件

| 文件 | 动作 | 职责 |
|---|---|---|
| `sdlc/subagent/orchestrator.py` | 新增 | `Orchestrator` + `delegate` 工具实现 |
| `sdlc/subagent/tools/delegate_tool.py` | 新增 | 主 agent 派发工具（含深度/预算护栏） |
| `sdlc/subagent/tool_schemas.py` | 扩展 | 增 `delegate` schema |

#### 3.5.3 关键接口与护栏

```python
# subagent/orchestrator.py
class Orchestrator:
    def __init__(self, pool: SubagentPool, max_delegate_depth: int = 1,
                 concurrency: int = 3): ...
    async def run(self, agent: Subagent, task: SubagentTask,
                  subtasks: list[SubTask]) -> SubagentResult:
        sem = asyncio.Semaphore(self.concurrency)   # 复用并发骨架
        async def _one(st): 
            async with sem:
                return await self.pool.invoke(st.worker_agent_id, ...)
        results = await asyncio.gather(*[_one(s) for s in subtasks])
        return await self._merge(agent, results)    # 主 agent 汇总 + 一致性校验
```

**防失控**（[roadmap/03 §6.2](../../../roadmap/03-pillar-agent-intelligence.md)）：
- `max_delegate_depth=1`：worker 不能再派发（防递归爆炸）。
- 预算按派发数量比例分配，接 `CostTracker`。
- 每次 delegate 记审计。

#### 3.5.4 向后兼容

- 仅当 Subagent 授权 `delegate` 工具且 Stage `runtime="par"` 时启用；默认关闭。
- 复用 `Semaphore` 骨架，不新造并发框架。

#### 3.5.5 验收

- [ ] design 可派发并行子 agent 并汇总。
- [ ] 派发深度 ≤ 1、预算比例分配、全程审计。

---

### 3.6 M-A6：反馈学习闭环（与 [05 M-D5] 共建）

#### 3.6.1 目标

把"反模式被拒 ≥3 次入 MUST"的**计数式**学习，升级为**效果加权**：决策上线效果 → 效果分 → 下次同类任务高分优先注入、低分规避。此处只讲 agent 侧**消费**；信号**产出**见 [05 §七]。

#### 3.6.2 新增/改动文件

| 文件 | 动作 | 职责 |
|---|---|---|
| `sdlc/kb/adr.py` | 新增 | ADR（决策记录）读写，含 `outcome`/`effect_score` 字段 |
| `sdlc/kb/memory.py` | 改 | 注入时按 effect_score 排序：高分决策优先，低分反模式规避 |

#### 3.6.3 数据模型

```python
# kb/adr.py
@dataclass
class ADR:
    id: str
    decision: str
    context: str
    made_by_agent: str
    made_at: str
    outcome: str = ""            # 上线后效果描述（由 [05 M-D5] 回写）
    effect_score: float = 0.0    # -1..1；正=好效果，负=事故/回滚
    sample_count: int = 0        # 足够样本才生效，防噪声驱动
```

#### 3.6.4 关键约束

- **闭环必须验证**：效果加权后必须由 [05 M-D3 回归] 证明"产物变好而非强化偏好"。
- **足够样本才生效**：`sample_count` 低于阈值时不改变注入行为（单次信号不驱动）。
- 一次线上事故权重 > 三次无后果拒绝（effect_score 的加权体现，非简单计数）。

#### 3.6.5 向后兼容

- ADR 无 `outcome`/`effect_score`（存量记录）时 `effect_score=0`，注入行为退化为现有逻辑。

#### 3.6.6 验收

- [ ] ADR 带 outcome；效果加权注入生效。
- [ ] 回归证明产物质量不退化（[05 M-D3]）。

---

## 四、依赖与顺序

```
M-A1 工具接入 ──→ M-A2 Runtime（reflect/act 要调工具）──→ M-A5 多 agent（worker 复用 tool-loop）
M-A3 澄清 ══共用挂起机制══ [03 M-B1 异步 Gate]
M-A2 reflect 判据 ══共用 acceptance_criteria+Rule══ [05 M-D2 judge]
M-A4 语义记忆 ── 独立，可与 M-A2/A3 并行
M-A6 反馈消费 ←── [05 M-D5 信号产出] ── 需 M-D3 回归把关
```

**季度落位**：M-A1/A2（Q1 主线）→ M-A3/A4（Q2 辅线）→ M-A5（Q3 辅线）→ M-A6（Q4）。

---

## 五、风险与缓解（工程视角）

| 风险 | 缓解 |
|---|---|
| tool schema 接入后 agent 行为漂移 | M-A1 先只对新授权工具的 agent 开启；存量 read/write agent 回归测试锁定 |
| 反思/多 agent 成本翻倍 | 分级启用（YAML 显式开）+ `max_reflect` + `CostTracker` 预算门控；轻量 Stage 保持单轮 |
| sqlite-vec 平台兼容/安装失败 | optional 依赖 + fingerprint 降级；CI 双路径测试 |
| delegate 递归失控 | `max_delegate_depth=1` 硬限 + 预算比例分配 + 审计 |
| 反馈学习强化错误偏好 | sample_count 门槛 + [05 M-D3] 回归验证（安全阀）|
| 改 `pool.py` 牵连所有 Stage | `invoke_once` 抽取保持 `invoke` 签名不变；single 路径回归全绿再合 |

---

返回：[00 导航](./00-README.md) · 上一篇：[01 Q0 加固](./01-q0-mainpath-hardening.md) · 下一篇：[03 支柱二 团队协作](./03-pillar-collaboration.md)
