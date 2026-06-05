"""Tests for InitDetector project auto-detection."""
from __future__ import annotations

from pathlib import Path

import pytest

from sdlc.core.init_detector import InitDetector, ProjectInfo


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    return tmp_path


class TestInitDetectorDetect:
    def test_detect_python_project(self, project_dir: Path) -> None:
        (project_dir / "pyproject.toml").write_text('[project]\nname = "myapp"\n')
        (project_dir / "requirements.txt").write_text("flask\n")

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.language == "python"
        assert info.name == project_dir.name
        assert "python" in info.tech_stack

    def test_detect_django_project(self, project_dir: Path) -> None:
        (project_dir / "manage.py").write_text("")
        (project_dir / "pyproject.toml").write_text("")

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.framework == "django"
        assert info.language == "python"
        assert info.adapter_id == "python-django"

    def test_detect_flask_project(self, project_dir: Path) -> None:
        (project_dir / "app.py").write_text("from flask import Flask")

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.framework == "flask"
        assert info.adapter_id == "python-flask"

    def test_detect_fastapi_project(self, project_dir: Path) -> None:
        (project_dir / "main.py").write_text("")
        (project_dir / "api").mkdir()

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.framework == "fastapi"
        assert info.adapter_id == "python-fastapi"

    def test_detect_java_maven(self, project_dir: Path) -> None:
        (project_dir / "pom.xml").write_text("<project></project>")

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.language == "java"
        assert info.build_tool == "maven"

    def test_detect_spring_boot(self, project_dir: Path) -> None:
        (project_dir / "Application.java").write_text("")
        (project_dir / "src").mkdir()
        (project_dir / "src" / "main").mkdir()
        (project_dir / "src" / "main" / "java").mkdir()

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.framework == "spring-boot"
        assert info.adapter_id == "jd-spring-boot"

    def test_detect_node_project(self, project_dir: Path) -> None:
        (project_dir / "package.json").write_text('{"name": "myapp"}')

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.language == "javascript"
        assert info.build_tool == "npm"

    def test_detect_nestjs(self, project_dir: Path) -> None:
        (project_dir / "nest-cli.json").write_text("{}")

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.framework == "nestjs"
        assert info.adapter_id == "node-nestjs"

    def test_detect_nextjs(self, project_dir: Path) -> None:
        (project_dir / "next.config.ts").write_text("")

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.framework == "nextjs"

    def test_detect_go_project(self, project_dir: Path) -> None:
        (project_dir / "go.mod").write_text("module example.com/myapp\n")

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.language == "go"
        assert info.build_tool == "go"

    def test_detect_rust_project(self, project_dir: Path) -> None:
        (project_dir / "Cargo.toml").write_text('[package]\nname = "myapp"\n')

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.language == "rust"
        assert info.build_tool == "cargo"
        assert info.adapter_id == "rust-axum"

    def test_detect_flutter(self, project_dir: Path) -> None:
        (project_dir / "pubspec.yaml").write_text("name: myapp\n")

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.framework == "flutter"
        assert info.language == "dart"
        assert info.adapter_id == "mobile-flutter"

    def test_detect_terraform(self, project_dir: Path) -> None:
        (project_dir / "main.tf").write_text("")

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.language == "hcl"
        assert info.build_tool == "terraform"
        assert info.adapter_id == "infra-terraform"

    def test_detect_docker(self, project_dir: Path) -> None:
        (project_dir / "Dockerfile").write_text("FROM python:3.11\n")

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.has_docker is True
        assert "docker" in info.tech_stack

    def test_detect_ci(self, project_dir: Path) -> None:
        (project_dir / ".github").mkdir()
        (project_dir / ".github" / "workflows").mkdir()

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.has_ci is True

    def test_detect_gitlab_ci(self, project_dir: Path) -> None:
        (project_dir / ".gitlab-ci.yml").write_text("")

        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.has_ci is True

    def test_empty_project(self, project_dir: Path) -> None:
        detector = InitDetector()
        info = detector.detect(project_dir)

        assert info.name == project_dir.name
        assert info.language == ""
        assert info.framework == ""
        assert info.adapter_id == "no-tech"

    def test_project_name_from_dir(self, project_dir: Path) -> None:
        detector = InitDetector()
        info = detector.detect(project_dir)
        assert info.name == project_dir.name


class TestInitDetectorGenerateConfig:
    def test_generates_config_dict(self, project_dir: Path) -> None:
        (project_dir / "pyproject.toml").write_text("")

        detector = InitDetector()
        info = detector.detect(project_dir)
        config = detector.generate_config(info, project_dir)

        assert "project" in config
        assert config["project"]["name"] == project_dir.name
        assert config["project"]["language"] == "python"
        assert config["adapter"] == "python-fastapi"
        assert config["profile"] == "new-feature"
        assert config["stages"]["enabled"] is True
        assert config["gates"]["enabled"] is True

    def test_config_includes_tech_stack(self, project_dir: Path) -> None:
        (project_dir / "pyproject.toml").write_text("")
        (project_dir / "Dockerfile").write_text("FROM python:3.11\n")

        detector = InitDetector()
        info = detector.detect(project_dir)
        config = detector.generate_config(info, project_dir)

        assert "python" in config["project"]["tech_stack"]
        assert "docker" in config["project"]["tech_stack"]


class TestProjectInfo:
    def test_default_values(self) -> None:
        info = ProjectInfo()
        assert info.name == ""
        assert info.tech_stack == []
        assert info.language == ""
        assert info.framework == ""
        assert info.has_docker is False
        assert info.has_ci is False
        assert info.adapter_id == ""
        assert info.profile_id == ""
