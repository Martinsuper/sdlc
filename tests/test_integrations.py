"""Tests for the sdlc.integrations package."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from sdlc.integrations.filesystem import FileSystem
from sdlc.integrations.git_client import GitClient
from sdlc.integrations.http_client import HTTPClient
from sdlc.integrations.mcp_client import MCPClient
from sdlc.integrations.shell_runner import ShellResult, ShellRunner
from sdlc.integrations.whitelist import (
    ALL,
    SecurityError,
    is_command_allowed,
    validate_command_safety,
)

# ---------------------------------------------------------------------------
# whitelist.py tests
# ---------------------------------------------------------------------------


class TestIsCommandAllowed:
    """Tests for is_command_allowed."""

    def test_empty_command_not_allowed(self) -> None:
        assert is_command_allowed([]) is False

    def test_git_status_allowed(self) -> None:
        assert is_command_allowed(["git", "status"]) is True

    def test_git_commit_allowed(self) -> None:
        assert is_command_allowed(["git", "commit"]) is True

    def test_git_forbidden_subcommand(self) -> None:
        assert is_command_allowed(["git", "remote"]) is False

    def test_git_no_subcommand_allowed(self) -> None:
        # git alone is allowed since base command is in whitelist
        assert is_command_allowed(["git"]) is True

    def test_ls_allowed_any_subcommand(self) -> None:
        # ls has empty set = all subcommands allowed
        assert is_command_allowed(["ls", "-la"]) is True
        assert is_command_allowed(["ls", "/tmp"]) is True

    def test_cat_allowed_any_subcommand(self) -> None:
        assert is_command_allowed(["cat", "file.txt"]) is True

    def test_unknown_command_not_allowed(self) -> None:
        assert is_command_allowed(["rm", "-rf", "/"]) is False

    def test_python_allowed_flags(self) -> None:
        assert is_command_allowed(["python", "-m", "pytest"]) is True
        assert is_command_allowed(["python", "-c", "print(1)"]) is False  # -c removed from whitelist
        assert is_command_allowed(["python", "-V"]) is True

    def test_python_forbidden_flag(self) -> None:
        assert is_command_allowed(["python", "-O"]) is False

    def test_pip_allowed_subcommands(self) -> None:
        assert is_command_allowed(["pip", "install", "httpx"]) is True
        assert is_command_allowed(["pip", "list"]) is True
        assert is_command_allowed(["pip", "show", "httpx"]) is True

    def test_pip_forbidden_subcommand(self) -> None:
        assert is_command_allowed(["pip", "uninstall", "httpx"]) is False

    def test_docker_allowed(self) -> None:
        assert is_command_allowed(["docker", "build", "."]) is True
        assert is_command_allowed(["docker", "run", "image"]) is False  # docker run removed from whitelist

    def test_custom_whitelist(self) -> None:
        custom: dict[str, set[str]] = {"echo": ALL, "mytool": {"run"}}
        assert is_command_allowed(["echo", "hello"], whitelist=custom) is True
        assert is_command_allowed(["mytool", "run"], whitelist=custom) is True
        assert is_command_allowed(["mytool", "build"], whitelist=custom) is False
        assert is_command_allowed(["git", "status"], whitelist=custom) is False


class TestValidateCommandSafety:
    """Tests for validate_command_safety."""

    def test_safe_command_passes(self) -> None:
        # Should not raise
        validate_command_safety(["git", "status"])
        validate_command_safety(["ls", "-la"])

    def test_pipe_operator_detected(self) -> None:
        with pytest.raises(SecurityError, match="Shell operator"):
            validate_command_safety(["cat", "file.txt", "|", "grep", "foo"])

    def test_semicolon_detected(self) -> None:
        with pytest.raises(SecurityError, match="Shell operator"):
            validate_command_safety(["echo", "hello;", "rm", "-rf"])

    def test_and_operator_detected(self) -> None:
        with pytest.raises(SecurityError, match="Shell operator"):
            validate_command_safety(["git", "status", "&&", "git", "push"])

    def test_or_operator_detected(self) -> None:
        with pytest.raises(SecurityError, match="Shell operator"):
            validate_command_safety(["git", "status", "||", "echo", "fail"])

    def test_redirect_out_detected(self) -> None:
        with pytest.raises(SecurityError, match="Shell operator"):
            validate_command_safety(["echo", "hello", ">", "file.txt"])

    def test_redirect_append_detected(self) -> None:
        with pytest.raises(SecurityError, match="Shell operator"):
            validate_command_safety(["echo", "hello", ">>", "file.txt"])

    def test_redirect_in_detected(self) -> None:
        with pytest.raises(SecurityError, match="Shell operator"):
            validate_command_safety(["cat", "<", "file.txt"])

    def test_command_substitution_dollar(self) -> None:
        with pytest.raises(SecurityError, match="Command substitution"):
            validate_command_safety(["echo", "$(whoami)"])

    def test_command_substitution_backtick(self) -> None:
        with pytest.raises(SecurityError, match="Command substitution"):
            validate_command_safety(["echo", "`whoami`"])

    def test_path_traversal_detected(self) -> None:
        with pytest.raises(SecurityError, match="Path traversal"):
            validate_command_safety(["cat", "../etc/passwd"])

    def test_env_var_dollar_brace_detected(self) -> None:
        with pytest.raises(SecurityError, match="Environment variable"):
            validate_command_safety(["echo", "${HOME}"])

    def test_env_var_dollar_name_detected(self) -> None:
        with pytest.raises(SecurityError, match="Environment variable"):
            validate_command_safety(["echo", "$HOME"])


# ---------------------------------------------------------------------------
# shell_runner.py tests
# ---------------------------------------------------------------------------


class TestShellResult:
    """Tests for ShellResult dataclass."""

    def test_creation(self) -> None:
        result = ShellResult(exit_code=0, stdout="hello", stderr="", duration_ms=100)
        assert result.exit_code == 0
        assert result.stdout == "hello"
        assert result.stderr == ""
        assert result.duration_ms == 100

    def test_nonzero_exit(self) -> None:
        result = ShellResult(exit_code=1, stdout="", stderr="error", duration_ms=50)
        assert result.exit_code == 1
        assert result.stderr == "error"


class TestShellRunner:
    """Tests for ShellRunner."""

    def test_allowed_command_executes(self) -> None:
        runner = ShellRunner()
        result = runner.run(["echo", "hello"])
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert result.duration_ms >= 0

    def test_denied_command_raises_security_error(self) -> None:
        runner = ShellRunner()
        with pytest.raises(SecurityError):
            runner.run(["rm", "-rf", "/"])

    def test_shell_operator_raises_security_error(self) -> None:
        runner = ShellRunner()
        with pytest.raises(SecurityError, match="Shell operator"):
            runner.run(["echo", "hello", "|", "grep", "h"])

    def test_custom_whitelist(self) -> None:
        runner = ShellRunner(whitelist={"echo": ALL})
        result = runner.run(["echo", "custom"])
        assert result.exit_code == 0
        assert "custom" in result.stdout

    def test_custom_whitelist_denies_others(self) -> None:
        runner = ShellRunner(whitelist={"echo": ALL})
        with pytest.raises(SecurityError, match="Command not allowed"):
            runner.run(["git", "status"])

    def test_timeout_propagated(self) -> None:
        runner = ShellRunner(whitelist={"sleep": ALL}, default_timeout=1)
        with pytest.raises(subprocess.TimeoutExpired):
            runner.run(["sleep", "10"], timeout=1)

    def test_cwd_parameter(self) -> None:
        runner = ShellRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.run(["ls"], cwd=Path(tmpdir))
            assert result.exit_code == 0

    def test_command_with_path_traversal_raises(self) -> None:
        runner = ShellRunner()
        with pytest.raises(SecurityError, match="Path traversal"):
            runner.run(["cat", "../etc/passwd"])


# ---------------------------------------------------------------------------
# http_client.py tests
# ---------------------------------------------------------------------------


class TestHTTPClient:
    """Tests for HTTPClient using respx for mocking."""

    @respx.mock
    def test_get(self) -> None:
        respx.get("https://example.com/api").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        with HTTPClient() as client:
            resp = client.get("https://example.com/api")
            assert resp.status_code == 200
            assert resp.json() == {"status": "ok"}

    @respx.mock
    def test_post(self) -> None:
        respx.post("https://example.com/api").mock(
            return_value=httpx.Response(201, json={"created": True})
        )
        with HTTPClient() as client:
            resp = client.post("https://example.com/api", json={"name": "test"})
            assert resp.status_code == 201
            assert resp.json() == {"created": True}

    @respx.mock
    def test_put(self) -> None:
        respx.put("https://example.com/api/1").mock(
            return_value=httpx.Response(200, json={"updated": True})
        )
        with HTTPClient() as client:
            resp = client.put("https://example.com/api/1", json={"name": "updated"})
            assert resp.status_code == 200
            assert resp.json() == {"updated": True}

    @respx.mock
    def test_delete(self) -> None:
        respx.delete("https://example.com/api/1").mock(
            return_value=httpx.Response(204)
        )
        with HTTPClient() as client:
            resp = client.delete("https://example.com/api/1")
            assert resp.status_code == 204

    def test_context_manager(self) -> None:
        client = HTTPClient()
        client.__enter__()
        # Should not raise
        client.__exit__(None, None, None)

    @respx.mock
    def test_custom_timeout(self) -> None:
        respx.get("https://example.com/api").mock(
            return_value=httpx.Response(200, text="ok")
        )
        client = HTTPClient(timeout=10)
        resp = client.get("https://example.com/api")
        assert resp.status_code == 200
        client.close()


# ---------------------------------------------------------------------------
# git_client.py tests
# ---------------------------------------------------------------------------


class TestGitClient:
    """Tests for GitClient with mocked subprocess."""

    def _mock_run(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> MagicMock:
        mock = MagicMock()
        mock.stdout = stdout
        mock.stderr = stderr
        mock.returncode = returncode
        return mock

    @patch("sdlc.integrations.git_client.subprocess.run")
    def test_current_branch(self, mock_run: MagicMock) -> None:
        mock_run.return_value = self._mock_run(stdout="main\n")
        client = GitClient()
        assert client.current_branch() == "main"
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "rev-parse", "--abbrev-ref", "HEAD"]

    @patch("sdlc.integrations.git_client.subprocess.run")
    def test_current_sha(self, mock_run: MagicMock) -> None:
        sha = "abc123def456"
        mock_run.return_value = self._mock_run(stdout=sha + "\n")
        client = GitClient()
        assert client.current_sha() == sha
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "rev-parse", "HEAD"]

    @patch("sdlc.integrations.git_client.subprocess.run")
    def test_is_clean_true(self, mock_run: MagicMock) -> None:
        mock_run.return_value = self._mock_run(stdout="")
        client = GitClient()
        assert client.is_clean() is True

    @patch("sdlc.integrations.git_client.subprocess.run")
    def test_is_clean_false(self, mock_run: MagicMock) -> None:
        mock_run.return_value = self._mock_run(stdout="M file.py\n")
        client = GitClient()
        assert client.is_clean() is False

    @patch("sdlc.integrations.git_client.subprocess.run")
    def test_diff(self, mock_run: MagicMock) -> None:
        diff_output = "diff --git a/file.py b/file.py\n+new line\n"
        mock_run.return_value = self._mock_run(stdout=diff_output)
        client = GitClient()
        assert client.diff() == diff_output
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "diff"]

    @patch("sdlc.integrations.git_client.subprocess.run")
    def test_diff_staged(self, mock_run: MagicMock) -> None:
        diff_output = "diff --git a/file.py b/file.py\n+staged change\n"
        mock_run.return_value = self._mock_run(stdout=diff_output)
        client = GitClient()
        assert client.diff(staged=True) == diff_output
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "diff", "--staged"]

    @patch("sdlc.integrations.git_client.subprocess.run")
    def test_log(self, mock_run: MagicMock) -> None:
        log_output = "abc123 commit msg\ndef456 another msg\n"
        mock_run.return_value = self._mock_run(stdout=log_output)
        client = GitClient()
        result = client.log(n=5, oneline=True)
        assert result == log_output
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "log", "-5", "--oneline"]

    @patch("sdlc.integrations.git_client.subprocess.run")
    def test_log_no_oneline(self, mock_run: MagicMock) -> None:
        log_output = "commit abc123\nAuthor: test\n\n    msg\n"
        mock_run.return_value = self._mock_run(stdout=log_output)
        client = GitClient()
        result = client.log(n=3, oneline=False)
        assert result == log_output
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "log", "-3"]

    @patch("sdlc.integrations.git_client.subprocess.run")
    def test_list_files(self, mock_run: MagicMock) -> None:
        files_output = "src/main.py\nsrc/utils.py\nREADME.md\n"
        mock_run.return_value = self._mock_run(stdout=files_output)
        client = GitClient()
        result = client.list_files()
        assert result == ["src/main.py", "src/utils.py", "README.md"]

    @patch("sdlc.integrations.git_client.subprocess.run")
    def test_list_files_empty(self, mock_run: MagicMock) -> None:
        mock_run.return_value = self._mock_run(stdout="")
        client = GitClient()
        assert client.list_files() == []

    @patch("sdlc.integrations.git_client.subprocess.run")
    def test_cwd_propagated(self, mock_run: MagicMock) -> None:
        mock_run.return_value = self._mock_run(stdout="main\n")
        client = GitClient(cwd=Path("/tmp/myrepo"))
        client.current_branch()
        call_args = mock_run.call_args
        assert call_args[1]["cwd"] == Path("/tmp/myrepo")


# ---------------------------------------------------------------------------
# filesystem.py tests
# ---------------------------------------------------------------------------


class TestFileSystem:
    """Tests for FileSystem."""

    def test_read_file(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "test.txt"
        file_path.write_text("hello world")
        fs = FileSystem(project_root=tmp_dir)
        assert fs.read_file(file_path) == "hello world"

    def test_read_file_not_found(self, tmp_dir: Path) -> None:
        fs = FileSystem(project_root=tmp_dir)
        with pytest.raises(FileNotFoundError):
            fs.read_file(tmp_dir / "nonexistent.txt")

    def test_read_file_is_directory(self, tmp_dir: Path) -> None:
        sub_dir = tmp_dir / "subdir"
        sub_dir.mkdir()
        fs = FileSystem(project_root=tmp_dir)
        with pytest.raises(ValueError, match="not a file"):
            fs.read_file(sub_dir)

    def test_write_file(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "output.txt"
        fs = FileSystem(project_root=tmp_dir)
        fs.write_file(file_path, "hello")
        assert file_path.read_text() == "hello"

    def test_write_file_creates_parent_dirs(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "deep" / "nested" / "dir" / "file.txt"
        fs = FileSystem(project_root=tmp_dir)
        fs.write_file(file_path, "content")
        assert file_path.read_text() == "content"

    def test_write_file_overwrite(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "file.txt"
        fs = FileSystem(project_root=tmp_dir)
        fs.write_file(file_path, "first")
        fs.write_file(file_path, "second")
        assert file_path.read_text() == "second"

    def test_list_files(self, tmp_dir: Path) -> None:
        (tmp_dir / "a.txt").write_text("a")
        (tmp_dir / "b.txt").write_text("b")
        (tmp_dir / "sub").mkdir()
        (tmp_dir / "sub" / "c.txt").write_text("c")
        fs = FileSystem(project_root=tmp_dir)
        files = fs.list_files(tmp_dir, pattern="*.txt")
        names = [f.name for f in files]
        assert "a.txt" in names
        assert "b.txt" in names
        assert "c.txt" not in names  # not in top-level glob

    def test_list_files_recursive(self, tmp_dir: Path) -> None:
        (tmp_dir / "a.txt").write_text("a")
        (tmp_dir / "sub").mkdir()
        (tmp_dir / "sub" / "c.txt").write_text("c")
        fs = FileSystem(project_root=tmp_dir)
        files = fs.list_files(tmp_dir, pattern="**/*.txt")
        names = [f.name for f in files]
        assert "a.txt" in names
        assert "c.txt" in names

    def test_list_files_not_directory(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "file.txt"
        file_path.write_text("x")
        fs = FileSystem(project_root=tmp_dir)
        with pytest.raises(ValueError, match="not a directory"):
            fs.list_files(file_path)

    def test_file_info(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "info.txt"
        file_path.write_text("some content here")
        fs = FileSystem(project_root=tmp_dir)
        info = fs.file_info(file_path)
        assert info["size"] == len("some content here")
        assert info["is_file"] is True
        assert "modified" in info
        assert "mode" in info
        assert str(file_path.resolve()) == info["path"]

    def test_file_info_not_found(self, tmp_dir: Path) -> None:
        fs = FileSystem(project_root=tmp_dir)
        with pytest.raises(FileNotFoundError):
            fs.file_info(tmp_dir / "nonexistent.txt")

    def test_file_info_is_directory(self, tmp_dir: Path) -> None:
        fs = FileSystem(project_root=tmp_dir)
        with pytest.raises(ValueError, match="not a file"):
            fs.file_info(tmp_dir)

    def test_read_file_custom_encoding(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "utf8.txt"
        file_path.write_text("héllo", encoding="utf-8")
        fs = FileSystem(project_root=tmp_dir)
        assert fs.read_file(file_path, encoding="utf-8") == "héllo"


# ---------------------------------------------------------------------------
# mcp_client.py and skill_runner.py tests are in
# tests/test_integrations_mcp_skill.py
# ---------------------------------------------------------------------------

