from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

DONGBOOT_ADAPTER = AdapterDef(
    id="dongboot",
    name="DongBoot 企业微服务框架",
    version="1.0",
    detect_patterns=[
        {"glob": "**/pom.xml", "contains": "dong-boot-starter"},
        {"glob": "**/application.yml", "contains": "dongboot"},
        {"glob": "**/application.properties", "contains": "dongboot"},
    ],
    components=[
        ComponentDef(id="dong-log", type="logging", detect="BizLogger", enforce=True),
        ComponentDef(id="dong-thread", type="threadpool", detect="DongThread", enforce=True),
        ComponentDef(id="dong-dal", type="db", detect="DongDAL", enforce=True),
        ComponentDef(id="dong-cache", type="cache", detect="DongCache", enforce=True),
        ComponentDef(id="dong-mq", type="mq", detect="DongMQ", enforce=True),
        ComponentDef(id="dong-web", type="web", detect="DongWeb", enforce=True),
        ComponentDef(id="dong-config", type="config", detect="DongConfig", enforce=True),
        ComponentDef(id="dong-hot-deploy", type="deploy", detect="hot_deploy", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["dongboot-must", "jd-coding-must"],
    required_kb=[
        "rules/MUST.yaml",
        "standards/coding-style.md",
        "architecture/component-catalog.md",
    ],
)


def register_dongboot(registry: AdapterRegistry) -> None:
    registry.register(DONGBOOT_ADAPTER)
