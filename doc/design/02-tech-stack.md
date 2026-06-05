# 02. 技术栈 (v1.0)

> Python 3.11+ / uv / 核心库 / 选型理由

---

## 一、概览

| 维度 | 选型 | 版本 |
|---|---|---|
| 语言 | Python | 3.11+（用 `tomllib`、StrEnum、ExceptionGroup） |
| 包管理 | uv | 0.4+ |
| CLI 框架 | click | 8.1+ |
| 终端美化 | rich | 13+ |
| 数据校验 | pydantic | 2.6+ |
| YAML | ruamel.yaml | 0.18+（保 round-trip） |
| 模板 | jinja2 | 3.1+ |
| HTTP | httpx | 0.27+ |
| SQLite | 内置 sqlite3 | — |
| 异步 | asyncio + uvloop | asyncio 内置 + uvloop 0.19+ |
| 重试 | tenacity | 8.2+ |
| LLM SDK | anthropic | 0.34+ |
| LLM 回退 | openai | 1.30+ |
| MCP | mcp（官方） | 0.5+ |
| Git | GitPython | 3.1+ |
| 测试 | pytest + pytest-asyncio | 8+ / 0.23+ |
| Mock | pytest-mock + respx | 3.12+ / 0.21+ |
| 覆盖率 | coverage | 7.4+ |
| Lint | ruff | 0.4+ |
| 类型 | mypy | 1.10+ |
| 格式 | ruff format | — |
| Pre-commit | pre-commit | 3.7+ |
| 文档 | mkdocs-material（可选） | 9.5+ |
| CHANGELOG | git-cliff | 2.0+ |

**总数**：核心 12 + 测试 5 + 工具 5 = 22 个直接依赖。

---

## 二、核心库逐项理由

### 2.1 CLI 层

| 库 | 理由 | 替代 |
|---|---|---|
| **click 8.1+** | 装饰器声明 + 自动帮助 + 上下文嵌套 + 异步友好 | typer（绑定 pydantic 但启动慢） |
| **rich 13+** | 进度条 + 表格 + 语法高亮 + live log | — |

**为什么不用 typer**：typer 强绑 pydantic/click，封装太重；本工具需要细粒度控制命令行为和异常处理。

### 2.2 数据层

| 库 | 理由 | 替代 |
|---|---|---|
| **pydantic 2.6+** | Rust 核心，10x 性能；schema 强类型；JSON schema 自动生成；与 LangChain/AutoGen 生态一致 | dataclasses（无验证）、attrs（弱生态） |
| **ruamel.yaml** | 保 round-trip（注释/顺序）；支持 YAML 1.2；可写不破坏原文件 | PyYAML（破坏 round-trip） |

**为什么不用 PyYAML**：Adapter/Stage YAML 经常需要人工编辑后保留注释/顺序；PyYAML 会重写整个文件。

### 2.3 模板与渲染

| 库 | 理由 |
|---|---|
| **jinja2 3.1+** | Stage prompt 模板；继承/宏；沙箱；社区标准 |

**为什么不用 mako/jinja2-alt**：生态/稳定性/可读性完胜。

### 2.4 异步与 HTTP

| 库 | 理由 | 替代 |
|---|---|---|
| **asyncio（内置）** | 标准库，零成本 | trio（生态弱） |
| **uvloop 0.19+** | asyncio 2-4x 加速；asyncio 兼容 API | — |
| **httpx 0.27+** | async/await + sync 双模；HTTP/2；timeouts 完善 | aiohttp（弱 type）、requests（同步） |

**为什么不用 requests**：本工具所有 IO 都异步化，requests 会成瓶颈。

### 2.5 LLM SDK

| 库 | 理由 |
|---|---|
| **anthropic 0.34+** | 官方 SDK；tool_use / prompt_caching / streaming |
| **openai 1.30+** | 回退；价格优势；多 provider |
| **tenacity 8.2+** | 重试退避（指数 + 抖动） |

**为什么不只用 anthropic**：限流/成本/可用性；多 provider 是基本要求。

### 2.6 MCP / 外部

| 库 | 理由 |
|---|---|
| **mcp 0.5+** | Anthropic 官方 MCP Python SDK |
| **GitPython 3.1+** | diff / commit / blame / log |

### 2.7 测试

| 库 | 用途 |
|---|---|
| **pytest 8+** | 主框架 |
| **pytest-asyncio** | 异步测试 |
| **pytest-mock** | mock 简化 |
| **respx** | httpx mock |
| **coverage** | 覆盖率 |
| **freezegun** | 时间冻结（审计/过期测试） |
| **factory-boy** | 测试数据 |

### 2.8 质量工具

| 库 | 用途 |
|---|---|
| **ruff 0.4+** | lint + format（替代 flake8/black/isort） |
| **mypy 1.10+** | 类型检查 |
| **pre-commit** | hook 编排 |

---

## 三、目录结构

