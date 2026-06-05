"""Tests for sdlc.client -- SdlcClient Python API."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from sdlc.client import SdlcClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_deps() -> MagicMock:
    """Create a mock DependencyContainer with all required attributes."""
    deps = MagicMock()
    deps.coordinator = MagicMock()
    deps.state = MagicMock()
    deps.catalog = MagicMock()
    return deps


# ---------------------------------------------------------------------------
# SdlcClient construction
# ---------------------------------------------------------------------------


class TestSdlcClientInit:
    @patch("sdlc.client.build_deps")
    def test_creates_with_config(self, mock_build: MagicMock) -> None:
        mock_build.return_value = _make_mock_deps()
        SdlcClient(config={"key": "val"})
        mock_build.assert_called_once_with({"key": "val"})

    @patch("sdlc.client.build_deps")
    def test_creates_without_config(self, mock_build: MagicMock) -> None:
        mock_build.return_value = _make_mock_deps()
        SdlcClient()
        mock_build.assert_called_once_with(None)


# ---------------------------------------------------------------------------
# SdlcClient.init
# ---------------------------------------------------------------------------


class TestSdlcClientInitMethod:
    @patch("sdlc.client.build_deps")
    def test_init_returns_dict(self, mock_build: MagicMock) -> None:
        mock_build.return_value = _make_mock_deps()
        client = SdlcClient()

        from sdlc.kb.models import ScanResult

        scan_result = ScanResult(
            kb_files={"conventions.md": "# Conventions"},
            recommendations=["python adapter"],
            warnings=[],
            confidence=0.8,
            next_steps=["Review KB files"],
        )

        with patch("sdlc.kb.scanner.Scanner") as mock_scanner:
            mock_scanner.return_value.scan.return_value = scan_result
            result = client.init(path=Path("/tmp/test-project"))
            assert isinstance(result, dict)
            assert "kb_files" in result
            assert result["confidence"] == 0.8


# ---------------------------------------------------------------------------
# SdlcClient.status
# ---------------------------------------------------------------------------


class TestSdlcClientStatus:
    @patch("sdlc.client.build_deps")
    def test_status_by_pipeline_id(self, mock_build: MagicMock) -> None:
        deps = _make_mock_deps()
        mock_build.return_value = deps
        client = SdlcClient()

        from sdlc.state.models import PipelineSummary

        expected = PipelineSummary(
            id="p-1",
            entry_kind="feature",
            profile_id="new-feature",
            status="RUNNING",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        deps.state.load_pipeline.return_value = expected

        result = client.status(pipeline_id="p-1")
        assert result is not None
        assert result.id == "p-1"
        deps.state.load_pipeline.assert_called_once_with("p-1")

    @patch("sdlc.client.build_deps")
    def test_status_list_pipelines(self, mock_build: MagicMock) -> None:
        deps = _make_mock_deps()
        mock_build.return_value = deps
        client = SdlcClient()

        expected = []
        deps.state.list_pipelines.return_value = expected

        result = client.status(status="RUNNING")
        assert result == expected
        deps.state.list_pipelines.assert_called_once_with(status="RUNNING")

    @patch("sdlc.client.build_deps")
    def test_status_pipeline_not_found(self, mock_build: MagicMock) -> None:
        deps = _make_mock_deps()
        mock_build.return_value = deps
        client = SdlcClient()

        deps.state.load_pipeline.return_value = None
        result = client.status(pipeline_id="nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# SdlcClient.kb_list
# ---------------------------------------------------------------------------


class TestSdlcClientKbList:
    @patch("sdlc.client.build_deps")
    def test_kb_list_no_project_root(self, mock_build: MagicMock) -> None:
        deps = _make_mock_deps()
        mock_build.return_value = deps
        client = SdlcClient()

        with patch("sdlc.utils.paths.project_root", side_effect=Exception("no root")):
            result = client.kb_list()
            assert result == []

    @patch("sdlc.client.build_deps")
    def test_kb_list_no_kb_dir(self, mock_build: MagicMock) -> None:
        deps = _make_mock_deps()
        mock_build.return_value = deps
        client = SdlcClient()

        with patch("sdlc.utils.paths.project_root", return_value=Path("/tmp/nonexistent")):
            result = client.kb_list()
            assert result == []


# ---------------------------------------------------------------------------
# SdlcClient.rule_list
# ---------------------------------------------------------------------------


class TestSdlcClientRuleList:
    @patch("sdlc.client.build_deps")
    def test_rule_list_no_rules_dir(self, mock_build: MagicMock) -> None:
        deps = _make_mock_deps()
        mock_build.return_value = deps
        client = SdlcClient()

        with patch("sdlc.utils.paths.project_root", side_effect=Exception("no root")):
            result = client.rule_list()
            assert result == []

    @patch("sdlc.client.build_deps")
    def test_rule_list_returns_list(self, mock_build: MagicMock) -> None:
        deps = _make_mock_deps()
        mock_build.return_value = deps
        client = SdlcClient()

        with patch("sdlc.utils.paths.project_root", return_value=Path("/tmp/nonexistent")):
            result = client.rule_list()
            assert isinstance(result, list)


# ---------------------------------------------------------------------------
# SdlcClient.stage_list
# ---------------------------------------------------------------------------


class TestSdlcClientStageList:
    @patch("sdlc.client.build_deps")
    def test_stage_list_returns_list(self, mock_build: MagicMock) -> None:
        deps = _make_mock_deps()
        mock_build.return_value = deps
        client = SdlcClient()

        deps.catalog.list_stages.return_value = []
        result = client.stage_list()
        assert result == []


# ---------------------------------------------------------------------------
# SdlcClient.doctor
# ---------------------------------------------------------------------------


class TestSdlcClientDoctor:
    @patch("sdlc.client.build_deps")
    def test_doctor_returns_dict(self, mock_build: MagicMock) -> None:
        deps = _make_mock_deps()
        mock_build.return_value = deps
        client = SdlcClient()

        result = client.doctor()
        assert isinstance(result, dict)
        assert "python_version" in result
        assert "uv_installed" in result
        assert "sdlc_home_exists" in result
        assert "disk_space_ok" in result

    @patch("sdlc.client.build_deps")
    def test_doctor_python_version_check(self, mock_build: MagicMock) -> None:
        deps = _make_mock_deps()
        mock_build.return_value = deps
        client = SdlcClient()

        import sys

        result = client.doctor()
        expected = sys.version_info >= (3, 11)
        assert result["python_version"] == expected
