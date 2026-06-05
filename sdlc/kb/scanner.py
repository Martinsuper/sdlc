"""kb — 7-stage scanner (stub for M2)."""

from pathlib import Path

from sdlc.kb.models import ScanResult


class Scanner:
    """Seven-stage project scanner. Full implementation deferred to M2."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def scan(self, depth: int = 5, no_llm: bool = False) -> ScanResult:
        """Run the 7-stage scan pipeline.

        This is a stub; the full implementation will arrive in milestone M2.
        """
        raise NotImplementedError("Scanner will be implemented in M2")
