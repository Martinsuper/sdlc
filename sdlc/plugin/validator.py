"""Plugin validation (M-C1).

Checks a plugin directory is well-formed and installable before it is packed or
published: manifest shape, sdlc-core version compatibility, and that the entry
YAML parses and carries the keys its extension type requires. Reuses the real
YAML loader so "parses" means the same thing it does at load time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

from sdlc.plugin.manifest import PluginManifest
from sdlc.utils.yaml_io import load_yaml

# Minimal required top-level keys per plugin type's entry YAML.
_REQUIRED_KEYS: dict[str, tuple[str, ...]] = {
    "adapter": ("id",),
    "profile": ("id", "base_stages"),
    "stage": ("id", "category"),
    "rule-set": ("rules",),
    "subagent": ("id", "role"),
    "gate": ("id", "after_stage"),
    "skill": ("id",),
}


@dataclass
class ValidationReport:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PluginValidator:
    def __init__(self, sdlc_version: str | None = None) -> None:
        # Injectable for tests; defaults to the installed distribution version.
        if sdlc_version is None:
            from importlib.metadata import version

            try:
                sdlc_version = version("sdlc")
            except Exception:
                sdlc_version = "0"
        self.sdlc_version = sdlc_version

    def validate(self, plugin_dir: Path) -> ValidationReport:
        errors: list[str] = []
        warnings: list[str] = []

        try:
            manifest = PluginManifest.load(plugin_dir)
        except FileNotFoundError as e:
            return ValidationReport(ok=False, errors=[str(e)])
        except Exception as e:
            return ValidationReport(ok=False, errors=[f"Cannot read manifest: {e}"])

        errors.extend(manifest.validate_shape())

        # sdlc-core version compatibility (skip if shape already bad).
        if manifest.sdlc_version:
            try:
                spec = SpecifierSet(manifest.sdlc_version)
                if Version(self.sdlc_version) not in spec:
                    warnings.append(
                        f"sdlc {self.sdlc_version} does not satisfy plugin "
                        f"constraint {manifest.sdlc_version!r}"
                    )
            except InvalidSpecifier:
                errors.append(f"Invalid sdlc_version specifier: {manifest.sdlc_version!r}")

        # Entry YAML: exists, parses, has required keys for the type.
        if manifest.entry:
            entry_path = plugin_dir / manifest.entry
            if not entry_path.exists():
                errors.append(f"Entry file not found: {manifest.entry}")
            else:
                data = load_yaml(entry_path)
                if not isinstance(data, dict):
                    errors.append(f"Entry YAML must be a mapping: {manifest.entry}")
                else:
                    for key in _REQUIRED_KEYS.get(manifest.type, ()):
                        if key not in data:
                            errors.append(f"Entry YAML missing required key: {key!r}")

        return ValidationReport(ok=not errors, errors=errors, warnings=warnings)
