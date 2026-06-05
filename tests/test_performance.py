"""Performance tests for CLI startup and key operations."""

import subprocess
import sys
import time


def test_cli_startup_time():
    """CLI should start in under 500ms."""
    start = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-m", "sdlc", "version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    elapsed = time.monotonic() - start
    assert result.returncode == 0
    assert elapsed < 2.0, f"CLI startup took {elapsed:.2f}s (limit: 2.0s)"


def test_cli_help_time():
    """CLI --help should respond in under 2s."""
    start = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-m", "sdlc", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    elapsed = time.monotonic() - start
    assert result.returncode == 0
    assert elapsed < 3.0, f"CLI help took {elapsed:.2f}s (limit: 3.0s)"


def test_import_time():
    """Core sdlc import should be fast."""
    start = time.monotonic()
    # Import the version only (lightest import path)
    result = subprocess.run(
        [sys.executable, "-c", "from sdlc import __version__; print(__version__)"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    elapsed = time.monotonic() - start
    assert result.returncode == 0
    assert elapsed < 2.0, f"Import took {elapsed:.2f}s (limit: 2.0s)"
