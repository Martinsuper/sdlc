# 08. KB 引擎 (v1.0)

> `sdlc init` 扫描 + KB 写入 + 规则强制 + 豁免管理

---

## 一、KB 整体架构

```
sdlc init ─→ Scanner ─┐
                     ├─→ KnowledgeBase (读/写)
Pipeline run ─→ StageRunner ─→ KBWriter (diff-only) ─┘
                                      ↓
                                RuleEnforcer (注入+校验)
                                      ↓
                              ExceptionManager (豁免)
                                      ↓
                                Reconciler (定期)
```

**KB 文件分布**：
- 项目级 L2：`<project>/doc/kb/`
- 全局级 L3：`~/.sdlc/kb/`

---

## 二、Scanner（sdlc init）

### 2.1 七阶段扫描

```
Stage 1: 基础扫描
  - 文件树（git ls-files）
  - 关键 manifest（package.json / pom.xml / go.mod / Cargo.toml / pyproject.toml / ...）
  - CI 配置（.github/workflows/、.gitlab-ci.yml、.circleci/）
  - 容器化（Dockerfile、docker-compose.yml、k8s/）

Stage 2: 技术栈检测
  - 语言/版本
  - 框架/库
  - 构建工具
  - 运行时

Stage 3: 组件提取
  - 依赖图
  - 入口点（main/app/cmd/）
  - 关键模块

Stage 4: 规范反推
  - Lint 配置（.eslintrc、.pylintrc、checkstyle.xml、.rubocop.yml）
  - 格式化（.prettierrc、.editorconfig）
  - Git hooks（.husky/、.git/hooks/）
  - Code style（CONTRIBUTING.md、.editorconfig）

Stage 5: 知识导入
  - 已有 doc/、docs/、README.md
  - ADR（Architecture Decision Records）
  - CHANGELOG / RELEASE NOTES
  - 已有 KB（如果有，merge）

Stage 6: AI 深度分析
  - 调 LLM 总结：
    - 项目领域（订单/支付/搜索/...）
    - 业务核心
    - 已知技术债
    - 建议规则
    - 反模式

Stage 7: 写入
  - 生成 11 个主文件
  - 生成 3 个子目录骨架
  - 生成 CLAUDE.md / AGENTS.md
  - 等待人工 review
```

### 2.2 Scanner 实现

```python
class Scanner:
    def __init__(self, root: Path, llm: LLMClient, config: Config):
        self.root = root
        self.llm = llm
        self.config = config

    def scan(self, depth: int = 5, no_llm: bool = False) -> ScanResult:
        context = ScanContext(root=self.root)
        # Stage 1-5: 静态扫描
        self._stage1_basic(context, depth)
        self._stage2_techstack(context)
        self._stage3_components(context)
        self._stage4_standards(context)
        self._stage5_import_existing(context)
        # Stage 6: LLM 增强
        if not no_llm:
            self._stage6_ai_analysis(context)
        # Stage 7: 写入
        return self._stage7_write(context)

    def _stage1_basic(self, ctx, depth):
        ctx.file_tree = git_ls_files(self.root, depth)
        ctx.manifests = self._parse_manifests()
        ctx.ci = self._parse_ci()
        ctx.containers = self._parse_containers()

    def _stage2_techstack(self, ctx):
        ctx.languages = self._detect_languages()
        ctx.frameworks = self._detect_frameworks()
        ctx.build_tools = self._detect_build_tools()

    # ... 其他 stages

    def _stage6_ai_analysis(self, ctx):
        prompt = render(self.config.prompts["kb_analyze"], ctx=ctx)
        analysis = self.llm.complete(prompt)
        ctx.ai_summary = parse_analysis(analysis)
        # AI 提取：项目领域、业务核心、规则建议
```

### 2.3 输出

```python
@dataclass
class ScanResult:
    context: ScanContext
    kb_files: dict[str, str]  # 11 主文件 + 3 子目录
    recommendations: list[Recommendation]  # 推荐 Adapter/Profile
    warnings: list[str]  # 需要人工确认
    confidence: float  # 0-1
    next_steps: list[str]
```

