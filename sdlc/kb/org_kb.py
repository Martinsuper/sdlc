"""Organization-level KB sharing (M-B5).

Adds an org layer beneath the existing project/global KB, so cross-team norms
(rules, standards, architecture, anti-patterns) can be inherited and then
overridden locally — the same override-priority idea as the 4-layer config
loader, applied to KB entries.

Precedence (low → high): org  <  global  <  project. A project entry with the
same key wins over the org's. Org entries are fetched from a source (server or a
local snapshot dir); when no org source is configured this degrades to
project-only, so a team without org KB is unaffected.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Layer precedence — later layers override earlier ones on key collision.
_LAYER_ORDER = ("org", "global", "project")


@dataclass
class KBEntry:
    key: str
    content: str
    layer: str  # org | global | project
    kind: str = "note"  # rule | standard | architecture | pattern | anti-pattern | note
    meta: dict[str, Any] = field(default_factory=dict)


def _load_layer(directory: Path | None, layer: str) -> dict[str, KBEntry]:
    """Load a layer's entries from a directory of JSON files (one entry each).

    Missing/unreadable directories yield an empty layer — a layer is always
    optional, so absence never errors."""
    entries: dict[str, KBEntry] = {}
    if directory is None or not directory.exists():
        return entries
    for f in sorted(directory.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        key = str(d.get("key") or f.stem)
        entries[key] = KBEntry(
            key=key,
            content=str(d.get("content", "")),
            layer=layer,
            kind=str(d.get("kind", "note")),
            meta=d.get("meta", {}) or {},
        )
    return entries


class OrgKB:
    """Merges org/global/project KB layers with project-wins precedence.

    Any layer directory may be None (that layer is simply absent). subscriptions
    optionally restrict which org 'kind's are inherited (a team can subscribe to
    only the domains it cares about)."""

    def __init__(
        self,
        org_dir: Path | None = None,
        global_dir: Path | None = None,
        project_dir: Path | None = None,
        subscriptions: set[str] | None = None,
    ) -> None:
        self.org_dir = org_dir
        self.global_dir = global_dir
        self.project_dir = project_dir
        self.subscriptions = subscriptions  # None = inherit all org kinds

    @property
    def has_org(self) -> bool:
        return self.org_dir is not None and self.org_dir.exists()

    def _layers(self) -> dict[str, dict[str, KBEntry]]:
        org = _load_layer(self.org_dir, "org")
        if self.subscriptions is not None:
            org = {k: e for k, e in org.items() if e.kind in self.subscriptions}
        return {
            "org": org,
            "global": _load_layer(self.global_dir, "global"),
            "project": _load_layer(self.project_dir, "project"),
        }

    def merged(self) -> dict[str, KBEntry]:
        """Return the effective KB: later layers override earlier by key."""
        layers = self._layers()
        out: dict[str, KBEntry] = {}
        for layer in _LAYER_ORDER:
            out.update(layers[layer])
        return out

    def get(self, key: str) -> KBEntry | None:
        return self.merged().get(key)

    def overridden_keys(self) -> list[str]:
        """Keys where a higher layer shadows an org entry — useful to show a
        team what local decisions diverge from org norms."""
        layers = self._layers()
        org_keys = set(layers["org"])
        higher = set(layers["global"]) | set(layers["project"])
        return sorted(org_keys & higher)

    def by_kind(self, kind: str) -> list[KBEntry]:
        return [e for e in self.merged().values() if e.kind == kind]
