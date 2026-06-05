"""kb — Weekly KB reconciler."""

from __future__ import annotations

from sdlc.audit import AuditEventType, AuditLogger
from sdlc.kb.fingerprint import compute_layer_fingerprint
from sdlc.kb.knowledge_base import KnowledgeBase
from sdlc.state import StateStore


class Reconciler:
    """Weekly KB reconciler.

    Checks for duplicate entries, health issues, and stale fingerprints.
    """

    def __init__(
        self,
        kb: KnowledgeBase,
        state: StateStore | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self.kb = kb
        self.state = state
        self.audit = audit

    def run(self) -> list[str]:
        """Run the weekly reconciliation pass.

        Returns a list of issue descriptions found during reconciliation.
        """
        issues: list[str] = []
        # 1. Check for duplicate KB entries (fingerprint-based)
        issues.extend(self._check_duplicates())
        # 2. Check KB health (missing required files, empty files)
        issues.extend(self._check_health())
        # 3. Check for stale fingerprints
        issues.extend(self._check_fingerprints())
        # Emit audit event
        self._emit_reconcile(issues)
        return issues

    # ------------------------------------------------------------------
    # Internal checks
    # ------------------------------------------------------------------

    def _check_duplicates(self) -> list[str]:
        """Check for duplicate content in KB files (fingerprint-based)."""
        issues: list[str] = []
        seen_fingerprints: dict[str, str] = {}
        for layer in self.kb.list_layers():
            if layer.fingerprint in seen_fingerprints:
                issues.append(
                    f"Duplicate content: {layer.name} same as {seen_fingerprints[layer.fingerprint]}"
                )
            else:
                seen_fingerprints[layer.fingerprint] = layer.name
        return issues

    def _check_health(self) -> list[str]:
        """Check KB file health: empty files and missing critical files."""
        issues: list[str] = []
        # Check for empty files
        for layer in self.kb.list_layers():
            if layer.size_bytes == 0:
                issues.append(f"Empty KB file: {layer.name}")
        # Check for missing critical files (only if kb is project-scoped)
        if self.kb.scope == "project":
            critical = ["conventions.md"]
            for name in critical:
                if not self.kb.exists(name):
                    issues.append(f"Missing critical KB file: {name}")
        return issues

    def _check_fingerprints(self) -> list[str]:
        """Check if stored fingerprints match actual file content."""
        issues: list[str] = []
        for layer in self.kb.list_layers():
            try:
                actual = compute_layer_fingerprint(layer.path)
            except FileNotFoundError:
                issues.append(f"Missing KB file on disk: {layer.name}")
                continue
            if actual != layer.fingerprint:
                issues.append(f"Fingerprint mismatch: {layer.name} (KB stale, needs refresh)")
        return issues

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def _emit_reconcile(self, issues: list[str]) -> None:
        """Emit an audit event for the reconciliation run."""
        if self.audit is None:
            return
        self.audit.emit(
            AuditEventType.KB_UPDATED,
            payload={
                "action": "reconcile",
                "issue_count": len(issues),
                "issues": issues[:20],
            },
        )
