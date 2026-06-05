# 05. CLI 与 API (v1.0)

> 19 个 CLI 命令 + 内部 Python API + 子命令设计

---

## 一、CLI 总览

| 分类 | 命令 | 数量 |
|---|---|---|
| 核心流程 | run / init / status / resume / trace | 5 |
| 知识管理 | kb (list/show/diff/scan/update) | 5 子命令 |
| 规则 | rule (list/show/add/disable/check/violations) | 6 子命令 |
| 资源浏览 | stage / adapter / profile / agent | 4 |
| 配置 | config / doctor / version | 3 |
| 辅助 | completion / replay / export / import / stats | 5 |

**总命令**：19 个顶层 + 30+ 子命令。

---

## 二、详细命令

### 2.1 `sdlc run` — 执行一个 SDLC 流程

```bash
sdlc run INPUT [OPTIONS]

INPUT:
  文本                   # 自由描述
  @path/to/file.md      # 从文件读
  -                     # 从 stdin 读
  PR/issue URL           # 自动 fetch

OPTIONS:
  -p, --profile ID        # 强制 Profile（auto|new-feature|bug-fix|hotfix|...）
  -e, --entry-kind KIND   # 强制 EntryKind
  -a, --adapter ID        # 强制 Adapter
  -s, --stages LIST       # 只跑指定 stages（逗号分隔）
  --skip-stages LIST      # 跳过
  --severity P0|P1|P2|P3  # 强制严重度
  --gate-mode auto|manual|skip
  --no-deploy             # 跑到 deploy 前停
  --no-monitor            # 不部署监控
  --no-kb-update          # 不更新 KB
  --dry-run               # 只生成 plan，不执行
  --resume-on-fail        # 失败后自动 resume
  --max-cost USD          # 成本上限（默认 $5）
  --timeout SECONDS       # 全流程超时
  --tag KEY=VAL           # 自定义标签

EXAMPLES:
  sdlc run "做一个订单查询接口"
  sdlc run @docs/feature-idea.md --severity P2
  sdlc run -p hotfix "线上订单创建 5xx 错误"
  sdlc run @pr-link --no-deploy
  echo "补 RateLimiter 单测" | sdlc run -
  sdlc run "迁移到 DongBoot 2.0" --stages s-clarify,s-design,s-impl
```

**Python API**：

```python
from sdlc import SdlcClient
client = SdlcClient()
result = client.run(
    input="做一个订单查询接口",
    profile="new-feature",
    severity="P2",
    no_deploy=False,
    max_cost=5.0,
)
print(result.status, result.cost, result.report_url)
```

### 2.2 `sdlc init` — 初始化项目

```bash
sdlc init [PATH] [OPTIONS]

PATH:
  .  # 当前目录（默认）
  /path/to/project

OPTIONS:
  --depth N              # 扫描深度（默认 5）
  --no-llm               # 不调 LLM，只做静态扫描
  --force                # 覆盖已存在 doc/kb/
  --template ID          # 用模板（default|empty|full）
  --adapter ID           # 强制使用某 Adapter
  --no-commit            # 不自动 git commit
  --interactive / -i     # 关键决策询问用户

EXAMPLES:
  sdlc init                       # 扫描当前项目
  sdlc init ~/work/myapp -i       # 交互式
  sdlc init --template empty      # 空白 KB
  sdlc init --no-llm              # 离线模式
```

### 2.3 `sdlc status` — 状态查询

```bash
sdlc status [PIPELINE_ID] [OPTIONS]

OPTIONS:
  --all                 # 所有 pipeline
  --status STATUS       # 过滤（running|paused|completed|failed）
  --since TIMESPEC      # 起始时间（1d|2026-06-01）
  --limit N             # 最多 N 条
  --json                # JSON 输出
  --watch               # 实时刷新

EXAMPLES:
  sdlc status                       # 当前 active
  sdlc status feat-2026-06-05-001   # 指定
  sdlc status --all --since 1d
  sdlc status --watch
```