---

## 三、KnowledgeBase 读写

### 3.1 数据类

```python
class KBLayer(BaseModel):
    name: str  # architecture/component-catalog.md
    type: Literal["markdown", "yaml", "json"]
    path: Path
    schema: type[BaseModel] | None = None
    fingerprint: str  # sha256
    last_modified: datetime
    size_bytes: int

class KnowledgeBase:
    def __init__(self, root: Path, scope: Literal["project", "global"]):
        self.root = root
        self.scope = scope
        self.layers: dict[str, KBLayer] = {}
        self._load()

    def _load(self):
        """加载所有 KB 文件到 layers"""
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            layer_name = str(path.relative_to(self.root))
            self.layers[layer_name] = KBLayer(
                name=layer_name,
                type=self._detect_type(path),
                path=path,
                schema=self._schema_for(layer_name),
                fingerprint=file_fingerprint(path),
                last_modified=datetime.fromtimestamp(path.stat().st_mtime),
                size_bytes=path.stat().st_size,
            )

    def get(self, name: str) -> KBLayer:
        if name not in self.layers:
            raise KBFileNotFoundError(name)
        return self.layers[name]

    def list(self, pattern: str = "**/*") -> list[KBLayer]: ...
    def exists(self, name: str) -> bool: ...
    def for_role(self, role: str) -> dict[str, Any]:
        """按 role 返回 KB 内容（用于 Subagent 注入）"""
        ...
```

### 3.2 读取优化

```python
class KBReadCache:
    """内存 LRU 缓存，避免重复读文件"""
    def __init__(self, max_size_mb: int = 50):
        self.cache = LRUCache(max_size_bytes=max_size_mb * 1024 * 1024)

    def get(self, path: Path) -> str:
        mtime = path.stat().st_mtime
        if path in self.cache and self.cache[path].mtime == mtime:
            return self.cache[path].content
        content = path.read_text()
        self.cache[path] = CachedContent(content=content, mtime=mtime)
        return content
```

---

## 四、Writer（自动更新）

### 4.1 写入策略

**diff-only 模式**（默认）：
```python
def append(target: KBLayer, content: str) -> KBDelta:
    # 1. 读现有
    existing = target.read()
    # 2. 计算 delta
    delta = compute_diff(existing, content)
    # 3. 检查重复
    if fingerprint(delta) in target.known_fingerprints:
        return KBDelta(skipped=True, reason="duplicate")
    # 4. 追加（不覆盖原有）
    target.write(existing + "\n" + content)
    # 5. 更新 fingerprint
    target.known_fingerprints.add(fingerprint(delta))
    return KBDelta(skipped=False, delta_hash=...)
```

**append-mode 模式**（Markdown）：
- 在文件末尾追加 `## <stage_id> (<ts>)\n<content>\n`
- 不破坏原结构
- 每个 delta 有指纹

**update-mode 模式**（YAML 规则）：
- 用 ruamel.yaml 改字段
- 保持注释/顺序
- 触发 fingerprint 更新

### 4.2 写入流程

```python
class KBWriter:
    def __init__(self, kb: KnowledgeBase, audit: AuditLogger, state: StateStore):
        self.kb = kb
        self.audit = audit
        self.state = state
        self._queue: asyncio.Queue[KBDelta] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def update_after_stage(self, stage_id: str,
                                  artifacts: list[Artifact]) -> list[KBDelta]:
        """按 stage→KB 映射表写入"""
        stage_def = self.stage_catalog.get(stage_id)
        deltas = []
        for upd in (stage_def.post_kb_update or []):
            delta_content = self._render_template(upd, stage_id, artifacts)
            delta = await self._enqueue_write(upd.target, delta_content)
            deltas.append(delta)
        return deltas

    async def _enqueue_write(self, target: str, content: str) -> KBDelta:
        delta = KBDelta(
            target=target,
            content=content,
            fingerprint=fingerprint(content),
            ts=now(),
        )
        await self._queue.put(delta)
        return delta

    async def start(self):
        """启动 batch 写入协程"""
        self._task = asyncio.create_task(self._batch_writer())

    async def _batch_writer(self):
        """每 30s 批量落盘"""
        while True:
            await asyncio.sleep(30)
            batch = []
            while not self._queue.empty():
                batch.append(self._queue.get_nowait())
            if batch:
                await self._flush(batch)

    async def _flush(self, batch: list[KBDelta]):
        for delta in batch:
            try:
                self._write_one(delta)
                self.audit.emit("kb_updated", delta.dict())
                self.state.record_kb_delta(delta)
            except KBWriteConflictError as e:
                self.audit.emit("kb_write_conflict", {...})
                # 24h 内可回滚
                raise
```

