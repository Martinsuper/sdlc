# 04. 支柱三 · 生态开放开发方案

> 版本：v2.0-dev-design（2026-07-16）
> 承接：[roadmap/05 支柱三](../../../roadmap/05-pillar-ecosystem.md)
> 覆盖里程碑：M-C1（插件 SDK）、M-C2（市场）、M-C3（CI 集成）、M-C4（MCP 生态）、M-C5（IDE/IM 集成）、M-C6（A2A）
> 一句话：sdlc 已有极好的**扩展能力**（4 层加载 + YAML 零代码扩展），缺的是**扩展的分发与发现**。本支柱补 SDK（供给）→ 市场（分发）→ 集成（连接）。
> 顺序逻辑：先做 SDK 让"写扩展"变简单，再做市场让"找/装扩展"变简单 —— 没有顺滑的 SDK，市场里没有优质内容可分发。

---

## 一、方案目标与对应里程碑

| 里程碑 | 目标 | 季度 | 主要落点 |
|---|---|---|---|
| M-C1 | `plugin new/validate/test/pack` | Q3 | `cli/plugin_cmd.py`（新）·`plugin/`（新包） |
| M-C2 | `market search/install/publish` | Q3 | `cli/market_cmd.py`（新）·`market/`（新包） |
| M-C3 | GitHub Actions PR 触发 review/test 回帖 | Q3 | `.github/actions/`·CLI 机器可读输出 |
| M-C4 | MCP server 目录 + 一键配置 + 能力发现 | Q4 | `integrations/mcp_client.py`·`market/` |
| M-C5 | VS Code / 飞书 slash 触发 Stage | Q4 | 外部薄壳（调 CLI/server） |
| M-C6 | 跨进程 agent 协作 demo | Q4 | `subagent/a2a.py`（新） |

---

## 二、现状锚点（真实代码）

| 关注点 | 文件:行 | 现状 |
|---|---|---|
| 零代码扩展 | `adapter/registry.py:29` `load_from_yaml` | Adapter 从 YAML 装载；Profile/Stage/Rule/Gate 同构 |
| 内置扩展 | `sdlc/builtin/{profiles,stages,rules,gates,subagents}/*.yaml` | 22 Adapter/14 Profile/548 Rule/12 Stage/10 Gate/11 Subagent 全 YAML |
| 4 层加载 | `utils/config*` | 项目 → `.sdlc/ext/` → 用户 `~/.sdlc/ext/` → 内置（市场装到用户层） |
| MCP 客户端 | `integrations/mcp_client.py` | 已实现，[02 M-A1] 接入 agent 工具循环 |
| CLI 输出 | `cli/run_cmd.py:150` | 目前人类可读文本，CI 需补机器可读（JSON） |
| A2A 前置 | [02 M-A5] Orchestrator-Worker | 进程内多 agent；A2A 是其跨进程标准化 |

> **关键洞察**：所有扩展点已是 YAML + registry 模式，SDK/市场本质是"**给现成扩展机制加脚手架、校验、打包、分发**"，不需重造扩展模型。

---

## 三、逐里程碑工程方案

### 3.1 M-C1：插件 SDK 与贡献者工具链

#### 3.1.1 目标

把"写扩展"门槛降到最低。现状写 Adapter 要手懂 YAML schema，缺脚手架/校验/测试/打包。

| 能力 | 现状 | 目标命令 |
|---|---|---|
| 脚手架 | 手写 YAML | `sdlc plugin new adapter <name>` |
| 校验 | 无 | `sdlc plugin validate` |
| 本地测试 | 无 | `sdlc plugin test`（样例输入干跑） |
| 打包 | 无 | `sdlc plugin pack`（含元数据/版本/签名） |
| 调试 | 靠审计日志 | `--debug`（决策链/注入 context/工具调用） |

#### 3.1.2 新增文件（新包 `sdlc/plugin/`）

| 文件 | 职责 |
|---|---|
| `sdlc/cli/plugin_cmd.py` | `plugin` 命令组 |
| `sdlc/plugin/scaffold.py` | 各扩展类型的模板生成（自带注释与示例） |
| `sdlc/plugin/validator.py` | schema + 依赖 + 冲突校验（复用各 registry 的 `load_from_yaml` 校验） |
| `sdlc/plugin/packer.py` | 打包为 `.sdlcpkg`（tar + manifest + 签名） |
| `sdlc/plugin/manifest.py` | `PluginManifest` schema |

#### 3.1.3 插件类型（覆盖全部扩展点）

```
plugin（可打包分发单元）
├── adapter    技术栈适配器
├── profile    工作流画像
├── stage      自定义阶段
├── rule-set   规则集
├── subagent   角色 agent
├── gate       审批闸门
└── skill      工具/技能包
```

#### 3.1.4 关键接口 / manifest

