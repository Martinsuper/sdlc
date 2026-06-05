"""kb — KnowledgeBase file I/O."""

from pathlib import Path

from sdlc.kb.models import KBLayer
from sdlc.utils.exceptions import SdlcError
from sdlc.utils.fingerprint import file_fingerprint
from sdlc.utils.time import format_iso, now_utc


class KBFileNotFoundError(SdlcError):
    """Raised when a requested KB layer does not exist."""


def _detect_type(name: str) -> str:
    """Infer the layer type from the file extension."""
    suffix = Path(name).suffix.lower()
    if suffix in (".yml", ".yaml"):
        return "yaml"
    if suffix == ".json":
        return "json"
    return "markdown"


class KnowledgeBase:
    """Represents a knowledge-base tree rooted at *root*.

    ``root`` is typically ``<project>/doc/kb/`` or ``~/.sdlc/kb/``.
    """

    def __init__(self, root: Path, scope: str = "project") -> None:
        self.root = root
        self.scope = scope
        self.layers: dict[str, KBLayer] = {}
        self._load()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Walk the KB tree and populate ``self.layers``."""
        if not self.root.is_dir():
            return
        for p in sorted(self.root.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(self.root)
            name = str(rel)
            try:
                fp = file_fingerprint(p)
                stat = p.stat()
            except (FileNotFoundError, OSError):
                continue
            self.layers[name] = KBLayer(
                name=name,
                type=_detect_type(name),
                path=p.resolve(),
                fingerprint=fp,
                last_modified=format_iso(now_utc()),
                size_bytes=stat.st_size,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, name: str) -> KBLayer:
        """Return the :class:`KBLayer` for *name*, or raise."""
        if name not in self.layers:
            raise KBFileNotFoundError(
                f"KB layer not found: {name}",
                details={"name": name, "scope": self.scope},
            )
        return self.layers[name]

    def list_layers(self, pattern: str = "**/*") -> list[KBLayer]:
        """Return layers whose name matches *pattern* (glob-style).

        Supports patterns like ``**/*.yaml``, ``architecture/*``, and
        the default ``**/*`` which matches every layer.
        """
        if pattern == "**/*":
            return list(self.layers.values())
        from pathlib import PurePosixPath

        return [
            layer
            for layer in self.layers.values()
            if PurePosixPath(layer.name).match(pattern)
        ]

    def exists(self, name: str) -> bool:
        """Return ``True`` if a layer named *name* is loaded."""
        return name in self.layers

    def read_content(self, name: str) -> str:
        """Read and return the full text content of layer *name*."""
        layer = self.get(name)
        return layer.path.read_text(encoding="utf-8")