### 4.3 回滚

```python
class KBRollback:
    def __init__(self, state: StateStore):
        self.state = state

    def rollback(self, delta_id: int) -> bool:
        """回滚单个 delta"""
        delta = self.state.get_kb_delta(delta_id)
        if (now() - delta.ts).hours > 24:
            raise RollbackExpiredError()
        # 重新构造 file 状态
        target = delta.target
        # 找到此 delta 之前的所有 deltas
        prior = self.state.get_kb_deltas_before(target, delta.ts)
        # 重写
        ...
```

---

## 五、RuleEnforcer（规则强制）

### 5.1 4 种 Enforcer

```python
class Enforcer(Protocol):
    def check(self, rule: Rule, context: dict) -> list[Violation]: ...

class CREnforcer:
    """在 code review 阶段检查"""
    def check(self, rule, context) -> list[Violation]:
        # 检查代码/文档是否违反规则
        # context: {files, diff, pr_meta}
        violations = []
        for f in context.get("files", []):
            if not self._check_file(f, rule):
                violations.append(Violation(
                    rule_id=rule.id,
                    file=f.path,
                    line=f.line,
                    message=rule.message,
                    severity="error" if rule.action == "block" else "warning",
                ))
        return violations

class LintEnforcer:
    """调 lint 工具"""
    def check(self, rule, context) -> list[Violation]:
        tool = rule.config.get("tool", "ruff")
        result = run_lint(tool, context["files"])
        return parse_lint_output(result, rule)

class CIEnforcer:
    """触发 CI workflow"""
    async def check(self, rule, context) -> list[Violation]:
        result = await trigger_ci(context["pipeline_id"], rule.config["workflow"])
        return parse_ci_result(result, rule)

class RuntimeEnforcer:
    """在 stage 前后注入 pre/post hook"""
    async def pre(self, rule, context) -> None:
        # 跑检查脚本
        ...
    async def post(self, rule, context) -> list[Violation]:
        ...
```

### 5.2 注入流程

```python
class RuleInjector:
    def __init__(self, rule_engine: RuleEngine, kb: KnowledgeBase):
        ...

    def inject_to_subagent(self, stage_id: str, subagent: Subagent,
                            task: SubagentTask) -> SubagentTask:
        rules = self.rule_engine.for_stage(stage_id)
        # 1. System prompt 注入 MUST
        must_rules = [r for r in rules if r.level == "MUST"]
        if must_rules:
            addon = "\n".join(f"MUST: {r.description}" for r in must_rules)
            task.context["system_addon"] = addon
        # 2. Context 注入全量
        task.context["rules"] = [r.dict() for r in rules]
        # 3. 任务 context 注入
        return task
```

### 5.3 执行检查

```python
class RuleChecker:
    def __init__(self, enforcers: dict[str, Enforcer]):
        self.enforcers = enforcers

    def check(self, stage_id: str, context: dict) -> list[Violation]:
        rules = self.rule_engine.for_stage(stage_id)
        all_violations = []
        for rule in rules:
            enforcer = self.enforcers[rule.enforcer]
            violations = enforcer.check(rule, context)
            all_violations.extend(violations)
        return all_violations
```

---

## 六、ExceptionManager（豁免管理）

### 6.1 数据模型

