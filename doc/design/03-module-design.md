# 03. 模块设计 (v1.0)

> 13 个包逐个接口/类/职责

---

## 总览

| 包 | 行数估 | 核心类/函数 | 依赖 |
|---|---|---|---|
| `cli/` | ~600 | 19 个命令 | core, all |
| `core/` | ~1200 | 4 引擎 | adapter, stage, profile, rule, kb, subagent, state, audit |
| `kb/` | ~1000 | 5 类 | state, audit, integrations |
| `llm/` | ~700 | LLMClient + cache | integrations |
| `subagent/` | ~500 | Pool + caller | llm, kb |
| `adapter/` | ~400 | Registry + loader | integrations |
| `stage/` | ~400 | Catalog + runner | llm, subagent, kb, integrations |
| `profile/` | ~250 | Registry | adapter, stage, rule |
| `rule/` | ~500 | Engine + enforcer | kb, state |
| `gate/` | ~400 | Engine + decision | state, audit |
| `audit/` | ~250 | Logger | state |
| `state/` | ~500 | Store + snapshot | audit |
| `integrations/` | ~800 | MCP/Skill/Shell/HTTP/Git | — |
| `utils/` | ~400 | yaml/path/fingerprint/exception | — |

**总计**：~8400 行 Python 代码（M1+M2 MVP 约 3500 行）。

---

## 一、utils/（基础工具）

### 1.1 职责
最底层工具，无业务依赖。

### 1.2 文件
```
utils/
├── __init__.py
├── exceptions.py     # 异常层级
├── paths.py          # 路径解析
├── yaml_io.py        # ruamel.yaml 包装
├── fingerprint.py    # 文件/目录 hash
├── async_runner.py   # with timeout/retry
├── logging.py        # structured logging
├── time.py           # 时间/时区
├── git.py            # 简化 git 操作
└── text.py           # 文本处理（trim/normalize）
```

### 1.3 关键接口

```python
# exceptions.py
class SdlcError(Exception): pass
class ConfigError(SdlcError): pass
class EntryDetectionError(SdlcError): pass
class PipelineBuildError(SdlcError): pass
class StageExecutionError(SdlcError): pass
class LLMError(SdlcError): pass
class AdapterNotFoundError(SdlcError): pass
class KBWriteConflictError(SdlcError): pass
class ResumeExpiredError(SdlcError): pass
class RuleViolationError(SdlcError): pass

# paths.py
def sdlc_home() -> Path  # ~/.sdlc
def project_root(start: Path) -> Path
def ensure_dir(p: Path) -> Path

# yaml_io.py
def load_yaml(p: Path) -> Any
def save_yaml(p: Path, data: Any, preserve: bool = True) -> None
def load_yaml_str(s: str) -> Any

# fingerprint.py
def file_fingerprint(p: Path) -> str  # sha256
def dir_fingerprint(p: Path) -> str  # 聚合
```

---

## 二、core/（编排引擎）

### 2.1 职责
SDLC 编排 4 大引擎 + 调度协调器。

### 2.2 文件
```
core/
├── __init__.py
├── entry_detector.py     # 12 EntryPoint 检测
├── pipeline_builder.py   # DAG 构造
├── stage_runner.py       # 8 步生命周期
├── gate_engine.py        # 6 触发模式
├── pipeline.py           # Pipeline / Stage / Artifact 数据类
├── run_coordinator.py    # 顶层调度
└── result.py             # PipelineResult / StageResult
```

### 2.3 entry_detector.py

