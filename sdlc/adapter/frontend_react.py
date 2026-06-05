from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

FRONTEND_REACT_ADAPTER = AdapterDef(
    id="frontend-react",
    name="React Frontend",
    version="1.0",
    detect_patterns=[
        {"glob": "**/package.json", "contains": "react"},
    ],
    components=[
        ComponentDef(id="react-router", type="routing", detect="react-router", enforce=True),
        ComponentDef(id="redux", type="state", detect="createStore", enforce=True),
        ComponentDef(id="axios", type="http", detect="axios", enforce=True),
        ComponentDef(id="jest", type="testing", detect="jest", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["frontend-must"],
    required_kb=["rules/frontend-must.yaml"],
)


def register_frontend_react(registry: AdapterRegistry) -> None:
    registry.register(FRONTEND_REACT_ADAPTER)
