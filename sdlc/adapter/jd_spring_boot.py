from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

JD_SPRING_BOOT_ADAPTER = AdapterDef(
    id="jd-spring-boot",
    name="企业 Spring Boot 框架",
    version="1.0",
    detect_patterns=[
        {"glob": "**/pom.xml", "contains": "spring-boot-starter"},
    ],
    components=[
        ComponentDef(id="spring-mvc", type="web", detect="@Controller", enforce=True),
        ComponentDef(id="spring-data", type="db", detect="@Repository", enforce=True),
        ComponentDef(id="spring-security", type="security", detect="@EnableWebSecurity", enforce=True),
        ComponentDef(id="spring-actuator", type="monitor", detect="@Endpoint", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["jd-coding-must", "spring-boot-must"],
    required_kb=["rules/MUST.yaml", "standards/spring-boot-guide.md"],
)


def register_jd_spring_boot(registry: AdapterRegistry) -> None:
    registry.register(JD_SPRING_BOOT_ADAPTER)
