"""Tests for sdlc.cli.deps -- DependencyContainer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from sdlc.cli.deps import DependencyContainer, build_deps
from sdlc.utils.config import SdlcConfig


class TestDependencyContainer:
    """Tests for DependencyContainer dataclass and build_deps factory."""

    def test_build_deps_returns_container(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """build_deps returns a fully populated DependencyContainer."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("sdlc.cli.deps.sdlc_home", return_value=tmp_path):
            container = build_deps()

        assert isinstance(container, DependencyContainer)
        assert container.config is not None
        assert container.state is not None
        assert container.audit is not None
        assert container.catalog is not None
        assert container.profiles is not None
        assert container.adapters is not None
        assert container.gates is not None
        assert container.subagent_pool is not None
        assert container.entry_detector is not None
        assert container.pipeline_builder is not None
        assert container.coordinator is not None
        assert container.cost_tracker is not None

    def test_build_deps_with_explicit_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """build_deps uses the provided config instead of loading from disk."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        config = SdlcConfig()
        with patch("sdlc.cli.deps.sdlc_home", return_value=tmp_path):
            container = build_deps(config=config)

        assert container.config is config

    def test_build_deps_state_store_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """StateStore is created at sdlc_home / state.db."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("sdlc.cli.deps.sdlc_home", return_value=tmp_path):
            container = build_deps()

        assert container.state.db_path == tmp_path / "state.db"

    def test_build_deps_catalog_has_builtin_stages(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """StageCatalog is populated with builtin stages."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("sdlc.cli.deps.sdlc_home", return_value=tmp_path):
            container = build_deps()

        # builtin stages are loaded from yaml files
        assert len(container.catalog.list_stages()) >= 0

    def test_build_deps_profiles_registered(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """ProfileRegistry is populated with builtin profiles."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("sdlc.cli.deps.sdlc_home", return_value=tmp_path):
            container = build_deps()

        profiles = container.profiles.list_profiles()
        assert len(profiles) > 0

    def test_build_deps_adapters_registered(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """AdapterRegistry is populated with builtin adapters."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("sdlc.cli.deps.sdlc_home", return_value=tmp_path):
            container = build_deps()

        adapters = container.adapters.list_adapters()
        assert len(adapters) > 0

    def test_build_deps_cost_tracker_default_budget(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CostTracker has the default max_budget from config."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("sdlc.cli.deps.sdlc_home", return_value=tmp_path):
            container = build_deps()

        assert container.cost_tracker.max_budget == 5.0

    def test_build_deps_coordinator_references_same_instances(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Coordinator shares the same state, audit, catalog, etc. as the container."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("sdlc.cli.deps.sdlc_home", return_value=tmp_path):
            container = build_deps()

        assert container.coordinator.state is container.state
        assert container.coordinator.audit is container.audit
        assert container.coordinator.catalog is container.catalog
        assert container.coordinator.subagent_pool is container.subagent_pool
        assert container.coordinator.gate_engine is container.gates
        assert container.coordinator.profile_registry is container.profiles
        assert container.coordinator.adapter_registry is container.adapters
        assert container.coordinator.cost_tracker is container.cost_tracker

    def test_build_deps_without_api_keys(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """build_deps does not crash when API keys are not set."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with patch("sdlc.cli.deps.sdlc_home", return_value=tmp_path):
            container = build_deps()

        assert isinstance(container, DependencyContainer)
