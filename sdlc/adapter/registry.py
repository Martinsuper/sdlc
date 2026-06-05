from pathlib import Path

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.utils.exceptions import SdlcError
from sdlc.utils.yaml_io import load_yaml


class AdapterNotFoundError(SdlcError):
    pass


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, AdapterDef] = {}

    def register(self, adapter_def: AdapterDef) -> None:
        self._adapters[adapter_def.id] = adapter_def

    def get(self, adapter_id: str) -> AdapterDef:
        adapter = self._adapters.get(adapter_id)
        if not adapter:
            raise AdapterNotFoundError(f"Adapter '{adapter_id}' not found in registry")
        return adapter

    def list_adapters(self) -> list[AdapterDef]:
        return list(self._adapters.values())

    def has(self, adapter_id: str) -> bool:
        return adapter_id in self._adapters

    def load_from_yaml(self, path: Path) -> int:
        data = load_yaml(path)
        if not data or not isinstance(data, dict):
            return 0
        if "id" in data:
            items = [data]
        else:
            items = data.get("adapters", [])
            if not isinstance(items, list):
                return 0
        count = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            components = []
            for c in item.get("components", []):
                if isinstance(c, dict):
                    components.append(
                        ComponentDef(
                            id=c.get("id", ""),
                            type=c.get("type", ""),
                            detect=c.get("detect", ""),
                            enforce=c.get("enforce", True),
                        )
                    )
            adapter = AdapterDef(
                id=item.get("id", ""),
                name=item.get("name", ""),
                version=item.get("version", "1.0"),
                detect_patterns=item.get("detect_patterns", []),
                components=components,
                enforce_rules=item.get("enforce_rules", True),
                rule_sets=item.get("rule_sets", []),
                required_kb=item.get("required_kb", []),
            )
            if adapter.id:
                self.register(adapter)
                count += 1
        return count
