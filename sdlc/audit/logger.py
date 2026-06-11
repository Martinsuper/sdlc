import json
import logging
import shutil
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from sdlc.audit.events import AuditEventType
from sdlc.utils.paths import ensure_dir
from sdlc.utils.time import now_utc

logger = logging.getLogger(__name__)

# Maximum log file size before rotation (100 MB)
_MAX_LOG_SIZE = 100 * 1024 * 1024
# Maximum number of rotated backup files to keep
_MAX_BACKUPS = 3


def _rotate_if_needed(path: Path) -> None:
    """Rotate the log file if it exceeds _MAX_LOG_SIZE.

    Rotation strategy: rename to .1, .2, etc. and drop files beyond
    _MAX_BACKUPS.
    """
    if not path.is_file():
        return
    try:
        size = path.stat().st_size
    except OSError:
        return
    if size < _MAX_LOG_SIZE:
        return

    # Shift existing backups: .2 -> .3, .1 -> .2
    for i in range(_MAX_BACKUPS, 1, -1):
        older = path.with_suffix(f".{i - 1}.jsonl")
        newer = path.with_suffix(f".{i}.jsonl")
        if older.is_file():
            try:
                shutil.move(str(older), str(newer))
            except OSError:
                logger.warning("Failed to rotate audit log backup %s", older)

    # Rotate current file to .1
    try:
        shutil.move(str(path), str(path.with_suffix(".1.jsonl")))
    except OSError:
        logger.warning("Failed to rotate audit log %s", path)


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
        # Rotate before writing if the file has grown too large
        _rotate_if_needed(self.log_path)

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

        # Stream processing: read line-by-line, match on the fly, keep only
        # a sliding window of the most recent *limit* matches to avoid OOM.
        # We read in reverse order (tail first) by loading lines into a small
        # buffer only when we need to reverse-iterate. For very large files,
        # we still avoid loading everything by reading backwards from the end.
        # Simple approach: read all lines but only store matches, capped at limit.
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
                # Stop collecting once we have enough to yield the most recent
                # limit items.  Keep a sliding window of at most limit matches.
                if len(matches) > limit:
                    # Drop oldest match to keep memory bounded
                    matches.pop(0)

        yield from reversed(matches)