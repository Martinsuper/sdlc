# 03. 支柱二 · 团队协作开发方案

> 版本：v2.0-dev-design（2026-07-16）
> 承接：[roadmap/04 支柱二](../../../roadmap/04-pillar-collaboration.md)
> 覆盖里程碑：M-B1（异步 Gate）、M-B2（sdlc-server）、M-B3（Web 控制台）、M-B4（IM 通知）、M-B5（组织 KB）、M-B6（轻量权限）
> 一句话：把 Gate 从"同步阻塞、遇 block 直接 stop"改造成"挂起→通知→他人放行→自动 resume"，并提供**可选**自托管 server 承载团队协作。
> 铁律：**CLI 永远独立可跑，server 永远是可选增强，server 挂时 CLI 降级本地。**

---

## 一、方案目标与对应里程碑

| 里程碑 | 目标 | 季度 | 主要落点 |
|---|---|---|---|
| M-B1 | 异步 Gate 闭环（挂起态 + 本地 approve） | Q2 | `state/schema.py`·`run_coordinator.py`·`cli/approve_cmd.py`（新） |
| M-B2 | sdlc-server MVP（单命令拉起 + CLI 对接） | Q2 | `server/`（新包） |
| M-B3 | Web 控制台只读版 | Q2 | `server/web/`（新） |
| M-B4 | IM 通知闭环（飞书/Slack 卡片放行） | Q3 | `integrations/notify/`（新） |
| M-B5 | 组织 KB 共享（继承 + 订阅） | Q4 | `kb/org_kb.py`（新） |
| M-B6 | 轻量权限治理（5 角色 + approver 绑定） | Q4 | `server/auth.py`（新）·`gate/` |

---

## 二、现状锚点（真实代码）

| 关注点 | 文件:行 | 现状 |
|---|---|---|
| Gate 同步阻塞 | `core/run_coordinator.py:344-366` | 遇 `GateAction.BLOCK`：`should_stop=True`、cancel 所有 task、后续 SKIPPED |
| 顺序模式 stop | `stage/runner.py:467-473` | BLOCK 或 FAILED 直接 `break` |
| Gate 决策 | `gate/engine.py:80-92` | `MANUAL_REVIEW` 已生成 reviewer + deadline，但运行时无"挂起"承接 |
| Gate 定义 | `gate/models.py:25-46` | `GateDef` 有 reviewer/deadline_hours；`GateDecision` 有 metadata |
| Pipeline 状态机 | `state/schema.py:107-116` `VALID_TRANSITIONS` | `RUNNING→{COMPLETED,FAILED,PAUSED}`；**无 WAITING_APPROVAL** |
| 状态存储 | `state/store.py:92` `update_pipeline_status` | 校验 `VALID_TRANSITIONS`；`save_pipeline` 带 `meta_json` |
| resume | `cli/resume_cmd.py` + `store.py:274-310` | 已有 resume token + `deps.coordinator.run` 重跑机制 |
| 状态列举 | `store.py:112` `list_pipelines(status=...)` | 可按状态查（Web/审批中心数据源） |
| 审计 | `audit/events.py` | 有 `GATE_TRIGGERED`/`GATE_DECISION`；**无 approval 相关事件** |
| 配置 4 层 | `utils/config*` | 项目/`.sdlc/ext`/用户/内置（组织 KB 复用此覆盖思想） |

---

## 三、逐里程碑工程方案

### 3.1 M-B1：异步 Gate 闭环（本支柱地基，与 [02 M-A3] 共用挂起机制）

#### 3.1.1 目标流程

```
Stage 完成 → Gate 判定 MANUAL_REVIEW
      ▼
Pipeline 存 WAITING_APPROVAL（不占运行进程，可关终端）
      ▼
按 Gate.notifications 推送（Web 待办 / IM 卡片 / CLI 提示）
      ▼
approver 放行/拒绝/补充（带理由）→ 写回 approval 结果
      ▼
Pipeline 自动 resume（复用现有 resume）→ 继续下一 Stage
      │
      └─ SLA 超时 → 升级通知 / 按策略自动放行或阻断
```

