from __future__ import annotations

from sdlc.adapter.models import AdapterDef
from sdlc.adapter.registry import AdapterRegistry

NO_TECH_ADAPTER = AdapterDef(
    id="no-tech",
    name="Generic / No specific tech",
    version="1.0",
    detect_patterns=[],
    components=[],
    enforce_rules=False,
    rule_sets=[],
    required_kb=[],
)


def register_no_tech(registry: AdapterRegistry) -> None:
    registry.register(NO_TECH_ADAPTER)
