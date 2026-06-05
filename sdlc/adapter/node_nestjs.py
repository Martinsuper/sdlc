from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

NODE_NESTJS_ADAPTER = AdapterDef(
    id="node-nestjs",
    name="Node NestJS",
    version="1.0",
    detect_patterns=[
        {"glob": "**/package.json", "contains": "@nestjs/core"},
    ],
    components=[
        ComponentDef(id="nest-modules", type="module", detect="@Module", enforce=True),
        ComponentDef(id="nest-guards", type="security", detect="@Injectable", enforce=True),
        ComponentDef(id="nest-interceptors", type="interceptor", detect="@Injectable", enforce=True),
        ComponentDef(id="typeorm", type="db", detect="TypeOrmModule", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["node-must"],
    required_kb=["rules/node-must.yaml"],
)


def register_node_nestjs(registry: AdapterRegistry) -> None:
    registry.register(NODE_NESTJS_ADAPTER)