输出（rich 表格）：
```
ID                         ENTRY        PROFILE       STATUS      COST    STAGE
feat-2026-06-05-001        feature      new-feature   running     $0.42   s-impl-backend (3/9)
bug-2026-06-04-007         bug          bug-fix       completed   $0.18   -
hotfix-2026-06-03-002      hotfix       hotfix        failed      $0.31   s-deploy
```

### 2.4 `sdlc resume` — 恢复

```bash
sdlc resume PIPELINE_ID [OPTIONS]

OPTIONS:
  --token TOKEN          # 不查 prompt
  --from-stage STAGE     # 强制从某 stage 重跑
  --reset-gates          # 重新过 gate
  --force                # 跳过 token 验证（仅 owner）

EXAMPLES:
  sdlc resume feat-2026-06-05-001
  sdlc resume feat-2026-06-05-001 --from-stage s-impl-backend
```

### 2.5 `sdlc trace` — 链路追踪

```bash
sdlc trace PIPELINE_ID [OPTIONS]

OPTIONS:
  --stage STAGE          # 只看某 stage
  --type TYPE            # 事件类型
  --since TS             # 时间过滤
  --json                 # JSON 输出
  --follow               # 实时跟踪（类似 tail -f）

EXAMPLES:
  sdlc trace feat-2026-06-05-001
  sdlc trace feat-2026-06-05-001 --type llm_called
  sdlc trace feat-2026-06-05-001 --follow
```

### 2.6 `sdlc rule` — 规则管理

```bash
sdlc rule list                           # 列出所有规则
sdlc rule list --level MUST --category deployment
sdlc rule show RULE_ID                   # 详细
sdlc rule add --from-file rules.yaml    # 批量加
sdlc rule add -                          # 从 stdin
sdlc rule disable RULE_ID --until 2026-12-31 --reason "..."
sdlc rule check STAGE_ID                 # 在某 stage 检查
sdlc rule violations [--since 7d]        # 历史违规

EXAMPLES:
  sdlc rule list --level MUST
  sdlc rule show dongboot-hot-deploy-only-in-dev
  sdlc rule disable dongboot-hot-deploy-only-in-dev --until 2026-12-31 --reason "P0 紧急修复"
  sdlc rule check s-deploy
```

### 2.7 `sdlc kb` — KB 管理

```bash
sdlc kb list                            # 列出所有 KB 文件
sdlc kb show PATH                       # 显示内容
sdlc kb diff PATH1 PATH2                # diff
sdlc kb scan [--full]                   # 重扫（增量/全量）
sdlc kb update --stage STAGE_ID         # 手动触发某 stage 的 KB 更新
sdlc kb stats                           # KB 健康度统计
sdlc kb reconcile                       # reconcile（去重/合并）

EXAMPLES:
  sdlc kb list
  sdlc kb show architecture/component-catalog.md
  sdlc kb scan --full
  sdlc kb stats
```

### 2.8 `sdlc stage` — Stage 浏览

```bash
sdlc stage list                         # 所有
sdlc stage list --category impl         # 按 category
sdlc stage show STAGE_ID                # 详细
sdlc stage validate STAGE_ID            # 校验 YAML schema
sdlc stage run STAGE_ID --input ...     # 单 stage 跑（开发调试用）

EXAMPLES:
  sdlc stage list
  sdlc stage show s-impl-backend
  sdlc stage validate ~/.sdlc/stages/custom/s-extra.yaml
  sdlc stage run s-clarify --input "做一个登录接口"
```

### 2.9 `sdlc adapter` — Adapter 浏览

```bash
sdlc adapter list
sdlc adapter show ID
sdlc adapter detect [PATH]              # 在项目根检测
sdlc adapter validate PATH.yaml
sdlc adapter init --name NAME --detect "glob:..."

EXAMPLES:
  sdlc adapter list
  sdlc adapter detect .
  sdlc adapter show dongboot
```

### 2.10 `sdlc profile` — Profile 浏览

```bash
sdlc profile list
sdlc profile show ID
sdlc profile resolve --entry feature --severity P2
sdlc profile init --name NAME --entry-kinds feature
sdlc profile validate PATH.yaml
```

