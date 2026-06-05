"""sdlc.rule.loader — load rules from YAML files."""

from __future__ import annotations

from pathlib import Path

from sdlc.rule.models import Rule
from sdlc.utils.yaml_io import load_yaml


def load_rules_from_yaml(path: Path) -> list[Rule]:
    """Load a list of Rule objects from a YAML file.

    The YAML file should contain a top-level list of rule dicts, e.g.::

        - id: NO-THREAD-SLEEP
          level: MUST
          category: coding
          description: "禁止使用 Thread.sleep"
          enforcer: cr
          pattern: "java\\.lang\\.Thread\\.sleep"
          message: "禁止使用 Thread.sleep"
          action: block
          severity: P1
          applies_to: ["**/*.java"]
          references: []
    """
    data = load_yaml(path)
    if data is None:
        return []
    if not isinstance(data, list):
        raise TypeError(f"Expected a list of rules in {path}, got {type(data).__name__}")
    return [Rule(**item) for item in data]
