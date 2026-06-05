from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

INFRA_TERRAFORM_ADAPTER = AdapterDef(
    id="infra-terraform",
    name="Terraform Infrastructure",
    version="1.0",
    detect_patterns=[
        {"glob": "**/*.tf", "contains": ""},
    ],
    components=[
        ComponentDef(id="terraform-aws", type="cloud", detect="aws_", enforce=True),
        ComponentDef(id="terraform-k8s", type="orchestration", detect="kubernetes_", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["infra-must"],
    required_kb=["rules/infra-must.yaml"],
)


def register_infra_terraform(registry: AdapterRegistry) -> None:
    registry.register(INFRA_TERRAFORM_ADAPTER)
