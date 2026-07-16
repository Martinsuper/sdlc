"""Tests for resource browsing CLI commands."""

from click.testing import CliRunner

from sdlc.cli.main import cli


def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "sdlc" in result.output
    assert "python" in result.output


def test_doctor():
    runner = CliRunner()
    # --no-check-llm keeps doctor deterministic/offline for CI
    result = runner.invoke(cli, ["doctor", "--no-check-llm"])
    assert result.exit_code == 0
    assert "Python >= 3.11" in result.output
    assert "All checks passed" in result.output


def test_completion_bash():
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "bash"])
    assert result.exit_code == 0
    assert "bashrc" in result.output


def test_completion_zsh():
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "zsh"])
    assert result.exit_code == 0
    assert "zshrc" in result.output


def test_completion_fish():
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "fish"])
    assert result.exit_code == 0
    assert "fish" in result.output


def test_completion_invalid_shell():
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "powershell"])
    assert result.exit_code != 0


# --- Stage commands ---


def test_stage_list_empty():
    runner = CliRunner()
    result = runner.invoke(cli, ["stage", "list"])
    assert result.exit_code == 0
    # Empty catalog, so "No stages found" or an empty table
    assert "No stages found" in result.output or "Pipeline Stages" in result.output


def test_stage_show_not_found():
    runner = CliRunner()
    result = runner.invoke(cli, ["stage", "show", "nonexistent"])
    assert result.exit_code == 1
    assert "Stage not found" in result.output


# --- Adapter commands ---


def test_adapter_list():
    runner = CliRunner()
    result = runner.invoke(cli, ["adapter", "list"])
    assert result.exit_code == 0
    assert "dongboot" in result.output


def test_adapter_show():
    runner = CliRunner()
    result = runner.invoke(cli, ["adapter", "show", "dongboot"])
    assert result.exit_code == 0
    assert "DongBoot" in result.output
    assert "Components" in result.output
    assert "Detect Patterns" in result.output


def test_adapter_show_not_found():
    runner = CliRunner()
    result = runner.invoke(cli, ["adapter", "show", "nonexistent"])
    assert result.exit_code == 1
    assert "Adapter not found" in result.output


def test_adapter_detect():
    runner = CliRunner()
    result = runner.invoke(cli, ["adapter", "detect", "."])
    assert result.exit_code == 0
    # Either detected adapters or "No adapters detected"
    assert "No adapters detected" in result.output or "✓" in result.output


# --- Profile commands ---


def test_profile_list():
    runner = CliRunner()
    result = runner.invoke(cli, ["profile", "list"])
    assert result.exit_code == 0
    assert "new-feature" in result.output
    assert "bug-fix" in result.output


def test_profile_show():
    runner = CliRunner()
    result = runner.invoke(cli, ["profile", "show", "new-feature"])
    assert result.exit_code == 0
    assert "新功能" in result.output
    assert "Base Stages" in result.output


def test_profile_show_not_found():
    runner = CliRunner()
    result = runner.invoke(cli, ["profile", "show", "nonexistent"])
    assert result.exit_code == 1
    assert "Profile not found" in result.output


# --- Agent commands ---


def test_agent_list():
    runner = CliRunner()
    result = runner.invoke(cli, ["agent", "list"])
    assert result.exit_code == 0
    assert "SA-1" in result.output
    # The table may truncate "requirements-analyst" with ellipsis
    assert "requirements-ana" in result.output


def test_agent_show():
    runner = CliRunner()
    result = runner.invoke(cli, ["agent", "show", "SA-1"])
    assert result.exit_code == 0
    assert "requirements-analyst" in result.output
    assert "Role:" in result.output
    assert "Model:" in result.output


def test_agent_show_not_found():
    runner = CliRunner()
    result = runner.invoke(cli, ["agent", "show", "nonexistent"])
    assert result.exit_code == 1
    assert "Subagent not found" in result.output