### 2.11 `sdlc agent` — Subagent 浏览

```bash
sdlc agent list
sdlc agent show ID
sdlc agent invoke ID --task "..."     # 直接调
sdlc agent test ID                    # 用样例任务测试
sdlc agent init --name NAME --role architect
```

### 2.12 `sdlc config` — 配置

```bash
sdlc config show                       # 当前生效配置
sdlc config get KEY
sdlc config set KEY VALUE
sdlc config reset [--confirm]
sdlc config path                       # 配置文件路径
sdlc config edit                       # $EDITOR
```

### 2.13 `sdlc doctor` — 自检

```bash
sdlc doctor [OPTIONS]

CHECKS:
  ✓ Python 版本 ≥ 3.11
  ✓ uv 已安装
  ✓ 配置文件可读
  ✓ LLM API key 有效（探测性 ping）
  ✓ MCP server 可达
  ✓ 网络可达
  ✓ 磁盘空间 ≥ 1GB
  ✓ KB 路径可写
  ✓ Shell 白名单配置

OUTPUT:
  ✓ 所有检查通过 / 或列出问题
```

### 2.14 `sdlc version`

```bash
sdlc version
# sdlc 0.1.0 (python 3.11.5, claude-opus-4-7 default)
```

### 2.15 `sdlc completion` — Shell 补全

```bash
sdlc completion bash > /etc/bash_completion.d/sdlc
sdlc completion zsh > "${fpath[1]}/_sdlc"
sdlc completion fish > ~/.config/fish/completions/sdlc.fish
```

### 2.16 `sdlc replay` — 重放

```bash
sdlc replay PIPELINE_ID [OPTIONS]

OPTIONS:
  --stage STAGE          # 只重放某 stage
  --fresh                 # 不读上次结果，完全重跑

EXAMPLES:
  sdlc replay feat-2026-06-05-001 --stage s-impl-backend
```

### 2.17 `sdlc export` / `sdlc import`

```bash
sdlc export PIPELINE_ID --output PATH.tar.gz
sdlc import PATH.tar.gz                  # 导入到本项目
```

### 2.18 `sdlc stats` — 统计

```bash
sdlc stats [--since 7d] [--by model|stage|adapter|profile]

OUTPUT:
  - Pipeline 总数
  - 成功率
  - 平均成本 / 耗时
  - 按 model 成本占比
  - 按 stage 平均耗时
  - 规则违规 Top 5
  - KB 更新频次
```

---

## 三、内部 Python API

### 3.1 顶层 `SdlcClient`

```python
from sdlc import SdlcClient
from sdlc.models import Input, PipelineResult

class SdlcClient:
    def __init__(self, config: Config | None = None):
        self.deps = build_deps(config or load_config())

    def run(self, input: str | Path | Input, **opts) -> PipelineResult: ...
    def init(self, path: Path = Path("."), **opts) -> InitResult: ...
    def status(self, **filters) -> list[PipelineSummary]: ...
    def resume(self, pipeline_id: str, **opts) -> PipelineResult: ...
    def trace(self, pipeline_id: str, **filters) -> Iterator[AuditEvent]: ...

    # 知识
    def kb_list(self) -> list[KBFile]: ...
    def kb_show(self, path: str) -> str: ...
    def kb_update(self, target: str, delta: str, **opts) -> KBDelta: ...

    # 规则
    def rule_list(self, **filters) -> list[Rule]: ...
    def rule_check(self, stage_id: str, **ctx) -> list[Violation]: ...

    # 资源
    def stage_list(self) -> list[StageDef]: ...
    def adapter_detect(self, path: Path) -> list[AdapterDef]: ...
    def profile_resolve(self, entry: EntryKind, **ctx) -> ProfileDef: ...

    # 调试
    def doctor(self) -> DoctorReport: ...
```

### 3.2 异步入口

