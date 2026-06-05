"""Tests for kb, rule, and config CLI commands."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from sdlc.cli.config_cmd import config
from sdlc.cli.kb_cmd import kb
from sdlc.cli.rule_cmd import rule


@pytest.fixture()
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# KB command tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def kb_dir(tmp_path):
    """Create a temporary KB directory with sample files."""
    kb_root = tmp_path / "doc" / "kb"
    kb_root.mkdir(parents=True)
    (kb_root / "architecture").mkdir()
    (kb_root / "architecture" / "component-catalog.md").write_text("# Components\n")
    (kb_root / "architecture" / "api-style.yaml").write_text("style: rest\n")
    (kb_root / "coding").mkdir()
    (kb_root / "coding" / "conventions.md").write_text("# Conventions\nUse type hints.\n")
    return kb_root


class TestKbList:
    def test_list_with_files(self, runner, kb_dir):
        with patch("sdlc.cli.kb_cmd.project_root", return_value=kb_dir.parent.parent):
            result = runner.invoke(kb, ["list"])
        assert result.exit_code == 0
        assert "component-catalog.md" in result.output
        assert "api-style.yaml" in result.output
        assert "conventions.md" in result.output

    def test_list_empty(self, runner, tmp_path):
        kb_root = tmp_path / "doc" / "kb"
        kb_root.mkdir(parents=True)
        with patch("sdlc.cli.kb_cmd.project_root", return_value=tmp_path):
            result = runner.invoke(kb, ["list"])
        assert result.exit_code == 0
        assert "No KB files found" in result.output

    def test_list_with_pattern(self, runner, kb_dir):
        with patch("sdlc.cli.kb_cmd.project_root", return_value=kb_dir.parent.parent):
            result = runner.invoke(kb, ["list", "--pattern", "**/*.yaml"])
        assert result.exit_code == 0
        assert "api-style.yaml" in result.output
        assert "component-catalog.md" not in result.output


class TestKbShow:
    def test_show_existing(self, runner, kb_dir):
        with patch("sdlc.cli.kb_cmd.project_root", return_value=kb_dir.parent.parent):
            result = runner.invoke(kb, ["show", "architecture/component-catalog.md"])
        assert result.exit_code == 0
        assert "# Components" in result.output

    def test_show_missing(self, runner, kb_dir):
        with patch("sdlc.cli.kb_cmd.project_root", return_value=kb_dir.parent.parent):
            result = runner.invoke(kb, ["show", "nonexistent.md"])
        assert result.exit_code == 1
        assert "KB file not found" in result.output


class TestKbDiff:
    def test_diff_different_files(self, runner, kb_dir):
        with patch("sdlc.cli.kb_cmd.project_root", return_value=kb_dir.parent.parent):
            result = runner.invoke(
                kb,
                ["diff", "architecture/component-catalog.md", "coding/conventions.md"],
            )
        assert result.exit_code == 0
        assert "---" in result.output or "+++" in result.output

    def test_diff_identical_files(self, runner, kb_dir):
        # Create two identical files
        (kb_dir / "a.md").write_text("same content\n")
        (kb_dir / "b.md").write_text("same content\n")
        with patch("sdlc.cli.kb_cmd.project_root", return_value=kb_dir.parent.parent):
            result = runner.invoke(kb, ["diff", "a.md", "b.md"])
        assert result.exit_code == 0
        assert "Files are identical" in result.output

    def test_diff_missing_file(self, runner, kb_dir):
        with patch("sdlc.cli.kb_cmd.project_root", return_value=kb_dir.parent.parent):
            result = runner.invoke(kb, ["diff", "nonexistent.md", "also-missing.md"])
        assert result.exit_code == 1
        assert "KB file not found" in result.output


class TestKbStats:
    def test_stats_with_files(self, runner, kb_dir):
        with patch("sdlc.cli.kb_cmd.project_root", return_value=kb_dir.parent.parent):
            result = runner.invoke(kb, ["stats"])
        assert result.exit_code == 0
        assert "Files:" in result.output
        assert "Total Size:" in result.output
        assert "markdown:" in result.output
        assert "yaml:" in result.output


class TestKbScan:
    def test_scan_message(self, runner):
        result = runner.invoke(kb, ["scan"])
        assert result.exit_code == 0
        assert "not yet available" in result.output


class TestKbUpdate:
    def test_update_message(self, runner):
        result = runner.invoke(kb, ["update"])
        assert result.exit_code == 0
        assert "KB update triggered" in result.output

    def test_update_with_stage(self, runner):
        result = runner.invoke(kb, ["update", "--stage", "design"])
        assert result.exit_code == 0
        assert "design" in result.output


class TestKbReconcile:
    def test_reconcile_message(self, runner):
        result = runner.invoke(kb, ["reconcile"])
        assert result.exit_code == 0
        assert "not yet available" in result.output


# ---------------------------------------------------------------------------
# Rule command tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def rules_dir(tmp_path):
    """Create a temporary rules directory with sample YAML."""
    rdir = tmp_path / "doc" / "kb" / "rules"
    rdir.mkdir(parents=True)
    (rdir / "coding.yaml").write_text(
        "- id: NO-THREAD-SLEEP\n"
        "  level: MUST\n"
        "  category: coding\n"
        "  description: No Thread.sleep\n"
        "  enforcer: cr\n"
        "  pattern: 'java.lang.Thread.sleep'\n"
        "  message: No Thread.sleep\n"
        "  action: block\n"
        "  severity: P1\n"
        "  applies_to:\n"
        "    - '**/*.java'\n"
        "  scope:\n"
        "    stages:\n"
        "      - implement\n"
        "      - review\n"
        "- id: USE-TYPE-HINTS\n"
        "  level: SHOULD\n"
        "  category: coding\n"
        "  description: Use type hints in Python\n"
        "  enforcer: lint\n"
        "  action: warn\n"
        "  severity: P2\n"
        "  scope:\n"
        "    stages:\n"
        "      - implement\n"
    )
    return rdir


def _patch_project_root(tmp_path):
    """Patch project_root to return tmp_path (which contains doc/kb/rules)."""
    return patch("sdlc.cli.rule_cmd.project_root", return_value=tmp_path)


class TestRuleList:
    def test_list_with_rules(self, runner, rules_dir, tmp_path):
        with _patch_project_root(tmp_path):
            result = runner.invoke(rule, ["list"])
        assert result.exit_code == 0
        assert "NO-THREAD-SLEEP" in result.output
        assert "USE-TYPE-HINTS" in result.output

    def test_list_no_rules(self, runner, tmp_path):
        # No rules directory
        with _patch_project_root(tmp_path):
            result = runner.invoke(rule, ["list"])
        assert result.exit_code == 0
        assert "No rules found" in result.output

    def test_list_filter_level(self, runner, rules_dir, tmp_path):
        with _patch_project_root(tmp_path):
            result = runner.invoke(rule, ["list", "--level", "MUST"])
        assert result.exit_code == 0
        assert "NO-THREAD-SLEEP" in result.output
        # USE-TYPE-HINTS is SHOULD, should not appear in filtered output
        assert "USE-TYPE-HINTS" not in result.output

    def test_list_json_format(self, runner, rules_dir, tmp_path):
        with _patch_project_root(tmp_path):
            result = runner.invoke(rule, ["list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_filter_category(self, runner, rules_dir, tmp_path):
        with _patch_project_root(tmp_path):
            result = runner.invoke(rule, ["list", "--category", "coding"])
        assert result.exit_code == 0
        assert "NO-THREAD-SLEEP" in result.output


class TestRuleShow:
    def test_show_existing(self, runner, rules_dir, tmp_path):
        with _patch_project_root(tmp_path):
            result = runner.invoke(rule, ["show", "NO-THREAD-SLEEP"])
        assert result.exit_code == 0
        assert "NO-THREAD-SLEEP" in result.output
        assert "MUST" in result.output
        assert "No Thread.sleep" in result.output
        assert "P1" in result.output

    def test_show_missing(self, runner, rules_dir, tmp_path):
        with _patch_project_root(tmp_path):
            result = runner.invoke(rule, ["show", "FAKE-RULE"])
        assert result.exit_code == 1
        assert "Rule not found" in result.output


class TestRuleAdd:
    def test_add_from_file(self, runner, tmp_path):
        rule_file = tmp_path / "custom.yaml"
        rule_file.write_text(
            "- id: CUSTOM-001\n"
            "  level: MAY\n"
            "  category: style\n"
            "  description: Custom rule\n"
        )
        result = runner.invoke(rule, ["add", "--from-file", str(rule_file)])
        assert result.exit_code == 0
        assert "Loaded 1 rules" in result.output

    def test_add_no_file(self, runner):
        result = runner.invoke(rule, ["add"])
        assert result.exit_code == 0
        assert "Please specify --from-file" in result.output


class TestRuleDisable:
    def test_disable_existing(self, runner, rules_dir, tmp_path):
        with _patch_project_root(tmp_path):
            result = runner.invoke(rule, ["disable", "NO-THREAD-SLEEP", "--reason", "testing"])
        assert result.exit_code == 0
        assert "disabled" in result.output

    def test_disable_missing(self, runner, rules_dir, tmp_path):
        with _patch_project_root(tmp_path):
            result = runner.invoke(rule, ["disable", "FAKE-RULE"])
        assert result.exit_code == 1
        assert "Rule not found" in result.output


class TestRuleCheck:
    def test_check_stage(self, runner, rules_dir, tmp_path):
        with _patch_project_root(tmp_path):
            result = runner.invoke(rule, ["check", "implement"])
        assert result.exit_code == 0
        assert "Rules for stage 'implement'" in result.output
        assert "NO-THREAD-SLEEP" in result.output

    def test_check_empty_stage(self, runner, rules_dir, tmp_path):
        with _patch_project_root(tmp_path):
            result = runner.invoke(rule, ["check", "nonexistent-stage"])
        assert result.exit_code == 0
        assert "Rules for stage 'nonexistent-stage': 0" in result.output


class TestRuleViolations:
    def test_violations_message(self, runner):
        result = runner.invoke(rule, ["violations"])
        assert result.exit_code == 0
        assert "requires audit log" in result.output


# ---------------------------------------------------------------------------
# Config command tests
# ---------------------------------------------------------------------------


class TestConfigShow:
    def test_show_default(self, runner):
        with patch("sdlc.utils.config_loader.load_config") as mock_load:
            from sdlc.utils.config import SdlcConfig

            mock_load.return_value = SdlcConfig()
            result = runner.invoke(config, ["show"])
        assert result.exit_code == 0
        assert "LLM Provider:" in result.output
        assert "anthropic" in result.output

    def test_show_json(self, runner):
        with patch("sdlc.utils.config_loader.load_config") as mock_load:
            from sdlc.utils.config import SdlcConfig

            mock_load.return_value = SdlcConfig()
            result = runner.invoke(config, ["show", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "llm" in data


class TestConfigGet:
    def test_get_existing_key(self, runner):
        with patch("sdlc.utils.config_loader.load_config") as mock_load:
            from sdlc.utils.config import SdlcConfig

            mock_load.return_value = SdlcConfig()
            result = runner.invoke(config, ["get", "llm.provider"])
        assert result.exit_code == 0
        assert "anthropic" in result.output

    def test_get_nested_key(self, runner):
        with patch("sdlc.utils.config_loader.load_config") as mock_load:
            from sdlc.utils.config import SdlcConfig

            mock_load.return_value = SdlcConfig()
            result = runner.invoke(config, ["get", "llm.model"])
        assert result.exit_code == 0

    def test_get_missing_key(self, runner):
        with patch("sdlc.utils.config_loader.load_config") as mock_load:
            from sdlc.utils.config import SdlcConfig

            mock_load.return_value = SdlcConfig()
            result = runner.invoke(config, ["get", "nonexistent.key"])
        assert result.exit_code == 1
        assert "Key not found" in result.output


class TestConfigSet:
    def test_set_message(self, runner):
        result = runner.invoke(config, ["set", "llm.provider", "openai"])
        assert result.exit_code == 0
        assert "Set llm.provider = openai" in result.output


class TestConfigPath:
    def test_path_output(self, runner):
        result = runner.invoke(config, ["path"])
        assert result.exit_code == 0
        assert "SDLC Home:" in result.output
        assert "User Config:" in result.output
        assert "Project Config:" in result.output


class TestConfigTestLlm:
    def test_test_llm_no_keys(self, runner):
        # With no API keys set, should skip gracefully
        env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")}
        result = runner.invoke(config, ["test-llm"], env=env)
        assert result.exit_code == 0
        assert "Testing LLM connectivity" in result.output
