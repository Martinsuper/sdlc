from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

GO_KRATOS_ADAPTER = AdapterDef(
    id="go-kratos",
    name="Go Kratos",
    version="1.0",
    detect_patterns=[
        {"glob": "**/go.mod", "contains": "go-kratos/kratos"},
    ],
    components=[
        ComponentDef(id="kratos-proto", type="proto", detect="proto", enforce=True),
        ComponentDef(id="kratos-wire", type="di", detect="wire.Build", enforce=True),
        ComponentDef(id="kratos-config", type="config", detect="conf.Load", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["go-must"],
    required_kb=["rules/go-must.yaml"],
)


def register_go_kratos(registry: AdapterRegistry) -> None:
    registry.register(GO_KRATOS_ADAPTER)
