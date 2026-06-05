"""kb — Knowledge-base fingerprint utilities."""

import hashlib
from pathlib import Path

from sdlc.utils.fingerprint import file_fingerprint


def compute_kb_fingerprint(content: str) -> str:
    """SHA256 hash of *content* string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_layer_fingerprint(path: Path) -> str:
    """SHA256 hash of the file at *path*."""
    return file_fingerprint(path)
