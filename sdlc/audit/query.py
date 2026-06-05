from datetime import datetime
from typing import Any

from sdlc.audit.events import AuditEventType
from sdlc.audit.logger import AuditLogger


def count_events(
    logger: AuditLogger,
    event_type: AuditEventType | None = None,
    pipeline_id: str | None = None,
    since: datetime | None = None,
) -> int:
    return sum(1 for _ in logger.query(event_type=event_type, pipeline_id=pipeline_id, since=since))


def get_latest(
    logger: AuditLogger,
    event_type: AuditEventType | None = None,
    pipeline_id: str | None = None,
    n: int = 5,
) -> list[dict[str, Any]]:
    return list(logger.query(event_type=event_type, pipeline_id=pipeline_id, limit=n))


def summarize(logger: AuditLogger, pipeline_id: str | None = None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in logger.query(pipeline_id=pipeline_id, limit=10000):
        t = event.get("type", "unknown")
        counts[t] = counts.get(t, 0) + 1
    return counts
