# 07. 扩展机制 (v1.0)

> 加 Adapter / Stage / Profile / Rule / Subagent 的零代码流程

---

## 一、设计目标

**不碰 Python 代码**就能扩展 sdlc：
- 加新技术栈支持（Adapter）
- 加新项目类型（Profile）
- 加新工作流（Stage）
- 加新约束（Rule）
- 加新专家（Subagent）

---

## 二、加载层级与优先级

```
优先级从高到低（高优先级覆盖低优先级）：
1. --config 指定路径
2. 项目级 .sdlc/ext/  ← 项目定制
3. 用户级 ~/.sdlc/ext/ ← 个人定制
4. 全局内置 sdlc/builtin/ ← sdlc 自带
```

**加载器行为**：
- 同名资源：高优先级覆盖低优先级
- 冲突 → 启动时打印 WARN，但不阻断
- 用 `sdlc config path` 看当前生效

---

## 三、加 Adapter

### 3.1 零代码路径

```bash
# 1. 在项目根创建 .sdlc/ext/adapters/my-stack.yaml
cat > .sdlc/ext/adapters/my-stack.yaml <<'EOF'
id: my-stack
name: My Company Stack
version: 1.0
detect_patterns:
  - glob: "**/package.json"
    contains: "mycorp"
  - glob: "**/Cargo.toml"
    contains: "mycorp"
components:
  - id: my-storage
    type: db
    detect: "MyStorage"
    enforce: true
enforce_rules: true
rule_sets:
  - mycorp-must
required_kb:
  - rules/MUST.yaml
  - standards/coding-style.md
EOF

# 2. 验证
sdlc adapter validate .sdlc/ext/adapters/my-stack.yaml

# 3. 在项目里检测
sdlc adapter detect .
# → [dongboot, my-stack]  # 自动识别两个
```

### 3.2 Adapter YAML Schema

```yaml
id: string                       # 必填，全局唯一
name: string                     # 显示名
version: semver                  # 1.0
detect_patterns:                 # 触发检测
  - glob: "**/pom.xml"
    contains: "<artifactId>dong-boot"
  - glob: "**/src/main/java"
    contains: "com.jd"
  - regex: "dongboot-starter"
    path: "**/pom.xml"
components:                      # 框架组件列表
  - id: string                   # 组件 id
    name: string                 # 显示名
    type: enum                   # logging|db|threadpool|http|lock|cache|...
    detect:                      # 检测方式
      type: import               # import 检测
      pattern: "com.jd.donglog.BizLogger"
      # 或
      type: annotation           # 注解检测
      pattern: "@DongLog"
      # 或
      type: yaml                 # 配置文件检测
      path: "application.yml"
      contains: "dong-log"
    enforce: bool                 # 是否强制使用
    config_template: path?       # 配置生成模板
    docs_url: string?
enforce_rules: bool
rule_sets: [string]              # 引用规则集
required_kb: [string]            # 必读 KB 文件
custom_stages:                   # 可选：本 Adapter 专用 stage
  - id: string
    file: stages/xxx.yaml
mcp_servers:                     # 调用的 MCP servers
  - name: string
    config: object?
```

### 3.3 内置 Adapter 库位置

```
sdlc/builtin/adapters/
├── dongboot.yaml          # 18 DongBoot 组件
├── jd-spring-boot.yaml
├── node-nestjs.yaml
├── python-fastapi.yaml
├── go-gin.yaml
├── rust-axum.yaml
├── ...
```

### 3.4 编程式扩展（高级）

```python
# my_extension.py
from sdlc.adapter import register_adapter

register_adapter(
    id="my-stack",
    name="My Company Stack",
    detect_patterns=[...],
    components=[...],
    enforce_rules=True,
    rule_sets=["mycorp-must"],
)

# 然后 sdlc 自动加载（通过 sdlc --plugin my_extension.py）
```

---

## 四、加 Stage

### 4.1 零代码路径

```bash
cat > .sdlc/ext/stages/s-data-migration.yaml <<'EOF'
id: s-data-migration
name: 数据迁移
category: migration
description: |
  执行数据迁移脚本（带 backup + dry-run + 回滚机制）。
required_artifacts:
  - migration-script.sql
  - migration-plan.md
produces_artifacts:
  - migration-report.md
  - rollback-plan.md
pre_kb_load:
  - conventions.md
  - data-catalog.md
post_kb_update:
  - target: data-catalog.md
    op: append
    template: |
      ## {{ stage_id }} ({{ ts }})
      - 迁移：{{ artifacts[0].path }}
      - 影响行数：{{ result.row_count }}
      - 耗时：{{ result.duration_ms }}ms
subagent: SA-9
model: claude-sonnet-4-6
timeout: 3600
retry:
  max: 1
  backoff: fixed
gates:
  - after: always
    trigger: on_rule_violation
    reviewer: DBA
    deadline_hours: 24
EOF

sdlc stage validate .sdlc/ext/stages/s-data-migration.yaml
```

### 4.2 Stage YAML Schema

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `id` | ✓ | string | 唯一 |
| `name` | ✓ | string | 显示名 |
| `category` | ✓ | enum | 见 06-stage-execution §6 |
| `description` | | string | |
| `required_artifacts` | | list | 上游 artifacts |
| `produces_artifacts` | | list | 产出 artifacts |
| `pre_kb_load` | | list | 跑前读 KB |
| `post_kb_update` | | list | 跑后写 KB |
| `subagent` | | SA-X | 调哪个 subagent |
| `model` | | string | 覆盖 subagent 默认 model |
| `timeout` | ✓ | int | 秒 |
| `retry` | | object | max/backoff |
| `gates` | | list | 见 06 |
| `custom_fields` | | object | 透传给 Subagent |

