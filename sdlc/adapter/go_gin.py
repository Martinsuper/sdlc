from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

GO_GIN_ADAPTER = AdapterDef(
    id="go-gin",
    name="Go Gin",
    version="1.0",
    detect_patterns=[
        {"glob": "**/go.mod", "contains": "gin-gonic/gin"},
    ],
    components=[
        ComponentDef(id="gin-router", type="web", detect="gin.Engine", enforce=True),
        ComponentDef(id="gin-middleware", type="middleware", detect="gin.HandlerFunc", enforce=True),
        ComponentDef(id="gorm", type="db", detect="gorm.Open", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["go-must"],
    required_kb=["rules/go-must.yaml"],
)


def register_go_gin(registry: AdapterRegistry) -> None:
    registry.register(GO_GIN_ADAPTER)
