from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key_env: str = "ANTHROPIC_API_KEY"
    base_url: str | None = None
    max_tokens: int = Field(gt=0, default=8192)
    temperature: float | None = Field(default=0.7, ge=0.0, le=2.0)
    timeout: float = Field(gt=0, default=120.0)
    max_cost_usd: float = Field(ge=0, default=5.0)
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
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cache_enabled: bool = True
    cache_dir: Path | None = None
    audit_enabled: bool = True
    no_color: bool = False

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: str) -> str:
        """Accept case-insensitive log level strings."""
        if isinstance(v, str):
            v_upper = v.upper()
            valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
            if v_upper in valid:
                return v_upper
            raise ValueError(
                f"log_level must be one of {sorted(valid)}, got {v!r}"
            )
        return v
