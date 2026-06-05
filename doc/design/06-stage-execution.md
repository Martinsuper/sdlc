# 06. Stage 执行流程 (v1.0)

> Stage 生命周期 8 步 + 错误处理 + Gate 集成 + KB 联动

---

## 一、Stage 8 步生命周期

```
┌────────────────────────────────────────────────────────┐
│  1. 加载 + 准备                                       │
│  2. 加载 KB（pre_kb_load）                            │
│  3. 校验前置 artifacts                                 │
│  4. 注入规则（rule_inject）                            │
│  5. 调用 Subagent / 直接执行                           │
│  6. 解析结果 / 产出 artifacts                          │
│  7. 持久化（state + audit + meta）                     │
│  8. 写 KB（post_kb_update）                            │
└────────────────────────────────────────────────────────┘
         ↓
     触发 Gate 评估
         ↓
  PASS → 下一 stage
  REVIEW → 暂停 + 通知
  BLOCK → 终止 pipeline
```

---

## 二、每步详细

### 2.1 Step 1: 加载 + 准备

**动作**：
- 从 `StageCatalog` 取 `StageDef`
- 解析变量（`${PIPELINE_ID}`, `${STAGE_ID}` 等）
- 检查超时配置
- 准备隔离工作目录 `<pipeline-dir>/stages/<stage-id>/`
- 初始化 stage 级 logger

**异常**：
- Stage 不存在 → StageExecutionError
- 超时配置错误 → ConfigError

**审计**：
- `stage_prepare` event

### 2.2 Step 2: 加载 KB（pre_kb_load）

**动作**：
```python
# 从 StageDef.pre_kb_load 列出
files_to_load = stage_def.pre_kb_load
# 从 KnowledgeBase 读取
kb_context = {}
for f in files_to_load:
    content = kb.get(f).read()
    kb_context[f] = content
# 注入到 Subagent context
subagent_task.context["kb"] = kb_context
```

**如果 KB 文件不存在**：
- 启动 `KBWriter.bootstrap_if_missing` 自动生成骨架
- 或跳过（标记 `kb_missing` warning）
- 严重缺失（如 conventions.md）→ 终止 + 提示 `sdlc init`

**审计**：
- `kb_loaded` event（含指纹）
- 性能：记录 load 耗时

### 2.3 Step 3: 校验前置 artifacts

**动作**：
```python
# 从 StageDef.required_artifacts 列出
required = stage_def.required_artifacts
# 校验上游 artifacts 已生成
for art in required:
    artifact = artifact_store.get(art)
    if not artifact:
        raise MissingArtifactError(art)
    # 校验指纹（防止被外部修改）
    if artifact.content_hash != expected_hash:
        raise ArtifactTamperedError(art)
```

**异常**：
- MissingArtifactError → 终止
- ArtifactTamperedError → 终止 + 告警

**审计**：
- `artifact_verified` event

### 2.4 Step 4: 注入规则（rule_inject）

**动作**：
```python
# 从 RuleEngine 取出适用于本 stage 的规则
rules = rule_engine.for_stage(stage_id)
# 注入到 Subagent context
subagent_task.context["rules"] = [
    {
        "id": r.id,
        "level": r.level,
        "description": r.description,
        "must_follow": r.level == "MUST",
    }
    for r in rules
]
# MUST 规则额外加入 system prompt
system_addon = "\n".join(
    f"MUST: {r.description}" for r in rules if r.level == "MUST"
)
subagent_task.context["system_addon"] = system_addon
```

**如果规则有 enforcer**：
- `cr` enforcer：生成 CR checklist
- `lint` enforcer：跑 lint（阻塞型 → 跑完才进 step 5）
- `ci` enforcer：触发 CI workflow
- `runtime` enforcer：注入 pre-action hook

**审计**：
- `rules_injected` event

### 2.5 Step 5: 调用 Subagent / 直接执行

**动作（带 Subagent）**：
```python
# 从 SubagentPool 获取 Subagent
subagent = subagent_pool.get(stage_def.subagent)
# 构造 task
task = SubagentTask(
    agent_id=stage_def.subagent,
    input=stage_input,  # 含上游 artifacts
    context=subagent_task.context,  # 含 kb + rules
    artifacts_required=stage_def.produces_artifacts,
    max_iter=stage_def.max_iter or subagent.max_iter,
)
# 调用（可能多轮，max_iter 控制）
result = await subagent_pool.invoke(subagent.id, task)
# 解析 result
parsed = parse_subagent_output(result, stage_def.produces_artifacts)
```

**直接执行（无 Subagent）**：
- 适用于纯工具 stage（如 s-package 调 `mvn package`）
- `ShellRunner.run(...)` 或 `MCPClient.call(...)`

**子流程（Subagent 内部）**：
1. 构造 prompt（user input + system + context）
2. 调 LLM（首轮）
3. 解析 tool calls
4. 执行 tool
5. 收集 tool results
6. 调 LLM（次轮）
7. ... 循环到 max_iter 或 final answer

