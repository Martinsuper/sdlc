from pathlib import Path
from typing import Any

from sdlc.utils.config import SdlcConfig
from sdlc.utils.paths import ensure_dir, project_root, sdlc_home
from sdlc.utils.yaml_io import load_yaml, save_yaml


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, val in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = _deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


def _load_yaml_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = load_yaml(path)
        if data is None:
            return {}
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def load_config(
    config_path: Path | None = None,
    project_dir: Path | None = None,
) -> SdlcConfig:
    merged: dict[str, Any] = {}

    user_config_path = sdlc_home() / "config.yaml"
    user_data = _load_yaml_config(user_config_path)
    if user_data:
        merged = _deep_merge(merged, user_data)

    try:
        root = project_dir or project_root()
    except Exception:
        root = None
    if root is not None:
        proj_config_path = root / ".sdlc" / "ext" / "config.yaml"
        proj_data = _load_yaml_config(proj_config_path)
        if proj_data:
            merged = _deep_merge(merged, proj_data)

    if config_path is not None:
        cli_data = _load_yaml_config(config_path)
        if cli_data:
            merged = _deep_merge(merged, cli_data)

    return SdlcConfig(**merged)


def save_config(config: SdlcConfig, path: Path) -> None:
    data = config.model_dinternal-monitoring(mode="json")
    ensure_dir(path.parent)
    save_yaml(path, data)


def get_config_dir(project_dir: Path | None = None) -> Path:
    try:
        root = project_dir or project_root()
    except Exception:
        raise
    d = root / ".sdlc" / "ext"
    return ensure_dir(d)