```python
# plugin/manifest.py
@dataclass
class PluginManifest:
    id: str
    type: str                    # adapter | profile | stage | rule-set | subagent | gate | skill
    version: str                 # 语义化版本
    sdlc_version: str            # 依赖的 sdlc 核心版本约束（如 ">=2.0,<3.0"）
    author: str
    description: str
    entry: str                   # 主 YAML 文件相对路径
    checksum: str = ""           # 内容哈希
    signature: str = ""          # 可选签名（市场信任机制）

# plugin/validator.py
class PluginValidator:
    def validate(self, plugin_dir: Path) -> "ValidationReport":
        # 1. manifest schema 合法
        # 2. entry YAML 能被对应 registry.load_from_yaml 成功装载
        # 3. sdlc_version 约束可满足
        # 4. id 不与内置/已装冲突
        ...
```

#### 3.1.5 关键约束

- **契约稳定**：SDK 依赖的 schema 版本化，承诺向后兼容（否则生态因 breaking change 崩塌）。`sdlc_version` 约束是护栏。
- **签名与来源**：包带签名 + 来源元数据，为市场信任打基础。
- **文档即模板**：脚手架生成的模板自带注释与示例，"照着改"即可用。

#### 3.1.6 向后兼容

- 全新命令组 + 新包，不改任何既有扩展加载逻辑。校验器**复用**各 registry 现有 `load_from_yaml`，不另立一套 schema。

#### 3.1.7 验收

- [ ] `plugin new/validate/test/pack` 可用，文档 + 模板齐备。
- [ ] 贡献者 30 分钟内做出一个可用 Adapter。

---

### 3.2 M-C2：模板 / Adapter 市场

#### 3.2.1 定位

社区共建的扩展分发平台（类比 Homebrew tap / npm registry）。开源飞轮的核心引擎。

#### 3.2.2 新增文件（新包 `sdlc/market/`）

| 文件 | 职责 |
|---|---|
| `sdlc/cli/market_cmd.py` | `market search/install/publish/update` |
| `sdlc/market/registry_client.py` | registry 读写（静态 index.json 起步） |
| `sdlc/market/installer.py` | 装到 `~/.sdlc/ext/`（复用 4 层加载） |
| `sdlc/market/trust.py` | 签名校验 + 来源验证 |

#### 3.2.3 市场能力与命令

| 能力 | 命令 | 落点 |
|---|---|---|
| 发现 | `sdlc market search <kw>` | 查 registry index |
| 安装 | `sdlc market install <plugin>` | 装到 `~/.sdlc/ext/`，4 层加载自动生效 |
| 发布 | `sdlc market publish` | 提交（走签名 + 审核） |
| 版本 | `sdlc market update` | 语义化版本 + sdlc 核心版本约束 |

#### 3.2.4 registry 格式（静态起步，零运维冷启动）

```json
// index.json（GitHub repo 托管，成熟后再服务化）
{
  "schema_version": "1",
  "plugins": [
    {
      "id": "adapter-django", "type": "adapter", "version": "1.2.0",
      "sdlc_version": ">=2.0,<3.0",
      "author": "community/xxx", "verified": false,
      "download_url": "https://.../adapter-django-1.2.0.sdlcpkg",
      "checksum": "sha256:...", "downloads": 128, "rating": 4.6
    }
  ]
}
```

#### 3.2.5 冷启动策略（工程落点）

1. **官方先填充**：把内置 22 Adapter + 14 Profile + 11 Subagent + 548 Rule 作为首批**官方认证**条目上架 —— 开张即 50+ 优质内容。
2. **降摩擦**：M-C1 SDK 让贡献者 10 分钟发一个扩展。
3. **激励可见性**：贡献者榜 / 被引用次数 / 本周热门（registry 元数据支持）。

#### 3.2.6 关键约束

- 后端**可复用 [03 M-B2 server]**，也可做**静态 registry**（GitHub repo + index.json）起步。
- **私有 registry**：支持企业内部市场，复用 4 层加载覆盖思想（`config set market.url`）。
- 提交需过 `plugin validate` + 可选 eval（[05] 打通：市场条目附质量分）。

#### 3.2.7 向后兼容

- 市场装的扩展落在用户层 `~/.sdlc/ext/`，与项目级扩展共存、项目级可覆盖。不改加载优先级。

#### 3.2.8 验收

- [ ] `market search/install/publish` 可用。
- [ ] 官方 50+ 条目上架；`market install` 一键装用。
- [ ] 支持私有 registry。

---

### 3.3 M-C3：CI 集成（开源最自然的采用入口）

#### 3.3.1 目标

GitHub Actions 在 PR 触发 review/test/security Stage，结果回帖 PR。把 agent 织入现有 PR 流程，零习惯改变。**CI 是团队场景 → 直接拉动协作占比 KPI。**

#### 3.3.2 前置：CLI 机器可读输出

现状 `run_cmd.py` 输出人类文本。CI 需 JSON：

```python
# cli/run_cmd.py 增 --format json
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
# 输出：{"pipeline_id", "status", "stages":[{id,status,error,artifacts}], "cost_usd"}
```

#### 3.3.3 新增文件

| 文件 | 职责 |
|---|---|
| `.github/actions/sdlc-review/action.yml` | 复合 action：装 sdlc → 跑 Stage → 解析 JSON → 回帖 |
| `.github/actions/sdlc-review/comment.py` | 把 JSON 结果格式化为 PR 评论（gh api） |
| `docs/ci-integration.md` | 用户接入文档 |