**异常**：
- LLMError → 重试 3 次（tenacity 指数退避）→ fallback
- SubagentTimeout → 终止
- MaxIterExceeded → 强制总结

**审计**：
- `subagent_invoked` event
- `llm_called` event（每个 LLM 调用）
- `mcp_called` / `skill_used` event
- `tool_executed` event

### 2.6 Step 6: 解析结果 / 产出 artifacts

**动作**：
```python
# Subagent 输出的 raw response → 解析为结构化 artifacts
for art_def in stage_def.produces_artifacts:
    if art_def.type == "code":
        # 写代码文件到 work_dir
        path = work_dir / art_def.path
        path.write_text(parsed[art_def.id])
        artifact = Artifact(
            type="code",
            path=path,
            content_hash=hash(path),
            ...
        )
    elif art_def.type == "doc":
        # 写 markdown
        ...
    elif art_def.type == "test":
        # 写测试代码
        ...
    # 注册到 ArtifactStore
    artifact_store.register(artifact)
```

**校验**：
- 文件存在
- 大小 > 0
- 格式正确（按 type 走 schema）
- 关键字段非空

**异常**：
- ParseError → 重试 Subagent（不消耗 1 次 retry）

**审计**：
- `artifact_created` event（每个 artifact）

### 2.7 Step 7: 持久化

**动作（事务）**：
```python
# SQLite 事务
with state.db.begin():
    state.save_stage_result(StageResult(
        stage_id=stage_id,
        status="SUCCESS",
        artifacts=[a.id for a in new_artifacts],
        started_at=started_at,
        finished_at=now(),
        cost=total_cost,
    ))
    # 更新 pipeline 状态
    state.update_pipeline_status(pipeline_id, {
        "current_stage": next_stage_id,
        "completed_stages": append(completed, stage_id),
        "updated_at": now(),
    })
    # meta.json 同步
    meta = load_meta(pipeline_id)
    meta["state"]["current_stage"] = next_stage_id
    meta["state"]["completed_stages"].append(stage_id)
    meta["cost"] = aggregate_cost()
    meta["updated_at"] = now()
    save_meta(meta)
# 审计
audit.emit("stage_end", {...})
audit.emit("pipeline_progress", {...})
```

**校验（对账）**：
- 事务成功后跑一致性检查
- SQLite.count = meta.json.length
- 任一不一致 → 报警 + 终止后续 stage

**审计**：
- `stage_end` event
- `state_consistent` event（成功）/ `state_inconsistent` event（失败）

### 2.8 Step 8: 写 KB（post_kb_update）

**动作**：
```python
# 从 StageDef.post_kb_update 取出映射
updates = stage_def.post_kb_update or []
for upd in updates:
    # 1. 构造 delta
    delta_content = render_template(
        upd.template,
        stage_id=stage_id,
        ts=now(),
        artifacts=new_artifacts,
    )
    # 2. 计算 fingerprint
    fp = fingerprint(delta_content)
    # 3. 检查去重
    if kb_dedup_check(target=upd.target, fp=fp):
        audit.emit("kb_dedup_skip", {...})
        continue
    # 4. diff-only 写入
    target_layer = kb.get(upd.target)
    target_layer.append(delta_content)
    # 5. 记录 delta
    state.record_kb_delta(
        pipeline_id, stage_id, upd.target, "append", fp
    )
    audit.emit("kb_updated", {
        "target": upd.target,
        "delta_hash": fp,
        "size": len(delta_content),
    })
```

**异步批处理**：
- 所有 KB 写入进入队列
- 30s 内 batch 落盘
- 失败时 24h 可回滚

**审计**：
- `kb_updated` event
- `kb_dedup_skip` event（重复）

---

## 三、Gate 集成

Stage 完成后立即触发：

```python
# StageRunner 内部
stage_result = await run_stage_8_steps(stage_def, pipeline, ctx)

# 触发 Gate
gate_decision = gate_engine.evaluate(stage_result, pipeline, context)

# 处理决策
if gate_decision.action == GateAction.AUTO_PASS:
    audit.emit("gate_passed", {...})
    continue_next_stage()
elif gate_decision.action == GateAction.MANUAL_REVIEW:
    audit.emit("gate_review", {...})
    pipeline.status = "paused"
    notify_reviewer(gate_decision.reviewer, gate_decision)
    # 等用户 sdlc resume
elif gate_decision.action == GateAction.BLOCK:
    audit.emit("gate_blocked", {...})
    pipeline.status = "failed"
    raise GateBlockError(gate_decision.reason)
elif gate_decision.action == GateAction.ESCALATE:
    audit.emit("gate_escalated", {...})
    notify_escalation(gate_decision)
```

详见 `07-gate-catalog.md` 在 prd/。

---

## 四、错误处理矩阵