#### 3.1.2 新增/改动文件

| 文件 | 动作 | 职责 |
|---|---|---|
| `sdlc/state/schema.py` | 改 | `VALID_TRANSITIONS` 增 WAITING_APPROVAL/WAITING_CLARIFICATION；新增 `waiting_context` 表 |
| `sdlc/state/store.py` | 扩展 | `save_waiting`/`load_waiting`/`resolve_waiting` 方法 |
| `sdlc/core/run_coordinator.py` | 改 | BLOCK/MANUAL_REVIEW 分流：manual→挂起而非 cancel |
| `sdlc/cli/approve_cmd.py` | 新增 | `sdlc approve/reject <pipeline> <gate>` 本地放行 |
| `sdlc/audit/events.py` | 扩展 | 增 `PIPELINE_SUSPENDED`/`APPROVAL_GRANTED`/`APPROVAL_REJECTED`/`SLA_ESCALATED` |

#### 3.1.3 状态机变更（`state/schema.py:107`）

```python
VALID_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"RUNNING", "SKIPPED"},
    "RUNNING": {"COMPLETED", "FAILED", "PAUSED",
                "WAITING_APPROVAL", "WAITING_CLARIFICATION"},   # ← 新增
    "WAITING_APPROVAL": {"RUNNING", "FAILED", "CANCELLED"},      # ← 新增：放行→RUNNING
    "WAITING_CLARIFICATION": {"RUNNING", "FAILED", "CANCELLED"}, # ← 新增（服务 [02 M-A3]）
    "FAILED": {"PENDING"},
    "PAUSED": {"RUNNING"},
    "COMPLETED": set(), "SKIPPED": set(), "NEW": {"RUNNING"}, "CANCELLED": set(),
}
```

新增挂起表（单表承载 approval + clarification 两类，[02 M-A3] 复用）：

```sql
CREATE TABLE IF NOT EXISTS waiting_context (
    pipeline_id TEXT NOT NULL,
    kind        TEXT NOT NULL,          -- 'approval' | 'clarification'
    ref_id      TEXT NOT NULL,          -- gate_id 或 question_id
    stage_id    TEXT,
    payload_json TEXT NOT NULL,         -- gate/问题详情、选项、SLA
    answer_json TEXT,                   -- 放行/拒绝/回答结果，NULL=未决
    reviewer    TEXT,
    deadline    TEXT,
    created_at  TEXT NOT NULL,
    resolved_at TEXT,
    PRIMARY KEY (pipeline_id, kind, ref_id),
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE CASCADE
);
```

#### 3.1.4 coordinator 分流（`run_coordinator.py:340`）

现状：`is_block` 一律 stop。改为区分 gate action：

```python
if result["status"] == "COMPLETED" and not is_block and not is_manual:
    completed_ids.add(result["stage_id"])
elif is_manual:
    # 挂起，而非取消
    self.state.save_waiting(
        pipeline_id=pipeline_id, kind="approval",
        ref_id=gate_decision.gate_id, stage_id=result["stage_id"],
        payload={"reason": gate_decision.reason,
                 "reviewer": gate_decision.reviewer,
                 "deadline": gate_decision.deadline},
    )
    self.state.update_pipeline_status(pipeline_id, "WAITING_APPROVAL")
    self.audit.emit(AuditEventType.PIPELINE_SUSPENDED, {...})
    should_stop = True   # 停止本次运行，但状态是"等待"而非"失败"
else:
    # BLOCK（硬阻断，如 MUST 违规）保持原语义：失败停止
    should_stop = True
```

**关键区分**：`MANUAL_REVIEW`→挂起可恢复；`BLOCK`（MUST 违规）→仍是硬失败。二者语义不同，不可混。

#### 3.1.5 approve/resume 衔接

