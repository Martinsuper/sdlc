# 01. 产品现状盘点与洞察

> 版本：v2.0-planning（2026-07-16）
> 用途：为后续四季度规划提供事实基线。所有战略与路线图结论都回扣本文的现状与瓶颈判断。
> 读者：产品、研发、社区 maintainer、潜在贡献者

---

## 一、一句话现状

`sdlc` 已是一个**功能完整、文档详尽、测试充分的 v1.0 GA 产品**：AI 驱动的全流程 SDLC 编排 CLI，用 7 个抽象把"从一句话需求到上线运维"的全过程建模为可组合、可插拔、可审计的流水线。

**但它还是一个"编排器"，不是一个"智能体平台"**。它把 LLM 调用编排得很好，却还没让每个 Subagent 真正"聪明"起来；它把单机流程跑得很顺，却还没让一个团队"协作"起来。这正是 v2.0 规划要跨越的鸿沟。

---

## 二、GA 已交付能力盘点

### 2.1 核心资产（已落地、有测试）

| 维度 | 数量 | 说明 |
|---|---|---|
| 抽象层 | 7 | Stage / Artifact / Gate / Pipeline / EntryPoint / Adapter / Profile |
| Python 包 | 13 | cli / core / kb / llm / subagent / adapter / stage / profile / rule / gate / audit / state / integrations |
| Stage（阶段） | 12 | clarify / design / impl-backend / impl-frontend / unit-test / cr / package / deploy / monitor-setup / docs / impact-analysis / security-scan |
| Profile（项目画像） | 14 | new-feature / bug-fix / hotfix / refactor / test / infra / release / revert / doc / migrate / audit / idea / frontend / full-stack |
| Adapter（技术栈） | 22 文件 / 18 适配器 | dongboot / spring / flask / django / fastapi / express / nestjs / react / vue / go-gin / go-kratos / rust-axum / terraform / android / flutter / ios / spark / no-tech |
| Rule（规则） | 548 across 9 rule sets | coding-must / python-must / node-must / go-must / rust-must / frontend-must / mobile-must / data-must / infra-must |
| Rule Enforcer | 4 | CREnforcer / LintEnforcer / CIEnforcer / RuntimeEnforcer |
| Gate（人工闸门） | 10 | PM Review / TL Review / Security Gate / Deploy Approval / Hotfix Emergency 等 |
| Subagent | 11 | requirements-analyst / architect / coder-backend / coder-frontend / tester-unit / reviewer / sre-writer / doc-writer / migration-engineer / security-auditor / devops-engineer |
| CLI 命令 | 19 | run / init / status / resume / stage / profile / adapter / kb / rule / agent / config / doctor / export / import / replay / trace / stats / version / completion |
| 测试 | 45 文件 / 965 tests | 92% 代码覆盖 |
| LLM Provider | Anthropic + OpenAI + OpenAI 兼容 | DeepSeek / Qwen / Moonshot / GLM / Ollama / SiliconFlow |

### 2.2 已具备的工程成熟度信号

- **分发就绪**：PyPI + Homebrew formula + Dockerfile + GitHub Actions 发布流水线，`LICENSE` / `SECURITY.md` / `CODE_OF_CONDUCT.md` / `CONTRIBUTING.md` 齐备。
- **可重现性**：4 层配置加载（CLI > 项目 `.sdlc/ext/` > 用户 `~/.sdlc/ext/` > 内置），相同配置 → 相同结果。
- **可审计性**：JSONL 审计日志 + 27 事件类型 + SQLite 6 表 2 视图，全链路可追溯。
- **可恢复性**：SQLite 状态机 + snapshots + pause/resume（12h 内可恢复）。
- **零代码扩展**：新增 Stage / Profile / Adapter / Rule / Gate 都是加 YAML，不改主流程。
- **成本护栏**：CostTracker 按模型记账 + 预算阈值 + `COST_EXCEEDED` 审计事件。

> 结论：**地基极其扎实**。v2.0 不应该重造地基，而应该在地基上盖"智能"和"协作"两层楼。

---

