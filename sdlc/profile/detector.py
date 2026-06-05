from typing import Any

from sdlc.profile.models import ProfileDef
from sdlc.profile.registry import ProfileRegistry


class ProfileDetector:
    def __init__(self, registry: ProfileRegistry) -> None:
        self.registry = registry

    def detect(self, entry_kind: str, **context: Any) -> ProfileDef:
        return self.registry.resolve(entry_kind, **context)
