# 09. Subagent 与 LLM (v1.0)

> Subagent 池 + LLM 抽象 + 多 provider + 缓存 + 成本跟踪

---

## 一、整体架构

```
┌──────────────────────────────────────────────────────────┐
│                  SubagentPool                            │
│                                                          │
│  invoke(SA-X, task)                                      │
│    ↓                                                     │
│  ┌────────────┐  ┌─────────────┐  ┌────────────────┐    │
│  │ 渲染 Prompt│→ │ 注入 KB    │→ │ 注入 Rules    │    │
│  └────────────┘  └─────────────┘  └────────────────┘    │
│         ↓                                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │  LLMClient (Anthropic 主 + OpenAI 回退)         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │   │
│  │  │ Cache 检查  │→ │ Anthropic 调 │→ │ Fallback│ │   │
│  │  └──────────────┘  └──────────────┘  └──────────┘ │   │
│  └─────────────────────────────────────────────────┘   │
│         ↓                                               │
│  解析 tool calls → 循环 → 最终结果                       │
└──────────────────────────────────────────────────────────┘
```

---

## 二、LLM 抽象

### 2.1 接口

```python
# llm/models.py
class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class Message(BaseModel):
    role: Role
    content: str | list[ContentBlock]
    tool_call_id: str | None = None
    name: str | None = None

class Tool(BaseModel):
    name: str
    description: str
    input_schema: dict  # JSON schema

class CompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    tools: list[Tool] = []
    system: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    stop_sequences: list[str] = []
    metadata: dict = {}  # pipeline_id, stage_id, agent_id

class CompletionResponse(BaseModel):
    id: str
    model: str
    content: list[ContentBlock]
    stop_reason: str
    usage: Usage
    cost_usd: float
    duration_ms: int
    cached: bool = False

class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

class LLMClient(Protocol):
    async def complete(self, req: CompletionRequest) -> CompletionResponse: ...
    async def stream(self, req: CompletionRequest) -> AsyncIterator[str]: ...
    def model_info(self, model: str) -> ModelInfo: ...
```

### 2.2 Anthropic Provider

```python
# llm/anthropic_provider.py
class AnthropicProvider:
    PRICING = {
        "claude-opus-4-7":   {"in": 15.0,  "out": 75.0},   # $/1M tokens
        "claude-sonnet-4-6": {"in": 3.0,   "out": 15.0},
        "claude-haiku-4-5":  {"in": 0.80,  "out": 4.0},
    }

    def __init__(self, api_key: str, timeout: int = 60):
        self.client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout)

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        start = time.monotonic()
        try:
            response = await self.client.messages.create(
                model=req.model,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
                system=req.system,
                messages=[m.model_dinternal-monitoring() for m in req.messages if m.role != Role.SYSTEM],
                tools=[t.model_dinternal-monitoring() for t in req.tools] or None,
                stop_sequences=req.stop_sequences or None,
                metadata=req.metadata,
            )
            return self._to_response(response, start)
        except anthropic.RateLimitError as e:
            raise LLMRateLimitError(str(e))
        except anthropic.APITimeoutError as e:
            raise LLMTimeoutError(str(e))
        except anthropic.APIError as e:
            raise LLMError(str(e))

    def _to_response(self, raw, start) -> CompletionResponse:
        usage = raw.usage
        pricing = self.PRICING.get(raw.model, {"in": 0, "out": 0})
        cost = (usage.input_tokens * pricing["in"]
                + usage.output_tokens * pricing["out"]) / 1_000_000
        return CompletionResponse(
            id=raw.id,
            model=raw.model,
            content=[ContentBlock(type=b.type, **b.model_dinternal-monitoring())
                     for b in raw.content],
            stop_reason=raw.stop_reason,
            usage=Usage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0),
                cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0),
            ),
            cost_usd=cost,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
```

### 2.3 OpenAI Provider（回退）

```python
class OpenAIProvider:
    PRICING = {
        "gpt-4o":         {"in": 5.0,  "out": 15.0},
        "gpt-4o-mini":    {"in": 0.15, "out": 0.60},
        "o1":             {"in": 15.0, "out": 60.0},
        "o1-mini":        {"in": 3.0,  "out": 12.0},
    }

    def __init__(self, api_key: str, timeout: int = 60):
        self.client = openai.AsyncOpenAI(api_key=api_key, timeout=timeout)

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        # 转换 messages/tools 格式
        ...
```