## 二·五、诚实的现实层：端到端主路径当前断裂（P0 红线）

> 这是本次盘点最重要的一节。以上"GA 已交付"是**文档 + 单元测试意义上的完成**；但一次真实的端到端实测（2026-07-16，在独立测试仓库用 `sdlc run` 跑全流程）显示 **主路径 100% 失败**。这些结论已通过阅读当前代码逐一复核，不是过时记忆。

| 级别 | 问题 | 代码位置（已复核当前仍存在） | 用户可感知表现 |
|---|---|---|---|
| **P0** | 配置的 `temperature` 完全不生效 | `llm/client.py::MultiLLMClient.complete` 只 route model，从不注入 `config.llm.temperature`；`subagent/pool.py` 构造 `CompletionRequest` 不传 temperature，永远用默认 `0.7` | 网关的 thinking 模型（如 Opus 4.8）拒绝 `temperature=0.7`，每次调用必挂；`sdlc config set llm.temperature` 是死配置 |
| **P0** | 错误信息被吞没 | `cli/run_cmd.py` 失败仅打印 `Pipeline failed / Stages / Cost`，stage 级 error 不冒泡到终端，只在 `audit.jsonl` 可见 | 用户看到"失败"却无任何原因，无从排查 |
| **P1** | 400 类错误不重试不 fallback | `client.py::complete` 只对 `RateLimitError`/`TimeoutError` fallback，400（含可恢复的参数冲突）直接抛出 | 参数冲突类错误直接令 pipeline 失败，没有兜底 |
| **P1** | CWD 含旧包拷贝时加载错版本 | editable 安装 + `sys.path[0]=CWD` | 在特定目录运行加载到旧代码，行为不可预期 |
| **P2** | 配置体系三处路径/格式不一致 | `init` 写 `.sdlc/config.toml`，`config_loader` 读 `.sdlc/ext/config.yaml`，用户级又是 `~/.sdlc/config.yaml` | 配置"保存成功但不生效" |
| **P2** | `doctor` 全绿但 run 必挂 | `doctor` 不检查 LLM key / 连通性 / 真实补全 | 诊断给用户虚假安全感 |
| **P2** | `llm test` 只查初始化不发真实请求 | `llm_cmd.py` | 无法暴露 temperature 类运行时错误 |

**这对规划意味着什么（关键判断）**：

1. **飞轮转不起来的首要原因不是 agent 不够聪明，而是主路径断了。** 一份把"Agent 智能化"排在最前、却对"跑不通"只字不提的路线图是脱离现实的。
2. 因此路线图设立一个 **Q1 前置的"P0 稳定性与可用性加固"门槛**：在它通过前，任何战略支柱的新功能都不应大规模投入 —— 因为北极星（可信 Pipeline 数）在主路径断裂时恒等于 0。
3. 这也**倒逼支柱四（评估闭环）提前**：如果早有 E2E 冒烟 + 真实补全的评估门禁，这类 P0 不会以"GA"的名义发布。评估不是锦上添花，是防止"绿色单测掩盖红色主路径"的必需品。

> 修正后的成熟度共识：**"编排引擎"成熟度高，但"开箱即用的端到端可靠性"当前是最低分。** 见下方雷达新增行。

---

## 三、成熟度雷达（自评）

以 AI agent 产品的六个维度做 0–5 自评（5 = 业界最佳）：

| 维度 | 评分 | 依据 | 差距 |
|---|---|---|---|
| **编排能力** Orchestration | ★★★★★ 5 | DAG 构建、并发执行、状态机、resume 都已完整 | 无明显短板 |
| **开箱即用可靠性** Reliability | ★☆☆☆☆ 1 | 端到端 `sdlc run` 实测 100% 失败（见 §二·五），P0 未清 | 主路径断裂，最高优先级 |
| **可扩展性** Extensibility | ★★★★☆ 4 | 4 层加载 + YAML 零代码扩展，但缺插件 SDK / 市场 | 分发与发现机制缺失 |
| **可审计/可恢复** Observability | ★★★☆☆ 3 | 审计日志与状态齐全，但只有 CLI `trace/stats`，无可视化、无实时监控 | 缺 dashboard 与团队视图 |
| **Agent 智能** Agent Intelligence | ★★☆☆☆ 2 | 有 tool-loop 骨架，但工具仅 read/write/ask_user，无 planning/reflection/子agent | 智能化几乎待建 |
| **协作** Collaboration | ★☆☆☆☆ 1 | 纯单机 CLI，Gate 同步阻塞，无异步审批/多用户/组织视图 | 团队场景基本空白 |
| **质量闭环** Eval & Feedback | ★☆☆☆☆ 1 | 有成本记账，但无 agent 评估、无回归、无上线反馈回流 | "越用越好用"尚未量化验证 |

