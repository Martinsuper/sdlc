"""Registry client for the plugin marketplace (M-C2).

Starts as a static index.json (GitHub-hosted, zero ops) — a list of plugin
entries with id/type/version/download_url/checksum/trust metadata. The client
reads and searches it; a private registry is just a different URL (reusing the
config-layer override idea), so enterprises can self-host.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REGISTRY_SCHEMA_VERSION = "1"


@dataclass
class RegistryEntry:
    id: str
    type: str
    version: str
    download_url: str = ""
    sdlc_version: str = ">=2.0,<3.0"
    author: str = ""
    verified: bool = False
    checksum: str = ""
    downloads: int = 0
    rating: float = 0.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RegistryEntry:
        return cls(
            id=str(d.get("id", "")),
            type=str(d.get("type", "")),
            version=str(d.get("version", "")),
            download_url=str(d.get("download_url", "")),
            sdlc_version=str(d.get("sdlc_version", ">=2.0,<3.0")),
            author=str(d.get("author", "")),
            verified=bool(d.get("verified", False)),
            checksum=str(d.get("checksum", "")),
            downloads=int(d.get("downloads", 0)),
            rating=float(d.get("rating", 0.0)),
        )


@dataclass
class Registry:
    schema_version: str = REGISTRY_SCHEMA_VERSION
    plugins: list[RegistryEntry] = field(default_factory=list)


class RegistryClient:
    """Loads a registry from a local file or an HTTP URL and searches it."""

    def __init__(self, source: str) -> None:
        self.source = source

    def _load_raw(self) -> dict[str, Any]:
        if self.source.startswith(("http://", "https://")):
            import httpx

            resp = httpx.get(self.source, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
        else:
            data = json.loads(Path(self.source).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    def load(self) -> Registry:
        raw = self._load_raw()
        plugins = [RegistryEntry.from_dict(p) for p in raw.get("plugins", []) if isinstance(p, dict)]
        return Registry(
            schema_version=str(raw.get("schema_version", REGISTRY_SCHEMA_VERSION)),
            plugins=plugins,
        )

    def search(self, keyword: str = "", type_filter: str | None = None) -> list[RegistryEntry]:
        """Search by substring over id/author, optionally filtered by type.

        Results are ranked verified-first, then by downloads — so official,
        popular content surfaces above unknown entries (cold-start strategy)."""
        kw = keyword.lower()
        results = [
            e
            for e in self.load().plugins
            if (not kw or kw in e.id.lower() or kw in e.author.lower())
            and (type_filter is None or e.type == type_filter)
        ]
        results.sort(key=lambda e: (not e.verified, -e.downloads))
        return results

    def find(self, plugin_id: str) -> RegistryEntry | None:
        return next((e for e in self.load().plugins if e.id == plugin_id), None)
