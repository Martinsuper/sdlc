from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

NODE_EXPRESS_ADAPTER = AdapterDef(
    id="node-express",
    name="Node Express",
    version="1.0",
    detect_patterns=[
        {"glob": "**/package.json", "contains": "express"},
    ],
    components=[
        ComponentDef(id="express-router", type="web", detect="Router", enforce=True),
        ComponentDef(id="express-middleware", type="middleware", detect="next()", enforce=True),
        ComponentDef(id="body-parser", type="parser", detect="body-parser", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["node-must"],
    required_kb=["rules/node-must.yaml"],
)


def register_node_express(registry: AdapterRegistry) -> None:
    registry.register(NODE_EXPRESS_ADAPTER)