```python
@dataclass
class EntryPoint:
    kind: EntryKind  # IDEA|FEATURE|BUG|HOTFIX|REFACTOR|TEST|...
    raw_input: str
    detected_attachments: list[Path]
    confidence: float
    metadata: dict

class EntryDetector(Protocol):
    def detect(self, input: str | Path, **ctx) -> EntryPoint: ...

class DefaultEntryDetector:
    KEYWORDS = {
        EntryKind.IDEA: ["我想", "能否", "考虑"],
        EntryKind.FEATURE: ["新功能", "增加", "实现一个", "做一个"],
        EntryKind.BUG: ["报错", "异常", "不对", "失败", "bug"],
        EntryKind.HOTFIX: ["紧急", "线上", "立刻", "P0"],
        EntryKind.REFACTOR: ["重构", "优化", "清理"],
        EntryKind.TEST: ["测试", "覆盖率", "补单测"],
        EntryKind.INFRA: ["部署", "流水线", "CI", "镜像"],
        EntryKind.RELEASE: ["发布", "上线", "tag"],
        EntryKind.REVERT: ["回滚", "revert"],
        EntryKind.DOC: ["文档", "注释", "readme"],
        EntryKind.MIGRATE: ["迁移", "升级", "import"],
        EntryKind.AUDIT: ["审计", "安全", "合规"],
    }

    def detect(self, input, **ctx) -> EntryPoint:
        # 1. 文件类型检测（PR/issue/代码片段）
        # 2. 关键词匹配
        # 3. LLM 二次确认（可选）
        # 4. 返回 EntryPoint
```

### 2.4 pipeline_builder.py

```python
@dataclass
class Pipeline:
    id: str
    entry: EntryPoint
    profile: Profile
    stages: list[StageNode]  # DAG 邻接表
    artifacts: dict[str, Artifact]
    meta: Meta

class PipelineBuilder:
    def __init__(self, profile: Profile, stage_catalog: StageCatalog,
                 rule_engine: RuleEngine):
        self.profile = profile
        self.catalog = stage_catalog
        self.rules = rule_engine

    def build(self, entry: EntryPoint) -> Pipeline:
        # 7 步算法（见 prd/04-pipeline-builder.md）
        # 1. 选 base_stages from profile
        # 2. 应用 entry_specific_rules
        # 3. 注入 gate nodes
        # 4. 拓扑排序
        # 5. 验证 DAG 无环
        # 6. 分配 artifact 流向
        # 7. 生成 Pipeline
```

### 2.5 stage_runner.py

```python
@dataclass
class StageResult:
    stage_id: str
    status: StageStatus  # PENDING|RUNNING|SUCCESS|FAILED|SKIPPED
    artifacts: list[Artifact]
    started_at: datetime
    finished_at: datetime | None
    cost: Cost  # tokens/USD
    error: str | None

class StageRunner:
    def __init__(self, subagent_pool, llm_client, kb_writer,
                 audit, state, rules):
        ...

    async def run(self, pipeline: Pipeline) -> AsyncIterator[StageResult]:
        """逐 stage 执行"""
        for stage in self._topological_sort(pipeline):
            yield await self._run_one(stage, pipeline)

    async def _run_one(self, stage, pipeline) -> StageResult:
        # 8 步生命周期（见 06）
```

### 2.6 gate_engine.py

```python
@dataclass
class GateDecision:
    action: GateAction  # AUTO_PASS|MANUAL_REVIEW|BLOCK|ESCALATE
    reason: str
    reviewer: str | None
    deadline: datetime | None

class GateEngine:
    TRIGGERS = ["on_stage_end", "on_severity", "on_artifact",
                "on_rule_violation", "on_failure", "always"]

    def evaluate(self, stage_result, pipeline, context) -> GateDecision:
        # 见 06
```

### 2.7 run_coordinator.py

```python
class RunCoordinator:
    """顶层调度：组装所有引擎"""
    def __init__(self, deps: DependencyContainer):
        self.entry_detector = deps.entry_detector
        self.pipeline_builder = deps.pipeline_builder
        self.stage_runner = deps.stage_runner
        self.gate_engine = deps.gate_engine
        self.state = deps.state
        self.audit = deps.audit

    async def run(self, input: str | Path, **opts) -> PipelineResult:
        entry = self.entry_detector.detect(input)
        pipeline = self.pipeline_builder.build(entry)
        await self.state.save_pipeline(pipeline)
        results = []
        async for sr in self.stage_runner.run(pipeline):
            results.append(sr)
            decision = self.gate_engine.evaluate(sr, pipeline, results)
            await self._handle_decision(decision, sr, pipeline)
        return PipelineResult(pipeline, results)
```

---

## 三、kb/（知识引擎）

### 3.1 文件
```
kb/
├── __init__.py
├── scanner.py           # sdlc init 7 阶段
├── knowledge_base.py    # 11 KB 文件 IO
├── writer.py            # diff-only 写入
├── enforcer.py          # 规则强制
├── exceptions.py        # 临时豁免
├── models.py            # Pydantic 数据类
├── fingerprint.py       # KB 指纹
└── reconciler.py        # 每周 reconcile
```

