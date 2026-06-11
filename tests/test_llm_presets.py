"""Tests for LLM provider presets."""

from sdlc.llm.presets import ProviderPreset, get_preset, list_presets


def test_list_presets_returns_all():
    presets = list_presets()
    assert len(presets) == 8  # deepseek, qwen, moonshot, glm, ollama, siliconflow, openai, anthropic


def test_list_presets_returns_copies():
    p1 = list_presets()
    p2 = list_presets()
    assert p1 is not p2
    assert p1 == p2


def test_get_preset_valid_ids():
    expected_ids = ["deepseek", "qwen", "moonshot", "glm", "ollama", "siliconflow", "openai", "anthropic"]
    for pid in expected_ids:
        preset = get_preset(pid)
        assert preset is not None, f"Preset '{pid}' not found"
        assert preset.id == pid


def test_get_preset_invalid_id():
    assert get_preset("nonexistent") is None
    assert get_preset("") is None


def test_deepseek_preset_fields():
    p = get_preset("deepseek")
    assert p is not None
    assert p.name == "DeepSeek"
    assert p.base_url == "https://api.deepseek.com/v1"
    assert p.api_key_env == "DEEPSEEK_API_KEY"
    assert p.default_model == "deepseek-chat"
    assert p.provider_type == "openai-compatible"


def test_qwen_preset_fields():
    p = get_preset("qwen")
    assert p is not None
    assert p.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert p.api_key_env == "DASHSCOPE_API_KEY"
    assert p.default_model == "qwen-plus"


def test_moonshot_preset_fields():
    p = get_preset("moonshot")
    assert p is not None
    assert p.base_url == "https://api.moonshot.cn/v1"
    assert p.api_key_env == "MOONSHOT_API_KEY"
    assert p.default_model == "moonshot-v1-8k"


def test_glm_preset_fields():
    p = get_preset("glm")
    assert p is not None
    assert p.base_url == "https://open.bigmodel.cn/api/paas/v4"
    assert p.api_key_env == "GLM_API_KEY"
    assert p.default_model == "glm-4"


def test_ollama_preset_fields():
    p = get_preset("ollama")
    assert p is not None
    assert p.base_url == "http://localhost:11434/v1"
    assert p.api_key_env == ""  # Ollama needs no API key
    assert p.default_model == "llama3"


def test_siliconflow_preset_fields():
    p = get_preset("siliconflow")
    assert p is not None
    assert p.base_url == "https://api.siliconflow.cn/v1"
    assert p.api_key_env == "SILICONFLOW_API_KEY"
    assert p.default_model == "Qwen/Qwen2.5-72B-Instruct"


def test_openai_preset_fields():
    p = get_preset("openai")
    assert p is not None
    assert p.provider_type == "openai"
    assert p.base_url == "https://api.openai.com/v1"
    assert p.api_key_env == "OPENAI_API_KEY"
    assert p.default_model == "gpt-4o"


def test_anthropic_preset_fields():
    p = get_preset("anthropic")
    assert p is not None
    assert p.provider_type == "anthropic"
    assert p.api_key_env == "ANTHROPIC_API_KEY"
    assert p.default_model == "claude-sonnet-4-20250514"


def test_preset_is_frozen():
    p = get_preset("deepseek")
    assert p is not None
    # ProviderPreset is a frozen dataclass, attempting to set should raise
    try:
        p.id = "changed"  # type: ignore[misc]
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass
