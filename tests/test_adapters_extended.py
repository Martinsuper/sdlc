"""Tests for the 17 new adapter definitions and related YAML files."""

from pathlib import Path

import pytest

from sdlc.adapter import (
    DATA_SPARK_ADAPTER,
    DONGBOOT_ADAPTER,
    FRONTEND_REACT_ADAPTER,
    FRONTEND_VUE_ADAPTER,
    GO_GIN_ADAPTER,
    GO_KRATOS_ADAPTER,
    INFRA_TERRAFORM_ADAPTER,
    JD_SPRING_BOOT_ADAPTER,
    MOBILE_ANDROID_ADAPTER,
    MOBILE_FLUTTER_ADAPTER,
    MOBILE_IOS_ADAPTER,
    NO_TECH_ADAPTER,
    NODE_EXPRESS_ADAPTER,
    NODE_NESTJS_ADAPTER,
    PYTHON_DJANGO_ADAPTER,
    PYTHON_FASTAPI_ADAPTER,
    PYTHON_FLASK_ADAPTER,
    RUST_AXUM_ADAPTER,
    AdapterRegistry,
    register_data_spark,
    register_dongboot,
    register_frontend_react,
    register_frontend_vue,
    register_go_gin,
    register_go_kratos,
    register_infra_terraform,
    register_jd_spring_boot,
    register_mobile_android,
    register_mobile_flutter,
    register_mobile_ios,
    register_no_tech,
    register_node_express,
    register_node_nestjs,
    register_python_django,
    register_python_fastapi,
    register_python_flask,
    register_rust_axum,
)
from sdlc.adapter.detector import AdapterDetector
from sdlc.adapter.models import ComponentDef

# ---------------------------------------------------------------------------
# Adapter constant + register-function pairs
# ---------------------------------------------------------------------------

ALL_ADAPTERS = [
    (JD_SPRING_BOOT_ADAPTER, register_jd_spring_boot, "jd-spring-boot", 4),
    (PYTHON_FASTAPI_ADAPTER, register_python_fastapi, "python-fastapi", 4),
    (PYTHON_FLASK_ADAPTER, register_python_flask, "python-flask", 3),
    (PYTHON_DJANGO_ADAPTER, register_python_django, "python-django", 4),
    (NODE_NESTJS_ADAPTER, register_node_nestjs, "node-nestjs", 4),
    (NODE_EXPRESS_ADAPTER, register_node_express, "node-express", 3),
    (FRONTEND_REACT_ADAPTER, register_frontend_react, "frontend-react", 4),
    (FRONTEND_VUE_ADAPTER, register_frontend_vue, "frontend-vue", 4),
    (GO_GIN_ADAPTER, register_go_gin, "go-gin", 3),
    (GO_KRATOS_ADAPTER, register_go_kratos, "go-kratos", 3),
    (RUST_AXUM_ADAPTER, register_rust_axum, "rust-axum", 3),
    (MOBILE_ANDROID_ADAPTER, register_mobile_android, "mobile-android", 4),
    (MOBILE_IOS_ADAPTER, register_mobile_ios, "mobile-ios", 3),
    (MOBILE_FLUTTER_ADAPTER, register_mobile_flutter, "mobile-flutter", 3),
    (INFRA_TERRAFORM_ADAPTER, register_infra_terraform, "infra-terraform", 2),
    (DATA_SPARK_ADAPTER, register_data_spark, "data-spark", 3),
    (NO_TECH_ADAPTER, register_no_tech, "no-tech", 0),
]


# ---------------------------------------------------------------------------
# Tests: each adapter has required fields
# ---------------------------------------------------------------------------


