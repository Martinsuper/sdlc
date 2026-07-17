"""Installer for marketplace plugins (M-C2).

Unpacks a .sdlcpkg into the user extension dir (~/.sdlc/ext/<id>/) so the
existing 4-layer loader picks it up automatically — no separate plugin loader.
Verifies the package's checksum against the registry entry before installing.
"""

from __future__ import annotations

import tarfile
from pathlib import Path
from typing import IO

from sdlc.market.registry_client import RegistryEntry
from sdlc.market.trust import TrustError, verify_checksum
from sdlc.plugin.manifest import MANIFEST_FILENAME, PluginManifest


def ext_dir() -> Path:
    from sdlc.utils.paths import sdlc_home

    return sdlc_home() / "ext"


def install_package(
    pkg_path: Path, entry: RegistryEntry | None = None, dest: Path | None = None
) -> Path:
    """Verify (if a registry entry with a checksum is given) then unpack a
    .sdlcpkg into <ext>/<id>/. Returns the install dir.

    Raises TrustError on checksum mismatch and ValueError on a malformed
    package (no manifest)."""
    if entry is not None and entry.checksum and not verify_checksum(pkg_path, entry.checksum):
        raise TrustError(f"checksum mismatch for {pkg_path.name}")

    dest_root = dest or ext_dir()
    with tarfile.open(pkg_path, "r:gz") as tar:
        member = tar.extractfile(MANIFEST_FILENAME)
        if member is None:
            raise ValueError(f"no {MANIFEST_FILENAME} in package")
        manifest = PluginManifest.from_dict(_read_json(member))
        install_dir = dest_root / manifest.id
        install_dir.mkdir(parents=True, exist_ok=True)
        _safe_extract(tar, install_dir)
    return install_dir


def _read_json(member: IO[bytes]) -> dict[str, object]:
    import json

    data = json.loads(member.read().decode("utf-8"))
    return data if isinstance(data, dict) else {}


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    """Extract members, rejecting path traversal (absolute paths / '..') so a
    malicious package cannot write outside the install dir."""
    dest = dest.resolve()
    for m in tar.getmembers():
        target = (dest / m.name).resolve()
        if not str(target).startswith(str(dest)):
            raise ValueError(f"unsafe path in package: {m.name}")
    tar.extractall(dest)
