# 04. Pipeline 构建器 (v2.0)

> **Pipeline Builder = 从 EntryPoint + Profile + Adapter + 已有产物 → 自动生成最小 Pipeline DAG**  
> 用户无需关心"先做什么再做什么"——构建器决定

---

## 一、Pipeline Builder 总览

```
输入：
  - entrypoint: EntryPoint        # 用户从哪来
  - profile: Profile              # 项目类型
  - adapter: Adapter              # 技术栈
  - existing_artifacts: [Artifact]  # 已有产物（用于 resume）
  - user_overrides:               # 用户临时覆盖
      enabled_stages: [stage_id]?
      disabled_stages: [stage_id]?
      extra_stages: [stage_spec]?
      max_budget: {minutes, cost}?
      skip_gates: [gate_id]?

处理：
  1. 选 base stages（profile + entrypoint）
  2. 应用 overrides
  3. 校验依赖
  4. 校验 Gate 触发条件
  5. 构造 DAG
  6. 注入 Adapter 配置
  7. 估算预算
  8. 返回 Pipeline

输出：Pipeline（详见 01-core-concepts.md §5）
```

---

## 二、核心算法

### 2.1 伪代码

```python
def build_pipeline(
    entrypoint: EntryPoint,
    profile: Profile,
    adapter: Adapter,
    existing_artifacts: List[Artifact] = None,
    user_overrides: UserOverrides = None,
) -> Pipeline:
    
    # Step 1: 收集候选 stages
    candidates = set()
    candidates.update(profile.default_stages)
    candidates.update(entrypoint.default_stages)
    candidates.update(adapter.recommended_stages)
    
    # Step 2: 应用 Profile 必跳
    candidates -= set(profile.skip_stages)
    
    # Step 3: 应用 EntryPoint 必跳
    candidates -= set(entrypoint.skip_stages)
    
    # Step 4: 应用用户覆盖
    if user_overrides:
        if user_overrides.disabled_stages:
            candidates -= set(user_overrides.disabled_stages)
        if user_overrides.enabled_stages:
            candidates.update(user_overrides.enabled_stages)
        if user_overrides.extra_stages:
            candidates.update(user_overrides.extra_stages)
    
    # Step 5: 校验依赖
    candidates = enforce_dependencies(candidates, profile)
    
    # Step 6: 校验与已有产物的兼容性
    if existing_artifacts:
        # 如果已有 design_doc，跳过 clarify
        if has_artifact(existing_artifacts, "prd"):
            candidates.discard("clarify")
            candidates.add("clarify-validate")
    
    # Step 7: 转 stage instances
    stage_instances = []
    for sid in candidates:
        instance = create_stage_instance(sid, profile, adapter, user_overrides)
        stage_instances.append(instance)
    
    # Step 8: 构造 DAG edges
    edges = build_edges(stage_instances)
    
    # Step 9: 注入 Gates
    gates = collect_gates(profile, stage_instances, user_overrides)
    
    # Step 10: 估算预算
    budget = estimate_budget(stage_instances, adapter)
    
    # Step 11: 构造 Pipeline
    return Pipeline(
        id=f"{entrypoint.id}-{profile.id}-{adapter.id}-{ts}",
        entrypoint=entrypoint.id,
        profile=profile.id,
        adapter=adapter.id,
        stages=stage_instances,
        edges=edges,
        gates=gates,
        budget=budget,
        state="draft",
    )
```

### 2.2 依赖强制

```python
DEPENDENCY_RULES = {
    "design": ["clarify"],               # design 必在 clarify 之后
    "implement-backend": ["design"],
    "implement-frontend": ["design"],
    "implement-mobile": ["design"],
    "implement-infra": ["design"],
    "unit-test": ["implement-backend", "implement-frontend", "implement-mobile", "implement-infra"],
    "integration-test": ["unit-test"],
    "regression": ["unit-test"],
    "e2e-test": ["deploy"],
    "cr": ["implement-backend", "implement-frontend", "implement-mobile", "implement-infra"],
    "security-scan": ["cr"],
    "package": ["cr"],
    "deploy": ["package"],
    "monitor-setup": ["deploy"],
    "refactor": ["impact-analysis"],
    "docs-update": [],                    # 独立
}

def enforce_dependencies(candidates, profile):
    """补齐 stage 之间的依赖"""
    result = set(candidates)
    changed = True
    while changed:
        changed = False
        for stage in list(result):
            deps = DEPENDENCY_RULES.get(stage, [])
            for dep in deps:
                # 跳过非"该类"实现（如实现后端时不需要前端）
                if dep in result:
                    continue
                if dep_matches_profile(dep, profile):
                    result.add(dep)
                    changed = True
    return result

def dep_matches_profile(dep, profile):
    """某些依赖只在特定 profile 下需要"""
    RULE = {
        "impact-analysis": ["refactor", "migration", "performance", "security"],
        "diagnose": ["bug-fix", "hotfix"],
        "regression": ["refactor", "migration"],
    }
    return profile.id in RULE.get(dep, [])
```

