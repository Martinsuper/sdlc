# 10. 状态与恢复 (v1.0)

> SQLite 状态机 + 快照 + 12h Resume

---

## 一、整体设计

### 1.1 目标

1. **持久化**：Pipeline 状态可恢复
2. **原子性**：Stage 失败不留半成品
3. **可恢复**：12h 内可 resume
4. **可观测**：每个状态变更可追溯
5. **一致性**：SQLite + meta.json 双向对账

### 1.2 三层持久化

| 层 | 内容 | 格式 | 写入时机 |
|---|---|---|---|
| **L1 in-memory** | Stage 运行时对象 | Python 对象 | 运行时 |
| **L2 SQLite** | 状态/审计摘要/成本 | 表 | 每 stage 完成 |
| **L3 文件** | meta.json + audit.log + artifacts | JSON/JSONL/文件 | 同上 |

---

## 二、StateStore

### 2.1 接口

```python
class StateStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db = sqlite3.connect(
            db_path,
            isolation_level=None,  # autocommit
            check_same_thread=False,
        )
        self.db.row_factory = sqlite3.Row
        self._init_schema()
        self._lock = threading.RLock()

    def _init_schema(self):
        self.db.executescript(SCHEMA_SQL)  # 见 04-data-model §2.2

    # ---- Pipeline ----
    def save_pipeline(self, p: Pipeline) -> None: ...
    def load_pipeline(self, id: str) -> Pipeline: ...
    def update_pipeline_status(self, id: str, updates: dict) -> None: ...
    def list_pipelines(self, status: str | None = None,
                       since: datetime | None = None,
                       limit: int = 100) -> list[PipelineSummary]: ...
    def delete_pipeline(self, id: str) -> None: ...

    # ---- Stage ----
    def save_stage_result(self, r: StageResult) -> None: ...
    def load_stage_result(self, pipeline_id: str,
                           stage_id: str) -> StageResult: ...
    def list_stage_results(self, pipeline_id: str) -> list[StageResult]: ...

    # ---- Artifact ----
    def register_artifact(self, pipeline_id: str, stage_id: str,
                          artifact: Artifact) -> None: ...
    def list_artifacts(self, pipeline_id: str,
                        type: str | None = None) -> list[Artifact]: ...
    def get_artifact(self, id: str) -> Artifact: ...

    # ---- LLM ----
    def record_llm_call(self, pipeline_id: str, stage_id: str,
                        model: str, input_tokens: int, output_tokens: int,
                        cost_usd: float, duration_ms: int,
                        cached: bool) -> None: ...
    def get_pipeline_cost(self, pipeline_id: str) -> float: ...
    def get_cost_daily(self, since: datetime) -> list[CostStat]: ...

    # ---- KB ----
    def record_kb_delta(self, pipeline_id: str, stage_id: str,
                        target: str, operation: str,
                        fingerprint: str) -> int: ...  # 返回 delta_id
    def get_kb_deltas(self, target: str, since: datetime) -> list[KBDelta]: ...
    def get_kb_delta(self, delta_id: int) -> KBDelta: ...

    # ---- Resume ----
    def save_resume_token(self, pipeline_id: str,
                           token: str, expires_at: datetime) -> None: ...
    def verify_resume_token(self, pipeline_id: str,
                             token: str) -> bool: ...
    def get_resume_state(self, pipeline_id: str) -> ResumeState: ...

    # ---- Backup ----
    def backup(self, dest: Path) -> None: ...
    def restore(self, src: Path) -> None: ...
```

### 2.2 事务处理

```python
from contextlib import contextmanager

@contextmanager
def transaction(self):
    """事务上下文：要么全成功要么全回滚"""
    with self._lock:
        try:
            self.db.execute("BEGIN IMMEDIATE")
            yield self.db
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
```

**用法**：
```python
with state.transaction() as tx:
    tx.execute("UPDATE stages SET status=? WHERE id=?", ("SUCCESS", stage_id))
    tx.execute("UPDATE pipelines SET updated_at=? WHERE id=?", (now(), pipeline_id))
    # 自动 COMMIT
```

### 2.3 并发安全

- 单 StateStore 实例 + threading.RLock
- 多 Stage 并行用同一实例（SQLite WAL 模式）
- WAL 启用：`PRAGMA journal_mode=WAL`

