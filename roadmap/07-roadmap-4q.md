# 07. 四季度详细路线图（v2.0）

> 版本：v2.0-planning（2026-07-16）
> 承接：四大支柱 [03](./03-pillar-agent-intelligence.md) / [04](./04-pillar-collaboration.md) / [05](./05-pillar-ecosystem.md) / [06](./06-pillar-eval-quality.md)
> 粒度：季度主线 + 里程碑 + 验收 + KPI + 风险
> 排期依据：[02](./02-vision-strategy.md) 社区飞轮的启动顺序 + P0 稳定性门槛前置

---

## 一、排期总原则

飞轮启动顺序（[02 §四](./02-vision-strategy.md)）决定了季度排布，但 **P0 稳定性是一切之前的门槛**（[01 §二·五](./01-product-assessment.md)）：

```
Q0 门槛（Q1 前 2-3 周，与 Q1 重叠启动）
   稳定性红线：端到端主路径必须先跑通
        │
        ▼
Q1  让 agent 变聪明 + 堵住质量漏出
   主线：支柱一（Runtime/工具）  辅线：支柱四（冒烟门禁/eval 框架）
        │  飞轮有了"高质量单点" + "质量守门员"
        ▼
Q2  让团队用起来
   主线：支柱二（异步 Gate/server/控制台）  辅线：支柱一（语义记忆/多agent）
        │  飞轮有了"足够运行样本"
        ▼
Q3  让生态转起来
   主线：支柱三（SDK/市场/CI）  辅线：支柱四（回归/ROI）
        │  飞轮有了"资产放大 + 改进信号"
        ▼
Q4  闭合飞轮 + 前瞻
   主线：支柱四（反馈回流）+ 支柱三（A2A/集成）  辅线：支柱二（组织KB/权限）
        │  飞轮完整自转
        ▼
      v2.0 GA（真实可信的版本）
```

**每季度：1 条主线 + 1 条辅线**，避免四支柱并行导致资源分散（[02](./02-vision-strategy.md) 风险）。

---

## 二、里程碑总表（速查）

| 里程碑 | 支柱 | 季度 | 一句话 |
|---|---|---|---|
| **P0 稳定性加固** | — | Q1（前置） | temperature 贯穿、错误冒泡、400 fallback、doctor 探活 |
| M-D1 端到端冒烟门禁 | 四 | Q1 | 全 Profile 真实补全冒烟必绿，堵 P0 漏出 |
| M-A1 工具生态接入 | 一 | Q1 | Subagent 安全调用 grep/shell/mcp/skill |
| M-A2 Plan-Act-Reflect Runtime | 一 | Q1 | design/impl 会规划会反思 |
| M-D2 Eval 框架 + 黄金集 | 四 | Q1 | 产物质量可打分 |
| M-A3 结构化澄清 | 一 | Q2 | ask_user 异步挂起→回答→resume |
| M-B1 异步 Gate 闭环 | 二 | Q2 | 挂起→通知→放行→自动 resume |
| M-B2 sdlc-server MVP | 二 | Q2 | 一条命令拉起共享后端 |
| M-A4 语义记忆引擎 | 一 | Q2 | sqlite-vec 语义检索 |
| M-B3 Web 控制台只读版 | 二 | Q2 | Pipeline/审批/成本看板 |
| M-C1 插件 SDK | 三 | Q3 | plugin new/validate/test/pack |
| M-C2 市场 MVP | 三 | Q3 | search/install/publish + 官方 50+ 条目 |
| M-C3 CI 集成 | 三 | Q3 | PR 触发 review/test 回帖 |
| M-A5 Orchestrator-Worker | 一 | Q3 | design 派发并行子 agent |
| M-D3 跨版本回归 | 四 | Q3 | release 附回归报告，退化阻断 |
| M-B4 IM 通知闭环 | 二 | Q3 | 飞书/Slack 卡片放行 |
| M-D4 ROI 量化 | 四 | Q4 | 省时/降缺陷/加速发布可报告 |
| M-D5 + M-A6 反馈回流学习 | 四+一 | Q4 | 上线效果→决策效果分→agent 消费 |
| M-C4 MCP 工具生态 | 三 | Q4 | MCP 目录 + 能力发现 |
| M-C5 IDE + IM 集成 | 三 | Q4 | VS Code / slash 触发 |
| M-B5 组织 KB 共享 | 二 | Q4 | 跨团队 KB 继承订阅 |
| M-B6 轻量权限治理 | 二 | Q4 | 5 角色 + approver 绑定 |
| M-C6 A2A 协议雏形 | 三 | Q4 | 跨进程 agent 协作 demo |

---

## 三、Q0 前置门槛：P0 稳定性加固