### 3.2 关键接口

```python
# knowledge_base.py
class KnowledgeBase:
    def __init__(self, root: Path):
        self.root = root  # project_root/doc/kb/
        self.layers: dict[str, KBLayer] = {}  # name → KBLayer

    def get(self, name: str) -> KBLayer: ...
    def list(self) -> list[str]: ...
    def exists(self, name: str) -> bool: ...

class KBLayer:
    name: str
    type: Literal["markdown", "yaml", "json"]
    path: Path
    schema: type[BaseModel] | None

    def read(self) -> Any: ...
    def write(self, data: Any) -> None: ...
    def append(self, delta: Any) -> None: ...

# writer.py
class KBWriter:
    def __init__(self, kb: KnowledgeBase, audit: AuditLogger):
        self.kb = kb
        self.audit = audit

    def update_after_stage(self, stage_id: str,
                            artifacts: list[Artifact]) -> list[KBDelta]:
        """按 stage→KB 映射表写入"""
        deltas = []
        for mapping in self._mapping_for(stage_id):
            delta = self._build_delta(mapping, artifacts)
            if self._should_write(delta):
                self.kb.get(mapping.target).append(delta.content)
                deltas.append(delta)
                self.audit.emit("kb_updated", {...})
        return deltas
```

---

## 四、llm/（LLM 抽象）

### 4.1 文件
```
llm/
├── __init__.py
├── client.py            # 统一 LLMClient
├── anthropic_provider.py
├── openai_provider.py
├── cache.py             # prompt+context → response
├── prompt.py            # Jinja2 渲染
├── cost.py              # 成本跟踪
├── models.py            # Message/Tool/Response
└── config.py            # 路由配置
```

### 4.2 关键接口

```python
# client.py
class LLMClient(Protocol):
    async def complete(self, req: CompletionRequest) -> CompletionResponse: ...
    async def stream(self, req: CompletionRequest) -> AsyncIterator[str]: ...

class MultiLLMClient:
    """主+回退 + 多模型路由"""
    def __init__(self, primary: AnthropicProvider,
                 fallback: OpenAIProvider,
                 router: ModelRouter,
                 cache: LLMCache):
        ...

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        if cached := self.cache.get(req):
            return cached
        try:
            resp = await self.primary.complete(req)
        except (RateLimitError, APITimeoutError) as e:
            self.audit.emit("llm_fallback", {...})
            resp = await self.fallback.complete(req)
        self.cache.put(req, resp)
        await self.cost.track(req, resp)
        return resp

# prompt.py
class PromptRenderer:
    def __init__(self, template_dir: Path):
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def render(self, template: str, context: dict) -> str:
        tmpl = self.env.from_string(template)
        return tmpl.render(**context)
```

---

## 五、subagent/（Subagent 池）

### 5.1 文件
```
subagent/
├── __init__.py
├── pool.py              # 调度
├── registry.py          # 注册表
├── claude_caller.py     # 调外部 Claude
├── builtin.py           # 11 个内置 Subagent
└── models.py
```

### 5.2 关键接口

```python
@dataclass
class Subagent:
    id: str  # SA-1 ~ SA-11
    name: str
    role: str  # requirements-analyst | architect | coder-...
    model: str  # claude-opus-4-7 | sonnet | haiku
    tools: list[str]  # 允许用的工具
    kb_inject: list[str]  # 注入哪些 KB
    prompt: str
    max_iter: int = 10

class SubagentPool:
    def __init__(self, registry: SubagentRegistry,
                 llm: LLMClient, kb: KnowledgeBase):
        ...

    async def invoke(self, agent_id: str, task: SubagentTask) -> SubagentResult:
        agent = self.registry.get(agent_id)
        context = self._build_context(agent, task)
        response = await self.llm.complete(context)
        return self._parse_result(agent, response)

    def _build_context(self, agent, task) -> CompletionRequest:
        kb_context = self.kb.get_for_role(agent.role, agent.kb_inject)
        prompt = self.renderer.render(agent.prompt, {
            **task.dict(),
            **kb_context,
        })
        return CompletionRequest(
            model=agent.model,
            messages=[Message(role="user", content=prompt)],
            tools=agent.tools,
        )
```

