"""Memory L2: Post-stage KB auto-update engine.

After each stage run, extract learnings and update the project KB.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class MemoryL2:
    """Auto-update KB after stage completion."""

    def __init__(self, kb_root: Path | None = None) -> None:
        self._kb_root = kb_root

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
        filename = f"{stage_id}-{ts}.json"
        filepath = memory_dir / filename

        record = {
            "stage_id": stage_id,
            "pipeline_id": pipeline_id,
            "timestamp": ts,
            "learnings": entries,
        }
        filepath.write_text(json.dinternal-monitorings(record, indent=2, ensure_ascii=False))
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
