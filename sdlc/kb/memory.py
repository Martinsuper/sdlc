"""Memory L2: Post-stage KB auto-update engine.

After each stage run, extract learnings and update the project KB.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class MemoryL2:
    """Auto-update KB after stage completion."""

    def __init__(self, kb_root: Path | None = None, enable_semantic: bool = True) -> None:
        self._kb_root = kb_root
        self._enable_semantic = enable_semantic
        self._vector_store: Any = None  # lazily created on first semantic use

    def _get_vector_store(self) -> Any:
        """Lazily build the vector store under the KB root. Returns None if
        semantic memory is disabled or no KB root is configured."""
        if not self._enable_semantic or not self._kb_root:
            return None
        if self._vector_store is None:
            from sdlc.kb.vector_store import VectorStore

            self._vector_store = VectorStore(self._kb_root / "kb_vectors.db")
        return self._vector_store

    def index_text(self, doc_id: str, text: str, meta: dict[str, Any] | None = None) -> bool:
        """Add/replace a document in the semantic index. Returns False (no-op)
        when semantic memory is unavailable — never raises."""
        store = self._get_vector_store()
        if store is None:
            return False
        try:
            store.upsert(doc_id, text, meta or {})
            return True
        except Exception:
            return False

    def semantic_search(
        self, query: str, top_k: int = 5, where: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Return top-k semantically-relevant KB snippets for *query*.

        Degrades to an empty list (callers fall back to path/fingerprint
        retrieval) when semantic memory is unavailable, so this is always safe
        to call."""
        store = self._get_vector_store()
        if store is None:
            return []
        try:
            hits = store.search(query, top_k=top_k, where=where)
        except Exception:
            return []
        return [{"doc_id": h.doc_id, "score": h.score, "text": h.text, "meta": h.meta} for h in hits]

    def on_stage_complete(
        self,
        stage_id: str,
        result: dict[str, Any],
        pipeline_id: str | None = None,
    ) -> int:
        """Called after a stage completes. Writes learnings to KB.

        Returns the number of KB entries written.
        """
        if not self._kb_root or not self._kb_root.exists():
            return 0

        entries = self._extract_learnings(stage_id, result)
        if not entries:
            return 0

        # Write to kb/memory/ directory
        memory_dir = self._kb_root / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        short_id = uuid.uuid4().hex[:6]
        filename = f"{stage_id}-{ts}-{short_id}.json"
        filepath = memory_dir / filename

        record = {
            "stage_id": stage_id,
            "pipeline_id": pipeline_id,
            "timestamp": ts,
            "learnings": entries,
        }
        # Atomic write: write to temp file then rename
        tmp = filepath.with_suffix(".tmp")
        tmp.write_text(json.dinternal-monitorings(record, indent=2, ensure_ascii=False))
        tmp.rename(filepath)
        return len(entries)

    def _extract_learnings(
        self, stage_id: str, result: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract learnings from stage result."""
        learnings: list[dict[str, Any]] = []

        # Extract rule violations as learnings
        violations = result.get("rule_violations", [])
        for v in violations:
            learnings.append({
                "type": "rule_violation",
                "rule_id": v.get("id", ""),
                "level": v.get("level", ""),
                "message": v.get("message", ""),
                "stage": stage_id,
            })

        # Extract gate decisions
        gate_decision = result.get("gate_decision")
        if gate_decision:
            learnings.append({
                "type": "gate_decision",
                "gate_id": gate_decision.get("gate_id", "") if isinstance(gate_decision, dict) else getattr(gate_decision, "gate_id", ""),
                "action": gate_decision.get("action", "") if isinstance(gate_decision, dict) else getattr(gate_decision, "action", ""),
                "reason": gate_decision.get("reason", "") if isinstance(gate_decision, dict) else getattr(gate_decision, "reason", ""),
                "stage": stage_id,
            })

        # Extract errors
        errors = result.get("errors", [])
        if not errors:
            error = result.get("error")
            if error:
                errors = [error]
        for err in errors:
            learnings.append({
                "type": "error",
                "message": str(err),
                "stage": stage_id,
            })

        return learnings

    def get_recent_learnings(
        self, stage_id: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Retrieve recent learnings from KB memory."""
        if not self._kb_root:
            return []
        memory_dir = self._kb_root / "memory"
        if not memory_dir.exists():
            return []

        records: list[dict[str, Any]] = []
        for f in sorted(memory_dir.glob("*.json"), reverse=True)[:limit * 2]:
            try:
                data = json.loads(f.read_text())
                if stage_id and data.get("stage_id") != stage_id:
                    continue
                records.append(data)
                if len(records) >= limit:
                    break
            except (json.JSONDecodeError, OSError):
                continue
        return records