#### 3.3.4 约束

- 只做**适配层**，复用现有 CLI，不新增核心逻辑（[roadmap/05 §6.2]）。
- CI 用真实或 Ollama 模型（与 [05 M-D1] 冒烟共用思路，零成本可复现）。

#### 3.3.5 验收

- [ ] 开源仓库接 CI，PR 自动跑 review Stage 并回帖。

---

### 3.4 M-C4：MCP 工具生态

#### 3.4.1 目标

[02 M-A1] 已把 `mcp_call` 接入 agent。本里程碑把它**生态化**：MCP server 目录 + 一键配置 + 能力发现 + 审计。

#### 3.4.2 新增/改动文件

| 文件 | 动作 | 职责 |
|---|---|---|
| `sdlc/integrations/mcp_client.py` | 改 | 增能力发现：列出 server 可用工具 |
| `sdlc/market/` | 复用 | MCP server 配置作为一种"插件类型"进市场 |
| `sdlc/cli/mcp_cmd.py` | 新增 | `sdlc mcp add/list/test`（一键配置） |

#### 3.4.3 约束

- MCP server 白名单 + 权限分级 + 调用审计（回扣 [02 M-A1] 安全约束）。
- agent 能列出可用 MCP 工具按需调用，而非硬编码。

#### 3.4.4 验收

- [ ] MCP server 目录 + 一键配置 + 能力发现 + 审计。

---

### 3.5 M-C5：IDE / IM 原生集成

#### 3.5.1 目标

让 sdlc 嵌入研发既有触点，而非要求切工具。

| 触点 | 形态 | 价值 |
|---|---|---|
| VS Code | 轻量插件：选中代码→触发 Stage；看 Pipeline；审批 Gate | 不离开编辑器 |
| 飞书/Slack | 复用 [03 M-B4] 通知 + slash 触发 Pipeline | 团队协作自然入口 |

#### 3.5.2 落点

- IDE 插件做**轻量壳**：调 CLI / [03 M-B2] server API，不重造逻辑。
- IM slash：复用 [03 M-B4] `Notifier` + server 路由。
- **本仓库只提供 CLI/server 的稳定 API**；插件本身可作为独立仓库/市场条目。

#### 3.5.3 验收

- [ ] VS Code 插件触发 Stage；飞书/Slack slash 触发。

---

### 3.6 M-C6：A2A 协议雏形（前瞻）

#### 3.6.1 目标

[02 M-A5] 做了**进程内** Orchestrator-Worker。本里程碑把 agent 协作**跨进程/跨系统**标准化。

```
sdlc agent  ◄── A2A 协议 ──►  外部 agent 系统
（design agent）            （某团队专用安全审计 agent）
```

#### 3.6.2 新增文件

| 文件 | 职责 |
|---|---|
| `sdlc/subagent/a2a.py` | A2A 客户端/服务端：任务/结果/成功标准 schema 跨进程序列化 |

#### 3.6.3 约束

- **对齐社区标准**（MCP 的 agent 扩展 / 开放 A2A 规范），不自造孤岛。
- 交互契约**复用 [02 M-A5]** 定义的"任务/结果/成功标准" schema。
- A2A 是**可选高级能力**，不影响单机核心。外部 agent 走白名单 + 能力协商 + 审计。

#### 3.6.4 验收

- [ ] 跨进程 agent 协作 demo；对齐社区标准。

---

## 四、依赖与顺序

```
M-C1 SDK（供给）──→ M-C2 市场（分发）  先有优质内容才谈分发
M-C2 市场 ══ 后端可复用 ══ [03 M-B2 server]（也可静态 registry 起步）
M-C3 CI ── 依赖 CLI --format json（本方案 §3.3.2）
[02 M-A1 mcp 接入] ──→ M-C4 MCP 生态化
[02 M-A5 进程内多 agent] ──→ M-C6 A2A 跨进程
[03 M-B4 通知] ──→ M-C5 IM 集成
```

**季度落位**：M-C1/C2/C3（Q3 主线）→ M-C4/C5/C6（Q4）。

---

## 五、风险与缓解（工程视角）

| 风险 | 缓解 |
|---|---|
| 空市场冷启动失败 | 官方填充 50+；SDK 降摩擦；registry 元数据支持贡献榜 |
| 扩展质量参差损害口碑 | 提交过 `plugin validate` + 可选 eval；官方认证徽章；社区评分 |
| schema breaking change 崩塌生态 | schema 版本化 + `sdlc_version` 约束 + 弃用周期 |
| 恶意/不安全插件 | 签名 + 来源可查 + 白名单 + 审计；核心权限最小化 |
| 多端集成维护成本高 | 集成做轻量适配层，复用 CLI/server，不重造逻辑；插件可独立仓库 |
| A2A 自造孤岛 | 对齐社区标准协议，作可选高级能力 |

---

返回：[00 导航](./00-README.md) · 上一篇：[03 支柱二](./03-pillar-collaboration.md) · 下一篇：[05 支柱四 评估质量](./05-pillar-eval-quality.md)