class TestAdapterRequiredFields:
    """Every adapter must have id, name, version, detect_patterns, etc."""

    @pytest.mark.parametrize(
        "adapter,register_fn,expected_id,expected_components",
        ALL_ADAPTERS,
        ids=[a[2] for a in ALL_ADAPTERS],
    )
    def test_adapter_has_id(self, adapter, register_fn, expected_id, expected_components):
        assert adapter.id == expected_id

    @pytest.mark.parametrize(
        "adapter,register_fn,expected_id,expected_components",
        ALL_ADAPTERS,
        ids=[a[2] for a in ALL_ADAPTERS],
    )
    def test_adapter_has_name(self, adapter, register_fn, expected_id, expected_components):
        assert isinstance(adapter.name, str)
        assert len(adapter.name) > 0

    @pytest.mark.parametrize(
        "adapter,register_fn,expected_id,expected_components",
        ALL_ADAPTERS,
        ids=[a[2] for a in ALL_ADAPTERS],
    )
    def test_adapter_has_version(self, adapter, register_fn, expected_id, expected_components):
        assert isinstance(adapter.version, str)
        assert len(adapter.version) > 0

    @pytest.mark.parametrize(
        "adapter,register_fn,expected_id,expected_components",
        ALL_ADAPTERS,
        ids=[a[2] for a in ALL_ADAPTERS],
    )
    def test_adapter_detect_patterns_structure(self, adapter, register_fn, expected_id, expected_components):
        """detect_patterns must be a list of dicts with 'glob' key."""
        assert isinstance(adapter.detect_patterns, list)
        for pattern in adapter.detect_patterns:
            assert isinstance(pattern, dict)
            assert "glob" in pattern

    @pytest.mark.parametrize(
        "adapter,register_fn,expected_id,expected_components",
        ALL_ADAPTERS,
        ids=[a[2] for a in ALL_ADAPTERS],
    )
    def test_adapter_component_count(self, adapter, register_fn, expected_id, expected_components):
        assert len(adapter.components) == expected_components

    @pytest.mark.parametrize(
        "adapter,register_fn,expected_id,expected_components",
        ALL_ADAPTERS,
        ids=[a[2] for a in ALL_ADAPTERS],
    )
    def test_adapter_components_have_ids(self, adapter, register_fn, expected_id, expected_components):
        for comp in adapter.components:
            assert isinstance(comp, ComponentDef)
            assert len(comp.id) > 0
            assert len(comp.type) > 0

    @pytest.mark.parametrize(
        "adapter,register_fn,expected_id,expected_components",
        ALL_ADAPTERS,
        ids=[a[2] for a in ALL_ADAPTERS],
    )
    def test_adapter_rule_sets_structure(self, adapter, register_fn, expected_id, expected_components):
        assert isinstance(adapter.rule_sets, list)
        for rs in adapter.rule_sets:
            assert isinstance(rs, str)

    @pytest.mark.parametrize(
        "adapter,register_fn,expected_id,expected_components",
        ALL_ADAPTERS,
        ids=[a[2] for a in ALL_ADAPTERS],
    )
    def test_adapter_enforce_rules_type(self, adapter, register_fn, expected_id, expected_components):
        assert isinstance(adapter.enforce_rules, bool)

    @pytest.mark.parametrize(
        "adapter,register_fn,expected_id,expected_components",
        ALL_ADAPTERS,
        ids=[a[2] for a in ALL_ADAPTERS],
    )
    def test_adapter_required_kb_structure(self, adapter, register_fn, expected_id, expected_components):
        assert isinstance(adapter.required_kb, list)
        for kb in adapter.required_kb:
            assert isinstance(kb, str)


# ---------------------------------------------------------------------------
# Tests: register functions work with AdapterRegistry
# ---------------------------------------------------------------------------


class TestAdapterRegistration:
    """Each register_xxx function must add the adapter to the registry."""

    @pytest.mark.parametrize(
        "adapter,register_fn,expected_id,expected_components",
        ALL_ADAPTERS,
        ids=[a[2] for a in ALL_ADAPTERS],
    )
    def test_register_function(self, adapter, register_fn, expected_id, expected_components):
        r = AdapterRegistry()
        register_fn(r)
        assert r.has(expected_id)
        assert r.get(expected_id) is adapter

    def test_register_all_at_once(self):
        """All adapters can be registered simultaneously without conflict."""
        r = AdapterRegistry()
        for _, register_fn, _, _ in ALL_ADAPTERS:
            register_fn(r)
        # +1 for dongboot which is in ALL_ADAPTERS already
        total = len(ALL_ADAPTERS)
        assert len(r.list_adapters()) == total

    def test_register_dongboot_still_works(self):
        """Existing dongboot registration still works."""
        r = AdapterRegistry()
        register_dongboot(r)
        assert r.has("dongboot")
        assert r.get("dongboot") is DONGBOOT_ADAPTER


# ---------------------------------------------------------------------------
# Tests: specific adapter detect patterns
# ---------------------------------------------------------------------------