```python
@dataclass
class Exception:
    id: str
    rule_id: str
    reason: str
    granted_by: str  # 授权人
    granted_at: datetime
    expires_at: datetime
    scope: dict  # {files, stages, ...}
    auto_renew: bool = False
```

### 6.2 操作

```python
class ExceptionManager:
    def __init__(self, kb: KnowledgeBase, audit: AuditLogger):
        self.kb = kb
        self.audit = audit

    def add(self, exception: Exception) -> None:
        path = self.kb.root / "rules/exceptions/active.yaml"
        exceptions = self._load_active()
        exceptions.append(exception)
        save_yaml(path, exceptions)
        self.audit.emit("rule_exception_added", exception.dict())

    def is_active(self, rule_id: str, context: dict) -> Exception | None:
        """检查某 rule 在某 context 下是否有有效豁免"""
        for exc in self._load_active():
            if exc.rule_id != rule_id:
                continue
            if exc.expires_at < now():
                continue
            if not self._scope_matches(exc.scope, context):
                continue
            return exc
        return None

    def expire_check(self) -> list[Exception]:
        """返回已过期的豁免（用于告警）"""
        return [e for e in self._load_active() if e.expires_at < now()]
```

### 6.3 过期告警

```python
# 在 reconciler 中
def check_expiring_exceptions():
    manager = ExceptionManager(...)
    expiring = [e for e in manager._load_active()
                if e.expires_at - now() < timedelta(days=3)]
    if expiring:
        send_alert("rule_exception_expiring", expiring)
```

---

## 七、Reconciler（定期对账）

### 7.1 任务

每周跑一次（或手动 `sdlc kb reconcile`）：

```python
class Reconciler:
    async def run(self):
        # 1. 重复 delta 去重
        await self._deduplicate_deltas()
        # 2. 过期豁免清理/告警
        await self._handle_expiring_exceptions()
        # 3. KB 健康度检查
        await self._check_kb_health()
        # 4. 自动提取建议规则
        await self._suggest_rules()
        # 5. 写入审计
        self.audit.emit("kb_reconciled", {...})

    async def _suggest_rules(self):
        """从 lessons-learned.md 提取模式"""
        # 读 lessons-learned.md
        # LLM 提取："这个是不是个通用规则？"
        # 候选规则 → 标 auto_generated → 7 天人工确认
```

### 7.2 auto_generated 规则

```yaml
- id: suggested-avoid-tx-in-loop
  level: SHOULD
  category: db
  description: |
    检测到 3 次以上"循环中开事务"反模式。
  enforcer: cr
  auto_generated: true
  generated_from: lessons-learned.md#2026-05-12
  generated_at: 2026-05-15
  confirm_deadline: 2026-05-22
  confirmed_by: null
```

---

## 八、关键不变量

1. **不覆盖人工**：`doc/kb/conventions.md` 永远人工编辑，机器不写
2. **diff-only**：只追加，不修改原文
3. **幂等**：相同 stage 输出写两次结果相同
4. **可回滚**：24h 内可回滚任何 delta
5. **审计完整**：每次写都有 event
6. **fingerprint 去重**：相同内容不重复写
7. **隔离写入**：批量 + 异步，不阻塞 stage

---

## 九、性能预算

| 操作 | 典型耗时 |
|---|---|
| KB 单文件读 | < 10ms |
| KB 11 文件全读 | < 100ms |
| 单 delta 写入 | < 50ms |
| 30s batch flush | < 200ms（合并 IO） |
| 规则检查（100 文件） | 1-5s |
| 每周 reconcile | 30-60s |

---

## 十、错误处理

| 错误 | 行为 |
|---|---|
| KB 文件不存在 | 自动 bootstrap 骨架（警告） |
| KB 文件 lock | 重试 3 次 |
| 写入冲突 | 终止 + 人工 |
| Fingerprint 冲突 | 跳过 + 审计 |
| Schema 验证失败 | 终止 + 提示 |
| 24h rollback 过期 | 拒绝回滚 |

---

## 十一、版本

- v1.0 (2026-06-05): 初版