**雷达形状解读**：产品在"把流程跑起来"的工程维度已接近满分，但在"让 agent 变聪明"和"让团队用起来"两个决定天花板的维度上是最低分。**v2.0 的价值增量几乎全部来自把右侧三个低分维度拉起来。**

---

## 四、五大产品瓶颈（经代码验证）

以下瓶颈均通过阅读实际实现确认，不是文档推测。它们是 v2.0 四大战略支柱的直接来源。

### 瓶颈 1：Subagent 是"半个 agent" — 工具贫乏、无规划、无反思

**证据**（`sdlc/subagent/pool.py`）：
- `invoke()` 确实有 `for i in range(max_iter)` 的 tool-loop，会解析 `tool_use` 并回灌结果 —— 这是好的骨架。
- 但 `_execute_tool()` 只实现了三个工具：`read` / `write` / `ask_user`，其余一律返回 `"not implemented yet"`。
- `ask_user` 直接返回"Interactive user input is not available in this mode" —— **agent 无法在执行中向人求助**。
- 没有 planning 阶段（先分解任务再执行）、没有 reflection（自检产物质量再决定是否重试）、没有 subagent 派发（一个 agent 不能调度另一个 agent）、**无法调用已接入的 MCP 工具与 Skill**（`integrations/` 里有 `mcp_client` / `skill_runner`，但 Subagent 的工具白名单里没暴露）。

**影响**：Subagent 本质仍是"带一点工具的单轮 prompt"，产物质量高度依赖 prompt 模板本身。这限制了复杂 Stage（如 design、impl）的上限。

### 瓶颈 2：Gate 同步阻塞 — 无异步审批，团队无法协作把关

**证据**（`sdlc/core/run_coordinator.py`）：
- 并发调度里遇到 `GateAction.BLOCK` 直接 `should_stop = True`，取消所有 running task，把 pending 全标 SKIPPED。
- Gate 的 `manual_review` 在 CLI 单进程内是"停下来等"，没有把待审状态推给人、没有通知渠道闭环、没有"别人在 Web/IM 上点了通过后自动 resume"的机制。

**影响**：Gate 的设计（approvers / SLA / checklist / notifications 字段）很完整，但运行时只能单机同步等待。**这让"人工把关"这个卖点在真实团队里几乎不可用** —— 没人愿意让终端一直挂着等审批。

### 瓶颈 3：记忆是"文件柜"，不是"大脑" — 无语义检索、无反馈学习

**证据**（`sdlc/kb/memory.py` MemoryL2 + PRD 13）：
- L2 KB 是 `doc/kb/` 下的 Markdown + JSON 文件集，检索靠 fingerprint 和路径，**没有向量化 / 语义检索**。
- "越用越好用"目前只体现在"反模式被拒 ≥3 次自动入 MUST" 这类**规则计数**，没有"这次上线后错误率下降了 → 强化该设计决策"的**效果反馈回流**。
- L3 全局 KB 的跨项目抽象仍停留在设计，缺实际的知识迁移机制。

**影响**：记忆增长是"越用越多"，但不是"越用越准"。Subagent 注入的 context 是关键词/路径匹配，不是相关性排序，长 KB 下噪声大。

### 瓶颈 4：纯单机 — 无团队协作面、无组织视图

**证据**：全部能力通过 CLI 暴露，状态存本地 SQLite。没有服务端、没有多用户、没有权限模型（PRD 提过 PM/TL/SRE/QA/Security 角色但未实现）、没有组织级 KB 共享、没有可视化控制台。

