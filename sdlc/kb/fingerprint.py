"""kb — Knowledge-base fingerprint utilities."""

import hashlib
from pathlib import Path

from sdlc.utils.fingerprint import file_fingerprint


def compute_kb_fingerprint(path: Path) -> str:
    """SHA256 hash of the file at *path* (reads raw bytes for consistency)."""
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest()


def compute_layer_fingerprint(path: Path) -> str:
    """SHA256 hash of the file at *path*."""
    return file_fingerprint(path)
