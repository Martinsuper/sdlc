from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

PYTHON_FLASK_ADAPTER = AdapterDef(
    id="python-flask",
    name="Python Flask",
    version="1.0",
    detect_patterns=[
        {"glob": "**/requirements.txt", "contains": "flask"},
    ],
    components=[
        ComponentDef(id="flask-restful", type="web", detect="Api", enforce=True),
        ComponentDef(id="flask-sqlalchemy", type="db", detect="SQLAlchemy", enforce=True),
        ComponentDef(id="flask-caching", type="cache", detect="Cache", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["python-must"],
    required_kb=["rules/python-must.yaml"],
)


def register_python_flask(registry: AdapterRegistry) -> None:
    registry.register(PYTHON_FLASK_ADAPTER)
