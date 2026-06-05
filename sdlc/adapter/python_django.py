from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

PYTHON_DJANGO_ADAPTER = AdapterDef(
    id="python-django",
    name="Python Django",
    version="1.0",
    detect_patterns=[
        {"glob": "**/requirements.txt", "contains": "django"},
    ],
    components=[
        ComponentDef(id="django-rest", type="web", detect="rest_framework", enforce=True),
        ComponentDef(id="django-orm", type="db", detect="models.Model", enforce=True),
        ComponentDef(id="django-admin", type="admin", detect="admin.site", enforce=True),
        ComponentDef(id="django-auth", type="security", detect="authenticate", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["python-must", "django-must"],
    required_kb=["rules/python-must.yaml", "rules/django-must.yaml"],
)


def register_python_django(registry: AdapterRegistry) -> None:
    registry.register(PYTHON_DJANGO_ADAPTER)
