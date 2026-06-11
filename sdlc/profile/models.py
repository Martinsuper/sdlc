from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProfileDef:
    id: str
    name: str = ""
    entry_kinds: list[str] = field(default_factory=list)
    base_stages: list[str] = field(default_factory=list)
    skip_stages: list[str] = field(default_factory=list)
    extra_stages: list[str] = field(default_factory=list)
    gates: list[dict[str, Any]] = field(default_factory=list)
    subagent_overrides: dict[str, str] = field(default_factory=dict)
    severity: str = "P2"
    stage_deps: dict[str, list[str]] = field(default_factory=dict)


BUILTIN_PROFILES: list[dict[str, Any]] = [
    {
        "id": "new-feature",
        "name": "新功能",
        "entry_kinds": ["feature", "idea"],
        "base_stages": [
            "s-clarify",
            "s-design",
            "s-impl-backend",
            "s-unit-test",
            "s-cr",
            "s-package",
            "s-deploy",
            "s-monitor-setup",
        ],
        "severity": "P2",
    },
    {
        "id": "bug-fix",
        "name": "Bug 修复",
        "entry_kinds": ["bug"],
        "base_stages": [
            "s-clarify",
            "s-impl-backend",
            "s-unit-test",
            "s-cr",
            "s-package",
            "s-deploy",
        ],
        "skip_stages": ["s-design", "s-monitor-setup"],
        "severity": "P1",
    },
    {
        "id": "hotfix",
        "name": "紧急修复",
        "entry_kinds": ["hotfix"],
        "base_stages": ["s-clarify", "s-impl-backend", "s-unit-test", "s-deploy"],
        "skip_stages": ["s-design", "s-cr", "s-monitor-setup"],
        "severity": "P0",
    },
    {
        "id": "refactor",
        "name": "重构",
        "entry_kinds": ["refactor"],
        "base_stages": [
            "s-clarify",
            "s-design",
            "s-impl-backend",
            "s-unit-test",
            "s-cr",
            "s-package",
            "s-deploy",
        ],
        "severity": "P2",
    },
    {
        "id": "test",
        "name": "补充测试",
        "entry_kinds": ["test"],
        "base_stages": ["s-clarify", "s-unit-test", "s-cr"],
        "skip_stages": ["s-design", "s-impl-backend", "s-deploy"],
        "severity": "P3",
    },
    {
        "id": "infra",
        "name": "基础设施",
        "entry_kinds": ["infra"],
        "base_stages": [
            "s-clarify",
            "s-design",
            "s-impl-backend",
            "s-unit-test",
            "s-deploy",
            "s-monitor-setup",
        ],
        "severity": "P1",
    },
    {
        "id": "release",
        "name": "发布",
        "entry_kinds": ["release"],
        "base_stages": ["s-clarify", "s-package", "s-deploy", "s-monitor-setup"],
        "skip_stages": ["s-design", "s-impl-backend"],
        "severity": "P1",
    },
    {
        "id": "revert",
        "name": "回滚",
        "entry_kinds": ["revert"],
        "base_stages": ["s-clarify", "s-deploy"],
        "skip_stages": ["s-design", "s-impl-backend"],
        "severity": "P0",
    },
    {
        "id": "doc",
        "name": "文档",
        "entry_kinds": ["doc"],
        "base_stages": ["s-clarify"],
        "skip_stages": ["s-design", "s-impl-backend", "s-deploy"],
        "severity": "P3",
    },
    {
        "id": "migrate",
        "name": "迁移",
        "entry_kinds": ["migrate"],
        "base_stages": [
            "s-clarify",
            "s-design",
            "s-impl-backend",
            "s-unit-test",
            "s-cr",
            "s-deploy",
        ],
        "severity": "P1",
    },
    {
        "id": "audit",
        "name": "审计",
        "entry_kinds": ["audit"],
        "base_stages": ["s-clarify", "s-cr"],
        "skip_stages": ["s-design", "s-impl-backend", "s-deploy"],
        "severity": "P1",
    },
    {
        "id": "idea",
        "name": "想法",
        "entry_kinds": ["idea"],
        "base_stages": ["s-clarify"],
        "severity": "P3",
    },
    {
        "id": "frontend",
        "name": "前端功能",
        "entry_kinds": ["feature"],
        "base_stages": [
            "s-clarify",
            "s-design",
            "s-impl-frontend",
            "s-unit-test",
            "s-cr",
            "s-deploy",
        ],
        "severity": "P2",
    },
    {
        "id": "full-stack",
        "name": "全栈功能",
        "entry_kinds": ["feature"],
        "base_stages": [
            "s-clarify",
            "s-design",
            "s-impl-backend",
            "s-impl-frontend",
            "s-unit-test",
            "s-cr",
            "s-package",
            "s-deploy",
            "s-monitor-setup",
        ],
        "severity": "P2",
    },
]
