from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

PYTHON_FASTAPI_ADAPTER = AdapterDef(
    id="python-fastapi",
    name="Python FastAPI",
    version="1.0",
    detect_patterns=[
        {"glob": "**/requirements.txt", "contains": "fastapi"},
        {"glob": "**/pyproject.toml", "contains": "fastapi"},
    ],
    components=[
        ComponentDef(id="uvicorn", type="server", detect="uvicorn", enforce=True),
        ComponentDef(id="pydantic", type="validation", detect="BaseModel", enforce=True),
        ComponentDef(id="sqlalchemy", type="db", detect="SQLAlchemy", enforce=True),
        ComponentDef(id="redis", type="cache", detect="redis", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["python-must"],
    required_kb=["rules/python-must.yaml"],
)


def register_python_fastapi(registry: AdapterRegistry) -> None:
    registry.register(PYTHON_FASTAPI_ADAPTER)