```python
# cli/approve_cmd.py
@click.command()
@click.argument("pipeline_id")
@click.argument("gate_id")
@click.option("--reject", is_flag=True)
@click.option("--reason", default="")
def approve(pipeline_id, gate_id, reject, reason):
    store = StateStore(sdlc_home() / "state.db")
    store.resolve_waiting(pipeline_id, "approval", gate_id,
                          answer={"approved": not reject, "reason": reason,
                                  "reviewer": current_user()})
    audit.emit(APPROVAL_REJECTED if reject else APPROVAL_GRANTED, {...})
    if not reject:
        # 复用现有 resume：从挂起 stage 之后继续
        deps = build_deps()
        asyncio.run(deps.coordinator.resume_from_waiting(pipeline_id))
```

`coordinator.resume_from_waiting`：读 `waiting_context` 已 resolved 的记录 → 把 answer 注入 context → 从下一个未完成 stage 续跑（复用 `run` 的 stage 调度，跳过 completed_ids）。

#### 3.1.6 向后兼容

- `--gate-mode skip`（`run_cmd.py:32`）行为不变：跳过 Gate，不产生挂起。
- 无 server 时：`sdlc approve` 直接本地放行（守住 CLI 独立可跑）。
- BLOCK 硬阻断语义不变，存量测试不受影响。

#### 3.1.7 测试要点

- 遇 manual gate → 断言 WAITING_APPROVAL、进程可退出、DB 有 waiting 记录。
- `sdlc approve` → 断言 resume、后续 stage 跑完、状态 COMPLETED。
- `sdlc approve --reject` → 断言 FAILED/CANCELLED，不续跑。
- SLA 超时 → 断言 `SLA_ESCALATED` 事件（超时策略可配）。

#### 3.1.8 验收

- [ ] Pipeline 遇 Gate 挂起后可关终端；他人放行后自动 resume。
- [ ] CLI `approve` 无 server 也能本地放行。
- [ ] 审批人/时间/理由入审计，可追溯。

---

### 3.2 M-B2：sdlc-server MVP

#### 3.2.1 定位与约束

一个**可选**轻量服务端，承载共享 Pipeline 状态 + 审批队列。不改 CLI 核心逻辑，只把"本地 SQLite"补充为"团队共享后端"。

| 约束 | 落点 |
|---|---|
| 单二进制/一条命令 | `sdlc server start`，SQLite 起步，零外部依赖 |
| CLI 无缝对接 | `sdlc config set server.url http://...`，CLI 状态读写指向 server |
| 渐进存储 | 默认 SQLite；大团队可选 Postgres（配置切换） |
| 本地兜底 | server 不可达 → CLI 降级本地 `state.db` |

#### 3.2.2 新增文件（新包 `sdlc/server/`）

| 文件 | 职责 |
|---|---|
| `sdlc/server/__init__.py` | 包入口 |
| `sdlc/server/app.py` | HTTP app（基于 `http.server` 或轻量框架，见 §3.2.4 选型） |
| `sdlc/server/routes.py` | REST：pipelines / waiting / approve / cost |
| `sdlc/server/backend.py` | `RemoteStateBackend`：CLI 侧把 StateStore 调用转 HTTP |
| `sdlc/cli/server_cmd.py` | `sdlc server start/stop/status` |

#### 3.2.3 CLI 对接（关键抽象：StateStore 后端可切换）

现状 CLI 直连本地 `StateStore`。引入后端抽象，让远程/本地对 CLI 透明：

```python
# server/backend.py
class StateBackend(Protocol):
    def list_pipelines(self, **kw) -> list[PipelineSummary]: ...
    def load_waiting(self, pipeline_id: str) -> list[dict]: ...
    def resolve_waiting(self, ...) -> None: ...
    # ……与 StateStore 读写子集同签名

class RemoteStateBackend(StateBackend):
    def __init__(self, base_url: str, token: str, local_fallback: StateStore):
        self.base_url = base_url; self.local = local_fallback
    def list_pipelines(self, **kw):
        try:
            return self._get("/pipelines", kw)        # httpx（已是依赖）
        except (httpx.ConnectError, httpx.TimeoutException):
            return self.local.list_pipelines(**kw)    # ← server 挂 → 本地兜底
```

`cli/deps.py` 的 `build_deps` 按 `config.server.url` 是否配置，注入 `RemoteStateBackend` 或直接 `StateStore`。

#### 3.2.4 技术选型（开源友好）

