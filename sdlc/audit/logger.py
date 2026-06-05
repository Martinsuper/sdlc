import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from sdlc.audit.events import AuditEventType
from sdlc.utils.paths import ensure_dir
from sdlc.utils.time import now_utc


class AuditLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        ensure_dir(log_path.parent)

    def emit(
        self,
        event_type: AuditEventType,
        payload: dict[str, Any],
        pipeline_id: str | None = None,
    ) -> None:
        event = {
            "ts": now_utc().isoformat(),
            "type": event_type.value,
            "pipeline_id": pipeline_id,
            "payload": payload,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dinternal-monitorings(event, ensure_ascii=False, default=str) + "\n")

    def query(
        self,
        event_type: AuditEventType | str | None = None,
        pipeline_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> Iterator[dict[str, Any]]:
        if not self.log_path.is_file():
            return
        matches: list[dict[str, Any]] = []
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event_type is not None:
                    type_val = (
                        event_type.value if isinstance(event_type, AuditEventType) else event_type
                    )
                    if event.get("type") != type_val:
                        continue
                if pipeline_id is not None and event.get("pipeline_id") != pipeline_id:
                    continue
                if since is not None:
                    try:
                        event_ts = datetime.fromisoformat(event["ts"])
                        if event_ts < since:
                            continue
                    except (KeyError, ValueError):
                        continue
                matches.append(event)
        yield from reversed(matches[-limit:])
