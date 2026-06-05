# 13. 开发流程 (v1.0)

> sdlc 项目自身的 Git / CI / 版本 / CHANGELOG / Code Review 流程

---

## 一、Git 仓库结构

```
sdlc/                                  # 仓库根
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # Lint + Test + E2E
│   │   ├── release.yml               # 自动发版
│   │   └── docs.yml                  # 自动部署文档
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug.md
│   │   ├── feature.md
│   │   └── question.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── CODEOWNERS
├── .vscode/
│   ├── settings.json                 # 编辑器配置
│   └── extensions.json               # 推荐扩展
├── docs/                             # mkdocs 源
│   ├── index.md
│   ├── getting-started/
│   ├── user-guide/
│   ├── reference/
│   └── developer-guide/
├── sdlc/                             # 主包
│   ├── __init__.py
│   ├── cli/
│   ├── utils/
│   ├── core/
│   ├── kb/
│   ├── llm/
│   ├── subagent/
│   ├── adapter/
│   ├── stage/
│   ├── profile/
│   ├── rule/
│   ├── gate/
│   ├── audit/
│   ├── state/
│   ├── integrations/
│   └── builtin/                       # 内置 Subagent/Stage/Profile
│       ├── subagents/
│       ├── stages/
│       ├── profiles/
│       ├── rules/
│       └── gates/
├── templates/                        # Jinja2 模板
│   ├── subagent.md
│   ├── stage.yaml
│   ├── gate.yaml
│   └── ...
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── perf/
│   ├── contract/
│   ├── property/
│   ├── snapshots/
│   ├── fixtures/
│   └── conftest.py
├── scripts/
│   ├── binternal-monitoring_version.py
│   ├── update_homebrew.sh
│   ├── build_docker.sh
│   └── dev_setup.sh
├── pyproject.toml
├── uv.lock
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── .gitignore
├── .python-version                   # 3.12
├── .pre-commit-config.yaml
├── .ruff.toml
├── .mypy.ini
├── Dockerfile
├── docker-compose.yml
├── mkdocs.yml
└── prd/                              # 设计文档
    ├── 00-README.md
    ├── 01-core-concepts.md
    └── ...
```

---

## 二、分支策略

### 2.1 Trunk-Based Development

```
main (永远 green)
  │
  ├── feature/<name>        # 短命分支，1-3 天
  │     # 完成后 squash merge
  │
  ├── fix/<name>
  │
  └── release/<version>     # 1-2 周，stable
```

### 2.2 分支命名

- `feature/<short-name>`：新功能
- `fix/<short-name>`：bug 修复
- `refactor/<short-name>`：重构
- `docs/<short-name>`：文档
- `chore/<short-name>`：杂项
- `release/<version>`：发布准备

### 2.3 合并策略

- Feature → Main：squash merge
- Release → Main：merge commit
- Hotfix → Main：squash merge

### 2.4 保护规则（main）

- 必须 PR
- 至少 1 个 reviewer
- 必须通过 CI
- 必须无 unresolved comments
- 不可直接 push
- 不可 force-push

---

## 三、Commit 规范

### 3.1 Conventional Commits

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**：
- `feat`：新功能
- `fix`：bug 修复
- `docs`：文档
- `style`：格式
- `refactor`：重构
- `perf`：性能
- `test`：测试
- `chore`：杂项
- `ci`：CI
- `build`：构建系统

**Scope**（可选）：
- `cli` / `kb` / `llm` / `subagent` / `adapter` / `stage` / `profile` / `rule` / `gate` / `state` / `audit`

**Example**：
```
feat(kb): add diff-only write mode

实现 KB 写入的 diff-only 策略，避免不必要覆盖。
通过 fingerprint 检测内容是否真的变化。

- 添加 diff-only 算法（基于 unified diff）
- 添加 fingerprint 计算
- 添加单元测试

Closes #123
```

### 3.2 自动校验

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/compilerla/conventional-pre-commit
    rev: v3.3.0
    hooks:
      - id: conventional-pre-commit
        stages: [commit-msg]
        args: []