- HTTP 层优先 **stdlib `http.server` + `httpx`（已有依赖）**，避免引 FastAPI/uvicorn 重栈（[roadmap/02 已否决 FastAPI]）。若并发需求上升再评估轻量 ASGI。
- 认证起步：**bearer token**（`sdlc server start` 生成，`config set server.token` 配）。SSO/OIDC 作为 M-B6 后的可选插件。

#### 3.2.5 向后兼容

- 不配 `server.url` → CLI 行为与 GA 完全一致（本地 SQLite）。
- server 是新包，不改既有包契约。

#### 3.2.6 验收

- [ ] `sdlc server start` 10 分钟内团队可用。
- [ ] server 挂时 CLI 降级本地、不阻塞。
- [ ] 共享状态 + 审批队列可用。

---

### 3.3 M-B3：Web 控制台只读版

#### 3.3.1 目标

补 Observability 缺口（[roadmap/01] 雷达仅 3 分）。**只读优先**：先"看"，写操作（审批）逐步加。

#### 3.3.2 核心视图与数据源（全部来自已有 SQLite + 审计，主要是可视化层）

| 视图 | 数据源 |
|---|---|
| Pipeline 看板 | `v_pipeline_summary` 视图（`state/schema.py:88`） |
| 审批中心 | `waiting_context` 表（M-B1） |
| Stage 详情 | `stages` + `artifacts` 表 + 审计 JSONL |
| 成本看板 | `v_cost_daily` 视图（`state/schema.py:96`）+ [01 §3.8] 修复后的 cost |
| 质量趋势 | [05] eval 分数（打通支柱四） |

#### 3.3.3 新增文件

| 文件 | 职责 |
|---|---|
| `sdlc/server/web/` | 内嵌静态资源（HTML/JS），`server start` 即带 UI |
| `sdlc/server/routes.py` | 扩展只读 API：`/dashboard/*` |

#### 3.3.4 约束

- 技术栈轻量、内嵌静态资源，**不引重前端运维**（[roadmap/04 §6.3]）。
- 数据源已具备，主要工作是聚合 API + 前端渲染。

#### 3.3.5 验收

- [ ] 能看到全团队 Pipeline 状态与待审 Gate。
- [ ] 成本看板反映真实成本（依赖 [01 §3.8]）。

---

### 3.4 M-B4：IM 通知闭环

#### 3.4.1 目标

`GateDef` 已有通知字段设计但运行时未闭环。做**飞书 + Slack** 两个渠道的卡片（带通过/拒绝按钮），抽象通知接口供社区扩展。

#### 3.4.2 新增文件

| 文件 | 职责 |
|---|---|
| `sdlc/integrations/notify/__init__.py` | `Notifier` 协议 + 注册 |
| `sdlc/integrations/notify/feishu.py` | 飞书卡片（webhook + 交互回调） |
| `sdlc/integrations/notify/slack.py` | Slack Block Kit |

#### 3.4.3 接口

```python
class Notifier(Protocol):
    name: str
    async def notify_pending(self, pipeline_id: str, gate: dict) -> None: ...
    async def handle_callback(self, payload: dict) -> "ApprovalAction": ...
    # 卡片按钮点击 → server 回调 → resolve_waiting → resume（复用 M-B1）
```

#### 3.4.4 约束

- 卡片放行走 server 的 `/approve` 回调 → 复用 M-B1 的 `resolve_waiting` + resume，**不新增审批逻辑**。
- 通知失败不阻断 Pipeline（挂起态已持久化，通知只是触达手段）。

#### 3.4.5 验收

- [ ] 飞书/Slack 卡片带按钮，点击即放行并触发 resume。

---

### 3.5 M-B5：组织 KB 共享

#### 3.5.1 目标

现状 KB = 项目内 `doc/kb/` + 全局 `~/.sdlc/kb/`。加**组织级**层：跨仓库/跨团队共享，各项目继承 + 本地覆盖（复用 4 层加载覆盖思想）。

