"""Tests for ProviderFactory."""

import os
from unittest.mock import patch

import pytest

from sdlc.llm.anthropic_provider import AnthropicProvider
from sdlc.llm.openai_compatible import OpenAICompatibleProvider
from sdlc.llm.openai_provider import OpenAIProvider
from sdlc.llm.provider_factory import ProviderFactory, ProviderNotFoundError
from sdlc.utils.config import LLMConfig


class TestProviderFactoryCreate:
    def test_create_anthropic(self):
        config = LLMConfig(provider="anthropic", model="claude-sonnet-4-20250514")
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, AnthropicProvider)

    def test_create_openai(self):
        config = LLMConfig(provider="openai", model="gpt-4o")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAIProvider)

    def test_create_openai_compatible_with_base_url(self):
        config = LLMConfig(
            provider="openai-compatible",
            model="custom-model",
            base_url="https://custom.api.com/v1",
            api_key_env="CUSTOM_API_KEY",
        )
        with patch.dict(os.environ, {"CUSTOM_API_KEY": "sk-test"}):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAICompatibleProvider)

    def test_create_openai_compatible_without_base_url_raises(self):
        config = LLMConfig(
            provider="openai-compatible",
            model="custom-model",
        )
        with pytest.raises(ProviderNotFoundError, match="openai-compatible provider requires"):
            ProviderFactory.create(config)

    def test_create_with_preset_deepseek(self):
        config = LLMConfig(
            provider="deepseek",
            model="deepseek-chat",
            api_key_env="DEEPSEEK_API_KEY",
        )
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.provider_name == "deepseek"

    def test_create_with_preset_qwen(self):
        config = LLMConfig(
            provider="qwen",
            model="qwen-plus",
            api_key_env="DASHSCOPE_API_KEY",
        )
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-test"}):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.provider_name == "qwen"

    def test_create_with_preset_moonshot(self):
        config = LLMConfig(
            provider="moonshot",
            model="moonshot-v1-8k",
            api_key_env="MOONSHOT_API_KEY",
        )
        with patch.dict(os.environ, {"MOONSHOT_API_KEY": "sk-test"}):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.provider_name == "moonshot"

    def test_create_with_preset_glm(self):
        config = LLMConfig(
            provider="glm",
            model="glm-4",
            api_key_env="GLM_API_KEY",
        )
        with patch.dict(os.environ, {"GLM_API_KEY": "sk-test"}):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.provider_name == "glm"

    def test_create_with_preset_ollama(self):
        config = LLMConfig(
            provider="ollama",
            model="llama3",
            api_key_env="OLLAMA_API_KEY",
        )
        # Ollama has empty api_key_env, so no key needed
        provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.provider_name == "ollama"

    def test_create_with_preset_siliconflow(self):
        config = LLMConfig(
            provider="siliconflow",
            model="Qwen/Qwen2.5-72B-Instruct",
            api_key_env="SILICONFLOW_API_KEY",
        )
        with patch.dict(os.environ, {"SILICONFLOW_API_KEY": "sk-test"}):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.provider_name == "siliconflow"

    def test_create_with_preset_openai(self):
        config = LLMConfig(
            provider="openai",
            model="gpt-4o",
            api_key_env="OPENAI_API_KEY",
        )
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAIProvider)

    def test_create_with_preset_anthropic(self):
        config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            api_key_env="ANTHROPIC_API_KEY",
        )
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, AnthropicProvider)

    def test_create_unknown_provider_with_base_url(self):
        config = LLMConfig(
            provider="my-custom-llm",
            model="my-model",
            base_url="https://my-llm.example.com/v1",
            api_key_env="MY_LLM_API_KEY",
        )
        with patch.dict(os.environ, {"MY_LLM_API_KEY": "sk-test"}):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.provider_name == "my-custom-llm"

    def test_create_unknown_provider_without_base_url_raises(self):
        config = LLMConfig(
            provider="unknown-provider",
            model="some-model",
        )
        with pytest.raises(ProviderNotFoundError, match="Unknown provider"):
            ProviderFactory.create(config)

    def test_create_case_insensitive(self):
        config = LLMConfig(provider="DeepSeek", model="deepseek-chat")
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.provider_name == "deepseek"

    def test_create_with_whitespace(self):
        config = LLMConfig(provider="  deepseek  ", model="deepseek-chat")
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}):
            provider = ProviderFactory.create(config)
        assert isinstance(provider, OpenAICompatibleProvider)


class TestProviderFactoryFallback:
    def test_create_fallback_with_explicit_config(self):
        config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            fallback_provider="openai",
            fallback_model="gpt-4o-mini",
            fallback_api_key_env="OPENAI_API_KEY",
        )
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-openai"}):
            fallback = ProviderFactory.create_fallback(config)
        assert fallback is not None
        assert isinstance(fallback, OpenAIProvider)

    def test_create_fallback_auto_anthropic_to_openai(self):
        config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
        )
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-openai"}):
            fallback = ProviderFactory.create_fallback(config)
        assert fallback is not None
        assert isinstance(fallback, OpenAIProvider)

    def test_create_fallback_auto_no_openai_key(self):
        config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
        )
        with patch.dict(os.environ, {}, clear=True):
            # Ensure OPENAI_API_KEY is not set
            os.environ.pop("OPENAI_API_KEY", None)
            fallback = ProviderFactory.create_fallback(config)
        assert fallback is None

    def test_create_fallback_auto_openai_to_anthropic(self):
        config = LLMConfig(
            provider="deepseek",
            model="deepseek-chat",
        )
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-anthropic"}):
            fallback = ProviderFactory.create_fallback(config)
        assert fallback is not None
        assert isinstance(fallback, AnthropicProvider)

    def test_create_fallback_no_fallback_configured_no_keys(self):
        config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
        )
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            fallback = ProviderFactory.create_fallback(config)
        assert fallback is None

    def test_create_fallback_with_preset_fallback(self):
        config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            fallback_provider="deepseek",
            fallback_model="deepseek-chat",
            fallback_api_key_env="DEEPSEEK_API_KEY",
        )
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test-deepseek"}):
            fallback = ProviderFactory.create_fallback(config)
        assert fallback is not None
        assert isinstance(fallback, OpenAICompatibleProvider)
        assert fallback.provider_name == "deepseek"