> 时机：Q1 启动的前 2–3 周，作为 Q1 的准入条件。**在它通过前不投入支柱新功能。**
> 目标：让端到端 `sdlc run` 从 100% 失败变为稳定通过。

### 任务清单（均来自 [01 §二·五](./01-product-assessment.md) 已复核的 P0/P1/P2）

| # | 任务 | 涉及文件 | 完成定义 |
|---|---|---|---|
| 1 | temperature 从 config 贯穿到 provider | `llm/client.py`、`subagent/pool.py`、`llm/models.py` | 用户配置的 temperature 生效；thinking 模型不再撞 0.7；不兼容时按模型省略该字段 |
| 2 | stage error 冒泡到终端 | `cli/run_cmd.py`、`core/run_coordinator.py` | run 失败时终端显示错误首行 + 定位提示 |
| 3 | 400 类错误可重试/fallback | `llm/client.py` | 可恢复的参数冲突走 fallback 或明确报错，不静默失败 |
| 4 | doctor 真实探活 | `cli/doctor_cmd.py` | 检查 LLM key + 发真实最小补全 + 参数兼容校验 |
| 5 | llm test 发真实请求 | `cli/llm_cmd.py` | 暴露运行时参数错误 |
| 6 | 配置路径统一 | `cli/init_cmd.py`、`utils/config*` | init 写入路径 = loader 读取路径 |
| 7 | CWD 包加载校验 | 入口 | 防止加载 CWD 旧包拷贝 |
| 8 | CostTracker pricing 缺失 | `llm/cost.py` | 网关无 pricing 时有兜底估算，stats 不失真（也服务 Q4 ROI）|

### 验收标准（准入 Q1 的硬门槛）

- [ ] 在干净测试仓库，`sdlc run "加个订单查询接口"` 用真实模型跑到完成（至少 1 个 Profile 全流程）。
- [ ] 全 14 Profile 用本地 Ollama 冒烟通过（由 M-D1 门禁保证）。
- [ ] `sdlc doctor` 全绿 ⟺ `sdlc run` 能跑（不再假绿）。
- [ ] 任一 stage 失败时，终端能看到根因。

> **注**：M-D1（端到端冒烟门禁）与本门槛并行推进 —— 修复是"治标"，门禁是"防复发"，两者一起才算真正解决。

---

## 四、Q1：让 Agent 变聪明 + 堵住质量漏出

> 主线：支柱一（Agent Runtime）· 辅线：支柱四（评估门禁）
> 主题：在可靠的主路径上，让核心 Stage 的产物质量产生可度量的跃升。

### 里程碑

| 里程碑 | 内容 | 关键交付 |
|---|---|---|
| **M-D1** | 端到端冒烟门禁 | CI 全 Profile 真实补全冒烟；doctor/llm test 真实探活；错误可见性断言 |
| **M-A1** | 工具生态接入 | Subagent 工具集扩到 grep/glob/shell/mcp_call/skill；全走白名单 + 审计 |
| **M-A2** | Plan-Act-Reflect Runtime | design/impl/impact 默认启用规划+反思；reflection trace 留存；分级启用 + 预算门控 |
| **M-D2** | Eval 框架 + 黄金集 | eval 可跑；每 Stage 黄金集 ≥ 10 例；LLM-as-judge 打分（judge 与 reflect 共用判据）|

### 验收标准

- [ ] 主路径稳定（Q0 门槛通过）。
- [ ] design/impl Stage 开启 Plan-Act-Reflect 后，eval 判定的一次通过率相对基线提升可测（目标 +15pp 起步）。
- [ ] Subagent 能安全调用 shell（跑 test）与 MCP 工具，全程审计可回放。
- [ ] 每个核心 Stage 有黄金集 + LLM-as-judge 打分，能出一份"当前质量基线"报告。

### Q1 KPI

| 指标 | 目标 |
|---|---|
| 端到端冒烟通过率 | 100% |
| Stage 产物一次通过率（eval） | 建立基线 → 核心 Stage ≥ 70% |
| 覆盖 eval 的核心 Stage 占比 | ≥ 80% |
| 单次复杂 Stage 成本 | ≤ 1.5× 基线（反思增调用，预算门控） |

### Q1 风险

| 风险 | 缓解 |
|---|---|
| P0 修复牵连面大、回归多 | 冒烟门禁先行；小步提交；每步 eval |
| 反思增加成本超预算 | 分级启用 + max_reflect + 预算门控 |
| 黄金集标注工作量大 | 从现有审计/Artifact 半自动抽取 + 人工精修 |

---

## 五、Q2：让团队用起来

> 主线：支柱二（协作底座）· 辅线：支柱一（记忆/多 agent）
> 主题：把 Gate 从同步阻塞变异步闭环，让团队第一次能真正协作使用。

