# Plan: 支持三方大模型 API

## 问题

当前 LLM 层只硬编码了 Anthropic + OpenAI 两个 provider：
- `MultiLLMClient.__init__` 强制要求 `AnthropicProvider` + `OpenAIProvider`
- `ModelRouter.RULES` 只映射 3 个 Claude 模型
- `LLMConfig.provider` 只有 `"anthropic"` | `"openai"` 两种选择
- `build_deps()` 硬编码了两个 provider 的构造
- `config test-llm` 只检测这两个 provider

用户无法使用 DeepSeek、通义千问、Moonshot、GLM、Ollama 等三方 API。

## 设计方案

核心思路：**OpenAI 兼容协议统一适配**。市面上绝大多数三方模型（DeepSeek、通义、Moonshot、GLM、Ollama、vLLM、LiteLLM 等）都兼容 OpenAI Chat Completions API，只需改 `base_url` + `api_key` 即可接入。

### 架构

```
LLMConfig
  ├── provider: "anthropic" | "openai" | "openai-compatible"  ← 新增
  ├── model: str
  ├── base_url: str | None        ← 已有，将真正生效
  ├── api_key_env: str
  └── ...

MultiLLMClient
  ├── primary: LLMProvider        ← 改为协议类型
  ├── fallback: LLMProvider | None ← 允许为 None
  └── router: ModelRouter

LLMProvider (Protocol)            ← 新增协议
  ├── complete(req) -> CompletionResponse
  ├── stream(req) -> AsyncIterator[str]
  └── model_info(model) -> ModelInfo

OpenAICompatibleProvider          ← 新增
  └── 继承 OpenAIProvider，支持自定义 base_url

ProviderFactory                   ← 新增
  └── 从 LLMConfig 构建 provider 实例

ModelRouter                       ← 改造
  ├── RULES 改为动态（可配置）
  └── route() 根据 provider 类型路由到对应模型
```

### 变更清单

#### 1. 新增 `sdlc/llm/provider_protocol.py`
- 定义 `LLMProvider` Protocol（complete, stream, model_info）

#### 2. 新增 `sdlc/llm/openai_compatible.py`
- `OpenAICompatibleProvider` 继承 `OpenAIProvider`
- 构造函数接受 `base_url` 参数
- 预置常见三方模型定价（DeepSeek、Qwen、Moonshot、GLM 等）
- 支持 `model_info()` 返回正确的定价和上下文窗口

#### 3. 新增 `sdlc/llm/provider_factory.py`
- `ProviderFactory.create(config: LLMConfig) -> LLMProvider`
- 根据 `provider` 字段分派：
  - `"anthropic"` → `AnthropicProvider`
  - `"openai"` → `OpenAIProvider`
  - `"openai-compatible"` → `OpenAICompatibleProvider(base_url=...)`
  - 未知 provider → 尝试作为 OpenAI 兼容处理
- 预置常见三方 provider 配置模板

#### 4. 修改 `sdlc/llm/client.py`
- `MultiLLMClient.__init__` 改为接受 `LLMProvider` 协议类型
- `fallback` 允许为 `None`
- `complete()` 当 fallback 为 None 时不再 fallback
- `ModelRouter.RULES` 改为实例属性，从配置初始化
- 支持 `provider` 字段感知路由

#### 5. 修改 `sdlc/utils/config.py`
- `LLMConfig.provider` 增加 `"openai-compatible"` 选项
- `LLMConfig` 新增字段：
  - `fallback_provider: str | None = None`
  - `fallback_model: str | None = None`
  - `fallback_base_url: str | None = None`
  - `fallback_api_key_env: str | None = None`

#### 6. 修改 `sdlc/cli/deps.py`
- `build_deps()` 使用 `ProviderFactory` 构建 primary 和 fallback provider
- 不再硬编码 AnthropicProvider + OpenAIProvider

#### 7. 修改 `sdlc/cli/config_cmd.py`
- `config test-llm` 检测所有已配置的 provider
- `config show` 展示 provider 和 base_url

#### 8. 新增 `sdlc/llm/presets.py`
- 预置三方模型配置模板：
  - DeepSeek: base_url=`https://api.deepseek.com/v1`
  - 通义千问 Qwen: base_url=`https://dashscope.aliyuncs.com/compatible-mode/v1`
  - Moonshot: base_url=`https://api.moonshot.cn/v1`
  - GLM (智谱): base_url=`https://open.bigmodel.cn/api/paas/v4`
  - Ollama: base_url=`http://localhost:11434/v1`
  - SiliconFlow: base_url=`https://api.siliconflow.cn/v1`
  - 自定义: 任意 base_url

#### 9. 新增 `sdlc/cli/llm_cmd.py`
- `sdlc llm list` — 列出已配置和预置的 provider
- `sdlc llm test` — 测试 LLM 连通性
- `sdlc llm presets` — 列出预置三方模型模板

#### 10. 更新 `sdlc/cli/main.py`
- 注册 `llm` 命令组

#### 11. 更新 `sdlc/llm/__init__.py`
- 导出 `OpenAICompatibleProvider`, `ProviderFactory`, `LLMProvider`

#### 12. 测试
- `tests/test_openai_compatible.py` — 测试 OpenAI 兼容 provider
- `tests/test_provider_factory.py` — 测试工厂方法
- `tests/test_llm_presets.py` — 测试预置模板
- 更新 `tests/test_llm_router.py` — 测试动态路由

### 使用方式

```bash
# 配置 DeepSeek
sdlc config set llm.provider openai-compatible
sdlc config set llm.base_url https://api.deepseek.com/v1
sdlc config set llm.model deepseek-chat
sdlc config set llm.api_key_env DEEPSEEK_API_KEY

# 或配置通义千问
sdlc config set llm.provider openai-compatible
sdlc config set llm.base_url https://dashscope.aliyuncs.com/compatible-mode/v1
sdlc config set llm.model qwen-plus
sdlc config set llm.api_key_env DASHSCOPE_API_KEY

# 或配置 Ollama 本地模型
sdlc config set llm.provider openai-compatible
sdlc config set llm.base_url http://localhost:11434/v1
sdlc config set llm.model llama3
sdlc config set llm.api_key_env OLLAMA_API_KEY  # 可以是任意值

# 测试连通性
sdlc llm test

# 查看预置模板
sdlc llm presets

# YAML 配置示例
```

```yaml
llm:
  provider: openai-compatible
  base_url: https://api.deepseek.com/v1
  model: deepseek-chat
  api_key_env: DEEPSEEK_API_KEY
  max_tokens: 4096
  temperature: 0.7
  max_cost_usd: 5.0
  fallback_provider: anthropic
  fallback_model: claude-sonnet-4-20250514
  fallback_api_key_env: ANTHROPIC_API_KEY
```