### 2.3 DAG 构造

```python
def build_edges(stages: List[StageInstance]) -> List[Edge]:
    """默认线性 DAG；后续可重排（并行 stage）"""
    
    # 1. 按 category 排序
    CATEGORY_ORDER = [
        "requirement",  # clarify, impact
        "design",       # design, adr
        "implement",    # impl-*
        "test",         # unit, integration, regression, e2e
        "review",       # cr, security-scan
        "deploy",       # package, deploy
        "operate",      # monitor-setup
        "maintain",     # refactor, docs, migration
    ]
    
    sorted_stages = sorted(stages, key=lambda s: CATEGORY_ORDER.index(s.category))
    
    # 2. 线性连接
    edges = []
    for i in range(len(sorted_stages) - 1):
        edges.append(Edge(
            from_=sorted_stages[i].instance_id,
            to=sorted_stages[i+1].instance_id,
            on="success"
        ))
    
    # 3. 检测可并行 stage
    # 如：unit-test 和 integration-test 在某些场景可并行
    #     security-scan 和 docs-update 可并行
    parallel_groups = find_parallel_groups(sorted_stages)
    for group in parallel_groups:
        # 添加 fan-in node
        fan_in = create_fan_in_node(group)
        for s in group:
            edges.append(Edge(from_=s, to=fan_in, on="success"))
        # 删除原线性边
        ...
    
    return edges

PARALLEL_GROUPS = {
    ("unit-test", "security-scan"): "R2 同时跑",
    ("unit-test", "docs-update"): "编码后并行",
    ("e2e-test", "regression"): "部署后并行",
}
```

### 2.4 Gate 注入

```python
def collect_gates(profile, stages, user_overrides) -> List[Gate]:
    """收集所有 gate，按位置排序"""
    
    gates = []
    for stage in stages:
        if stage.gate and stage.gate.trigger != "never":
            # 应用 profile 必跳/必走
            if should_skip_gate(stage.gate, profile):
                continue
            # 应用用户覆盖
            if user_overrides and stage.gate.id in user_overrides.skip_gates:
                continue
            
            gate = Gate(
                id=stage.gate.id,
                name=stage.gate.name,
                after_stage=stage.instance_id,
                trigger=stage.gate.trigger,
                severity_threshold=stage.gate.severity_threshold,
                sla_hours=stage.gate.sla_hours,
                approvers=stage.gate.approvers,
                checklist=stage.gate.checklist,
            )
            gates.append(gate)
    
    return gates

def should_skip_gate(gate, profile):
    """某些 profile 跳过某些 gate"""
    SKIP_RULES = {
        "hotfix": ["gate-1-clarify", "gate-2-design", "gate-4-monitor"],
        "docs-only": ["gate-1-clarify", "gate-2-design", "gate-3-cr", "gate-4-monitor"],
        "test-only": ["gate-1-clarify", "gate-2-design", "gate-4-monitor"],
        "review-only": ["gate-1-clarify", "gate-2-design", "gate-4-monitor"],
    }
    return gate.id in SKIP_RULES.get(profile.id, [])
```

---

## 三、典型场景的 Pipeline 输出

### 3.1 场景 A：Java/DongBoot 新功能

```
输入：
  entrypoint=idea
  profile=new-feature
  adapter=dongboot

输出 Pipeline：
  stages:
    [s-clarify, s-design, s-impl, s-unit, s-cr, s-pkg, s-deploy, s-mon]
  edges: 7 条线性边
  gates:
    [gate-1 after s-clarify, gate-2 after s-design, gate-3 after s-cr, gate-4 after s-mon]
  budget: {max_minutes: 1440, max_cost_usd: 5.0}
```

### 3.2 场景 B：Python/Flask Bug 修复

```
输入：
  entrypoint=bug
  profile=bug-fix
  adapter=python-flask

输出 Pipeline：
  stages:
    [s-diagnose, s-fix, s-test, s-cr, s-deploy]
  edges: 4 条线性边
  gates:
    [gate-2 after s-fix, gate-3 after s-cr]  # 跳过 1、4
  budget: {max_minutes: 480, max_cost_usd: 2.0}
```

### 3.3 场景 C：紧急 Hotfix

```
输入：
  entrypoint=hotfix
  profile=hotfix
  adapter=dongboot

输出 Pipeline：
  stages:
    [s-diagnose, s-fix, s-test, s-deploy, s-verify]
  edges: 4 条线性边
  gates:
    [gate-3 after s-test]  # 仅 TL Gate
  budget: {max_minutes: 180, max_cost_usd: 1.5}
```

### 3.4 场景 D：重构

