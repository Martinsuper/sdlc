"""Plugin packaging (M-C1).

Packs a validated plugin directory into a single ``.sdlcpkg`` (gzip tar) with a
content checksum written back into the manifest, ready for marketplace upload
(M-C2). Packing validates first — a broken plugin should never be publishable.
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

from sdlc.plugin.manifest import MANIFEST_FILENAME, PluginManifest
from sdlc.plugin.validator import PluginValidator

PKG_SUFFIX = ".sdlcpkg"


def _dir_checksum(plugin_dir: Path) -> str:
    """Stable SHA-256 over all files except the manifest (which stores the
    checksum itself). Sorted for determinism."""
    h = hashlib.sha256()
    for f in sorted(plugin_dir.rglob("*")):
        if f.is_file() and f.name != MANIFEST_FILENAME:
            h.update(f.relative_to(plugin_dir).as_posix().encode())
            h.update(f.read_bytes())
    return "sha256:" + h.hexdigest()


def pack(plugin_dir: Path, out_dir: Path | None = None) -> Path:
    """Validate then pack ``plugin_dir`` into ``<id>-<version>.sdlcpkg``.

    Raises ValueError if validation fails. Returns the archive path."""
    report = PluginValidator().validate(plugin_dir)
    if not report.ok:
        raise ValueError("Plugin failed validation:\n  " + "\n  ".join(report.errors))

    manifest = PluginManifest.load(plugin_dir)
    manifest.checksum = _dir_checksum(plugin_dir)

    out_dir = out_dir or plugin_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"{manifest.id}-{manifest.version}{PKG_SUFFIX}"

    with tarfile.open(archive, "w:gz") as tar:
        # Write the checksum-updated manifest from memory (not the on-disk one).
        manifest_bytes = (manifest.to_json() + "\n").encode("utf-8")
        info = tarfile.TarInfo(name=MANIFEST_FILENAME)
        info.size = len(manifest_bytes)
        tar.addfile(info, io.BytesIO(manifest_bytes))
        # Add every other file under its plugin-relative path.
        for f in sorted(plugin_dir.rglob("*")):
            if f.is_file() and f.name != MANIFEST_FILENAME:
                tar.add(f, arcname=f.relative_to(plugin_dir).as_posix())
    return archive


def read_manifest_from_pkg(archive: Path) -> PluginManifest:
    """Extract just the manifest from a .sdlcpkg (used by the marketplace)."""
    with tarfile.open(archive, "r:gz") as tar:
        member = tar.extractfile(MANIFEST_FILENAME)
        if member is None:
            raise ValueError(f"No {MANIFEST_FILENAME} in {archive}")
        return PluginManifest.from_dict(json.loads(member.read().decode("utf-8")))