**影响**：产品当前是"个人开发者的强力工具"，还不是"团队的协作平台"。开源社区里，团队采用（而非个人尝鲜）才是留存与口碑的关键。

### 瓶颈 5：没有 Agent 评估体系 — "好不好用"全靠感觉

**证据**：`tests/` 是软件工程意义的单元/集成/E2E 测试，验证的是"代码正确"，不是"agent 产物质量好"。没有 eval 数据集、没有 LLM-as-judge、没有跨版本回归对比、没有 ROI 量化（省了多少时间 / 减少多少缺陷）。

**影响**：无法回答三个致命问题 ——（a）换个模型 / 改个 prompt，产物质量是变好还是变差？（b）v1.1 比 v1.0 强在哪，有数据吗？（c）向团队证明 ROI 的依据是什么？开源项目缺这套，贡献者改 prompt 时无从判断优劣，社区演进会失焦。

---

## 五、瓶颈 → 战略支柱映射

| 瓶颈 | 对应 v2.0 战略支柱 | 文档 |
|---|---|---|
| 1. Subagent 半个 agent | **支柱一：Agent 智能化深化** | [03](./03-pillar-agent-intelligence.md) |
| 3. 记忆是文件柜 | **支柱一：Agent 智能化深化**（语义记忆子方向） | [03](./03-pillar-agent-intelligence.md) |
| 2. Gate 同步阻塞 | **支柱二：团队协作与企业化** | [04](./04-pillar-collaboration.md) |
| 4. 纯单机 | **支柱二：团队协作与企业化** | [04](./04-pillar-collaboration.md) |
| — 扩展分发缺市场 | **支柱三：生态开放与集成** | [05](./05-pillar-ecosystem.md) |
| 5. 无评估体系 | **支柱四：评估与质量闭环** | [06](./06-pillar-eval-quality.md) |

---

## 六、开源社区定位下的特殊考量

产品明确走**开源社区驱动**路线（非闭源企业销售），这改变了功能优先级的排序逻辑：

| 决策维度 | 开源驱动下的取舍 |
|---|---|
| **贡献者体验优先** | 扩展点（Adapter/Stage/Rule）的编写、测试、发布链路要极其顺滑；插件 SDK 与本地调试工具优先级高于企业 SSO。 |
| **可观测性先做本地版** | Web 控制台先做"单机 / 团队自托管"版本，而非 SaaS 多租户；降低采用门槛。 |
| **市场即社区飞轮** | 模板/Adapter 市场是开源项目的核心增长引擎（类比 VS Code 插件市场、Homebrew tap），应作为一等公民而非商业化附属。 |
| **评估数据要可共享** | eval 数据集、benchmark 结果应能开源、可复现，让社区能对比"这个 PR 让 agent 变好了吗"。 |
| **默认开箱可用** | 不能强依赖付费模型 —— 三方 OpenAI 兼容（含 Ollama 本地）已是好基础，要继续强化"零成本本地可跑"。 |
| **治理透明** | 路线图、RFC、决策记录公开；企业级特性（权限/审计上链）作为可选模块，不绑架核心。 |

**反面清单（本轮不重点投入）**：闭源 SaaS 计费、企业销售 GTM、SSO/SCIM 等 IT 采购特性 —— 这些在社区达到规模前是过早优化。

---

## 七、现状盘点小结

1. **保住的**：7 抽象、13 包、YAML 零代码扩展、审计/状态/恢复、成本护栏 —— v2.0 不动地基。
2. **要补的**：Agent 从"半个"补成"完整"（planning/reflection/工具/子agent/语义记忆）。
3. **要建的**：团队协作面（异步 Gate + Web 控制台 + 可观测）、评估闭环（evals + 反馈回流）、生态市场（插件 SDK + 模板市场）。
4. **要守的**：开源优先、本地可跑、贡献者友好、治理透明。

下一篇：[02-愿景与战略](./02-vision-strategy.md) —— 把这些判断收敛为北极星、四大支柱与成功指标。