### 里程碑

| 里程碑 | 内容 | 关键交付 |
|---|---|---|
| **M-A3** | 结构化澄清 | ask_user 异步挂起→回答→resume（与异步 Gate 共用机制）|
| **M-B1** | 异步 Gate 闭环 | WAITING_APPROVAL 状态；CLI `approve` 本地放行；SLA 超时升级 |
| **M-B2** | sdlc-server MVP | 单二进制一条命令拉起；CLI 对接；共享状态与审批队列；本地降级兜底 |
| **M-A4** | 语义记忆引擎 | sqlite-vec 落地；本地 embedding；按角色+相关性注入 |
| **M-B3** | Web 控制台只读版 | Pipeline 看板 + 审批中心 + 成本看板（内嵌于 server）|

### 验收标准

- [ ] 一个 Pipeline 遇 Gate 挂起后可关终端；他人在 Web/CLI 放行后自动 resume。
- [ ] `sdlc server start` 10 分钟内团队可用；server 挂时 CLI 降级本地不阻塞。
- [ ] 语义记忆使 KB 相关上下文命中率 ≥ 75%。
- [ ] Web 控制台能看到全团队 Pipeline 状态与待审 Gate。

### Q2 KPI

| 指标 | 目标 |
|---|---|
| 异步 Gate 平均审批时长 | < 4h |
| KB 相关上下文命中率 | ≥ 75% |
| 接入 server/控制台的团队数 | ≥ 15（早期）|
| 团队协作 Pipeline 占比 | ≥ 20% |

### Q2 风险

| 风险 | 缓解 |
|---|---|
| server 运维吓退个人用户 | CLI 独立可跑；SQLite 单二进制；本地兜底 |
| 语义记忆违反本地可跑 | 锁定 sqlite-vec + Ollama embedding |
| 异步状态机复杂引入 bug | 复用已有 resume/状态机；充分 E2E |

---

## 六、Q3：让生态转起来

> 主线：支柱三（SDK/市场/CI）· 辅线：支柱四（回归/守门）
> 主题：把前两季的单点改进沉淀为社区可复用资产，启动开源飞轮。

### 里程碑

| 里程碑 | 内容 | 关键交付 |
|---|---|---|
| **M-C1** | 插件 SDK | plugin new/validate/test/pack；脚手架 + 文档 + 调试 |
| **M-C2** | 市场 MVP | market search/install/publish；静态 registry 起步；官方 50+ 条目上架 |
| **M-C3** | CI 集成 | GitHub Actions 在 PR 触发 review/test；结果回帖 PR |
| **M-A5** | Orchestrator-Worker | design 派发并行子 agent 并汇总；防失控（深度/预算）|
| **M-D3** | 跨版本回归 | release 附回归报告；产物质量退化阻断发布 |

### 验收标准

- [ ] 贡献者用 SDK 30 分钟内做出一个可用 Adapter 并发布到市场。
- [ ] 市场开张即有 50+ 官方认证条目；`market install` 一键装用。
- [ ] 一个开源仓库接 CI，PR 自动跑 review Stage 并回帖。
- [ ] 每次 release 自动产出回归报告；模拟一次质量退化能被阻断。

### Q3 KPI

| 指标 | 目标 |
|---|---|
| 市场可用 Adapter/模板数 | ≥ 60（官方 50 + 社区起步）|
| 写一个 Adapter 耗时 | < 30 分钟 |
| CI 集成的仓库数 | ≥ 30 |
| 每次 release 附回归报告 | 100% |

### Q3 风险

| 风险 | 缓解 |
|---|---|
| 市场冷启动空 | 官方填充 + SDK 降摩擦 + 贡献榜激励 |
| 扩展质量参差 | validate + 可选 eval + 认证徽章 |
| 多 agent 失控/超成本 | 派发深度限 1 + 预算比例分配 + 审计 |

---

## 七、Q4：闭合飞轮 + 前瞻布局

> 主线：支柱四（反馈回流）+ 支柱三（连接扩展）· 辅线：支柱二（组织化）
> 主题：让"越用越好用"闭环自转，并为下一年前瞻布局。收敛为 v2.0 GA。

### 里程碑

| 里程碑 | 内容 | 关键交付 |
|---|---|---|
| **M-D4** | ROI 量化 | CostTracker pricing 修复；省时/降缺陷/加速发布报告（进控制台）|
| **M-D5 + M-A6** | 反馈回流学习 | eval + 上线效果 → 决策效果分 → agent 消费；回归验证不退化 |
| **M-C4** | MCP 工具生态 | MCP server 目录 + 一键配置 + 能力发现 + 审计 |
| **M-C5** | IDE + IM 集成 | VS Code 插件触发 Stage；飞书/Slack slash 触发 |
| **M-B5** | 组织 KB 共享 | 组织级 KB 继承 + 项目覆盖 + 跨团队订阅 |
| **M-B6** | 轻量权限治理 | 5 角色 + Gate approver 绑定 + 审计可追溯 |
| **M-C6** | A2A 协议雏形 | 跨进程 agent 协作 demo；对齐社区标准 |