```python
def _init_schema(self):
    self.db.execute("PRAGMA journal_mode=WAL")
    self.db.execute("PRAGMA synchronous=NORMAL")
    self.db.execute("PRAGMA foreign_keys=ON")
```

### 2.4 备份策略

```python
def backup(self, dest: Path):
    """在线备份（不阻塞）"""
    with self.db:
        # 用 SQLite 在线备份 API
        backup_db = sqlite3.connect(dest)
        self.db.backup(backup_db)
        backup_db.close()
```

**自动备份**：
- 每次 `sdlc run` 结束 → 增量备份
- 每日 0 点 → 全量备份
- 保留 7 天

---

## 三、Snapshot

### 3.1 Snapshot 内容

每个 stage 完成时生成：

```python
@dataclass
class Snapshot:
    pipeline_id: str
    taken_at: datetime
    stage_id: str  # 刚完成的那 stage
    state: dict    # 完整 StateStore 关键内容
    meta: dict     # meta.json
    fingerprint: str  # sha256

def take_snapshot(state: StateStore, pipeline_id: str) -> Snapshot:
    p = state.load_pipeline(pipeline_id)
    stages = state.list_stage_results(pipeline_id)
    artifacts = state.list_artifacts(pipeline_id)
    return Snapshot(
        pipeline_id=pipeline_id,
        taken_at=now(),
        stage_id=stages[-1].stage_id if stages else None,
        state={
            "pipeline": p.dict(),
            "stages": [s.dict() for s in stages],
            "artifacts": [a.dict() for a in artifacts],
        },
        meta=load_meta(pipeline_id),
        fingerprint=...,
    )
```

### 3.2 存储位置

```
.sdlc/
├── state.db
├── audit.log
├── snapshots/
│   ├── feat-2026-06-05-001/
│   │   ├── stage-s-clarify.snap.json
│   │   ├── stage-s-design.snap.json
│   │   └── ...
```

只存最近 5 个 snapshot，旧的删除。

---

## 四、Resume

### 4.1 Token 设计

```python
import secrets
import jwt

def generate_resume_token(pipeline_id: str) -> str:
    return secrets.token_urlsafe(32)

def verify_resume_token(self, pipeline_id: str, token: str) -> bool:
    """简单 token：存 DB 验证"""
    row = self.db.execute(
        "SELECT token, expires_at FROM resume_tokens WHERE pipeline_id=?",
        (pipeline_id,)
    ).fetchone()
    if not row:
        return False
    if row["token"] != token:
        return False
    if datetime.fromisoformat(row["expires_at"]) < now():
        return False
    return True
```

**有效期**：默认 12h，可配置 `--resume-ttl 24h`。

### 4.2 Resume 流程

```python
async def resume_pipeline(pipeline_id: str, token: str | None,
                          from_stage: str | None = None) -> PipelineResult:
    # 1. 验证 token
    if token is None:
        token = prompt("Enter resume token: ")
    if not state.verify_resume_token(pipeline_id, token):
        raise ResumeExpiredError(pipeline_id)

    # 2. 加载 state
    pipeline = state.load_pipeline(pipeline_id)
    completed = state.list_stage_results(pipeline_id)
    completed_ids = {s.stage_id for s in completed if s.status == "SUCCESS"}

    # 3. 找 next stage
    if from_stage:
        # 用户强制从 from_stage 重跑
        next_stages = [s for s in pipeline.stages if s.id == from_stage]
    else:
        # 自动找第一个未完成 stage
        next_stages = [s for s in pipeline.stages if s.id not in completed_ids]

    # 4. 验证 DAG 一致性
    for s in next_stages:
        for dep in s.depends_on:
            if dep not in completed_ids:
                raise InconsistentStateError(f"dep {dep} not completed")

    # 5. 重建 sub-pipeline（只跑剩余）
    sub_pipeline = Pipeline(
        id=pipeline_id,
        stages=next_stages,
        ...
    )

    # 6. 继续跑
    async for stage_result in stage_runner.run(sub_pipeline):
        yield stage_result
```

### 4.3 边界情况

| 情况 | 处理 |
|---|---|
| Token 过期 | 拒绝 + 提示重新 `sdlc run` |
| Token 不存在 | 拒绝 |
| Pipeline 状态 completed | 拒绝（无 stage 可跑） |
| Pipeline 状态 failed | 允许（从失败 stage 重跑） |
| meta.json 与 SQLite 不一致 | 报警 + 提示人工 |
| KB 在 resume 期间被改 | 提示（KB 指纹会变化，stage 可能需要重跑） |
| 外部文件被改（artifact tampering） | 终止 + 提示 |

