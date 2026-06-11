"""Preset configurations for third-party LLM providers."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderPreset:
    """A preset configuration for a third-party LLM provider."""
    id: str
    name: str
    base_url: str
    api_key_env: str
    default_model: str
    provider_type: str = "openai-compatible"
    description: str = ""


PRESETS: list[ProviderPreset] = [
    ProviderPreset(
        id="deepseek",
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        default_model="deepseek-chat",
        description="DeepSeek V3 / R1 推理模型",
    ),
    ProviderPreset(
        id="qwen",
        name="通义千问 (Qwen)",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="DASHSCOPE_API_KEY",
        default_model="qwen-plus",
        description="阿里云通义千问大模型",
    ),
    ProviderPreset(
        id="moonshot",
        name="Moonshot (月之暗面)",
        base_url="https://api.moonshot.cn/v1",
        api_key_env="MOONSHOT_API_KEY",
        default_model="moonshot-v1-8k",
        description="Kimi 大模型",
    ),
    ProviderPreset(
        id="glm",
        name="GLM (智谱)",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key_env="GLM_API_KEY",
        default_model="glm-4",
        description="智谱 ChatGLM 大模型",
    ),
    ProviderPreset(
        id="ollama",
        name="Ollama (本地)",
        base_url="http://localhost:11434/v1",
        api_key_env="",
        default_model="llama3",
        description="Ollama 本地模型服务",
    ),
    ProviderPreset(
        id="siliconflow",
        name="SiliconFlow",
        base_url="https://api.siliconflow.cn/v1",
        api_key_env="SILICONFLOW_API_KEY",
        default_model="Qwen/Qwen2.5-72B-Instruct",
        description="SiliconFlow 模型推理平台",
    ),
    ProviderPreset(
        id="openai",
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4o",
        provider_type="openai",
        description="OpenAI GPT 系列模型",
    ),
    ProviderPreset(
        id="anthropic",
        name="Anthropic",
        base_url="",
        api_key_env="ANTHROPIC_API_KEY",
        default_model="claude-sonnet-4-20250514",
        provider_type="anthropic",
        description="Anthropic Claude 系列模型",
    ),
]


def get_preset(preset_id: str) -> ProviderPreset | None:
    """Get a preset by ID."""
    for p in PRESETS:
        if p.id == preset_id:
            return p
    return None


def list_presets() -> list[ProviderPreset]:
    """List all available presets."""
    return list(PRESETS)
