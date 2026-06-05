from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

MOBILE_FLUTTER_ADAPTER = AdapterDef(
    id="mobile-flutter",
    name="Flutter",
    version="1.0",
    detect_patterns=[
        {"glob": "**/pubspec.yaml", "contains": "flutter"},
    ],
    components=[
        ComponentDef(id="flutter-bloc", type="state", detect="Bloc", enforce=True),
        ComponentDef(id="dio", type="http", detect="Dio", enforce=True),
        ComponentDef(id="hive", type="db", detect="Hive", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["mobile-must"],
    required_kb=["rules/mobile-must.yaml"],
)


def register_mobile_flutter(registry: AdapterRegistry) -> None:
    registry.register(MOBILE_FLUTTER_ADAPTER)
