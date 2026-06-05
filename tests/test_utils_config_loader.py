from pathlib import Path

from sdlc.utils.config import SdlcConfig
from sdlc.utils.config_loader import (
    _deep_merge,
    _load_yaml_config,
    get_config_dir,
    load_config,
    save_config,
)


def test_load_config_returns_defaults_with_no_files(tmp_dir, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_dir))
    cfg = load_config(project_dir=tmp_dir)
    assert cfg.llm.provider == "anthropic"
    assert cfg.log_level == "INFO"
    assert cfg.cache_enabled is True


def test_load_config_from_config_path(tmp_dir, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_dir))
    config_file = tmp_dir / "custom.yaml"
    config_file.write_text("llm:\n  provider: openai\n  model: gpt-4o\nlog_level: DEBUG\n")
    cfg = load_config(config_path=config_file, project_dir=tmp_dir)
    assert cfg.llm.provider == "openai"
    assert cfg.llm.model == "gpt-4o"
    assert cfg.log_level == "DEBUG"


def test_deep_merge_flat():
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}
    result = _deep_merge(base, override)
    assert result == {"a": 1, "b": 3, "c": 4}


def test_deep_merge_nested():
    base = {"llm": {"provider": "anthropic", "model": "claude"}, "log_level": "INFO"}
    override = {"llm": {"provider": "openai"}, "cache_enabled": False}
    result = _deep_merge(base, override)
    assert result == {
        "llm": {"provider": "openai", "model": "claude"},
        "log_level": "INFO",
        "cache_enabled": False,
    }


def test_deep_merge_override_wins():
    base = {"x": 10}
    override = {"x": 20}
    result = _deep_merge(base, override)
    assert result["x"] == 20


def test_load_yaml_config_missing_file():
    result = _load_yaml_config(Path("/nonexistent/path.yaml"))
    assert result == {}


def test_load_yaml_config_invalid_yaml(tmp_dir):
    bad_file = tmp_dir / "bad.yaml"
    bad_file.write_text(":\n  :\n    - [invalid")
    result = _load_yaml_config(bad_file)
    assert isinstance(result, dict)


def test_save_and_load_roundtrip(tmp_dir, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_dir))
    original = SdlcConfig(
        llm={"provider": "openai", "model": "gpt-4o"},
        log_level="DEBUG",
        cache_enabled=False,
    )
    path = tmp_dir / "roundtrip.yaml"
    save_config(original, path)
    assert path.is_file()
    loaded = load_config(config_path=path, project_dir=tmp_dir)
    assert loaded.llm.provider == "openai"
    assert loaded.llm.model == "gpt-4o"
    assert loaded.log_level == "DEBUG"
    assert loaded.cache_enabled is False


def test_load_config_project_level(tmp_dir, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_dir))
    ext_dir = tmp_dir / ".sdlc" / "ext"
    ext_dir.mkdir(parents=True)
    proj_cfg = ext_dir / "config.yaml"
    proj_cfg.write_text("log_level: WARNING\nllm:\n  temperature: 0.3\n")
    cfg = load_config(project_dir=tmp_dir)
    assert cfg.log_level == "WARNING"
    assert cfg.llm.temperature == 0.3
    assert cfg.llm.provider == "anthropic"


def test_load_config_priority(tmp_dir, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_dir))
    ext_dir = tmp_dir / ".sdlc" / "ext"
    ext_dir.mkdir(parents=True)
    proj_cfg = ext_dir / "config.yaml"
    proj_cfg.write_text("log_level: WARNING\nllm:\n  provider: openai\n")
    cli_cfg = tmp_dir / "cli.yaml"
    cli_cfg.write_text("log_level: ERROR\n")
    cfg = load_config(config_path=cli_cfg, project_dir=tmp_dir)
    assert cfg.log_level == "ERROR"
    assert cfg.llm.provider == "openai"


def test_get_config_dir(tmp_dir):
    d = get_config_dir(project_dir=tmp_dir)
    assert d == tmp_dir / ".sdlc" / "ext"
    assert d.is_dir()