```
~/claude-workspace/SDLC/                  # 项目根（即将 init）
├── pyproject.toml                         # uv 项目元数据
├── uv.lock                                # 锁定依赖
├── README.md                              # 用户文档
├── CHANGELOG.md                           # 由 git-cliff 自动生成
├── .python-version                        # 3.11
├── .gitignore
├── .pre-commit-config.yaml
├── .ruff.toml
├── mypy.ini
├── sdlc.py                                # 入口（python -m sdlc 等价）
├── sdlc/                                  # 主包
│   ├── __init__.py
│   ├── __main__.py                        # python -m sdlc
│   ├── py.typed                           # 标记为类型完整
│   ├── cli/                               # 命令
│   ├── core/                              # 引擎
│   ├── kb/                                # KB
│   ├── llm/                               # LLM
│   ├── subagent/                          # Subagent
│   ├── adapter/                           # Adapter 加载
│   ├── stage/                             # Stage 加载
│   ├── profile/                           # Profile
│   ├── rule/                              # 规则
│   ├── gate/                              # Gate
│   ├── audit/                             # 审计
│   ├── state/                             # 状态
│   ├── integrations/                      # 外部
│   └── utils/                             # 工具
├── stages/                                # 默认 stage 库
├── adapters/                              # 默认 adapter 库
├── profiles/                              # 默认 profile 库
├── rules/                                 # 默认全局规则
├── prompts/                               # Subagent prompt 模板
├── gates/                                 # 默认 gate 库
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── fixtures/
│   └── golden/                            # golden file 对比
├── examples/                              # 示例项目
├── scripts/                               # 开发脚本
└── docs/                                  # mkdocs 源码
    └── design/                            # 本目录
```

---

## 四、pyproject.toml 关键字段

```toml
[project]
name = "sdlc"
version = "0.1.0"
description = "AI 驱动的全流程 SDLC 编排工具"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "duanluyao1" }]

dependencies = [
  "click>=8.1",
  "rich>=13",
  "pydantic>=2.6",
  "ruamel.yaml>=0.18",
  "jinja2>=3.1",
  "httpx>=0.27",
  "anthropic>=0.34",
  "openai>=1.30",
  "tenacity>=8.2",
  "mcp>=0.5",
  "gitpython>=3.1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8",
  "pytest-asyncio>=0.23",
  "pytest-mock>=3.12",
  "respx>=0.21",
  "coverage>=7.4",
  "freezegun>=1.5",
  "factory-boy>=3.3",
  "ruff>=0.4",
  "mypy>=1.10",
  "pre-commit>=3.7",
  "git-cliff>=2.0",
  "mkdocs-material>=9.5",
]

[project.scripts]
sdlc = "sdlc.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "PT", "RET", "SIM", "TCH"]

[tool.mypy]
strict = true
python_version = "3.11"
warn_unused_ignores = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra -q --strict-markers"
markers = [
  "e2e: 端到端测试",
  "integration: 集成测试",
  "slow: 慢测试（>5s）",
  "llm: 需 LLM API key",
]
```

---

## 五、为什么不选其他语言

| 语言 | 否决理由 |
|---|---|
| **Go** | 编译/分发友好但：① 生态对 YAML/模板弱；② 调 LLM SDK 简陋；③ Prompt 渲染/AI agent 框架几乎全 Python；④ 本工具是 orchestrator 不是 service，性能瓶颈在 IO 而非 CPU |
| **Node/TS** | 异步 OK 但：① 类型系统对 schema 弱（zod 偏弱）；② LLM 生态不如 Python；③ 团队认知成本 |
| **Rust** | 性能最好但：① 开发速度 5-10x 慢；② AI 生态为零；③ 招人难 |
| **Shell** | 显然不行（复杂逻辑） |

**结论**：Python 是 AI orchestration 的事实标准，本工具与 LangChain/AutoGen/CrewAI 同一生态，长期受益。

---

## 六、Python 版本特性依赖

| 特性 | 用于 |
|---|---|
| `tomllib`（3.11） | 读 pyproject.toml |
| `StrEnum`（3.11） | 枚举类型 |
| `ExceptionGroup`（3.11） | 多异常聚合（LLM 批量失败时） |
| `typing.Self`（3.11） | 链式 API |
| `asyncio.TaskGroup`（3.11） | 并发 stage 错误聚合 |
| `match`（3.10） | 分支匹配 |

**最低 3.11**，3.12 已发布但部分库兼容滞后，保守选 3.11。

---

## 七、性能与体积

- 启动时间：< 200ms（本地命令）/ < 1s（首次 LLM 调用前）
- 内存：典型 50-100MB，LLM 流式时 200MB
- 安装包大小：~25MB（wheel）
- 冷启动 LLM：2-5s（API latency），缓存命中 < 50ms

---

## 八、安全依赖

- 0 个 transitive 风险高依赖
- 所有 CLI 命令无提权要求
- LLM API key 走 keyring / 环境变量，不写文件
- 用户项目只读为主，写入走白名单路径（`doc/kb/`, `.sdlc/`, `audit.log`）

---

## 九、版本

- v1.0 (2026-06-05): 初版，对应 prd/ v2.2
