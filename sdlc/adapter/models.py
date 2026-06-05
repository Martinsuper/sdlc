from dataclasses import dataclass, field


@dataclass
class ComponentDef:
    id: str
    type: str
    detect: str = ""
    enforce: bool = True


@dataclass
class AdapterDef:
    id: str
    name: str
    version: str = "1.0"
    detect_patterns: list[dict[str, str]] = field(default_factory=list)
    components: list[ComponentDef] = field(default_factory=list)
    enforce_rules: bool = True
    rule_sets: list[str] = field(default_factory=list)
    required_kb: list[str] = field(default_factory=list)
