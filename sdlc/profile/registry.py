from pathlib import Path
from typing import Any

from sdlc.profile.models import BUILTIN_PROFILES, ProfileDef
from sdlc.utils.exceptions import SdlcError
from sdlc.utils.yaml_io import load_yaml


class ProfileNotFoundError(SdlcError):
    pass


class ProfileRegistry:
    def __init__(self) -> None:
        self._profiles: dict[str, ProfileDef] = {}

    def register(self, profile_def: ProfileDef) -> None:
        self._profiles[profile_def.id] = profile_def

    def get(self, profile_id: str) -> ProfileDef:
        profile = self._profiles.get(profile_id)
        if not profile:
            raise ProfileNotFoundError(f"Profile '{profile_id}' not found in registry")
        return profile

    def list_profiles(self) -> list[ProfileDef]:
        return list(self._profiles.values())

    def has(self, profile_id: str) -> bool:
        return profile_id in self._profiles

    def resolve(self, entry_kind: str, **context: Any) -> ProfileDef:
        for profile in self._profiles.values():
            if entry_kind in profile.entry_kinds:
                return profile
        return self.get("new-feature")

    def load_from_yaml(self, path: Path) -> int:
        data = load_yaml(path)
        if not data or not isinstance(data, dict):
            return 0
        if "id" in data:
            items = [data]
        else:
            items = data.get("profiles", [])
            if not isinstance(items, list):
                return 0
        count = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            profile = ProfileDef(
                id=item.get("id", ""),
                name=item.get("name", ""),
                entry_kinds=item.get("entry_kinds", []),
                base_stages=item.get("base_stages", []),
                skip_stages=item.get("skip_stages", []),
                extra_stages=item.get("extra_stages", []),
                gates=item.get("gates", []),
                subagent_overrides=item.get("subagent_overrides", {}),
                severity=item.get("severity", "P2"),
            )
            if profile.id:
                self.register(profile)
                count += 1
        return count

    def load_builtin_yaml(self) -> int:
        """Load profiles from builtin/profiles/*.yaml."""
        import importlib.util

        spec = importlib.util.find_spec("sdlc.builtin.profiles")
        if not spec or not spec.submodule_search_locations:
            return 0
        builtin_dir = Path(spec.submodule_search_locations[0])
        count = 0
        for f in sorted(builtin_dir.glob("*.yaml")):
            try:
                data = load_yaml(f)
                if data and isinstance(data, dict) and "id" in data:
                    profile = ProfileDef(
                        id=data["id"],
                        name=str(data.get("name", data["id"])),
                        entry_kinds=data.get("entry_kinds", []),
                        base_stages=data.get("base_stages", []),
                        skip_stages=data.get("skip_stages", []),
                        extra_stages=data.get("extra_stages", []),
                        gates=data.get("gates", []),
                        subagent_overrides=data.get("subagent_overrides", {}),
                        severity=data.get("severity", "P2"),
                    )
                    self.register(profile)
                    count += 1
            except Exception:
                pass
        return count


def register_builtins(registry: ProfileRegistry) -> int:
    count = 0
    for item in BUILTIN_PROFILES:
        profile = ProfileDef(**item)
        registry.register(profile)
        count += 1
    # Load from YAML files, overriding hardcoded definitions
    count += registry.load_builtin_yaml()
    return count