class TestAdapterDetectPatterns:
    """Verify detect_patterns are correct for key adapters."""

    def test_jd_spring_boot_detects_pom_with_spring_boot(self, tmp_dir):
        r = AdapterRegistry()
        register_jd_spring_boot(r)
        d = AdapterDetector(r)
        (tmp_dir / "pom.xml").write_text(
            "<artifactId>spring-boot-starter-web</artifactId>", encoding="utf-8"
        )
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "jd-spring-boot"

    def test_python_fastapi_detects_requirements(self, tmp_dir):
        r = AdapterRegistry()
        register_python_fastapi(r)
        d = AdapterDetector(r)
        (tmp_dir / "requirements.txt").write_text("fastapi==0.100.0\n", encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "python-fastapi"

    def test_python_fastapi_detects_pyproject(self, tmp_dir):
        r = AdapterRegistry()
        register_python_fastapi(r)
        d = AdapterDetector(r)
        (tmp_dir / "pyproject.toml").write_text('fastapi = "^0.100"\n', encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "python-fastapi"

    def test_python_flask_detects_requirements(self, tmp_dir):
        r = AdapterRegistry()
        register_python_flask(r)
        d = AdapterDetector(r)
        (tmp_dir / "requirements.txt").write_text("flask==2.3.0\n", encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "python-flask"

    def test_python_django_detects_requirements(self, tmp_dir):
        r = AdapterRegistry()
        register_python_django(r)
        d = AdapterDetector(r)
        (tmp_dir / "requirements.txt").write_text("django==4.2\n", encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "python-django"

    def test_node_nestjs_detects_package_json(self, tmp_dir):
        r = AdapterRegistry()
        register_node_nestjs(r)
        d = AdapterDetector(r)
        (tmp_dir / "package.json").write_text('"@nestjs/core": "^10.0"', encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "node-nestjs"

    def test_node_express_detects_package_json(self, tmp_dir):
        r = AdapterRegistry()
        register_node_express(r)
        d = AdapterDetector(r)
        (tmp_dir / "package.json").write_text('"express": "^4.18"', encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "node-express"

    def test_frontend_react_detects_package_json(self, tmp_dir):
        r = AdapterRegistry()
        register_frontend_react(r)
        d = AdapterDetector(r)
        (tmp_dir / "package.json").write_text('"react": "^18.2"', encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "frontend-react"

    def test_frontend_vue_detects_package_json(self, tmp_dir):
        r = AdapterRegistry()
        register_frontend_vue(r)
        d = AdapterDetector(r)
        (tmp_dir / "package.json").write_text('"vue": "^3.3"', encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "frontend-vue"

    def test_go_gin_detects_go_mod(self, tmp_dir):
        r = AdapterRegistry()
        register_go_gin(r)
        d = AdapterDetector(r)
        (tmp_dir / "go.mod").write_text("github.com/gin-gonic/gin v1.9", encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "go-gin"

    def test_go_kratos_detects_go_mod(self, tmp_dir):
        r = AdapterRegistry()
        register_go_kratos(r)
        d = AdapterDetector(r)
        (tmp_dir / "go.mod").write_text("github.com/go-kratos/kratos/v2", encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "go-kratos"

    def test_rust_axum_detects_cargo_toml(self, tmp_dir):
        r = AdapterRegistry()
        register_rust_axum(r)
        d = AdapterDetector(r)
        (tmp_dir / "Cargo.toml").write_text('axum = "0.6"', encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "rust-axum"

    def test_mobile_android_detects_build_gradle(self, tmp_dir):
        r = AdapterRegistry()
        register_mobile_android(r)
        d = AdapterDetector(r)
        (tmp_dir / "build.gradle").write_text(
            "apply plugin: 'com.android.application'", encoding="utf-8"
        )
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "mobile-android"

    def test_mobile_ios_detects_package_swift(self, tmp_dir):
        r = AdapterRegistry()
        register_mobile_ios(r)
        d = AdapterDetector(r)
        (tmp_dir / "Package.swift").write_text("// swift-tools-version:5.9", encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "mobile-ios"

    def test_mobile_flutter_detects_pubspec(self, tmp_dir):
        r = AdapterRegistry()
        register_mobile_flutter(r)
        d = AdapterDetector(r)
        (tmp_dir / "pubspec.yaml").write_text("flutter:\n  sdk: flutter\n", encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "mobile-flutter"

    def test_infra_terraform_detects_tf_files(self, tmp_dir):
        r = AdapterRegistry()
        register_infra_terraform(r)
        d = AdapterDetector(r)
        (tmp_dir / "main.tf").write_text('resource "aws_s3_bucket" "b" {}', encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "infra-terraform"

    def test_data_spark_detects_pom(self, tmp_dir):
        r = AdapterRegistry()
        register_data_spark(r)
        d = AdapterDetector(r)
        (tmp_dir / "pom.xml").write_text(
            "<artifactId>spark-core_2.12</artifactId>", encoding="utf-8"
        )
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "data-spark"

    def test_data_spark_detects_requirements(self, tmp_dir):
        r = AdapterRegistry()
        register_data_spark(r)
        d = AdapterDetector(r)
        (tmp_dir / "requirements.txt").write_text("pyspark==3.4.0\n", encoding="utf-8")
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "data-spark"

    def test_no_tech_never_auto_detects(self, tmp_dir):
        """no-tech has empty detect_patterns so detector skips it."""
        r = AdapterRegistry()
        register_no_tech(r)
        d = AdapterDetector(r)
        result = d.detect(tmp_dir)
        assert result == []

    def test_no_match_returns_empty(self, tmp_dir):
        """A pom.xml without matching content returns no adapters."""
        r = AdapterRegistry()
        register_jd_spring_boot(r)
        d = AdapterDetector(r)
        (tmp_dir / "pom.xml").write_text("<artifactId>other</artifactId>", encoding="utf-8")
        result = d.detect(tmp_dir)
        assert result == []


# ---------------------------------------------------------------------------
# Tests: specific adapter properties
# ---------------------------------------------------------------------------


class TestNoTechAdapter:
    def test_no_tech_has_empty_patterns(self):
        assert NO_TECH_ADAPTER.detect_patterns == []

    def test_no_tech_has_empty_components(self):
        assert NO_TECH_ADAPTER.components == []

    def test_no_tech_enforce_rules_false(self):
        assert NO_TECH_ADAPTER.enforce_rules is False

    def test_no_tech_has_empty_rule_sets(self):
        assert NO_TECH_ADAPTER.rule_sets == []


class TestJdSpringBootTest:
    def test_rule_sets(self):
        assert JD_SPRING_BOOT_ADAPTER.rule_sets == ["jd-coding-must", "spring-boot-must"]

    def test_components(self):
        comp_ids = [c.id for c in JD_SPRING_BOOT_ADAPTER.components]
        assert comp_ids == ["spring-mvc", "spring-data", "spring-security", "spring-actuator"]


class TestPythonDjangoTest:
    def test_rule_sets(self):
        assert PYTHON_DJANGO_ADAPTER.rule_sets == ["python-must", "django-must"]

    def test_components(self):
        comp_ids = [c.id for c in PYTHON_DJANGO_ADAPTER.components]
        assert comp_ids == ["django-rest", "django-orm", "django-admin", "django-auth"]


class TestMobileAndroidTest:
    def test_detects_kts_gradle(self, tmp_dir):
        """Should also detect .kts gradle files."""
        r = AdapterRegistry()
        register_mobile_android(r)
        d = AdapterDetector(r)
        (tmp_dir / "build.gradle.kts").write_text(
            'id("com.android.application")', encoding="utf-8"
        )
        result = d.detect(tmp_dir)
        assert len(result) == 1
        assert result[0].id == "mobile-android"


class TestDataSparkTest:
    def test_has_two_detect_patterns(self):
        assert len(DATA_SPARK_ADAPTER.detect_patterns) == 2

    def test_rule_sets(self):
        assert DATA_SPARK_ADAPTER.rule_sets == ["data-must"]


# ---------------------------------------------------------------------------
# Tests: YAML profile files
# ---------------------------------------------------------------------------


class TestBuiltinProfileYamls:
    PROFILE_IDS = [
        "new-feature",
        "bug-fix",
        "hotfix",
        "refactor",
        "test",
        "infra",
        "release",
        "revert",
        "doc",
        "migrate",
        "audit",
        "idea",
        "frontend",
        "full-stack",
    ]

    @pytest.mark.parametrize("profile_id", PROFILE_IDS, ids=PROFILE_IDS)
    def test_profile_yaml_exists_and_loadable(self, profile_id):
        from sdlc.utils.yaml_io import load_yaml

        path = Path(__file__).parent.parent / "sdlc" / "builtin" / "profiles" / f"{profile_id}.yaml"
        assert path.exists(), f"Profile YAML missing: {path}"
        data = load_yaml(path)
        assert isinstance(data, dict)
        assert data["id"] == profile_id

    @pytest.mark.parametrize("profile_id", PROFILE_IDS, ids=PROFILE_IDS)
    def test_profile_yaml_has_required_fields(self, profile_id):
        from sdlc.utils.yaml_io import load_yaml

        path = Path(__file__).parent.parent / "sdlc" / "builtin" / "profiles" / f"{profile_id}.yaml"
        data = load_yaml(path)
        assert "id" in data
        assert "name" in data
        assert "entry_kinds" in data
        assert "base_stages" in data
        assert "severity" in data
        assert isinstance(data["entry_kinds"], list)
        assert isinstance(data["base_stages"], list)


# ---------------------------------------------------------------------------
# Tests: YAML rule files
# ---------------------------------------------------------------------------


class TestBuiltinRuleYamls:
    RULE_FILES = [
        "coding-must",
        "python-must",
        "node-must",
        "frontend-must",
        "go-must",
        "rust-must",
        "mobile-must",
        "infra-must",
        "data-must",
    ]

    @pytest.mark.parametrize("rule_file", RULE_FILES, ids=RULE_FILES)
    def test_rule_yaml_exists_and_loadable(self, rule_file):
        from sdlc.utils.yaml_io import load_yaml

        path = Path(__file__).parent.parent / "sdlc" / "builtin" / "rules" / f"{rule_file}.yaml"
        assert path.exists(), f"Rule YAML missing: {path}"
        data = load_yaml(path)
        assert isinstance(data, list)
        assert len(data) >= 2

    @pytest.mark.parametrize("rule_file", RULE_FILES, ids=RULE_FILES)
    def test_rule_entries_have_required_fields(self, rule_file):
        from sdlc.utils.yaml_io import load_yaml

        path = Path(__file__).parent.parent / "sdlc" / "builtin" / "rules" / f"{rule_file}.yaml"
        data = load_yaml(path)
        for entry in data:
            assert isinstance(entry, dict)
            assert "id" in entry
            assert "level" in entry
            assert "pattern" in entry
            assert "message" in entry
            assert "action" in entry
            assert "severity" in entry
            assert "applies_to" in entry

    @pytest.mark.parametrize("rule_file", RULE_FILES, ids=RULE_FILES)
    def test_rule_levels_valid(self, rule_file):
        from sdlc.utils.yaml_io import load_yaml

        path = Path(__file__).parent.parent / "sdlc" / "builtin" / "rules" / f"{rule_file}.yaml"
        data = load_yaml(path)
        valid_levels = {"MUST", "SHOULD", "MAY"}
        for entry in data:
            assert entry["level"] in valid_levels

    @pytest.mark.parametrize("rule_file", RULE_FILES, ids=RULE_FILES)
    def test_rule_actions_valid(self, rule_file):
        from sdlc.utils.yaml_io import load_yaml

        path = Path(__file__).parent.parent / "sdlc" / "builtin" / "rules" / f"{rule_file}.yaml"
        data = load_yaml(path)
        valid_actions = {"block", "warn", "info"}
        for entry in data:
            assert entry["action"] in valid_actions

    @pytest.mark.parametrize("rule_file", RULE_FILES, ids=RULE_FILES)
    def test_rule_severities_valid(self, rule_file):
        from sdlc.utils.yaml_io import load_yaml

        path = Path(__file__).parent.parent / "sdlc" / "builtin" / "rules" / f"{rule_file}.yaml"
        data = load_yaml(path)
        valid_severities = {"P0", "P1", "P2", "P3"}
        for entry in data:
            assert entry["severity"] in valid_severities

    def test_coding_must_has_3_rules(self):
        from sdlc.utils.yaml_io import load_yaml

        path = Path(__file__).parent.parent / "sdlc" / "builtin" / "rules" / "coding-must.yaml"
        data = load_yaml(path)
        assert len(data) == 3
        rule_ids = [r["id"] for r in data]
        assert "no-thread-sleep" in rule_ids
        assert "no-system-out" in rule_ids
        assert "no-hardcoded-secrets" in rule_ids

    def test_python_must_has_3_rules(self):
        from sdlc.utils.yaml_io import load_yaml

        path = Path(__file__).parent.parent / "sdlc" / "builtin" / "rules" / "python-must.yaml"
        data = load_yaml(path)
        assert len(data) == 3
        rule_ids = [r["id"] for r in data]
        assert "no-bare-except" in rule_ids
        assert "no-eval" in rule_ids

    def test_hardcoded_secrets_rule_applies_to_multiple_langs(self):
        from sdlc.utils.yaml_io import load_yaml

        path = Path(__file__).parent.parent / "sdlc" / "builtin" / "rules" / "coding-must.yaml"
        data = load_yaml(path)
        secret_rule = next(r for r in data if r["id"] == "no-hardcoded-secrets")
        assert len(secret_rule["applies_to"]) >= 3