### 2.4 MultiLLMClient（主+回退+路由）

```python
class MultiLLMClient:
    def __init__(self, primary: AnthropicProvider,
                 fallback: OpenAIProvider,
                 router: ModelRouter,
                 cache: LLMCache,
                 audit: AuditLogger,
                 cost: CostTracker):
        self.primary = primary
        self.fallback = fallback
        self.router = router
        self.cache = cache
        self.audit = audit
        self.cost = cost

    async def complete(self, req: CompletionRequest) -> CompletionResponse:
        # 1. 路由选择模型
        actual_model = self.router.route(req)
        req.model = actual_model
        # 2. 缓存检查
        if cached := await self.cache.get(req):
            cached.cached = True
            return cached
        # 3. 调主
        try:
            resp = await self.primary.complete(req)
        except (LLMRateLimitError, LLMTimeoutError) as e:
            self.audit.emit("llm_fallback", {
                "primary": self.primary.__class__.__name__,
                "fallback": self.fallback.__class__.__name__,
                "error": str(e),
            })
            resp = await self.fallback.complete(req)
        # 4. 缓存
        await self.cache.put(req, resp)
        # 5. 成本跟踪
        await self.cost.track(req, resp)
        return resp
```

### 2.5 ModelRouter

```python
class ModelRouter:
    """根据任务复杂度路由到不同模型"""

    RULES = [
        # (条件, 模型)
        (lambda r: r.metadata.get("tier") == "high", "claude-opus-4-7"),
        (lambda r: r.metadata.get("tier") == "low", "claude-haiku-4-5"),
        (lambda r: r.metadata.get("tier") == "medium", "claude-sonnet-4-6"),
        # 默认
        (lambda r: True, "claude-sonnet-4-6"),
    ]

    def route(self, req: CompletionRequest) -> str:
        for predicate, model in self.RULES:
            if predicate(req):
                return model
        return "claude-sonnet-4-6"
```

**Tier 决策**（由 Subagent 配置）：
- `high`：架构、CR、复杂决策 → opus
- `medium`：编码、测试、文档 → sonnet
- `low`：分类、提取、模板填充 → haiku

---

## 三、LLM Cache

### 3.1 缓存策略

```python
class LLMCache:
    """基于 fingerprint 的精确匹配缓存"""

    def __init__(self, db_path: Path, ttl_seconds: int = 86400,
                 max_size_mb: int = 500):
        self.db = sqlite3.connect(db_path)
        self.ttl = ttl_seconds
        self.max_size = max_size_mb * 1024 * 1024
        self._init_schema()

    def _init_schema(self):
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS llm_cache (
            fingerprint TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            request_json TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            last_hit_at INTEGER NOT NULL,
            hit_count INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_cache_created ON llm_cache(created_at);
        """)

    async def get(self, req: CompletionRequest) -> CompletionResponse | None:
        fp = self._fingerprint(req)
        row = self.db.execute(
            "SELECT response_json, created_at FROM llm_cache WHERE fingerprint=?",
            (fp,)
        ).fetchone()
        if not row:
            return None
        response_json, created_at = row
        if time.time() - created_at > self.ttl:
            return None  # 过期
        # 命中
        self.db.execute(
            "UPDATE llm_cache SET last_hit_at=?, hit_count=hit_count+1 WHERE fingerprint=?",
            (time.time(), fp)
        )
        return CompletionResponse.model_validate_json(response_json)

    async def put(self, req: CompletionRequest, resp: CompletionResponse) -> None:
        fp = self._fingerprint(req)
        self.db.execute(
            "INSERT OR REPLACE INTO llm_cache (fingerprint, model, request_json, response_json, created_at, last_hit_at) VALUES (?,?,?,?,?,?)",
            (fp, resp.model, req.model_dinternal-monitoring_json(), resp.model_dinternal-monitoring_json(), time.time(), time.time())
        )

    def _fingerprint(self, req: CompletionRequest) -> str:
        # 排除 metadata（每次不同）
        normalized = req.model_dinternal-monitoring(exclude={"metadata"})
        normalized.pop("temperature", None)  # 允许 temperature 变化
        return hashlib.sha256(json.dinternal-monitorings(normalized, sort_keys=True).encode()).hexdigest()
```

### 3.2 缓存命中率优化