```
组织 KB（server）
  ├── 组织级规则/规范/架构（所有团队继承）
  ├── 领域 KB（按 bounded context，可订阅）
  └── 全局模式/反模式库（呼应 L3）
        │ 继承 + 本地覆盖
        ▼
项目 KB（doc/kb/，本地）
```

#### 3.5.2 新增文件

| 文件 | 职责 |
|---|---|
| `sdlc/kb/org_kb.py` | 组织 KB 客户端：拉取/订阅/合并（继承+覆盖） |
| `sdlc/server/routes.py` | 扩展 `/org-kb/*` |

#### 3.5.3 约束

- 复用现有 4 层加载的**覆盖优先级思想**：组织级最低优先，项目级覆盖之。
- 组织 KB 存 server；无 server 时降级为纯本地（不阻塞）。

#### 3.5.4 验收

- [ ] 组织级 KB 继承 + 项目覆盖；跨团队订阅可用。

---

### 3.6 M-B6：轻量权限治理

#### 3.6.1 目标

PRD 设计了 PM/TL/SRE/QA/Security 五角色未实现。做**轻量够用**版：5 内置角色 + Gate approver 绑定 + 审计。**不做**细粒度 RBAC 矩阵/审批流引擎/字段级权限。

#### 3.6.2 新增/改动文件

| 文件 | 动作 | 职责 |
|---|---|---|
| `sdlc/server/auth.py` | 新增 | 5 角色定义 + token→role 映射 + `can_approve(role, gate)` |
| `sdlc/gate/models.py` | 扩展 | `GateDef` 增 `approver_roles: list[str]` |
| `sdlc/gate/engine.py` | 改 | manual review 时校验 approver 角色 |

#### 3.6.3 接口

```python
# server/auth.py
class Role(StrEnum):
    PM = "pm"; TL = "tl"; SRE = "sre"; QA = "qa"; SECURITY = "security"

def can_approve(role: Role, gate: GateDef) -> bool:
    return not gate.approver_roles or role.value in gate.approver_roles
```

#### 3.6.4 约束

- 轻量够用，避免企业 IAM 复杂度（[roadmap/02 取舍原则 3]）。
- 审计上链/合规报告作**可选企业模块**，不进核心。
- 无 server（个人模式）时权限校验旁路，不阻塞单机使用。

#### 3.6.5 验收

- [ ] 5 角色 + Gate approver 绑定 + 审计可追溯。

---

## 四、依赖与顺序

```
M-B1 异步 Gate（挂起态 + 状态机 + waiting_context 表）
   ├── 是本支柱一切的地基
   ├══ 与 [02 M-A3 澄清] 共用 waiting_context 表 + resume
   ▼
M-B2 server（承载共享状态/审批队列）
   ├──▶ M-B3 Web 控制台（server 的 UI/API）
   ├──▶ M-B4 IM 通知（server 回调触发 resolve+resume）
   ├──▶ M-B5 组织 KB（server 承载）
   └──▶ M-B6 权限（server 的 auth 层）
```

**季度落位**：M-B1/B2/B3（Q2 主线）→ M-B4（Q3 辅）→ M-B5/B6（Q4 辅）。

---

## 五、风险与缓解（工程视角）

| 风险 | 缓解 |
|---|---|
| 异步状态机引入 bug | 复用现有 resume + VALID_TRANSITIONS 校验；充分 E2E；BLOCK/manual 语义严格区分 |
| server 运维吓退个人用户 | CLI 永远独立可跑；单二进制 SQLite；`RemoteStateBackend` 本地兜底 |
| Web 变重前端项目 | 只读优先、内嵌静态资源、不引重前端栈 |
| 权限陷入企业 IAM 泥潭 | 轻量够用；重治理作可选模块；个人模式旁路 |
| IM 渠道碎片化 | 先飞书+Slack 两个，`Notifier` 协议供社区扩展 |
| waiting_context 表被两支柱共用产生耦合 | `kind` 字段区分；approval/clarification 各自分支，schema 一次设计到位 |

---

返回：[00 导航](./00-README.md) · 上一篇：[02 支柱一](./02-pillar-agent-intelligence.md) · 下一篇：[04 支柱三 生态开放](./04-pillar-ecosystem.md)
