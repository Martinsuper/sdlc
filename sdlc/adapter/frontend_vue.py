from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

FRONTEND_VUE_ADAPTER = AdapterDef(
    id="frontend-vue",
    name="Vue Frontend",
    version="1.0",
    detect_patterns=[
        {"glob": "**/package.json", "contains": "vue"},
    ],
    components=[
        ComponentDef(id="vue-router", type="routing", detect="vue-router", enforce=True),
        ComponentDef(id="vuex", type="state", detect="createStore", enforce=True),
        ComponentDef(id="axios", type="http", detect="axios", enforce=True),
        ComponentDef(id="vitest", type="testing", detect="vitest", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["frontend-must"],
    required_kb=["rules/frontend-must.yaml"],
)


def register_frontend_vue(registry: AdapterRegistry) -> None:
    registry.register(FRONTEND_VUE_ADAPTER)