- 30%+ 命中（典型 Subagent 工作流）
- 节省 50%+ 成本

### 3.3 失效场景

- 规则变化 → 清空
- KB 内容变化 → 标记 stale，下次 miss 自动重新生成
- TTL 到期 → 重新生成

---

## 四、Cost Tracker

```python
class CostTracker:
    def __init__(self, state: StateStore, audit: AuditLogger):
        self.state = state
        self.audit = audit

    async def track(self, req: CompletionRequest, resp: CompletionResponse) -> None:
        # 1. 写 llm_calls 表
        self.state.record_llm_call(
            pipeline_id=req.metadata.get("pipeline_id"),
            stage_id=req.metadata.get("stage_id"),
            model=resp.model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            cost_usd=resp.cost_usd,
            duration_ms=resp.duration_ms,
            cached=resp.cached,
        )
        # 2. 检查成本上限
        await self._check_budget(req)

    async def _check_budget(self, req):
        pipeline_id = req.metadata.get("pipeline_id")
        max_cost = req.metadata.get("max_cost", 5.0)
        total = self.state.get_pipeline_cost(pipeline_id)
        if total > max_cost:
            self.audit.emit("cost_exceeded", {
                "pipeline_id": pipeline_id,
                "current": total,
                "limit": max_cost,
            })
            raise CostExceededError(f"Pipeline cost ${total:.2f} exceeds ${max_cost:.2f}")
```

---

## 五、Subagent Pool

### 5.1 数据模型

```python
@dataclass
class Subagent:
    id: str  # SA-1 ~ SA-12+
    name: str  # kebab-case
    role: str
    model: str
    tools: list[str]  # 允许的工具名
    kb_inject: list[str]  # 注入 KB 文件
    prompt: str  # 已渲染
    max_iter: int = 10
    system_addon: str = ""

@dataclass
class SubagentTask:
    agent_id: str
    input: str
    context: dict
    artifacts_required: list[str]
    pipeline_id: str
    stage_id: str
    max_iter: int | None = None

@dataclass
class SubagentResult:
    success: bool
    output: str
    artifacts: dict[str, Any]  # artifact_id → content
    tool_calls: list[dict]
    iterations: int
    cost_usd: float
    error: str | None = None
```

### 5.2 Subagent 内循环

```python
class SubagentPool:
    def __init__(self, registry, llm, kb, audit):
        ...

    async def invoke(self, agent_id: str, task: SubagentTask) -> SubagentResult:
        agent = self.registry.get(agent_id)
        messages = self._initial_messages(agent, task)
        total_cost = 0.0
        iterations = 0
        max_iter = task.max_iter or agent.max_iter

        for i in range(max_iter):
            iterations += 1
            # 1. 调 LLM
            req = CompletionRequest(
                model=agent.model,
                messages=messages,
                tools=self._resolve_tools(agent.tools),
                system=agent.system_addon,
                metadata={
                    "pipeline_id": task.pipeline_id,
                    "stage_id": task.stage_id,
                    "agent_id": agent.id,
                    "iter": i,
                },
            )
            resp = await self.llm.complete(req)
            total_cost += resp.cost_usd
            # 2. 处理 tool calls
            tool_calls = [b for b in resp.content if b.type == "tool_use"]
            if not tool_calls:
                # 没有 tool call → 最终回答
                final_text = self._extract_text(resp.content)
                return SubagentResult(
                    success=True,
                    output=final_text,
                    artifacts=self._parse_artifacts(agent, final_text),
                    tool_calls=[],
                    iterations=iterations,
                    cost_usd=total_cost,
                )
            # 3. 执行 tool
            tool_results = []
            for tc in tool_calls:
                result = await self._execute_tool(tc, task, agent)
                tool_results.append(result)
            # 4. 追加到 messages
            messages.append(Message(role="assistant", content=resp.content))
            for tr in tool_results:
                messages.append(Message(
                    role="tool",
                    content=tr.content,
                    tool_call_id=tr.tool_call_id,
                ))

        # 超过 max iter
        return SubagentResult(
            success=False,
            output="",
            artifacts={},
            tool_calls=[],
            iterations=iterations,
            cost_usd=total_cost,
            error=f"Max iter ({max_iter}) exceeded",
        )
```

### 5.3 Tool 执行

