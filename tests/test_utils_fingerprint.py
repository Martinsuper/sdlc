from pathlib import Path

import pytest

from sdlc.utils.fingerprint import dir_fingerprint, file_fingerprint


def test_file_fingerprint_same_content(tmp_dir):
    f1 = tmp_dir / "a.txt"
    f2 = tmp_dir / "b.txt"
    f1.write_text("hello")
    f2.write_text("hello")
    assert file_fingerprint(f1) == file_fingerprint(f2)


def test_file_fingerprint_different_content(tmp_dir):
    f1 = tmp_dir / "a.txt"
    f2 = tmp_dir / "b.txt"
    f1.write_text("hello")
    f2.write_text("world")
    assert file_fingerprint(f1) != file_fingerprint(f2)


def test_file_fingerprint_not_found():
    with pytest.raises(FileNotFoundError):
        file_fingerprint(Path("/nonexistent_file_xyz"))


def test_dir_fingerprint_stable(tmp_dir):
    (tmp_dir / "x.txt").write_text("x")
    (tmp_dir / "y.txt").write_text("y")
    h1 = dir_fingerprint(tmp_dir)
    h2 = dir_fingerprint(tmp_dir)
    assert h1 == h2


def test_dir_fingerprint_empty_dir(tmp_dir):
    h = dir_fingerprint(tmp_dir)
    assert isinstance(h, str)
    assert len(h) == 64
