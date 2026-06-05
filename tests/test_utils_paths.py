import pytest

from sdlc.utils.exceptions import ConfigError
from sdlc.utils.paths import ensure_dir, project_root, sdlc_home


def test_sdlc_home_ends_with_dot_sdlc():
    result = sdlc_home()
    assert result.name == ".sdlc"


def test_ensure_dir_creates_directory(tmp_path):
    target = tmp_path / "a" / "b" / "c"
    assert not target.exists()
    result = ensure_dir(target)
    assert target.is_dir()
    assert result == target


def test_project_root_raises_config_error(tmp_path):
    with pytest.raises(ConfigError):
        project_root(start=tmp_path)


def test_project_root_finds_pyproject_toml(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    sub = tmp_path / "src" / "pkg"
    sub.mkdir(parents=True)
    assert project_root(start=sub) == tmp_path


def test_project_root_finds_sdlc_dir(tmp_path):
    (tmp_path / ".sdlc").mkdir()
    sub = tmp_path / "sub"
    sub.mkdir()
    assert project_root(start=sub) == tmp_path


def test_project_root_default_cwd(monkeypatch, tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert project_root() == tmp_path