---

## 六、adapter/（Adapter 加载）

### 6.1 文件
```
adapter/
├── __init__.py
├── registry.py
├── loader.py            # 从 YAML 加载
├── detector.py          # 自动检测
├── dongboot.py          # 18 DongBoot 组件（默认实现）
└── models.py
```

### 6.2 关键接口

```python
@dataclass
class AdapterDef:
    id: str
    name: str
    detect_patterns: list[str]  # 文件/正则
    components: list[ComponentDef]
    enforce_rules: bool
    rule_sets: list[str]
    required_kb: list[str]
    version: str

class AdapterRegistry:
    def __init__(self, builtin_dir: Path, user_dir: Path):
        self.adapters: dict[str, AdapterDef] = {}
        self._load(builtin_dir)
        self._load(user_dir)

    def detect_for_project(self, root: Path) -> list[AdapterDef]:
        """扫描项目根，匹配 detect_patterns"""
        ...

    def get(self, id: str) -> AdapterDef: ...
```

---

## 七、stage/（Stage 加载 + Runner）

### 7.1 文件
```
stage/
├── __init__.py
├── catalog.py
├── loader.py
├── runner.py
└── models.py
```

### 7.2 关键接口

```python
@dataclass
class StageDef:
    id: str  # s-clarify
    name: str
    category: str  # requirement|design|impl|test|review|...
    required_artifacts: list[str]
    produces_artifacts: list[str]
    pre_kb_load: list[str]
    post_kb_update: list[str] | None
    subagent: str  # SA-X
    timeout: int
    retry: int

class StageCatalog:
    def __init__(self, builtin_dir: Path, user_dir: Path):
        self.stages: dict[str, StageDef] = {}

    def get(self, id: str) -> StageDef: ...
    def list(self) -> list[StageDef]: ...
    def for_category(self, cat: str) -> list[StageDef]: ...
```

---

## 八、profile/（Project Profile）

### 8.1 文件
```
profile/
├── __init__.py
├── registry.py
├── detector.py
└── models.py
```

### 8.2 关键接口

```python
@dataclass
class ProfileDef:
    id: str  # new-feature|bug-fix|hotfix|refactor|...
    base_stages: list[str]
    skip_stages: list[str]
    extra_stages: list[str]
    gates: list[GateDef]
    subagent_overrides: dict[str, str]
    severity: Severity

class ProfileRegistry:
    def resolve(self, entry: EntryPoint, context: ProfileContext) -> ProfileDef:
        """根据 EntryPoint + 上下文选 Profile"""
        ...
```

---

## 九、rule/（规则引擎）

### 9.1 文件
```
rule/
├── __init__.py
├── engine.py
├── enforcer.py          # 4 个 enforcer
├── exceptions.py        # 豁免管理
├── loader.py
└── models.py
```

### 9.2 关键接口

```python
@dataclass
class Rule:
    id: str
    level: Literal["MUST", "SHOULD", "MAY"]
    category: str
    description: str
    enforcer: str  # cr|lint|ci|runtime
    config: dict
    exceptions: list[Exception] = field(default_factory=list)

class RuleEngine:
    def __init__(self, kb: KnowledgeBase):
        self.rules: list[Rule] = []
        self._load()

    def for_role(self, role: str) -> list[Rule]:
        """按角色过滤"""
        ...

    def for_stage(self, stage_id: str) -> list[Rule]:
        ...

    def add(self, rule: Rule) -> None: ...
    def disable(self, rule_id: str, until: datetime, reason: str) -> None: ...
```

---

## 十、gate/（Gate 引擎）

### 10.1 文件
```
gate/
├── __init__.py
├── engine.py
├── triggers.py          # 6 触发模式
├── decision.py
└── models.py
```

---

## 十一、audit/（审计）

### 11.1 文件
```
audit/
├── __init__.py
├── logger.py            # JSONL
├── events.py            # 25+ 事件类型
└── query.py             # 审计查询
```

### 11.2 关键接口

