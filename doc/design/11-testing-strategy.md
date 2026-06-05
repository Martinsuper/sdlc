# 11. 测试策略 (v1.0)

> 单元 + 集成 + E2E + 性能 + CI

---

## 一、测试金字塔

```
                  ╱  ╲
                 ╱ E2E ╲           5%   — 慢、贵、关键路径
                ╱───────╲
               ╱  集成测试 ╲        25%  — 跨模块
              ╱─────────────╲
             ╱   单元测试      ╲     70%  — 快、多、准
            ╱───────────────────╲
```

**目标覆盖率**：>= 80%（line + branch）

---

## 二、单元测试

### 2.1 工具

- `pytest` 8.2+
- `pytest-asyncio` 0.23+
- `pytest-cov` 5.0+
- `pytest-mock` 3.14+
- `freezegun`（时间测试）
- `respx`（httpx mock）

### 2.2 命名约定

```python
# tests/unit/test_<module>.py
def test_<func>_<scenario>_<expected>():
    ...

# 例子
def test_stage_runner_with_missing_artifact_raises_validation_error():
    ...
```

### 2.3 关键模块覆盖

| 模块 | 目标覆盖率 | 重点 |
|---|---|---|
| utils/* | 90% | 纯函数，easy |
| kb/scanner | 85% | 文件 I/O + 解析 |
| kb/writer | 90% | 事务、原子写 |
| llm/cache | 85% | 命中、过期、淘汰 |
| llm/router | 95% | 路由规则 |
| subagent/pool | 80% | mock LLM 后测 |
| adapter/detector | 90% | 文件识别 |
| stage/runner | 85% | 8 步生命周期 |
| gate/engine | 90% | 评估逻辑 |
| state/store | 85% | SQLite 事务、并发 |
| audit/logger | 80% | 事件完整性 |

### 2.4 Mock 策略

```python
# Mock LLM（关键）
@pytest.fixture
def mock_llm_client():
    client = AsyncMock()
    client.complete.return_value = CompletionResponse(
        id="resp-1",
        model="claude-sonnet-4-6",
        content=[ContentBlock(type="text", text="mock response")],
        stop_reason="end_turn",
        usage=Usage(input_tokens=100, output_tokens=50),
        cost_usd=0.001,
        duration_ms=500,
    )
    return client

# Mock 文件系统
@pytest.fixture
def fake_filesystem(tmp_path):
    fs = FakeFS()
    fs.create_file("/project/doc/kb/architecture.md", content="...")
    return fs

# Mock 时间
@freeze_time("2026-06-05 10:00:00")
def test_audit_log_includes_correct_timestamp():
    ...
```

### 2.5 异步测试

```python
@pytest.mark.asyncio
async def test_subagent_invoke_with_tool_call():
    agent = Subagent(id="sa-3", tools=["read", "write"], ...)
    task = SubagentTask(agent_id="sa-3", input="...", ...)

    pool = SubagentPool(registry=mock_registry,
                        llm=mock_llm_client,
                        ...)

    # Mock LLM 第一次返回 tool_call，第二次返回 text
    mock_llm.complete.side_effect = [
        CompletionResponse(..., content=[ContentBlock(type="tool_use", name="read", input={...})]),
        CompletionResponse(..., content=[ContentBlock(type="text", text="done")]),
    ]

    result = await pool.invoke("sa-3", task)
    assert result.success
    assert result.iterations == 2
```

---

## 三、集成测试

### 3.1 测试范围

跨模块协作，**不 mock** 内部模块，只 mock 外部：
- LLM API（必须 mock，真实 API 太贵）
- 文件系统（用 tmp_path）
- 真实 SQLite（用内存或 tmp_path）
- 真实 subprocess（仅 CLI 集成时）

### 3.2 典型集成场景

| # | 场景 | 涉及模块 |
|---|---|---|
| I1 | 完整 Stage 跑通 | stage + llm + kb + state + audit |
| I2 | Pipeline 跑完（含 DAG） | stage + pipeline + state + audit |
| I3 | Adapter 检测到 dongboot → 加载 | adapter + registry |
| I4 | KB 扫描 → 写回 | kb/scanner + kb/writer + kb/state |
| I5 | Gate 拒绝 → 阻断后续 stage | gate + stage + pipeline |
| I6 | Resume（从 stage 3 续跑） | state + pipeline + stage |
| I7 | Cost 跟踪正确 | llm + state + audit |
| I8 | Rule 违规抛错 | rule + stage |
| I9 | CLI `sdlc run` 完整跑 | cli + 所有 |
| I10 | CLI `sdlc init` 创建项目 | cli + adapter + profile |

### 3.3 测试夹具

```python
@pytest.fixture
def sample_project(tmp_path):
    """一个带 dongboot + KB 的项目样本"""
    project = tmp_path / "sample-app"
    project.mkdir()
    (project / "pom.xml").write_text(POM_XML_SAMPLE)
    (project / "doc/kb").mkdir(parents=True)
    (project / "doc/kb/architecture.md").write_text("# Arch\n...")
    (project / "doc/kb/standards.md").write_text("## Standards\n...")
    return project

@pytest.fixture
def sdlc_env(tmp_path, monkeypatch):
    """完整 sdlc 运行环境"""
    home = tmp_path / ".sdlc"
    home.mkdir()
    monkeypatch.setenv("SDLC_HOME", str(home))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    # 准备内置 agents / stages / profiles
    ...
    return home

@pytest.fixture
def mock_anthropic(monkeypatch):
    """Mock Anthropic API（不真实调用）"""
    responses = []
    async def mock_complete(req):
        return responses.pop(0) if responses else DEFAULT_RESPONSE
    monkeypatch.setattr("anthropic.AsyncAnthropic.messages.create", mock_complete)
    return responses
```

### 3.4 数据驱动

```python
@pytest.mark.parametrize("stage_id,input,expected_output,expected_cost", [
    ("s-clarify", "做一个待办工具", {"goal": "..."}, 0.01),
    ("s-clarify", "做一个电商网站", {"goal": "...", "modules": [...]}, 0.02),
])
def test_stage_clarify_various_inputs(sdlc_env, sample_project,
                                       stage_id, input, expected_output, expected_cost):
    ...
```

---

## 四、E2E 测试

### 4.1 范围

**慢但真实**：
- 真实 Python 解释器
- 真实 LLM（用 sonnet + cache 命中可接受）
- 真实文件系统
- 真实 SQLite
- 真实 subprocess（不 mock）

### 4.2 E2E 场景

| # | 命令 | 期望 |
|---|---|---|
| E1 | `sdlc init --project demo` | 生成 `.sdlc/` + `meta.json` |
| E2 | `sdlc run --goal "fix typo in README"` | 1 个 stage SUCCESS，~30s |
| E3 | `sdlc run --goal "add user login"` | 4+ stages，~3min |
| E4 | `sdlc resume <id>` | 12h 内 token 可用 |
| E5 | `sdlc run --adapter dongboot` | 检测到 + 加载 |
| E6 | `sdlc run --stage s-design --skip-gate` | 跳过 gate |
| E7 | `sdlc run --mock-llm` | 不调真实 LLM |
| E8 | `sdlc doctor` | 无错误 |
| E9 | `sdlc stats` | 输出统计 |
| E10 | `sdlc replay <id>` | 重新跑 |

### 4.3 运行频率

- **PR check**：跑核心 E2E（E1、E2、E3），最长 5min
- **Nightly**：跑全部 E2E，最长 30min
- **Release**：全跑 + 性能

### 4.4 失败容忍

- LLM 行为非确定性 → assert 关键字段，不全等
- 时间敏感 → 用 `freezegun`
- 路径敏感 → 全用 `tmp_path`

---

## 五、性能测试

### 5.1 工具

- `pytest-benchmark`
- `asv`（airspeed velocity，跨版本对比）
- `locust`（CLI 压测，可选）

### 5.2 性能基准

```python
def test_pipeline_startup_bench(benchmark, sdlc_env):
    """启动 < 1s"""
    def setup():
        ...
    result = benchmark(sdlc.run_pipeline, "feat-2026-06-05-001")
    assert benchmark.stats.stats.mean < 1.0  # < 1s

def test_state_save_bench(benchmark, state):
    """save < 10ms"""
    p = make_pipeline(stages=10)
    benchmark(state.save_pipeline, p)
    assert benchmark.stats.stats.mean < 0.01

def test_kb_scan_100_files_bench(benchmark, sample_kb):
    """100 文件 < 1s"""
    benchmark(kb.scanner.scan, sample_kb)
    assert benchmark.stats.stats.mean < 1.0

def test_llm_cache_hit_bench(benchmark, cache):
    """cache hit < 1ms"""
    req = ...
    cache.put(req, ...)
    benchmark(cache.get, req)
    assert benchmark.stats.stats.mean < 0.001
```

### 5.3 性能预算

| 操作 | 目标 | 警告 | 失败 |
|---|---|---|---|
| CLI 启动 | < 200ms | 500ms | 1s |
| Pipeline 启动（含 init） | < 1s | 3s | 5s |
| Stage 调度 | < 100ms | 500ms | 1s |
| KB 扫描 100 文件 | < 1s | 3s | 5s |
| KB 写入 1 行 | < 50ms | 200ms | 500ms |
| StateStore save | < 10ms | 50ms | 100ms |
| LLM Cache hit | < 1ms | 5ms | 10ms |
| Snapshot 写盘 | < 200ms | 500ms | 1s |
| Backup 10MB DB | < 2s | 5s | 10s |
| 内存占用（idle） | < 50MB | 100MB | 200MB |
| 内存占用（跑 pipeline） | < 200MB | 500MB | 1GB |

### 5.4 回归保护

- CI 跑 bench
- 性能退化 > 20% → 警告
- 退化 > 50% → 失败

---

## 六、Contract 测试

### 6.1 LLM Provider 契约

```python
# 所有 LLM provider 实现必须通过
class TestLLMProviderContract:
    @pytest.mark.asyncio
    async def test_complete_returns_valid_response(self, provider):
        req = CompletionRequest(model=..., messages=[Message(role="user", content="hi")])
        resp = await provider.complete(req)
        assert isinstance(resp, CompletionResponse)
        assert resp.id
        assert resp.model
        assert resp.usage.input_tokens > 0

    @pytest.mark.asyncio
    async def test_rate_limit_raises_specific_error(self, provider, mock_429):
        ...

    @pytest.mark.asyncio
    async def test_invalid_api_key_raises_auth_error(self, provider):
        ...
```

### 6.2 Adapter 契约

```python
# 所有 Adapter 实现必须通过
class TestAdapterContract:
    def test_detect_returns_metadata(self, adapter, tmp_project):
        result = adapter.detect(tmp_project)
        assert "name" in result
        assert "version" in result

    def test_get_kb_paths_returns_list(self, adapter, tmp_project):
        paths = adapter.get_kb_paths(tmp_project)
        assert isinstance(paths, list)

    def test_get_profile_returns_dict(self, adapter, tmp_project):
        profile = adapter.get_profile(tmp_project)
        assert "stages" in profile
```

### 6.3 Gate 契约

```python
class TestGateContract:
    async def test_evaluate_returns_decision(self, gate, context):
        decision = await gate.evaluate(context)
        assert decision in {Decision.PASS, Decision.WARN, Decision.BLOCK}

    async def test_block_includes_reason(self, gate, bad_context):
        decision = await gate.evaluate(bad_context)
        if decision == Decision.BLOCK:
            assert "reason" in decision.metadata
```

---

## 七、Property-Based Testing

```python
from hypothesis import given, strategies as st

# 元数据往返不变
@given(
    pipeline_id=st.text(min_size=1, max_size=100),
    stages=st.lists(st.sampled_from(STAGE_IDS), min_size=1, max_size=10),
)
def test_meta_json_roundtrip(pipeline_id, stages):
    meta = Meta(
        pipeline_id=pipeline_id,
        stages=stages,
        ...
    )
    json_str = meta.to_json()
    restored = Meta.from_json(json_str)
    assert restored == meta

# KB 写入幂等
@given(
    file_path=st.text(min_size=1, max_size=200),
    content=st.text(min_size=0, max_size=10_000),
)
def test_kb_write_idempotent(file_path, content, tmp_path):
    kb = KnowledgeBase(tmp_path)
    kb.write(file_path, content, mode="append")
    fingerprint1 = kb.fingerprint(file_path)
    kb.write(file_path, content, mode="append")
    fingerprint2 = kb.fingerprint(file_path)
    # append mode 下内容追加，fingerprint 应该变
    assert fingerprint1 != fingerprint2
```

---

## 八、Snapshot 测试

```python
from syrupy import snapshot

def test_audit_log_event_serialization(snapshot, sample_event):
    """audit event JSON 格式稳定"""
    event = AuditEvent(
        ts=datetime(2026, 6, 5, 10, 0, 0),
        pipeline_id="feat-2026-06-05-001",
        event_type="stage_completed",
        data={"stage_id": "s-clarify", "duration_ms": 4500, ...},
    )
    assert event.to_json() == snapshot
```

snapshot 文件存 `tests/snapshots/`，首次跑生成 baseline。

---

## 九、CI 流水线

### 9.1 GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v1
      - run: ruff check .
      - run: ruff format --check .
      - uses: mypy-action@v1
        with:
          args: --strict sdlc/

  unit:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install uv && uv sync --all-extras
      - run: uv run pytest tests/unit -v --cov=sdlc --cov-report=xml
      - uses: codecov/codecov-action@v4

  integration:
    needs: unit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install uv && uv sync --all-extras
      - run: uv run pytest tests/integration -v
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

  e2e-core:
    needs: integration
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12', '3.13']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: ${{ matrix.python-version }}}
      - run: pip install uv && uv sync
      - run: uv run pytest tests/e2e -v -m "not slow"
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### 9.2 必需检查

- ✅ Lint（ruff）
- ✅ Type（mypy strict）
- ✅ Unit（>= 80% 覆盖）
- ✅ Integration
- ✅ E2E core
- ⏳ E2E full（nightly）
- ⏳ Bench（nightly）

### 9.3 Merge 门禁

所有 required check 必须通过 + 至少 1 个 reviewer + 无 unresolved comments。

---

## 十、测试组织

```
tests/
├── conftest.py              # 全局 fixture
├── fixtures/                # 共享数据
│   ├── pom_xml_sample.xml
│   ├── kb/
│   └── profiles/
├── unit/
│   ├── test_kb_scanner.py
│   ├── test_kb_writer.py
│   ├── test_llm_cache.py
│   ├── test_llm_router.py
│   ├── test_subagent_pool.py
│   ├── test_adapter_detector.py
│   ├── test_stage_runner.py
│   ├── test_gate_engine.py
│   ├── test_state_store.py
│   └── test_audit_logger.py
├── integration/
│   ├── test_stage_e2e.py        # I1
│   ├── test_pipeline_e2e.py     # I2
│   ├── test_adapter_e2e.py      # I3
│   ├── test_kb_e2e.py           # I4
│   ├── test_gate_e2e.py         # I5
│   ├── test_resume_e2e.py       # I6
│   ├── test_cost_tracking.py    # I7
│   ├── test_rule_e2e.py         # I8
│   └── test_cli_e2e.py          # I9, I10
├── e2e/
│   ├── conftest.py
│   ├── test_init.py
│   ├── test_run_simple.py
│   ├── test_run_complex.py
│   ├── test_resume.py
│   ├── test_adapter_dongboot.py
│   ├── test_doctor.py
│   ├── test_stats.py
│   └── test_replay.py
├── perf/
│   ├── test_bench_startup.py
│   ├── test_bench_kb.py
│   └── test_bench_state.py
├── contract/
│   ├── test_llm_provider.py
│   ├── test_adapter.py
│   └── test_gate.py
├── property/
│   ├── test_meta_roundtrip.py
│   └── test_kb_idempotent.py
└── snapshots/
    ├── test_audit_log_event_serialization.ambr
    └── ...
```

---

## 十一、CI 性能预算

| 阶段 | 目标 | 警告 |
|---|---|---|
| Lint | < 30s | 1min |
| Type check | < 1min | 3min |
| Unit | < 2min | 5min |
| Integration | < 5min | 10min |
| E2E core | < 10min | 20min |
| Total PR | < 20min | 30min |

---

## 十二、覆盖率

### 12.1 工具

`coverage.py` + `codecov.io`

### 12.2 报告

```bash
# 本地
uv run pytest --cov=sdlc --cov-report=html --cov-report=term
# HTML 写到 htmlcov/

# 阈值
--cov-fail-under=80
```

### 12.3 例外

```python
# 允许不覆盖
def rarely_called_legacy_function():  # pragma: no cover
    ...
```

### 12.4 趋势监控

- codecov.io 自动跟踪
- 降 > 2% → 警告
- 降 > 5% → 阻断 merge

---

## 十三、Mutation Testing（可选）

```bash
# mutmut
uv run mutmut run --paths-to-mutate=sdlc/
uv run mutmut report

# 目标 mutation score >= 70%
```

---

## 十四、版本

- v1.0 (2026-06-05): 初版
