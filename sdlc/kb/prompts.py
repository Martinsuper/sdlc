"""LLM prompt templates for project analysis during ``sdlc init``.

Each template is used in a specific sub-stage of Scanner Stage 6 to
guide the LLM to produce structured, actionable project knowledge.

Template variables (e.g. ``{project_name}``) are filled by
:func:`format_prompt`.  Literal braces that should appear in the
output must be doubled (``{{`` and ``}}``).
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Sub-stage 6a: Project Architecture Analysis
# ---------------------------------------------------------------------------

ARCHITECTURE_ANALYSIS_PROMPT = """\
你是一位资深架构师。请分析以下项目的源码，输出项目架构文档。

## 项目信息
- 名称: {project_name}
- 语言: {language}
- 框架: {framework}
- 构建工具: {build_tool}

## 文件结构
{file_tree}

## 关键源码
{source_snippets}

请严格按以下 Markdown 格式输出（不要添加额外的代码块包裹）：

# 项目架构文档

## 1. 系统概述
简要描述项目的目标和定位（2-3 句话）。

## 2. 架构风格
描述整体架构模式（如分层架构、微服务架构、单体架构、CQRS、六边形架构等），并说明选择原因。

## 3. 模块划分
用表格列出各模块：

| 模块名 | 路径 | 职责 | 关键文件 |
|--------|------|------|---------|

## 4. 层次关系
描述各层之间的调用和依赖关系，例如：Controller → Service → Repository → Database。

## 5. 技术选型
列出关键技术选型及其在项目中的作用。

## 6. 部署架构
如有 Docker/K8s/CI 配置，描述部署方式。如无，说明"未检测到部署配置"。
"""

# ---------------------------------------------------------------------------
# Sub-stage 6b: Entity / Model Extraction
# ---------------------------------------------------------------------------

ENTITY_EXTRACTION_PROMPT = """\
你是一位领域建模专家。请分析以下项目源码，提取核心实体模型。

## 项目架构概述
{architecture_summary}

## Model/Entity 相关源码
{model_sources}

请严格按以下 Markdown 格式输出（不要添加额外的代码块包裹）：

# 实体模型文档

## 1. 领域概述
简要描述核心业务领域（2-3 句话）。

## 2. 实体清单
对每个核心实体，按以下格式描述：

### {{EntityName}}
- **描述**: 一句话描述
- **字段**:

| 字段名 | 类型 | 说明 |
|--------|------|------|

- **关联**: 与其他实体的关系

## 3. 实体关系
用文字描述实体间的关联关系（一对多、多对多、组合、继承等）。

## 4. 值对象
列出重要的值对象定义（如有）。

## 5. 枚举类型
列出关键枚举定义及其取值（如有）。
"""

# ---------------------------------------------------------------------------
# Sub-stage 6c: API Reference Generation
# ---------------------------------------------------------------------------

API_REFERENCE_PROMPT = """\
你是一位 API 文档专家。请分析以下项目源码，生成接口文档。

## 项目架构概述
{architecture_summary}

## API/Controller 相关源码
{api_sources}

请严格按以下 Markdown 格式输出（不要添加额外的代码块包裹）：

# 接口文档

## 1. API 概述
- **接口风格**: REST / RPC / GraphQL / 其他
- **认证方式**: 描述认证机制（如有）
- **基础路径**: 如 /api/v1 等

## 2. 接口列表
按模块/资源分组，对每个接口描述：

### {{ResourceName}}

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|

## 3. 请求格式
对关键接口，描述请求参数和 body 格式：

### {{EndpointName}}
- **请求参数**:

| 参数名 | 位置 | 类型 | 必填 | 说明 |
|--------|------|------|------|------|

- **请求体** (如有):
```json
{{"example": "format"}}
```

## 4. 响应格式
对关键接口，描述响应格式：

### {{EndpointName}}
- **响应体**:
```json
{{"example": "format"}}
```

## 5. 错误码
列出接口错误码定义（如有）：

| 错误码 | HTTP状态码 | 描述 |
|--------|-----------|------|
"""

# ---------------------------------------------------------------------------
# Sub-stage 6d: Business Logic Analysis
# ---------------------------------------------------------------------------

BUSINESS_LOGIC_PROMPT = """\
你是一位业务分析专家。请分析以下项目源码，梳理核心业务逻辑。

## 项目架构概述
{architecture_summary}

## Service/Logic 相关源码
{service_sources}

请严格按以下 Markdown 格式输出（不要添加额外的代码块包裹）：

# 业务逻辑文档

## 1. 核心业务流程
对每个核心业务场景，描述完整处理流程：

### {{BusinessFlowName}}
- **触发条件**: 什么情况下触发此流程
- **处理步骤**:
  1. 步骤一
  2. 步骤二
  3. ...
- **输出结果**: 流程的最终产出

## 2. 数据流向
描述核心数据从输入到输出的完整路径，例如：用户请求 → Controller → Service → Repository → DB → 返回响应。

## 3. 关键算法
描述核心计算逻辑和算法（如有）。对于每个算法：
- **名称**: 算法名
- **用途**: 解决什么问题
- **核心逻辑**: 简要描述算法思路
- **复杂度**: 时间/空间复杂度（如可推断）

## 4. 业务规则
列出重要的业务校验和约束规则：
- 规则1: 描述
- 规则2: 描述

## 5. 外部依赖
描述第三方服务调用和集成点：

| 服务名 | 用途 | 调用方式 | 异常处理 |
|--------|------|---------|---------|
"""

# ---------------------------------------------------------------------------
# Template application helper
# ---------------------------------------------------------------------------

def format_prompt(template: str, **kwargs: str) -> str:
    """Format a prompt template with the given keyword arguments.

    Missing keys are replaced with empty strings instead of raising KeyError.
    Literal braces in the template must be doubled (``{{`` / ``}}``).

    If ``str.format`` fails (e.g. due to unescaped braces in the template),
    falls back to simple ``str.replace`` substitution for known variables.
    """
    # Provide defaults for all known variables
    defaults: dict[str, str] = {
        "project_name": "(unknown)",
        "language": "(unknown)",
        "framework": "(unknown)",
        "build_tool": "(unknown)",
        "file_tree": "(not available)",
        "source_snippets": "(not available)",
        "architecture_summary": "(not available)",
        "model_sources": "(not available)",
        "api_sources": "(not available)",
        "service_sources": "(not available)",
    }
    merged = {**defaults, **kwargs}
    try:
        return template.format(**merged)
    except ValueError as exc:
        import logging
        logging.getLogger(__name__).warning(
            "format_prompt fallback to simple replace: %s", exc,
        )
        result = template
        for key, value in merged.items():
            result = result.replace(f"{{{key}}}", value)
        return result