```
输入：
  entrypoint=refactor
  profile=refactor
  adapter=spring-boot

输出 Pipeline：
  stages:
    [s-impact, s-design, s-refactor, s-unit, s-regression, s-cr, s-deploy]
  edges: 6 条线性边
  gates:
    [gate-2 after s-design, gate-3 after s-cr]
  budget: {max_minutes: 2880, max_cost_usd: 8.0}
```

### 3.5 场景 E：加监控（最简）

```
输入：
  entrypoint=monitor
  profile=monitor-only
  adapter=dongboot

输出 Pipeline：
  stages:
    [s-monitor-setup]
  edges: []
  gates:
    [gate-4]  # 监控必走 SRE
  budget: {max_minutes: 60, max_cost_usd: 0.5}
```

### 3.6 场景 F：从代码评审开始

```
输入：
  entrypoint=code
  profile=review-only
  adapter=auto-detect

输出 Pipeline：
  stages:
    [s-cr]
  edges: []
  gates: []  # review-only 不走 Gate
  budget: {max_minutes: 30, max_cost_usd: 0.2}
```

### 3.7 场景 G：完整迁移（最重）

```
输入：
  entrypoint=idea
  profile=migration
  adapter=auto-detect (MySQL → TiDB)

输出 Pipeline：
  stages:
    [s-clarify, s-impact, s-design, s-impl, s-unit, s-integration, s-regression, s-cr, s-security-scan, s-pkg, s-deploy, s-verify, s-mon]
  edges: 12 条线性边（部分可并行）
  gates:
    [gate-1, gate-2, gate-3, gate-4]  # 全部
  budget: {max_minutes: 4320, max_cost_usd: 15.0}
```

---

## 四、Resume / Checkpoint 机制

### 4.1 自动 Checkpoint

```python
# 每个 stage 完成后
def on_stage_completed(stage_instance, artifacts, pipeline):
    snapshot = {
        "stage_id": stage_instance.id,
        "completed_at": now(),
        "artifacts": [a.to_dict() for a in artifacts],
        "pipeline_state": pipeline.to_dict(),
    }
    save_snapshot(pipeline.id, snapshot)
    append_audit_log(pipeline.id, "stage_completed", snapshot)
```

### 4.2 Resume 算法

```python
def resume_pipeline(pipeline_id: str) -> Pipeline:
    pipeline = load_pipeline(pipeline_id)
    snapshot = load_latest_snapshot(pipeline_id)
    
    # 标记已完成的 stage
    completed_stage_ids = [s["stage_id"] for s in snapshot["stages_completed"]]
    
    for stage in pipeline.stages:
        if stage.id in completed_stage_ids:
            stage.state = "completed"
            stage.outputs = [load_artifact(a) for a in snapshot["artifacts_by_stage"][stage.id]]
        else:
            stage.state = "pending"
    
    pipeline.state = "active"
    return pipeline
```

### 4.3 用户提示

```
检测到之前的 pipeline [name]，已运行到 [stage]，现在要从 [next_stage] 继续。
- 输入 "继续"：从 next_stage 跑
- 输入 "重新跑 [stage_id]"：从指定 stage 重跑
- 输入 "修改 [stage_id] 的输入"：先编辑再跑
```

---

## 五、用户覆盖

### 5.1 覆盖语法（自然语言）

```
"跳过 unit-test"          → disabled_stages: [unit-test]
"加上 security-scan"      → extra_stages: [security-scan]
"不超过 30 分钟"           → max_budget.minutes: 30
"不要 Gate 1"             → skip_gates: [gate-1]
"用 junior 替代 senior"   → subagent_override
```

### 5.2 覆盖优先级

```
用户覆盖 > Profile > Adapter 默认 > Stage 默认
```

---

## 六、Pipeline 状态转换详解

```
draft
  │  start (user confirm)
  ↓
active
  │  pause (user request)
  ↓
paused
  │  resume
  ↓
active
  │  stage failed
  ↓
paused (with error)
  │  retry
  ↓
active
  │  all stages done
  ↓
completed
  │  any stage fatal fail
  ↓
failed
```

**关键事件**：
- `pipeline_started`
- `stage_started`
- `stage_completed`
- `stage_failed`
- `gate_pending`
- `gate_approved`
- `gate_rejected`
- `pipeline_paused`
- `pipeline_resumed`
- `pipeline_completed`
- `pipeline_failed`

---

## 七、并行优化

### 7.1 何时并行

- 独立可并行：unit-test ↔ security-scan
- 部署后并行：regression ↔ e2e-test
- 监控后并行：runbook ↔ dashboard（实际是同 stage 的不同产物）

### 7.2 资源限制

```yaml
parallel:
  max_concurrent_stages: 3       # 最多同时 3 个 stage
  cost_per_minute_usd: 0.01      # 限速，避免烧钱
```

---

## 八、版本

- v2.0 (2026-06-05): Pipeline Builder（取代 v1.0 的固定 7 阶段 DAG）
