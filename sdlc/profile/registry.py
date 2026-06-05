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

    def match_score(self, profile: ProfileDef, entry_kind: str, **context: Any) -> float:
        """Score how well a profile matches the given entry_kind and context.

        Returns a float between 0.0 and 1.0.  Weights:
          - entry kind match:   0.40
          - tech stack match:   0.30
          - severity alignment: 0.15
          - keyword match:      0.15
        """
        score = 0.0

        # Entry kind match (weight 0.4)
        if entry_kind in profile.entry_kinds:
            score += 0.4

        # Tech stack match (weight 0.3)
        tech_stack = context.get("tech_stack", [])
        if tech_stack and any(t in str(profile.base_stages) for t in tech_stack):
            score += 0.3

        # Severity alignment (weight 0.15)
        severity = context.get("severity", "P2")
        if severity == profile.severity:
            score += 0.15

        # Keyword match (weight 0.15)
        keywords = context.get("keywords", [])
        profile_text = f"{profile.name} {profile.id} {' '.join(profile.entry_kinds)}".lower()
        if keywords and any(kw.lower() in profile_text for kw in keywords):
            score += 0.15

        return min(score, 1.0)

    def resolve(self, entry_kind: str, **context: Any) -> ProfileDef:
        """Return the best-matching profile for *entry_kind*, using multi-factor scoring."""
        best_profile: ProfileDef | None = None
        best_score = -1.0
        for profile in self._profiles.values():
            score = self.match_score(profile, entry_kind, **context)
            if score > best_score:
                best_score = score
                best_profile = profile
        if best_profile:
            return best_profile
        return self.get("new-feature")  # fallback

    def resolve_all(self, entry_kind: str, **context: Any) -> list[tuple[ProfileDef, float]]:
        """Return all profiles ranked by match score (descending).

        Each element is a ``(profile, score)`` tuple.
        """
        scored = [(p, self.match_score(p, entry_kind, **context)) for p in self._profiles.values()]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored

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