```python
from sdlc import AsyncSdlcClient

class AsyncSdlcClient(SdlcClient):
    async def run(self, input, **opts) -> PipelineResult: ...
    async def init(self, path, **opts) -> InitResult: ...
    async def status(self) -> list[PipelineSummary]: ...
```

### 3.3 嵌入式使用（高级）

```python
from sdlc.core import (
    EntryDetector, PipelineBuilder, StageRunner,
)
from sdlc.adapters import AdapterRegistry
from sdlc.stages import StageCatalog

# 单独使用某个引擎
detector = EntryDetector()
entry = detector.detect("做一个订单查询")

catalog = StageCatalog()
builder = PipelineBuilder(profile=..., stage_catalog=catalog, ...)
pipeline = builder.build(entry)

runner = StageRunner(...)
async for stage_result in runner.run(pipeline):
    print(stage_result)
```

### 3.4 编程式注册自定义 Adapter

```python
from sdlc.adapter import register_adapter
from pathlib import Path

register_adapter(
    id="my-company-stack",
    name="My Company Stack",
    detect_patterns=[{"glob": "**/package.json", "contains": "mycorp"}],
    components=[...],
    enforce_rules=True,
    rule_sets=["mycorp-must"],
)
```

### 3.5 自定义 Stage 编程式注册

```python
from sdlc.stage import register_stage

register_stage(
    id="s-my-special",
    name="My Special Stage",
    category="extra",
    subagent="SA-12",
    produces_artifacts=["x.yaml"],
    pre_kb_load=["conventions.md"],
    post_kb_update=None,
    timeout=600,
)
```

---

## 四、命令共性

### 4.1 全局选项

```bash
-c, --config PATH       # 配置文件（默认 ~/.sdlc/config.toml）
-v, --verbose           # 多次使用增加详细度（-v / -vv / -vvv）
-q, --quiet             # 静默
--no-color              # 关闭颜色
--json                  # JSON 输出（machine-readable）
--dry-run               # 只显示将做什么
--confirm               # 危险操作二次确认
```

### 4.2 退出码

| Code | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 一般错误 |
| 2 | 配置错误 |
| 3 | 检测失败（找不到 Adapter/Profile） |
| 4 | Pipeline 构建失败 |
| 5 | Stage 执行失败 |
| 6 | LLM 失败（含 fallback 也失败） |
| 7 | 规则违规被阻断 |
| 8 | Gate 拒绝 |
| 9 | 用户取消 |
| 10 | Resume 失败（token 过期/不一致） |
| 64+ | 业务自定义 |

### 4.3 错误输出

```bash
$ sdlc run "..."
✗ Error: LLM API rate limit
  Cause: anthropic.RateLimitError on claude-opus-4-7
  Retried 3 times, fallback to gpt-4o also failed
  Suggestion: 检查 ANTHROPIC_API_KEY 配额；或 --max-cost 0.5 减少 token
  Trace: feat-2026-06-05-001 → s-clarify → SA-1
  Audit: ~/.sdlc/audit.log:1234
```

### 4.4 帮助格式（rich 渲染）

```
$ sdlc run --help

 Usage: sdlc run INPUT [OPTIONS]

 执行一个 SDLC 流程。

┌─ INPUT ─────────────────────────────────────────────────┐
│ 文本 | @file | - (stdin) | URL                          │
└──────────────────────────────────────────────────────────┘

┌─ Options ───────────────────────────────────────────────┐
│ -p, --profile ID       强制 Profile (auto|...)         │
│ -e, --entry KIND       强制 EntryKind                  │
│ --severity LEVEL       P0|P1|P2|P3                     │
│ --no-deploy            跑到 deploy 前停                 │
│ --max-cost USD         成本上限 (default 5.0)          │
│ --dry-run              只生成 plan                    │
└──────────────────────────────────────────────────────────┘

 Examples:
   sdlc run "做一个订单查询接口"
   sdlc run @pr-link --no-deploy
   sdlc run -p hotfix "线上 5xx"

 Docs: https://sdlc.dev/run
```

---

## 五、版本

- v1.0 (2026-06-05): 初版