```

### 3.3 自动 changelog

`release-please` 解析 conventional commits → 自动 binternal-monitoring version + 写 CHANGELOG + 打 tag + 发 release。

---

## 四、CI 流水线

### 4.1 触发

| 触发 | 工作流 |
|---|---|
| PR / push to main | ci.yml |
| push to main | release.yml, docs.yml |
| 手动 | release.yml（workflow_dispatch） |

### 4.2 ci.yml 阶段

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  ruff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v1
        with:
          args: check --output-format=github .
      - run: ruff format --check .

  mypy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install uv && uv sync --all-extras
      - run: uv run mypy sdlc/

  unit:
    needs: [ruff, mypy]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install uv && uv sync --all-extras
      - run: uv run pytest tests/unit -v --cov=sdlc --cov-report=xml --cov-fail-under=80
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

  e2e:
    needs: integration
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: ${{ matrix.python-version }}}
      - run: pip install uv && uv sync
      - run: uv run pytest tests/e2e -v -m "not slow"
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### 4.3 必需检查

- ✅ Ruff lint
- ✅ Ruff format
- ✅ Mypy strict
- ✅ Unit >= 80%
- ✅ Integration pass
- ✅ E2E pass（Python 3.11 + 3.12）
- ⏳ Docs build（PR 提示）
- ⏳ Bench（nightly）

---

## 五、Code Review

### 5.1 Reviewer 要求

- 至少 1 个 maintainer
- 大改动（> 500 行）：2 个
- 安全敏感：必须 security team

### 5.2 Review Checklist

#### 通用
- [ ] 命名清晰
- [ ] 函数短（< 50 行）
- [ ] 无副作用 / magic number
- [ ] 错误处理合理
- [ ] 日志完整
- [ ] 测试覆盖 >= 80%

#### 架构
- [ ] 模块边界正确
- [ ] 无循环依赖
- [ ] 符合 `01-architecture-overview.md` 的分层

#### 性能
- [ ] 不在 hot path 用同步 I/O
- [ ] 缓存合理
- [ ] 大文件不分次全读

#### 安全
- [ ] 无 SQL 注入
- [ ] 无路径遍历
- [ ] 敏感信息不写日志
- [ ] 输入校验

#### 兼容
- [ ] 不破坏 API
- [ ] 文档同步更新
- [ ] CHANGELOG entry（如有）

### 5.3 Review SLA

- 工作日 24h 内首次响应
- 工作日 48h 内完成 review

### 5.4 工具

- GitHub 内置 review
- `CODEOWNERS` 自动 assign
- Danger 自动化（可选）

### 5.5 CODEOWNERS

```
# .github/CODEOWNERS
*                          @duanluyao1
/sdlc/llm/                 @duanluyao1
/sdlc/state/               @duanluyao1
/sdlc/adapter/dongboot/    @dongboot-team
```

---

## 六、本地开发

### 6.1 环境准备

```bash
# 1. 克隆
git clone https://github.com/duanluyao1/sdlc.git
cd sdlc

# 2. 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. 装依赖
uv sync --all-extras

# 4. 装 pre-commit hook
uv run pre-commit install

# 5. 验证
uv run sdlc --version
uv run pytest tests/unit
```

### 6.2 日常开发循环

```bash
# 1. 切分支
git checkout -b feature/cool-thing

# 2. 改代码
# ... vim ...

# 3. 跑测试
uv run pytest tests/unit -v

# 4. 跑 lint
uv run ruff check . && uv run ruff format .

# 5. 跑 mypy
uv run mypy sdlc/

# 6. 提交
git add .
git commit -m "feat(kb): add diff-only write"

# 7. 推送
git push -u origin feature/cool-thing

# 8. 开 PR
gh pr create --fill

# 9. 等 review
# 10. 合并
```

### 6.3 调试

```bash
# 详细日志
uv run sdlc run --verbose --verbose --verbose

# IPython 调试
uv run ipython
>>> from sdlc.core import Pipeline
>>> p = Pipeline.from_yaml("...")
>>> p.validate()

# 断点
import pdb; pdb.set_trace()

# 时间旅行
from freezegun import freeze_time
@freeze_time("2026-06-05")
def test_...
```

### 6.4 编辑器

`.vscode/settings.json`：
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.testing.pytestEnabled": true,
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "ruff.enable": true,
  "mypy-type-checker.args": ["--config-file=mypy.ini"]
}
```

`.vscode/extensions.json`：
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.mypy-type-checker",
    "charliermarsh.ruff",
    "tamasfe.even-better-toml",
    "redhat.vscode-yaml"
  ]
}
```

---

## 七、版本与发布（sdlc 项目自身）

### 7.1 binternal-monitoring

`scripts/binternal-monitoring_version.py`：
```python
#!/usr/bin/env python3
"""Binternal-monitoring version using binternal-monitoring-my-version"""
import subprocess
import sys
from pathlib import Path

def binternal-monitoring(part: str):
    subprocess.run(["uv", "run", "binternal-monitoring-my-version", "binternal-monitoring", part], check=True)

if __name__ == "__main__":
    binternal-monitoring(sys.argv[1] if len(sys.argv) > 1 else "patch")
```

### 7.2 .binternal-monitoringversion.toml

```toml
[tool.binternal-monitoringversion]
current_version = "0.1.0"
parse = "(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)"
serialize = ["{major}.{minor}.{patch}"]
search = "{current_version}"
replace = "{new_version}"
regex = false
tag_name = "v{new_version}"
tag_message = "Release {new_version}"
commit = true
message = "chore(release): {new_version}"

