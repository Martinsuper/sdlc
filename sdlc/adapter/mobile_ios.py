from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

MOBILE_IOS_ADAPTER = AdapterDef(
    id="mobile-ios",
    name="iOS Swift",
    version="1.0",
    detect_patterns=[
        {"glob": "**/Package.swift", "contains": ""},
        {"glob": "**/*.xcodeproj", "contains": ""},
    ],
    components=[
        ComponentDef(id="uikit", type="ui", detect="UIViewController", enforce=True),
        ComponentDef(id="alamofire", type="http", detect="Alamofire", enforce=True),
        ComponentDef(id="coredata", type="db", detect="NSManagedObject", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["mobile-must"],
    required_kb=["rules/mobile-must.yaml"],
)


def register_mobile_ios(registry: AdapterRegistry) -> None:
    registry.register(MOBILE_IOS_ADAPTER)
