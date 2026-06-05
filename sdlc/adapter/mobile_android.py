from __future__ import annotations

from sdlc.adapter.models import AdapterDef, ComponentDef
from sdlc.adapter.registry import AdapterRegistry

MOBILE_ANDROID_ADAPTER = AdapterDef(
    id="mobile-android",
    name="Android",
    version="1.0",
    detect_patterns=[
        {"glob": "**/build.gradle", "contains": "com.android.application"},
        {"glob": "**/build.gradle.kts", "contains": "com.android.application"},
    ],
    components=[
        ComponentDef(id="android-activity", type="ui", detect="Activity", enforce=True),
        ComponentDef(id="android-fragment", type="ui", detect="Fragment", enforce=True),
        ComponentDef(id="retrofit", type="http", detect="Retrofit", enforce=True),
        ComponentDef(id="room", type="db", detect="@Entity", enforce=True),
    ],
    enforce_rules=True,
    rule_sets=["mobile-must"],
    required_kb=["rules/mobile-must.yaml"],
)


def register_mobile_android(registry: AdapterRegistry) -> None:
    registry.register(MOBILE_ANDROID_ADAPTER)