### 4.3 使用

```bash
# 1. 加到 profile
cat >> .sdlc/ext/profiles/data-migration.yaml <<EOF
extra_stages:
  - s-data-migration
EOF

# 2. 跑
sdlc run "迁移订单表加 status 字段" -p data-migration
```

---

## 五、加 Profile

### 5.1 零代码路径

```bash
cat > .sdlc/ext/profiles/data-migration.yaml <<'EOF'
id: data-migration
name: 数据迁移
entry_kinds: [migration, refactor]
base_stages:
  - s-clarify
  - s-design
  - s-data-migration
  - s-verify
  - s-monitor-setup
skip_stages: []
extra_stages: []
gates:
  - after: s-design
    trigger: always
    reviewer: DBA
  - after: s-data-migration
    trigger: always
    reviewer: DBA
severity: P1
subagent_overrides:
  SA-2:
    model: claude-opus-4-7
EOF
```

### 5.2 Profile Schema

见 `04-data-model.md §8`。

---

## 六、加 Rule

### 6.1 零代码路径

```bash
cat > .sdlc/ext/rules/custom/must-no-mock-in-prd.yaml <<'EOF'
- id: custom-no-mock-in-prd
  level: MUST
  category: documentation
  description: |
    PRD 中禁止使用"mock"作为生产方案描述。
  enforcer: cr
  scope:
    stages: [s-clarify, s-design]
  detection:
    type: text_match
    pattern: "(?i)mock(?!.*(开发|测试|桩))"
    target_files: ["**/prd.md", "**/arch.md"]
  action: warn
  message: |
    PRD 不应将 mock 作为生产方案。请用具体技术方案。
  references:
    - https://wiki.mycorp/standards/production-ready
EOF
```

### 6.2 Rule Schema

见 `04-data-model.md §5.3`。

### 6.3 加 enforcer（高级）

```python
from sdlc.rule import register_enforcer

class CustomEnforcer:
    def check(self, rule, context) -> list[Violation]:
        # 自定义检查
        ...

register_enforcer("my-enforcer", CustomEnforcer())
```

---

## 七、加 Subagent

### 7.1 零代码路径

```bash
mkdir -p .sdlc/ext/agents/prompts

cat > .sdlc/ext/agents/SA-12-data-engineer.yaml <<'EOF'
id: SA-12
name: data-engineer
role: data-engineer
model: claude-opus-4-7
tools: [read, write, ask_user, mcp]
kb_inject:
  - data-catalog.md
  - architecture/data-flow.md
  - standards/coding-style.md
prompt_file: prompts/sa-12-data-engineer.md
max_iter: 8
EOF

cat > .sdlc/ext/agents/prompts/sa-12-data-engineer.md <<'EOF'
# 数据工程师

你是数据工程师，负责：
1. 评审数据模型变更
2. 设计迁移方案
3. 编写迁移脚本

## 输入
- 需求描述
- 现有 schema
- KB 中的 data-catalog

## 输出
- 迁移脚本 SQL
- 回滚脚本
- 风险评估

## 规则
{{ rules | tojson }}

## KB
{{ kb | tojson }}
EOF

sdlc agent validate .sdlc/ext/agents/SA-12-data-engineer.yaml
```

### 7.2 Subagent YAML Schema

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | ✓ | SA-12+ |
| `name` | ✓ | kebab-case |
| `role` | ✓ | 角色名 |
| `model` | ✓ | claude-opus-4-7 / sonnet / haiku |
| `tools` | | 允许工具 |
| `kb_inject` | | 注入 KB 文件 |
| `prompt_file` | ✓ | prompt 模板 |
| `max_iter` | | 默认 10 |

### 7.3 编程式扩展

```python
from sdlc.subagent import register_subagent

register_subagent(
    id="SA-12",
    name="data-engineer",
    role="data-engineer",
    model="claude-opus-4-7",
    prompt="...",
    kb_inject=["data-catalog.md"],
    max_iter=8,
)
```

---

## 八、加 Gate

### 8.1 零代码路径

```bash
cat > .sdlc/ext/gates/security-review.yaml <<'EOF'
id: G-security
name: Security Review
trigger: on_stage
after_stages: [s-impl-backend]
reviewer_role: security-team
deadline_hours: 24
severity_required: [P0, P1, P2]
actions:
  - check: secrets_in_code
    tool: gitleaks
  - check: dependencies_cve
    tool: trivy
auto_fail_if: "secrets_in_code: high>0 OR cve_critical>0"
EOF
```

### 8.2 Gate Schema

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | ✓ | G-X |
| `name` | ✓ | |
| `trigger` | ✓ | always / on_severity / on_artifact / on_rule_violation / on_failure / on_stage |
| `after_stages` | | 适用 stages |
| `reviewer_role` | | 评审人角色 |
| `deadline_hours` | | 评审 SLA |
| `actions` | | 自动检查项 |
| `auto_fail_if` | | 自动失败条件 |

---

## 九、加载流程

```python
def load_all_extensions():
    layers = [
        Path("~/.sdlc/ext/").expanduser(),
        Path(".sdlc/ext/"),
    ]
    for layer in layers:
        if not layer.exists():
            continue
        _load_adapters(layer / "adapters")
        _load_stages(layer / "stages")
        _load_profiles(layer / "profiles")
        _load_rules(layer / "rules")
        _load_subagents(layer / "agents")
        _load_gates(layer / "gates")
    _validate_uniqueness()
    _validate_schemas()
    _resolve_conflicts()
```

加载时机：
- CLI 启动时（每次命令）
- 热加载（可选）：`sdlc config reload`

---

## 十、版本

- v1.0 (2026-06-05): 初版