| 阶段 | 错误类型 | 行为 | retry? | 终止？ |
|---|---|---|---|---|
| Step 1 加载 | StageNotFound | 立即终止 | ✗ | ✓ |
| Step 2 KB | KBMissing | 警告 + 跳过（不阻塞） | ✗ | ✗ |
| Step 2 KB | KBFileNotReadable | 终止 | ✗ | ✓ |
| Step 3 校验 | MissingArtifact | 终止 | ✗ | ✓ |
| Step 3 校验 | ArtifactTampered | 终止 + 告警 | ✗ | ✓ |
| Step 4 规则 | RuleConfigError | 警告 + 跳过规则 | ✗ | ✗ |
| Step 4 规则 | EnforcerFailed | 阻塞型→终止；告警型→继续 | ✗ | 视 enforcer |
| Step 5 Subagent | LLMError | 重试 3 次 → fallback | ✓ | fallback 后 |
| Step 5 Subagent | SubagentTimeout | 终止 | ✗ | ✓ |
| Step 5 Subagent | MaxIterExceeded | 警告 + 强制总结 | ✗ | ✗ |
| Step 5 Subagent | LLMFallbackFailed | 终止 | ✗ | ✓ |
| Step 5 Subagent | ToolError | 重试 1 次 | ✓ | 仍失败则 |
| Step 6 解析 | ParseError | 重试 Subagent（不消耗 retry） | ✓ | 仍失败则 |
| Step 6 解析 | ArtifactInvalid | 终止 | ✗ | ✓ |
| Step 7 持久化 | StateDBError | 终止 + 提示人工 | ✗ | ✓ |
| Step 7 持久化 | StateInconsistent | 终止 + 报警 | ✗ | ✓ |
| Step 8 KB | KBDuplicate | 跳过（正常） | ✗ | ✗ |
| Step 8 KB | KBWriteConflict | 终止 + 提示人工 | ✗ | ✓ |
| Step 8 KB | KBFileLocked | 重试 3 次 | ✓ | 仍失败则 |
| Gate | GateBlock | 终止 | ✗ | ✓ |
| 全流程 | CostExceed | 终止 + 报告 | ✗ | ✓ |
| 全流程 | Timeout | 终止 + 报告 | ✗ | ✓ |

---

## 五、并发与串行

### 5.1 串行（默认）

按拓扑序逐 stage 跑，依赖关系保证。

### 5.2 并行（同层内）

```yaml
# profile.yaml
parallel_groups:
  - stages: [s-impl-backend, s-impl-frontend]   # 可并行
  - stages: [s-test-backend, s-test-frontend]
```

实现：`asyncio.gather(*[run_stage(s) for s in group])`

### 5.3 约束

- 同一 stage 内串行（不并发步骤）
- 跨 stage 默认串行（除非 parallel_groups）
- 全局限流：同时最多 3 个 LLM 调用（避免 rate limit）

---

## 六、Stage 类型分类

| Category | 例子 | Subagent | LLM? | 外部依赖 |
|---|---|---|---|---|
| requirement | s-clarify | SA-1 | ✓ | ask_user |
| design | s-design, s-arch-review | SA-2 | ✓ | mcp |
| impl | s-impl-backend, s-impl-frontend | SA-3/4 | ✓ | skills, mcp |
| test | s-unit-test, s-integration-test | SA-5 | ✓ | dongmock |
| review | s-cr, s-arch-review | SA-6 | ✓ | enforcer |
| package | s-package | — | ✗ | mvn/npm |
| deploy | s-deploy, s-hotfix-deploy | — | ✗ | mcp (hot_deploy) |
| monitor | s-monitor-setup | SA-7 | ✓ | mcp |
| doc | s-docs | SA-8 | ✓ | — |
| migration | s-migrate, s-import | SA-9 | ✓ | — |
| audit | s-security-scan, s-deps-check | SA-10 | ✓ | — |
| infra | s-ci-setup, s-pipeline-update | SA-11 | ✓ | — |

---

## 七、性能预算

| 阶段 | 典型耗时 | 占比 |
|---|---|---|
| Step 1-4 准备 | < 2s | 5% |
| Step 5 Subagent | 30s-10min | 80% |
| Step 6 解析 | < 1s | 2% |
| Step 7 持久化 | < 0.5s | 1% |
| Step 8 KB | < 0.5s | 1% |
| Gate 评估 | < 1s | 2% |
| 其他 | 5% | 5% |

**单 stage 典型**：30s-10min 取决于 LLM 响应。

**Pipeline 典型 7 stage**：5-30min（M1 MVP 测过）；2-8h（带 Gate 等人 review）。

---

## 八、可观测性

每个 stage 产出：
- 1+ `StageResult` 持久化记录
- 5-50 个 audit event
- 1+ `llm_called` event（带 cost）
- 多个 `artifact_created` event
- 1+ `kb_updated` event
- 1 个 `stage_end` event

通过 `sdlc trace <pipeline_id> --stage <id>` 完整回放。

---

## 九、版本

- v1.0 (2026-06-05): 初版
