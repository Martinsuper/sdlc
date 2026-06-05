from pathlib import Path

from sdlc.adapter.models import AdapterDef
from sdlc.adapter.registry import AdapterRegistry


class AdapterDetector:
    def __init__(self, registry: AdapterRegistry) -> None:
        self.registry = registry

    def detect(self, project_root: Path) -> list[AdapterDef]:
        if not project_root.is_dir():
            return []
        matches = []
        for adapter in self.registry.list_adapters():
            if self._matches(adapter, project_root):
                matches.append(adapter)
        return matches

    def _matches(self, adapter: AdapterDef, project_root: Path) -> bool:
        if not adapter.detect_patterns:
            return False
        for pattern in adapter.detect_patterns:
            if self._pattern_matches(pattern, project_root):
                return True
        return False

    def _pattern_matches(self, pattern: dict[str, str], project_root: Path) -> bool:
        glob_str = pattern.get("glob", "")
        contains_str = pattern.get("contains", "")
        if not glob_str:
            return False
        matched_files = list(project_root.glob(glob_str))
        if not matched_files:
            return False
        if not contains_str:
            return True
        for f in matched_files:
            if not f.is_file():
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                if contains_str in content:
                    return True
            except Exception:
                continue
        return False