```python
class AuditEventType(str, Enum):
    PIPELINE_START = "pipeline_start"
    STAGE_START = "stage_start"
    STAGE_END = "stage_end"
    ARTIFACT_CREATED = "artifact_created"
    KB_UPDATED = "kb_updated"
    KB_INIT = "kb_init"
    RULE_VIOLATION = "rule_violation"
    GATE_TRIGGERED = "gate_triggered"
    GATE_DECISION = "gate_decision"
    LLM_CALLED = "llm_called"
    LLM_FALLBACK = "llm_fallback"
    SUBAGENT_INVOKED = "subagent_invoked"
    MCP_CALLED = "mcp_called"
    SKILL_USED = "skill_used"
    FILE_WRITTEN = "file_written"
    ERROR = "error"
    RESUME = "resume"
    PIPELINE_END = "pipeline_end"
    # ... 共 25+

class AuditLogger:
    def __init__(self, log_path: Path):
        self.log_path = log_path

    def emit(self, type: AuditEventType, payload: dict) -> None:
        event = {
            "ts": utcnow().isoformat(),
            "type": type.value,
            "payload": payload,
        }
        with self.log_path.open("a") as f:
            f.write(json.dinternal-monitorings(event) + "\n")

    def query(self, type: str | None = None,
              since: datetime | None = None) -> Iterator[dict]: ...
```

---

## 十二、state/（状态）

### 12.1 文件
```
state/
├── __init__.py
├── store.py             # SQLite
├── schema.py            # 表 DDL
├── snapshot.py          # 快照
├── resume.py            # 12h token
└── models.py
```

### 12.2 关键接口

```python
class StateStore:
    def __init__(self, db_path: Path):
        self.db = sqlite3.connect(db_path, isolation_level=None)
        self._init_schema()

    def save_pipeline(self, p: Pipeline) -> None: ...
    def load_pipeline(self, id: str) -> Pipeline: ...
    def save_stage_result(self, r: StageResult) -> None: ...
    def list_pipelines(self, status: str | None = None) -> list[Pipeline]: ...
    def get_resume_token(self, id: str) -> str: ...
    def verify_resume_token(self, id: str, token: str) -> bool: ...
```

### 12.3 SQLite Schema（核心 6 表）

```sql
-- pipelines
CREATE TABLE pipelines (
  id TEXT PRIMARY KEY,
  entry_kind TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  status TEXT NOT NULL,  -- running|paused|completed|failed
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  meta_json TEXT NOT NULL  -- 含 entry, options, summary
);

-- stages
CREATE TABLE stages (
  id TEXT PRIMARY KEY,
  pipeline_id TEXT NOT NULL,
  stage_def_id TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  error TEXT,
  FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
);
CREATE INDEX idx_stages_pipeline ON stages(pipeline_id);

-- artifacts
CREATE TABLE artifacts (
  id TEXT PRIMARY KEY,
  pipeline_id TEXT NOT NULL,
  stage_id TEXT NOT NULL,
  type TEXT NOT NULL,  -- code|doc|test|report|...
  path TEXT,
  content_hash TEXT,
  meta_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
);

-- llm_calls
CREATE TABLE llm_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pipeline_id TEXT NOT NULL,
  stage_id TEXT NOT NULL,
  model TEXT NOT NULL,
  input_tokens INTEGER,
  output_tokens INTEGER,
  cost_usd REAL,
  duration_ms INTEGER,
  cached INTEGER DEFAULT 0,
  created_at TEXT NOT NULL
);

-- kb_deltas
CREATE TABLE kb_deltas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pipeline_id TEXT,
  stage_id TEXT,
  target TEXT NOT NULL,  -- conventions.md
  operation TEXT NOT NULL,  -- append|update
  fingerprint TEXT NOT NULL,  -- 用于去重
  summary TEXT,
  created_at TEXT NOT NULL
);

-- audit_log_meta
CREATE TABLE audit_log_meta (
  pipeline_id TEXT PRIMARY KEY,
  log_path TEXT NOT NULL,
  event_count INTEGER DEFAULT 0,
  last_event_ts TEXT
);
```

---

## 十三、integrations/（外部集成）

