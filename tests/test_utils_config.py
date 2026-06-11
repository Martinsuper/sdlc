from sdlc.utils.config import LLMConfig, ProfileConfig, SdlcConfig


def test_sdlc_config_defaults():
    cfg = SdlcConfig()
    assert cfg.log_level == "INFO"
    assert cfg.cache_enabled is True
    assert cfg.audit_enabled is True
    assert cfg.no_color is False
    assert cfg.cache_dir is None


def test_llm_config_default_provider():
    llm = LLMConfig()
    assert llm.provider == "anthropic"
    assert llm.model == "claude-sonnet-4-20250514"
    assert llm.api_key_env == "ANTHROPIC_API_KEY"
    assert llm.base_url is None
    assert llm.max_tokens == 8192
    assert llm.temperature == 0.7
    assert llm.timeout == 120.0
    assert llm.max_cost_usd == 5.0


def test_sdlc_config_from_dict_override():
    cfg = SdlcConfig(log_level="DEBUG", cache_enabled=False, no_color=True)
    assert cfg.log_level == "DEBUG"
    assert cfg.cache_enabled is False
    assert cfg.no_color is True
    assert cfg.llm.provider == "anthropic"


def test_nested_field_override():
    cfg = SdlcConfig(llm=LLMConfig(provider="openai", model="gpt-4o"))
    assert cfg.llm.provider == "openai"
    assert cfg.llm.model == "gpt-4o"
    assert cfg.llm.api_key_env == "ANTHROPIC_API_KEY"


def test_profile_config_defaults():
    p = ProfileConfig()
    assert p.auto_detect is True
    assert p.default == "new-feature"


def test_sdlc_config_nested_dict_construction():
    cfg = SdlcConfig(
        **{
            "llm": {"provider": "openai", "model": "gpt-4o", "api_key_env": "OPENAI_API_KEY"},
            "profile": {"auto_detect": False, "default": "bugfix"},
            "log_level": "WARNING",
        }
    )
    assert cfg.llm.provider == "openai"
    assert cfg.llm.model == "gpt-4o"
    assert cfg.llm.api_key_env == "OPENAI_API_KEY"
    assert cfg.profile.auto_detect is False
    assert cfg.profile.default == "bugfix"
    assert cfg.log_level == "WARNING"
