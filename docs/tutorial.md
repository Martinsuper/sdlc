# SDLC 使用教程

> AI 驱动的全生命周期软件开发编排工具 —— 从需求到上线的完整自动化

---

## 目录

1. [安装与验证](#1-安装与验证)
2. [配置 LLM 模型](#2-配置-llm-模型)
3. [初始化项目](#3-初始化项目)
4. [运行 Pipeline](#4-运行-pipeline)
5. [查看状态与追踪](#5-查看状态与追踪)
6. [浏览项目资源](#6-浏览项目资源)
7. [规则管理](#7-规则管理)
8. [知识库管理](#8-知识库管理)
9. [配置管理](#9-配置管理)
10. [Python API](#10-python-api)
11. [完整工作流示例](#11-完整工作流示例)

---

## 1. 安装与验证

### 安装

```bash
# 推荐：使用 uv 安装
uv tool install -e .

# 或使用 pip
pip install -e .
```

### 验证安装

```bash
# 查看版本
sdlc version
# 输出: sdlc 1.0.0

# 运行环境诊断
sdlc doctor
# ✓ Python >= 3.11
# ✓ uv installed
# ✓ ~/.sdlc exists
# ✓ Disk space >= 1GB
```

---

## 2. 配置 LLM 模型

SDLC 支持所有 OpenAI 兼容的大模型 API。配置后所有 AI 功能（需求分析、代码生成、测试、审查等）都会使用该模型。

### 方式一：使用预置模板（一键配置）

```bash
# DeepSeek
sdlc config set llm.provider deepseek
sdlc config set llm.api_key_env DEEPSEEK_API_KEY
export DEEPSEEK_API_KEY="sk-..."

# 通义千问
sdlc config set llm.provider qwen
sdlc config set llm.api_key_env DASHSCOPE_API_KEY
export DASHSCOPE_API_KEY="sk-..."

# Moonshot (Kimi)
sdlc config set llm.provider moonshot
sdlc config set llm.api_key_env MOONSHOT_API_KEY
export MOONSHOT_API_KEY="sk-..."

# GLM (智谱)
sdlc config set llm.provider glm
sdlc config set llm.api_key_env GLM_API_KEY
export GLM_API_KEY="..."

# SiliconFlow
sdlc config set llm.provider siliconflow
sdlc config set llm.api_key_env SILICONFLOW_API_KEY
export SILICONFLOW_API_KEY="sk-..."

# Ollama 本地模型
sdlc config set llm.provider ollama
export OLLAMA_API_KEY="ollama"
```

### 方式二：自定义 OpenAI 兼容端点

适用于本地代理（如 one-api、new-api、vLLM、LiteLLM 等）：

```bash
sdlc config set llm.provider openai-compatible
sdlc config set llm.base_url http://localhost:4000/v1
sdlc config set llm.model glm-5.1
sdlc config set llm.api_key_env LOCAL_LLM_API_KEY
export LOCAL_LLM_API_KEY="sk-local"
```

### 方式三：YAML 配置文件

编辑 `~/.sdlc/config.yaml`（用户级）或 `.sdlc/config.yaml`（项目级）：

```yaml
llm:
  provider: openai-compatible
  base_url: http://localhost:4000/v1
  model: glm-5.1
  api_key_env: LOCAL_LLM_API_KEY
  max_tokens: 4096
  temperature: 0.7
  max_cost_usd: 5.0
  # 可选：配置 fallback，主模型失败时自动切换
  fallback_provider: anthropic
  fallback_model: claude-sonnet-4-20250514
  fallback_api_key_env: ANTHROPIC_API_KEY
```

### 验证 LLM 连通性

```bash
# 测试当前配置的 LLM
sdlc llm test

# 查看所有预置模板
sdlc llm presets

# 查看当前 LLM 配置
sdlc llm list
```

### 支持的预置模板

| 预设 ID | 名称 | 默认模型 | 端点 |
|---------|------|---------|------|
| `deepseek` | DeepSeek | deepseek-chat | api.deepseek.com/v1 |
| `qwen` | 通义千问 | qwen-plus | dashscope.aliyuncs.com |
| `moonshot` | Moonshot | moonshot-v1-8k | api.moonshot.cn/v1 |
| `glm` | GLM (智谱) | glm-4 | open.bigmodel.cn |
| `ollama` | Ollama 本地 | llama3 | localhost:11434/v1 |
| `siliconflow` | SiliconFlow | Qwen2.5-72B | api.siliconflow.cn/v1 |
| `openai` | OpenAI | gpt-4o | api.openai.com/v1 |
| `anthropic` | Anthropic | claude-sonnet-4 | (原生 SDK) |

### 切换模型

随时可以切换不同模型，无需重启：

```bash
# 切换到 kimi
sdlc config set llm.model kimi-k2.6

# 切换到 gpt-5
sdlc config set llm.model gpt-5.3-codex

# 切换到本地模型
sdlc config set llm.model llama3
```

---

## 3. 初始化项目

```bash
cd /path/to/your/project
sdlc init
```

`init` 自动完成：
1. **扫描项目** — 7 阶段 KB Scanner 分析代码结构
2. **检测技术栈** — 自动识别 Python/Java/Node/Go/Rust/Mobile/Infra
3. **匹配适配器** — 从 18 个适配器中选出最匹配的
4. **生成知识库** — 输出到 `doc/kb/` 目录
5. **创建配置** — 生成 `.sdlc/` 目录和默认配置

### 初始化输出示例

```
✓ Project scanned: 47 files analyzed
✓ Tech stack detected: Python / FastAPI
✓ Adapter matched: python-fastapi
✓ KB generated: doc/kb/ (8 files)
✓ Config created: .sdlc/config.yaml
```

### 项目结构

初始化后项目会新增：

```
your-project/
├── .sdlc/
│   └── config.yaml          # 项目级配置
└── doc/
    └── kb/                   # 知识库
        ├── architecture/
        │   └── component-catalog.md
        ├── api/
        │   └── endpoint-catalog.md
        ├── data/
        │   └── schema-catalog.md
        └── memory/           # L2 自动更新的学习记录
```

---

## 4. 运行 Pipeline

### 基本用法

用自然语言描述需求，SDLC 会自动编排完整流水线：

```bash
sdlc run "Add user authentication with JWT tokens"
```

### Pipeline 执行流程

```
输入 "Add user auth with JWT"
     │
     ▼
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  Entry Detect │───▶│Profile Match │───▶│Pipeline Build│
│  (feature)    │    │(new-feature) │    │(8 stages)    │
└─────────────┘    └──────────────┘    └──────────────┘
                                               │
     ┌─────────────────────────────────────────┘
     ▼
┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐
│ clarify │─▶│ design  │─▶│impl-back │─▶│unit-test │
└────┬────┘  └────┬────┘  └────┬─────┘  └────┬─────┘
     │            │            │              │
     ▼            ▼            ▼              ▼
  [Gate G1]   [Gate G10]   [Gate G6]    [Gate G7]
     │            │            │              │
     └────────────┴────────────┴──────────────┘
                        │
                        ▼
              ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌────────────┐
              │   cr    │─▶│package  │─▶│ deploy   │─▶│monitor-    │
              │(代码审查)│  │(打包)   │  │(部署)    │  │setup(监控) │
              └─────────┘  └─────────┘  └──────────┘  └────────────┘
```

每个阶段：
- AI 子代理执行具体任务
- Gate 质量门禁自动检查
- Rule 规则引擎自动执行
- Memory L2 自动记录学习

### 指定工作流 Profile

```bash
# Bug 修复（跳过设计阶段，更快）
sdlc run "Fix login timeout on mobile" --profile bug-fix

# 紧急修复（最短路径：需求→实现→测试→部署）
sdlc run "Fix payment gateway crash" --profile hotfix

# 前端功能
sdlc run "Add dashboard charts" --profile frontend

# 全栈功能
sdlc run "Add real-time notification system" --profile full-stack

# 重构
sdlc run "Refactor database access layer" --profile refactor
```

### 14 个内置 Profile

| Profile | 适用场景 | Stage 数 | 关键路径 |
|---------|---------|----------|---------|
| `new-feature` | 新功能开发 | 8 | clarify→design→impl→test→cr→package→deploy→monitor |
| `bug-fix` | Bug 修复 | 6 | clarify→impl→test→cr→package→deploy |
| `hotfix` | 紧急修复 | 4 | clarify→impl→test→deploy |
| `refactor` | 代码重构 | 7 | clarify→design→impl→test→cr→package→deploy |
| `test` | 补充测试 | 3 | clarify→test→cr |
| `infra` | 基础设施 | 6 | clarify→design→impl→test→deploy→monitor |
| `release` | 版本发布 | 4 | clarify→package→deploy→monitor |
| `revert` | 回滚 | 2 | clarify→deploy |
| `doc` | 文档 | 1 | clarify |
| `migrate` | 技术迁移 | 6 | clarify→design→impl→test→cr→deploy |
| `audit` | 安全审计 | 2 | clarify→cr |
| `idea` | 创意评估 | 1 | clarify |
| `frontend` | 前端功能 | 6 | clarify→design→impl-frontend→test→cr→deploy |
| `full-stack` | 全栈功能 | 9 | clarify→design→impl→impl-frontend→test→cr→package→deploy→monitor |

### 高级选项

```bash
# 指定适配器
sdlc run "Add REST endpoint" --adapter python-fastapi

# 指定入口类型（跳过自动检测）
sdlc run "Fix crash" --entry-kind bug

# 只运行特定阶段
sdlc run "Refactor API" --stages clarify,design

# 跳过某些阶段
sdlc run "Add feature" --skip-stages monitor-setup

# 设置严重级别
sdlc run "Security fix" --severity P0

# 设置成本上限（美元）
sdlc run "Big refactor" --max-cost 2.0

# 并发执行（最多 3 个 stage 并行）
sdlc run "Add feature" --concurrency 3

# 跳过质量门禁
sdlc run "Quick fix" --gate-mode skip

# 预览模式（不实际执行）
sdlc run "Add feature" --dry-run

# 失败后继续
sdlc run "Add feature" --resume-on-fail

# 跳过部署和监控
sdlc run "Add feature" --no-deploy --no-monitor

# 添加自定义标签
sdlc run "Add feature" --tag sprint=23 --tag team=backend
```

### 12 个内置 Stage

| Stage | 名称 | 类别 | 子代理 | 超时 |
|-------|------|------|--------|------|
| `s-clarify` | 需求澄清 | requirement | SA-1 | 30min |
| `s-design` | 架构设计 | design | SA-2 | 60min |
| `s-impl-backend` | 后端实现 | impl | SA-3 | 120min |
| `s-impl-frontend` | 前端实现 | impl | SA-4 | 120min |
| `s-unit-test` | 单元测试 | test | SA-5 | 60min |
| `s-cr` | 代码审查 | review | SA-6 | 30min |
| `s-security-scan` | 安全扫描 | security | SA-7 | 30min |
| `s-package` | 打包 | package | SA-8 | 30min |
| `s-deploy` | 部署 | deploy | SA-9 | 60min |
| `s-monitor-setup` | 监控配置 | monitor | SA-10 | 30min |
| `s-impact-analysis` | 影响分析 | analysis | SA-2 | 20min |
| `s-docs` | 文档生成 | docs | SA-11 | 30min |

---

## 5. 查看状态与追踪

```bash
# 列出所有 pipeline
sdlc status

# 查看特定 pipeline 详情
sdlc status --pipeline <pipeline-id>

# 详细展示每个 stage 的执行情况
sdlc status --pipeline <pipeline-id> --verbose

# 恢复暂停/失败的 pipeline
sdlc resume <pipeline-id>

# 追踪 pipeline 执行
sdlc trace <pipeline-id>

# 查看统计数据
sdlc stats

# 导出 pipeline 数据
sdlc export --pipeline <pipeline-id> --format json

# 重放 pipeline 执行过程
sdlc replay <pipeline-id>
```

---

## 6. 浏览项目资源

### 适配器（18 个）

```bash
# 列出所有适配器
sdlc adapter list

# 检测当前项目的适配器
sdlc adapter detect
```

| 适配器 | ID | 适用场景 |
|--------|-----|---------|
| DongBoot | `dongboot` | 企业微服务框架 |
| JD Spring Boot | `jd-spring-boot` | Java Spring Boot |
| Python FastAPI | `python-fastapi` | Python 异步 API |
| Python Flask | `python-flask` | Python Web |
| Python Django | `python-django` | Python 全栈 |
| Node NestJS | `node-nestjs` | TypeScript 企业级 |
| Node Express | `node-express` | Node.js Web |
| React | `frontend-react` | React 前端 |
| Vue | `frontend-vue` | Vue 前端 |
| Go Gin | `go-gin` | Go Web |
| Go Kratos | `go-kratos` | Go 微服务 |
| Rust Axum | `rust-axum` | Rust Web |
| Android | `mobile-android` | 安卓应用 |
| iOS | `mobile-ios` | iOS 应用 |
| Flutter | `mobile-flutter` | 跨端应用 |
| Terraform | `infra-terraform` | 基础设施 |
| Spark | `data-spark` | 数据工程 |
| No Tech | `no-tech` | 无特定技术栈 |

### 工作流 Profile（14 个）

```bash
sdlc profile list
```

### Stage（12 个）

```bash
sdlc stage list
```

### 子代理（11 个）

```bash
sdlc agent list
```

| 代理 | 角色 | 用途 |
|------|------|------|
| SA-1 | 需求分析师 | 需求澄清、拆解 |
| SA-2 | 架构师 | 设计、影响分析 |
| SA-3 | 后端工程师 | 后端代码实现 |
| SA-4 | 前端工程师 | 前端代码实现 |
| SA-5 | 测试工程师 | 单元测试 |
| SA-6 | 代码审查员 | CR 审查 |
| SA-7 | 安全工程师 | 安全扫描 |
| SA-8 | 打包工程师 | 构建、打包 |
| SA-9 | 运维工程师 | 部署 |
| SA-10 | SRE | 监控配置 |
| SA-11 | 文档工程师 | 文档生成 |

---

## 7. 规则管理

SDLC 内置 548 条规则，覆盖 9 个技术栈，4 种执行器。

```bash
# 列出所有规则
sdlc rule list

# 按类别过滤（security / quality / coding / design / ...）
sdlc rule list --category security

# 按级别过滤（MUST / SHOULD / MAY）
sdlc rule list --level MUST

# 按严重级别过滤
sdlc rule list --severity P0

# 针对特定 stage 检查规则
sdlc rule check --stage s-impl-backend

# 临时禁用规则
sdlc rule disable no-console-log --until 2026-07-01 --reason "Debug sprint"

# 重新启用
sdlc rule enable no-console-log
```

### 规则级别

| 级别 | 含义 | 违反后果 |
|------|------|---------|
| `MUST` | 必须遵守 | **阻断**（Gate 阻止继续） |
| `SHOULD` | 应该遵守 | 警告（不阻断） |
| `MAY` | 建议遵守 | 提示信息 |

### 规则覆盖范围

| 规则集 | 数量 | 覆盖场景 |
|--------|------|---------|
| coding-must | 60 | 通用编码：安全、命名、并发、错误处理 |
| python-must | 65 | Python：类型提示、async、Django/Flask/FastAPI |
| node-must | 60 | Node.js：ESM、Express、NestJS、安全 |
| frontend-must | 65 | 前端：React hooks、Vue、a11y、Web Vitals |
| go-must | 60 | Go：context、error wrapping、interface、generics |
| rust-must | 60 | Rust：lifetime、unsafe、async/tokio、FFI |
| mobile-must | 65 | 移动端：Compose/SwiftUI/Flutter、安全、签名 |
| infra-must | 65 | 基础设施：K8s、Terraform、AWS/GCP/Azure |
| data-must | 48 | 数据：Spark、Kafka、数据质量、GDPR |

### 10 个质量门禁

| Gate | 触发时机 | 评审人 | 阻断条件 |
|------|---------|--------|---------|
| G1 PM Review | s-clarify 后 | PM | 需求不完整 |
| G2 TL Review | s-design 后 | TechLead | 架构问题 |
| G3 Security Gate | s-security-scan 后 | SecOps | 安全漏洞 |
| G4 Deploy Approval | s-deploy 前 | ReleaseManager | 需要审批 |
| G5 Hotfix Emergency | 热修复时 | OnCall | 紧急审批 |
| G6 Code Quality | s-impl-backend 后 | TechLead | MUST 规则违反 |
| G7 Test Coverage | s-unit-test 后 | QA | 覆盖率不足 |
| G8 Release Readiness | s-deploy 后 | ReleaseManager | P0 违规 |
| G9 Compliance | s-design 后 | Compliance | 合规违规 |
| G10 Architecture | s-design 后 | Architect | 架构违规 |

---

## 8. 知识库管理

知识库（KB）是 SDLC 对项目的理解，自动维护。

```bash
# 扫描项目并更新 KB
sdlc kb scan

# 列出 KB 文件
sdlc kb list

# 查看特定 KB 文件详情
sdlc kb show architecture/component-catalog.md
```

### KB 结构

```
doc/kb/
├── architecture/          # 架构知识
│   └── component-catalog.md
├── api/                   # API 知识
│   └── endpoint-catalog.md
├── data/                  # 数据知识
│   └── schema-catalog.md
├── infra/                 # 基础设施知识
├── quality/               # 质量知识
├── security/              # 安全知识
├── operations/            # 运维知识
└── memory/                # L2 自动学习记录
    └── s-clarify-20260605T120000Z.json
```

### Memory L2 自动学习

每次 Pipeline 执行后，SDLC 自动将学习成果写入 `doc/kb/memory/`：
- 规则违反记录
- Gate 决策记录
- 错误信息记录

这些学习数据会在后续 Pipeline 中被读取，避免重复犯错。

---

## 9. 配置管理

### 4 层配置优先级

```
--config path.yaml          ← 最高优先级（单次调用）
.sdlc/config.yaml           ← 项目级
~/.sdlc/config.yaml         ← 用户级
builtin defaults            ← 最低优先级（内置默认）
```

### 常用命令

```bash
# 查看当前配置
sdlc config show

# 获取特定配置值（支持点号路径）
sdlc config get llm.model
sdlc config get llm.base_url

# 设置配置值
sdlc config set llm.model glm-5.1
sdlc config set llm.temperature 0.5
sdlc config set profile.default bug-fix
sdlc config set llm.max_cost_usd 10.0

# 查看配置文件路径
sdlc config path

# 重置所有用户配置
sdlc config reset --confirm
```

### 完整配置参考

```yaml
# ~/.sdlc/config.yaml 或 .sdlc/config.yaml

llm:
  provider: openai-compatible     # anthropic / openai / openai-compatible / 预设ID
  model: glm-5.1                  # 模型名称
  api_key_env: LOCAL_LLM_API_KEY  # API Key 环境变量名
  base_url: http://localhost:4000/v1  # OpenAI 兼容端点
  max_tokens: 4096                # 最大输出 token
  temperature: 0.7                # 温度 (0.0-2.0)
  timeout: 120.0                  # 超时秒数
  max_cost_usd: 5.0              # 单次 Pipeline 成本上限
  # Fallback 配置
  fallback_provider: anthropic    # 主模型失败时的备选
  fallback_model: claude-sonnet-4-20250514
  fallback_base_url: null
  fallback_api_key_env: ANTHROPIC_API_KEY

profile:
  auto_detect: true               # 自动检测入口类型
  default: new-feature            # 默认 Profile

log_level: INFO                   # DEBUG / INFO / WARNING / ERROR
cache_enabled: true               # 启用 LLM 缓存
cache_dir: null                   # 缓存目录（null = 默认）
audit_enabled: true               # 启用审计日志
no_color: false                   # 禁用彩色输出
```

### 环境变量

| 变量 | 用途 |
|------|------|
| `ANTHROPIC_API_KEY` | Anthropic API Key |
| `OPENAI_API_KEY` | OpenAI API Key |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `DASHSCOPE_API_KEY` | 通义千问 API Key |
| `MOONSHOT_API_KEY` | Moonshot API Key |
| `GLM_API_KEY` | 智谱 API Key |
| `SILICONFLOW_API_KEY` | SiliconFlow API Key |
| `OLLAMA_API_KEY` | Ollama API Key（可填任意值） |
| `SDLC_HOME` | 覆盖默认 `~/.sdlc/` 目录 |

---

## 10. Python API

除 CLI 外，SDLC 还提供 Python SDK，方便集成到自动化脚本和 CI/CD 流水线。

### 基本使用

```python
from sdlc import SdlcClient

client = SdlcClient()
```

### 初始化项目

```python
result = client.init(path=".")
print(result)  # {'adapter': 'python-fastapi', 'kb_files': 8, ...}
```

### 运行 Pipeline

```python
# 同步调用
result = client.run("Add user authentication with JWT")
print(result["pipeline_id"])
print(result["status"])
print(result["total_cost_usd"])

# 带选项
result = client.run(
    "Fix login timeout",
    profile="bug-fix",
    adapter="python-fastapi",
    max_cost=2.0,
)
```

### 查询状态

```python
# 列出所有 pipeline
pipelines = client.status()
for p in pipelines:
    print(p.pipeline_id, p.status, p.total_cost_usd)

# 查看特定 pipeline
status = client.status(pipeline_id="abc-123")
```

### 列出资源

```python
# Stage 列表
stages = client.stage_list()

# Rule 列表（按类别过滤）
security_rules = client.rule_list(category="security")
must_rules = client.rule_list(level="MUST")

# KB 文件列表
kb = client.kb_list()
```

### 诊断

```python
checks = client.doctor()
for check in checks:
    print(check.name, check.status, check.message)
```

---

## 11. 完整工作流示例

### 场景：为 FastAPI 项目添加新功能

```bash
# 1. 配置 LLM（首次使用）
sdlc config set llm.provider openai-compatible
sdlc config set llm.base_url http://localhost:4000/v1
sdlc config set llm.model glm-5.1
sdlc config set llm.api_key_env LOCAL_LLM_API_KEY
export LOCAL_LLM_API_KEY="sk-local"

# 2. 验证连通性
sdlc llm test
# ✓ Provider initialized: glm-5.1

# 3. 初始化项目
cd /path/to/my-fastapi-project
sdlc init
# ✓ Tech stack detected: Python / FastAPI
# ✓ Adapter matched: python-fastapi

# 4. 运行完整功能流水线
sdlc run "Add user registration with email verification"
# 自动执行: clarify → design → impl → test → cr → package → deploy → monitor

# 5. 查看执行状态
sdlc status --pipeline <id> --verbose

# 6. 如果失败，恢复执行
sdlc resume <pipeline-id>
```

### 场景：紧急 Bug 修复

```bash
# 使用 hotfix profile（最短路径：4个stage）
sdlc run "Fix payment gateway timeout on production" \
  --profile hotfix \
  --severity P0 \
  --max-cost 1.0
```

### 场景：前端功能开发

```bash
sdlc run "Add dashboard with real-time charts" \
  --profile frontend \
  --adapter frontend-react
```

### 场景：代码审查

```bash
# 只运行审查阶段
sdlc run "Review the authentication module" \
  --profile audit \
  --stages clarify,cr
```

### 场景：使用 Python API 自动化

```python
from sdlc import SdlcClient

client = SdlcClient()

# 批量处理 bug 列表
bugs = [
    "Fix memory leak in worker pool",
    "Fix race condition in cache invalidation",
    "Fix SQL injection in search endpoint",
]

for bug in bugs:
    result = client.run(bug, profile="bug-fix", max_cost=1.0)
    print(f"[{result['pipeline_id']}] {bug}: {result['status']}")
```

### 场景：切换不同模型做对比

```bash
# 用 DeepSeek 实现
sdlc config set llm.provider deepseek
sdlc config set llm.model deepseek-chat
sdlc run "Add rate limiting middleware"

# 切换到 GLM 对比
sdlc config set llm.model glm-5.1
sdlc run "Add rate limiting middleware"

# 切换到 GPT 对比
sdlc config set llm.model gpt-5.3-codex
sdlc run "Add rate limiting middleware"
```

---

## 常见问题

### Q: 本地模型代理如何配置？

如果使用 one-api / new-api / vLLM / LiteLLM 等本地代理：

```bash
sdlc config set llm.provider openai-compatible
sdlc config set llm.base_url http://localhost:4000/v1   # 你的代理地址
sdlc config set llm.model <模型名称>                      # 代理支持的模型名
sdlc config set llm.api_key_env LOCAL_LLM_API_KEY
export LOCAL_LLM_API_KEY="sk-no-key"                    # 本地通常不需要真实 key
```

先 `curl http://localhost:4000/v1/models` 确认可用模型列表。

### Q: 成本如何控制？

```bash
# 设置单次 Pipeline 成本上限
sdlc run "Add feature" --max-cost 2.0

# 或在配置中设置全局上限
sdlc config set llm.max_cost_usd 5.0
```

### Q: 如何跳过不需要的阶段？

```bash
# 跳过部署和监控
sdlc run "Add feature" --no-deploy --no-monitor

# 只运行特定阶段
sdlc run "Design only" --stages clarify,design
```

### Q: 如何恢复失败的 Pipeline？

```bash
sdlc resume <pipeline-id>
```

### Q: 支持哪些语言/框架？

18 个内置适配器覆盖：Python (FastAPI/Flask/Django)、Java (Spring Boot)、Node.js (Express/NestJS)、React、Vue、Go (Gin/Kratos)、Rust (Axum)、Android、iOS、Flutter、Terraform、Spark。
