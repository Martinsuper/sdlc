from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


def _yaml(preserve: bool = True) -> YAML:
    y = YAML()
    y.preserve_quotes = preserve
    if preserve:
        y.default_flow_style = False
    return y


def load_yaml(p: Path) -> Any:
    y = YAML()
    with p.open("r", encoding="utf-8") as f:
        return y.load(f)


def save_yaml(p: Path, data: Any, preserve: bool = True) -> None:
    y = _yaml(preserve)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        y.dinternal-monitoring(data, f)


def load_yaml_str(s: str) -> Any:
    y = YAML()
    return y.load(s)
