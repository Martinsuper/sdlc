from pathlib import Path

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key_env: str = "ANTHROPIC_API_KEY"
    base_url: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: float = 120.0
    max_cost_usd: float = 5.0
    # Fallback provider configuration
    fallback_provider: str | None = None
    fallback_model: str | None = None
    fallback_base_url: str | None = None
    fallback_api_key_env: str | None = None


class ProfileConfig(BaseModel):
    auto_detect: bool = True
    default: str = "new-feature"


class SdlcConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    profile: ProfileConfig = Field(default_factory=ProfileConfig)
    log_level: str = "INFO"
    cache_enabled: bool = True
    cache_dir: Path | None = None
    audit_enabled: bool = True
    no_color: bool = False