```python
async def _execute_tool(self, tool_call, task, agent) -> ToolResult:
    tool_name = tool_call.name
    if tool_name not in agent.tools:
        return ToolResult(
            tool_call_id=tool_call.id,
            content=f"Error: tool '{tool_name}' not allowed for {agent.id}",
        )
    # 调对应 tool
    if tool_name == "read":
        return await self._tool_read(tool_call.input)
    elif tool_name == "write":
        return await self._tool_write(tool_call.input, task)
    elif tool_name == "ask_user":
        return await self._tool_ask_user(tool_call.input, task)
    elif tool_name == "skill":
        return await self._tool_skill(tool_call.input, task)
    elif tool_name == "mcp":
        return await self._tool_mcp(tool_call.input, task)
    # ... 8 种内置 tool
```

### 5.4 11+ Subagent 默认配置

| ID | 名称 | Role | Model | 主要工作 |
|---|---|---|---|---|
| SA-1 | requirements-analyst | requirements | opus | 需求澄清 |
| SA-2 | architect | architect | opus | 架构设计 |
| SA-3 | coder-backend | impl | sonnet | 后端编码 |
| SA-4 | coder-frontend | impl | sonnet | 前端编码 |
| SA-5 | tester-unit | test | sonnet | 单元测试 |
| SA-6 | reviewer | review | opus | CR |
| SA-7 | sre-writer | monitor | sonnet | 监控告警 |
| SA-8 | doc-writer | doc | haiku | 文档 |
| SA-9 | migration-engineer | migration | sonnet | 迁移 |
| SA-10 | security-auditor | audit | opus | 安全审计 |
| SA-11 | devops-engineer | infra | sonnet | CI/Infra |

详见 `11-subagent-and-skills.md` in prd/。

---

## 六、Prompt 渲染

### 6.1 Jinja2 模板

```python
class PromptRenderer:
    def __init__(self, template_dir: Path):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=False,  # prompt 不是 HTML
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # 自定义 filter
        self.env.filters["tojson"] = lambda x: json.dinternal-monitorings(x, indent=2, ensure_ascii=False)
        self.env.filters["relative_time"] = lambda ts: humanize.naturaltime(ts)

    def render(self, template: str, context: dict) -> str:
        tmpl = self.env.from_string(template)
        return tmpl.render(**context)
```

### 6.2 模板示例

```jinja2
# prompts/sa-2-architect.md

# {{ agent.name }}

你是**{{ agent.role }}**，负责架构设计。

## 任务

{{ task.input }}

## 上游 artifacts

{% for art in task.artifacts %}
### {{ art.name }}
```{{ art.type }}
{{ art.content }}
```
{% endfor %}

## 项目知识

{% for name, content in kb.items() %}
### {{ name }}
{{ content }}
{% endfor %}

## 必须遵守的规则

{% for rule in rules %}
- **{{ rule.level }}** {{ rule.id }}: {{ rule.description }}
{% endfor %}

## 输出格式

请输出 JSON 格式：
```json
{
  "architecture": "...",
  "interfaces": [...],
  "components": [...]
}
```
```

---

## 七、Streaming（可选）

```python
async def stream(self, req: CompletionRequest) -> AsyncIterator[str]:
    """流式输出，用于实时显示"""
    if isinstance(self.primary, AnthropicProvider):
        async with self.client.messages.stream(...) as stream:
            async for text in stream.text_stream:
                yield text
```

CLI 用 rich 渲染：
```python
with Live(Text(""), refresh_per_second=10) as live:
    async for chunk in llm.stream(req):
        buffer += chunk
        live.update(Text(buffer))
```

---

## 八、错误与重试

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((LLMRateLimitError, LLMTimeoutError)),
)
async def call_with_retry(self, req):
    return await self.primary.complete(req)
```

**回退决策**：
```python
if isinstance(e, LLMRateLimitError):
    # 切换到 fallback
elif isinstance(e, LLMTimeoutError):
    # 重试 1 次，否则 fallback
elif isinstance(e, LLMContentFilterError):
    # 不重试，不 fallback，直接 fail
elif isinstance(e, LLMAuthError):
    # 终止（配置错误）
```

---

## 九、安全

- API key 走环境变量 / keyring
- 不写日志（即使 debug）
- 响应内容过滤（防注入）
- Tool 调用权限白名单
- 文件路径校验（防止读 `/etc/passwd`）

---

## 十、版本

- v1.0 (2026-06-05): 初版