---

## 五、Status 状态机

### 5.1 Pipeline 状态

```
            ┌──────┐
            │ NEW  │
            └──┬───┘
               │ start
               ↓
        ┌──────────────┐
   ┌───→│   RUNNING    │←──┐
   │    └──────┬───────┘   │
   │           │ gate       │ gate
   │           ↓            │
   │    ┌──────────────┐    │
   │    │   PAUSED     │────┘ (resume)
   │    └──────┬───────┘
   │           │ end
   │           ↓
   │    ┌──────────────┐
   └───│  COMPLETED   │
        └──────────────┘

        ┌──────────────┐
        │   FAILED     │ (任何 stage 失败)
        └──────────────┘

        ┌──────────────┐
        │  CANCELLED   │ (用户 Ctrl-C)
        └──────────────┘
```

### 5.2 Stage 状态

```
PENDING → RUNNING → SUCCESS
                    ↘ FAILED
                    ↘ SKIPPED
```

### 5.3 状态转换规则

```python
VALID_TRANSITIONS = {
    "PENDING": {"RUNNING", "SKIPPED"},
    "RUNNING": {"SUCCESS", "FAILED"},
    "SUCCESS": set(),  # 终态
    "FAILED": {"PENDING"},  # 允许重试
    "SKIPPED": set(),  # 终态
}

def assert_valid_transition(from_status, to_status):
    if to_status not in VALID_TRANSITIONS[from_status]:
        raise InvalidStateTransitionError(from_status, to_status)
```

---

## 六、并发模型

### 6.1 StageRunner 单实例

```python
class StageRunner:
    def __init__(self, ...):
        self._semaphore = asyncio.Semaphore(3)  # 最多 3 个 LLM 并发

    async def run_stage(self, stage):
        async with self._semaphore:
            return await self._run_stage_unsafe(stage)
```

### 6.2 StateStore 多线程

```python
# CLI 主线程
state = StateStore(db_path)

# 异步事件循环内
async def run():
    # 同实例可跨 stage 共享
    await stage_runner.run(pipeline, state=state)
```

### 6.3 多 Pipeline 并发

**限制**：sdlc 默认一次只跑 1 个 pipeline（MVP）。

**未来**：加调度器 `sdlc queue` 支持多 pipeline 排队。

---

## 七、清理与归档

### 7.1 定期清理

```python
# sdlc config set retention.days 30
def cleanup_old_pipelines(retention_days: int = 30):
    cutoff = now() - timedelta(days=retention_days)
    old = state.list_pipelines(since=None, until=cutoff)
    for p in old:
        if p.status in ("completed", "failed", "cancelled"):
            archive_pipeline(p)
            state.delete_pipeline(p.id)
            # 不删 audit.log（合规需要）
```

### 7.2 归档格式

```
~/.sdlc/archive/
└── 2026/
    └── 06/
        └── feat-2026-06-05-001.tar.gz
            ├── meta.json
            ├── audit.log
            ├── artifacts/
            └── summary.md  # 自动生成的总结
```

---

## 八、监控与告警

### 8.1 内置指标

```python
# 通过 audit.log 分析
sdlc stats --since 7d

# 输出：
# - 平均 stage 耗时
# - 平均 pipeline 成本
# - 失败率
# - 规则违规率
# - KB 更新频次
```

### 8.2 异常检测

```python
# sdlc doctor 时检查
def check_anomalies():
    # - 同一 pipeline 失败 ≥ 3 次
    # - 成本突增 5x
    # - 规则违规激增
    # - KB fingerprint 频繁变化
    ...
```

---

## 九、性能预算

| 操作 | 典型耗时 |
|---|---|
| 启动 + schema 初始化 | < 100ms |
| 单 pipeline.save | < 10ms |
| 单 stage.save | < 5ms |
| Snapshot 写盘 | < 200ms |
| 备份（10MB DB） | < 2s |
| 恢复 | < 5s |
| list_pipelines | < 50ms |

---

## 十、安全考虑

- DB 文件权限 600
- 不存 API key / 密码
- 审计日志不删（合规）
- Token 不写入日志

---

## 十一、版本

- v1.0 (2026-06-05): 初版