[[tool.binternal-monitoringversion.files]]
filename = "sdlc/__init__.py"
search = "__version__ = \"{current_version}\""
replace = "__version__ = \"{new_version}\""

[[tool.binternal-monitoringversion.files]]
filename = "pyproject.toml"
search = "version = \"{current_version}\""
replace = "version = \"{new_version}\""

[[tool.binternal-monitoringversion.files]]
filename = "CHANGELOG.md"
```

### 7.3 自动 release

`release-please` 监听 conventional commits → 自动：
- 决定 binternal-monitoring 级别（feat → minor, fix → patch, BREAKING CHANGE → major）
- 更新 `pyproject.toml` + `sdlc/__init__.py`
- 更新 `CHANGELOG.md`
- 创建 commit
- 创建 tag
- 创建 GitHub release

---

## 八、Issue 管理

### 8.1 标签

| 标签 | 用途 |
|---|---|
| `bug` | Bug |
| `enhancement` | 新功能 |
| `docs` | 文档 |
| `question` | 提问 |
| `good first issue` | 新手友好 |
| `help wanted` | 需要帮助 |
| `priority: high` | P0 |
| `priority: medium` | P1 |
| `priority: low` | P2 |
| `stage: clarify` / `design` / ... | 对应 PRD Stage |
| `adapter: dongboot` / ... | 对应 Adapter |
| `wontfix` | 不修 |
| `duplicate` | 重复 |

### 8.2 模板

`bug.md`：
```markdown
## Bug Description
...

## Reproduction
```python
# 复现代码
```

## Expected Behavior
...

## Actual Behavior
...

## Environment
- sdlc version: 0.1.0
- Python: 3.12.2
- OS: macOS 14
- LLM provider: anthropic

## Logs
```
...
```
```

`feature.md`：
```markdown
## Feature Description
...

## Use Case
...

## Proposed Solution
...

## Alternatives Considered
...

## Additional Context
...
```

### 8.3 SLA

- Triage 1 个工作日
- Priority high 7 天内解决
- Priority medium 30 天
- Priority low best effort

---

## 九、安全

### 9.1 报告

`SECURITY.md`：
```markdown
# Security Policy

## Supported Versions
| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |
| < 0.1   | ❌        |

## Reporting a Vulnerability
Email: security@duanluyao1.com
PGP: ...
- 48h 内确认
- 7 天内修复
- 公开 CVE（如适用）
```

### 9.2 扫描

```yaml
# .github/workflows/security.yml
name: Security

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # weekly

jobs:
  bandit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install uv bandit && uv sync
      - run: uv run bandit -r sdlc/

  pip-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install uv pip-audit && uv sync
      - run: uv run pip-audit

  trufflehog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD
```

### 9.3 依赖更新

- Dependabot 自动 PR
- 周一 review
- 安全漏洞 24h 内

---

## 十、文档

### 10.1 文档层级

| 文档 | 位置 | 何时写 |
|---|---|---|
| README | 仓库根 | 每次大版本 |
| PRD | `prd/` | 概念/需求变更时 |
| 设计稿 | `doc/design/` | 架构变更时 |
| API doc | `docs/reference/` | 改 API 时 |
| Changelog | `CHANGELOG.md` | release-please 自动 |
| 教程 | `docs/getting-started/` | 新功能发布时 |
| ADR | `docs/adr/` | 重大决策时 |

### 10.2 ADR 模板

```markdown
# ADR-NNN: <title>

## Status
Proposed | Accepted | Deprecated | Superseded

## Context
要解决的问题

## Decision
做的决策

## Consequences
正面 + 负面

## Alternatives Considered
考虑过的其他方案
```

### 10.3 docstring 规范

Google style：

```python
def fetch_pipeline(pipeline_id: str, *, include_artifacts: bool = False) -> Pipeline:
    """从 StateStore 加载 pipeline。

    Args:
        pipeline_id: Pipeline ID（如 "feat-2026-06-05-001"）。
        include_artifacts: 是否同时加载 artifacts。

    Returns:
        Pipeline 对象。

    Raises:
        PipelineNotFoundError: pipeline_id 不存在。
        StateStoreError: DB 读取失败。
    """
```

---

## 十一、沟通

### 11.1 渠道

- GitHub Issues：公开讨论
- GitHub Discussions：问答
- Discord：实时聊天
- Email：安全 / 法律

### 11.2 会议节奏

- 周一：本周计划
- 周三：mid-week sync
- 周五：周回顾 + demo

---

## 十二、版本

- v1.0 (2026-06-05): 初版