### 13.1 文件
```
integrations/
├── __init__.py
├── mcp_client.py        # MCP SDK 包装
├── skill_runner.py      # 调内置 skill
├── shell_runner.py      # 受限 shell
├── http_client.py       # httpx 包装
├── git_client.py        # git 操作
├── filesystem.py        # 文件读写
└── whitelist.py         # 命令白名单
```

### 13.2 关键接口

```python
# shell_runner.py
class ShellRunner:
    WHITELIST = {
        "git": {"commit", "diff", "log", "show", "status"},
        "ls": set(),  # 任何子命令
        "cat": set(),
        "mvn": {"compile", "test", "package", "install"},
        "npm": {"install", "test", "run", "build"},
        "go": {"build", "test", "mod"},
        "kubectl": {"get", "logs", "describe"},
    }

    def run(self, cmd: list[str], timeout: int = 60) -> ShellResult:
        if not self._allowed(cmd):
            raise SecurityError(f"command not allowed: {cmd}")
        ...

# mcp_client.py
class MCPClient:
    async def call(self, server: str, tool: str, args: dict) -> dict:
        """调外部 MCP server 工具"""
        ...
```

---

## 十四、cli/（命令层）

### 14.1 文件
```
cli/
├── __init__.py
├── main.py              # @click.group
├── run.py               # sdlc run
├── init.py              # sdlc init
├── status.py            # sdlc status
├── resume.py            # sdlc resume
├── trace.py             # sdlc trace
├── rule.py              # sdlc rule list/show/...
├── kb.py                # sdlc kb show/diff
├── stage.py             # sdlc stage list/show
├── adapter.py           # sdlc adapter list/detect
├── profile.py           # sdlc profile list
├── agent.py             # sdlc agent list/invoke
├── config.py            # sdlc config show/set
├── deps.py              # 依赖注入容器
└── ui.py                # rich 输出辅助
```

### 14.2 命令清单（19 个）

```python
# sdlc run INPUT [OPTIONS]
# sdlc init [PATH]
# sdlc status [PIPELINE_ID]
# sdlc resume PIPELINE_ID
# sdlc trace PIPELINE_ID [--since=...]
# sdlc rule {list,show,add,disable,check,violations}
# sdlc kb {list,show,diff,scan,update}
# sdlc stage {list,show,validate}
# sdlc adapter {list,detect,validate}
# sdlc profile {list,show,resolve}
# sdlc agent {list,invoke,test}
# sdlc config {show,set,get,reset}
# sdlc doctor                     # 自检
# sdlc version
# sdlc completion                 # shell 补全
# sdlc replay PIPELINE_ID         # 重放
# sdlc export PIPELINE_ID         # 导出元数据
# sdlc import PATH                # 导入配置
# sdlc stats                      # 统计
```

### 14.3 main.py 骨架

```python
@click.group()
@click.option("-c", "--config", type=Path, help="配置文件")
@click.option("-v", "--verbose", count=True)
@click.option("--no-color", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def main(ctx, config, verbose, no_color, dry_run):
    """SDLC AI 编排工具"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)
    ctx.obj["verbose"] = verbose
    ctx.obj["dry_run"] = dry_run
    setup_logging(verbose, no_color)
    ctx.obj["deps"] = build_deps(ctx.obj["config"])

# 注册子命令
main.add_command(run.run)
main.add_command(init.init)
# ... 共 19 个
```

---

## 十五、Dependency Injection 容器

```python
# cli/deps.py
@dataclass
class DependencyContainer:
    config: Config
    audit: AuditLogger
    state: StateStore
    llm: LLMClient
    cache: LLMCache
    cost: CostTracker
    adapter_registry: AdapterRegistry
    stage_catalog: StageCatalog
    profile_registry: ProfileRegistry
    rule_engine: RuleEngine
    kb: KnowledgeBase
    kb_writer: KBWriter
    subagent_pool: SubagentPool
    gate_engine: GateEngine
    mcp: MCPClient
    shell: ShellRunner
    http: HTTPClient
    git: GitClient
    # 引擎
    entry_detector: EntryDetector
    pipeline_builder: PipelineBuilder
    stage_runner: StageRunner
    run_coordinator: RunCoordinator

def build_deps(config: Config) -> DependencyContainer:
    """按 config 组装所有依赖，单例"""
    ...
```

---

## 十六、版本

- v1.0 (2026-06-05): 初版
