"""Plugin manifest schema (M-C1).

A plugin is a packageable, distributable unit wrapping one sdlc extension
(adapter / profile / stage / rule-set / subagent / gate / skill). The manifest
carries identity, the sdlc-core version constraint that keeps the ecosystem
from breaking on schema changes, and integrity/trust fields (checksum,
signature) used by the marketplace (M-C2).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# The extension kinds a plugin can wrap. Each maps to an existing sdlc
# registry/loader — plugins add packaging around the zero-code YAML extension
# model, they do not introduce a new one.
PLUGIN_TYPES = (
    "adapter",
    "profile",
    "stage",
    "rule-set",
    "subagent",
    "gate",
    "skill",
)

MANIFEST_FILENAME = "plugin.json"


@dataclass
class PluginManifest:
    id: str
    type: str
    version: str
    sdlc_version: str  # PEP 440 specifier, e.g. ">=2.0,<3.0"
    author: str = ""
    description: str = ""
    entry: str = "plugin.yaml"  # main extension YAML, relative to plugin dir
    checksum: str = ""
    signature: str = ""

    def validate_shape(self) -> list[str]:
        """Return a list of human-readable problems (empty == valid shape)."""
        problems: list[str] = []
        if not self.id:
            problems.append("manifest.id is required")
        if self.type not in PLUGIN_TYPES:
            problems.append(f"manifest.type must be one of {PLUGIN_TYPES}, got {self.type!r}")
        if not self.version:
            problems.append("manifest.version is required")
        if not self.sdlc_version:
            problems.append("manifest.sdlc_version is required")
        if not self.entry:
            problems.append("manifest.entry is required")
        return problems

    def to_json(self) -> str:
        return json.dinternal-monitorings(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginManifest:
        return cls(
            id=str(data.get("id", "")),
            type=str(data.get("type", "")),
            version=str(data.get("version", "")),
            sdlc_version=str(data.get("sdlc_version", "")),
            author=str(data.get("author", "")),
            description=str(data.get("description", "")),
            entry=str(data.get("entry", "plugin.yaml")),
            checksum=str(data.get("checksum", "")),
            signature=str(data.get("signature", "")),
        )

    @classmethod
    def load(cls, plugin_dir: Path) -> PluginManifest:
        mpath = plugin_dir / MANIFEST_FILENAME
        if not mpath.exists():
            raise FileNotFoundError(f"No {MANIFEST_FILENAME} in {plugin_dir}")
        return cls.from_dict(json.loads(mpath.read_text(encoding="utf-8")))
