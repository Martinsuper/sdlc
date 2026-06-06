"""Factory for creating LLM providers from configuration."""
from __future__ import annotations

import os

from sdlc.llm.anthropic_provider import AnthropicProvider
from sdlc.llm.openai_compatible import OpenAICompatibleProvider
from sdlc.llm.openai_provider import OpenAIProvider
from sdlc.llm.presets import ProviderPreset, get_preset
from sdlc.utils.config import LLMConfig
from sdlc.utils.exceptions import SdlcError


class ProviderNotFoundError(SdlcError):
    pass


class ProviderFactory:
    """Create LLM provider instances from configuration or presets."""

    @staticmethod
    def create(config: LLMConfig) -> AnthropicProvider | OpenAIProvider | OpenAICompatibleProvider:
        """Create a provider from LLMConfig.

        Supports:
        - provider="anthropic" -> AnthropicProvider
        - provider="openai" -> OpenAIProvider
        - provider="openai-compatible" -> OpenAICompatibleProvider(base_url=config.base_url)
        - provider=<preset_id> -> lookup preset, create OpenAICompatibleProvider
        """
        provider_type = config.provider.lower().strip()
        api_key = os.environ.get(config.api_key_env, "")

        # Check if it's a preset ID
        preset = get_preset(provider_type)
        if preset:
            return ProviderFactory._from_preset(preset, api_key or "sk-placeholder", config.timeout)

        # Standard providers
        if provider_type == "anthropic":
            return AnthropicProvider(api_key=api_key or "sk-placeholder", timeout=int(config.timeout))
        elif provider_type == "openai":
            return OpenAIProvider(api_key=api_key or "sk-placeholder", timeout=int(config.timeout))
        elif provider_type == "openai-compatible":
            if not config.base_url:
                raise ProviderNotFoundError(
                    "openai-compatible provider requires llm.base_url to be set. "
                    "Use 'sdlc config set llm.base_url https://...' or "
                    "'sdlc config set llm.provider <preset_id>'"
                )
            return OpenAICompatibleProvider(
                api_key=api_key or "sk-placeholder",
                base_url=config.base_url,
                timeout=int(config.timeout),
            )
        else:
            # Unknown provider - try as openai-compatible with base_url
            if config.base_url:
                return OpenAICompatibleProvider(
                    api_key=api_key or "sk-placeholder",
                    base_url=config.base_url,
                    timeout=int(config.timeout),
                    provider_name=provider_type,
                )
            raise ProviderNotFoundError(
                f"Unknown provider '{provider_type}'. "
                f"Set llm.base_url to use it as an OpenAI-compatible endpoint, "
                f"or use a preset ID (deepseek, qwen, moonshot, glm, ollama, siliconflow)."
            )

    @staticmethod
    def _from_preset(
        preset: ProviderPreset,
        api_key: str,
        timeout: float = 120.0,
    ) -> AnthropicProvider | OpenAIProvider | OpenAICompatibleProvider:
        """Create a provider from a preset configuration."""
        if preset.provider_type == "anthropic":
            return AnthropicProvider(api_key=api_key, timeout=int(timeout))
        elif preset.provider_type == "openai":
            return OpenAIProvider(api_key=api_key, timeout=int(timeout))
        else:
            return OpenAICompatibleProvider(
                api_key=api_key,
                base_url=preset.base_url,
                timeout=int(timeout),
                provider_name=preset.id,
            )

    @staticmethod
    def create_fallback(config: LLMConfig) -> AnthropicProvider | OpenAIProvider | OpenAICompatibleProvider | None:
        """Create a fallback provider if configured.

        Checks fallback_provider, fallback_base_url, fallback_api_key_env fields.
        If no fallback is configured, tries to create one from the opposite provider.
        """
        fb_provider = getattr(config, "fallback_provider", None)
        fb_model = getattr(config, "fallback_model", None)
        fb_base_url = getattr(config, "fallback_base_url", None)
        fb_key_env = getattr(config, "fallback_api_key_env", None)

        if fb_provider:
            fb_config = LLMConfig(
                provider=fb_provider,
                model=fb_model or "gpt-4o-mini",
                api_key_env=fb_key_env or "OPENAI_API_KEY",
                base_url=fb_base_url,
                timeout=config.timeout,
            )
            try:
                return ProviderFactory.create(fb_config)
            except ProviderNotFoundError:
                return None

        # Auto-fallback: if primary is anthropic, fallback to openai; vice versa
        primary = config.provider.lower()
        if primary == "anthropic":
            openai_key = os.environ.get("OPENAI_API_KEY", "")
            if openai_key:
                return OpenAIProvider(api_key=openai_key, timeout=int(config.timeout))
        elif primary != "openai":
            anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if anthropic_key:
                return AnthropicProvider(api_key=anthropic_key, timeout=int(config.timeout))

        return None