### 验收标准（也是 v2.0 GA 门槛）

- [ ] 反馈回流真实运转：一个决策上线效果好 → 下次同类任务被优先注入 → 回归证明产物变好而非退化。
- [ ] 至少 20 个团队能出 ROI 报告。
- [ ] 飞轮四环齐备：团队采用 → 运行样本 → eval 信号 → agent 改进 → 市场沉淀 → 覆盖扩大。
- [ ] v2.0 GA 满足全部健康度护栏（见 §八）。

### Q4 KPI（对齐 [02](./02-vision-strategy.md) Q4 目标）

| 指标 | 目标 |
|---|---|
| 周活跃可信 Pipeline 数 (WTP) | 基线 × 5 |
| 产物采纳率 | ≥ 80% |
| 团队协作 Pipeline 占比 | ≥ 50% |
| 市场可用 Adapter/模板数 | ≥ 100（社区占 ≥ 40%）|
| 覆盖 eval 的 Stage 占比 | 100% |
| ROI 可量化团队数 | ≥ 20 |

### Q4 风险

| 风险 | 缓解 |
|---|---|
| 反馈学习强化错误偏好 | 回归集验证 + 足够样本门槛 |
| A2A 自造孤岛 | 对齐社区标准，作可选高级能力 |
| 四支柱收尾并行、GA 压力大 | 前三季各支柱已可独立交付；Q4 只收尾非堆积 |

---

## 八、v2.0 GA 健康度护栏（贯穿全程，不可倒退）

| 护栏 | 约束 | 责任支柱 |
|---|---|---|
| 端到端冒烟通过率 | = 100%（每 release）| 四（M-D1）|
| 测试覆盖率 | ≥ 90%（不低于 GA）| 全 |
| 本地（Ollama）可跑通 Profile 占比 | 100% | 全 |
| 单需求 LLM 成本 | ≤ 1.2× GA 基线 | 一/四 |
| P0/P1 缺陷 | 每 release < 3 | 全 |
| 新特性附文档 + eval | 100% | 全 |
| CLI 独立可跑（无需 server） | 恒成立 | 二 |

---

## 九、季度资源与依赖关系

### 关键依赖链（跨季度）

```
Q0 P0 加固 ──→ 是 Q1 一切的前提
M-D1 冒烟门禁 ──→ 保护 Q1+ 所有改动不回归
M-A1 工具接入 ──→ M-A2 Runtime（反思要调工具）──→ M-A5 多agent
M-A3 澄清机制 ══╗
              ╠══ 共用异步挂起/resume 底层机制（合并投入）
M-B1 异步Gate ══╝
M-B2 server ──→ M-B3 控制台 / M-B5 组织KB（承载底座）
M-D2 eval框架 ──→ M-D3 回归 ──→ M-D5 反馈回流（信号链）
M-A2 reflect判据 ══ 共用 ══ M-D2 judge判据（acceptance_criteria + Rule）
M-C1 SDK ──→ M-C2 市场（先供给后分发）
```

### 复用点（一次投入多处受益）

| 复用 | 涉及里程碑 |
|---|---|
| 异步挂起/通知/resume 机制 | M-A3 澄清 + M-B1 异步 Gate |
| acceptance_criteria + Rule 判据 | M-A2 reflect + M-D2 judge |
| 已有并发调度骨架 | M-A5 子 agent 并发（下沉一层）|
| SQLite + 审计数据源 | M-B3 控制台 + M-D4 ROI |
| 4 层加载覆盖思想 | M-B5 组织KB + M-C2 私有 registry |
| 已有 integrations（mcp/skill/shell/git）| M-A1 工具接入 + M-C4 MCP 生态 |

---

## 十、路线图小结

- **Q0**：先修断裂的主路径 —— 没有它，北极星恒为 0。
- **Q1**：agent 变聪明（支柱一）+ 质量守门员上岗（支柱四），飞轮有了高质量单点。
- **Q2**：团队用起来（支柱二），飞轮有了运行样本。
- **Q3**：生态转起来（支柱三），飞轮有了资产放大。
- **Q4**：闭合反馈回流（支柱四+一），飞轮完整自转，收敛 v2.0 GA。

每季度单主线 + 单辅线，靠复用点降低总投入，靠健康度护栏防止倒退，靠冒烟门禁确保"这次 GA 是真的可信"。

返回：[00-导航总览](./00-README.md)
