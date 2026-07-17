"""Trust verification for marketplace installs (M-C2).

A downloaded package's content checksum must match the registry entry's before
install — the baseline defense against tampered/corrupted packages. Signature
verification is a stronger optional layer; here we ship checksum matching and a
signature hook the marketplace can populate.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def compute_checksum(data: bytes) -> str:
    """sha256 of raw bytes, formatted like the registry stores it."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def verify_checksum(pkg_path: Path, expected: str) -> bool:
    """True if the package's checksum matches the expected registry value.

    An empty expected value means the registry did not pin a checksum — treated
    as unverifiable (returns False) so install can warn rather than trust
    blindly."""
    if not expected:
        return False
    return compute_checksum(pkg_path.read_bytes()) == expected


class TrustError(Exception):
    """Raised when a package fails trust verification."""
