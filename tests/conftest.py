"""Shared test fixtures for sdlc test suite."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sdlc_home(tmp_dir, monkeypatch):
    """Override ~/.sdlc with a temp directory for isolation."""
    home = tmp_dir / ".sdlc"
    home.mkdir()
    monkeypatch.setenv("HOME", str(tmp_dir))
    return home
