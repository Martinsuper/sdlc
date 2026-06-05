"""Project auto-detection for `sdlc init`."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProjectInfo:
    """Detected project information."""
    name: str = ""
    tech_stack: list[str] = field(default_factory=list)
    language: str = ""
    framework: str = ""
    build_tool: str = ""
    has_docker: bool = False
    has_ci: bool = False
    test_framework: str = ""
    adapter_id: str = ""
    profile_id: str = ""


class InitDetector:
    """Auto-detect project type and recommend configuration."""

    DETECTION_RULES: list[dict[str, Any]] = [
        # Python
        {"files": ["pyproject.toml", "setup.py", "requirements.txt"], "language": "python", "build": "pip"},
        {"files": ["manage.py"], "framework": "django", "language": "python"},
        {"files": ["app.py", "wsgi.py"], "framework": "flask", "language": "python"},
        {"files": ["main.py"], "dirs": ["api", "routers"], "framework": "fastapi", "language": "python"},
        # Java/JVM
        {"files": ["pom.xml"], "language": "java", "build": "maven"},
        {"files": ["build.gradle", "build.gradle.kts"], "language": "java", "build": "gradle"},
        {"files": ["Application.java", "application.yml"], "dirs": ["src/main/java"], "framework": "spring-boot", "language": "java"},
        # Node.js
        {"files": ["package.json"], "language": "javascript", "build": "npm"},
        {"files": ["nest-cli.json"], "framework": "nestjs", "language": "typescript"},
        {"files": ["next.config.js", "next.config.ts"], "framework": "nextjs", "language": "typescript"},
        {"files": ["nuxt.config.ts"], "framework": "nuxt", "language": "typescript"},
        # Go
        {"files": ["go.mod"], "language": "go", "build": "go"},
        {"files": ["go.mod"], "dirs": ["internal/server"], "framework": "gin", "language": "go"},
        # Rust
        {"files": ["Cargo.toml"], "language": "rust", "build": "cargo"},
        # Mobile
        {"files": ["AndroidManifest.xml"], "framework": "android", "language": "kotlin"},
        {"files": ["Info.plist", "*.xcodeproj"], "framework": "ios", "language": "swift"},
        {"files": ["pubspec.yaml"], "framework": "flutter", "language": "dart"},
        # Infra
        {"files": ["main.tf", "variables.tf"], "language": "hcl", "build": "terraform"},
        {"files": ["docker-compose.yml", "Dockerfile"], "has_docker": True},
        {"files": [".github/workflows"], "has_ci": True},
        {"files": [".gitlab-ci.yml"], "has_ci": True},
        {"files": ["Jenkinsfile"], "has_ci": True},
    ]

    def detect(self, project_dir: Path) -> ProjectInfo:
        """Auto-detect project configuration from directory contents."""
        info = ProjectInfo(name=project_dir.name)
        score_map: dict[str, int] = {}

        for rule in self.DETECTION_RULES:
            matched = 0
            for f in rule.get("files", []):
                if (project_dir / f).exists():
                    matched += 1
            for d in rule.get("dirs", []):
                if (project_dir / d).is_dir():
                    matched += 1

            if matched > 0:
                if "language" in rule:
                    lang = rule["language"]
                    score_map[lang] = score_map.get(lang, 0) + matched
                    if not info.language or score_map[lang] > score_map.get(info.language, 0):
                        info.language = lang
                if "framework" in rule:
                    info.framework = rule["framework"]
                if "build" in rule:
                    info.build_tool = rule["build"]
                if rule.get("has_docker"):
                    info.has_docker = True
                if rule.get("has_ci"):
                    info.has_ci = True

        # Derive tech_stack from language + framework
        if info.language:
            info.tech_stack.append(info.language)
        if info.framework:
            info.tech_stack.append(info.framework)
        if info.has_docker:
            info.tech_stack.append("docker")

        # Derive adapter_id
        info.adapter_id = self._derive_adapter(info)
        # Derive profile_id
        info.profile_id = self._derive_profile(info)

        return info

    def _derive_adapter(self, info: ProjectInfo) -> str:
        """Map detected info to adapter ID."""
        fw = info.framework.lower() if info.framework else ""
        lang = info.language.lower()

        mapping = {
            "spring-boot": "jd-spring-boot",
            "django": "python-django",
            "flask": "python-flask",
            "fastapi": "python-fastapi",
            "nestjs": "node-nestjs",
            "express": "node-express",
            "react": "frontend-react",
            "vue": "frontend-vue",
            "gin": "go-gin",
            "kratos": "go-kratos",
            "axum": "rust-axum",
            "android": "mobile-android",
            "ios": "mobile-ios",
            "flutter": "mobile-flutter",
            "terraform": "infra-terraform",
            "spark": "data-spark",
        }
        if fw in mapping:
            return mapping[fw]
        # Fallback to language
        lang_map = {
            "python": "python-fastapi",
            "java": "jd-spring-boot",
            "javascript": "node-express",
            "typescript": "node-nestjs",
            "go": "go-gin",
            "rust": "rust-axum",
            "hcl": "infra-terraform",
            "kotlin": "mobile-android",
            "swift": "mobile-ios",
            "dart": "mobile-flutter",
        }
        return lang_map.get(lang, "no-tech")

    def _derive_profile(self, info: ProjectInfo) -> str:
        """Map detected info to profile ID."""
        return "new-feature"  # Default, can be refined

    def generate_config(self, info: ProjectInfo, project_dir: Path) -> dict[str, Any]:
        """Generate .sdlc/config.yaml content from detected info."""
        return {
            "project": {
                "name": info.name,
                "language": info.language,
                "framework": info.framework,
                "tech_stack": info.tech_stack,
            },
            "adapter": info.adapter_id,
            "profile": info.profile_id,
            "stages": {
                "enabled": True,
            },
            "gates": {
                "enabled": True,
            },
        }
