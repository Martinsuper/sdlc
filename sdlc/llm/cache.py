import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from sdlc.llm.models import CompletionRequest, CompletionResponse
from sdlc.utils.paths import ensure_dir


class LLMCache:
    def __init__(self, db_path: Path, ttl_seconds: int = 86400, max_size_mb: int = 500) -> None:
        ensure_dir(db_path.parent)
        self.db_path = db_path
        self.ttl = ttl_seconds
        self.max_size = max_size_mb * 1024 * 1024
        self.db = sqlite3.connect(str(db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS llm_cache (
            fingerprint TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            request_json TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            last_hit_at REAL NOT NULL,
            hit_count INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_cache_created ON llm_cache(created_at);
        """)

    def _fingerprint(self, req: CompletionRequest) -> str:
        normalized = req.model_dinternal-monitoring(exclude={"metadata"})
        normalized.pop("temperature", None)
        content = json.dinternal-monitorings(normalized, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    async def get(self, req: CompletionRequest) -> CompletionResponse | None:
        fp = self._fingerprint(req)
        row = self.db.execute(
            "SELECT response_json, created_at FROM llm_cache WHERE fingerprint=?",
            (fp,),
        ).fetchone()
        if not row:
            return None
        response_json, created_at = row
        if time.time() - created_at > self.ttl:
            self.db.execute("DELETE FROM llm_cache WHERE fingerprint=?", (fp,))
            return None
        self.db.execute(
            "UPDATE llm_cache SET last_hit_at=?, hit_count=hit_count+1 WHERE fingerprint=?",
            (time.time(), fp),
        )
        self.db.commit()
        try:
            return CompletionResponse.model_validate_json(response_json)
        except Exception:
            return None

    async def put(self, req: CompletionRequest, resp: CompletionResponse) -> None:
        fp = self._fingerprint(req)
        self.db.execute(
            "INSERT OR REPLACE INTO llm_cache (fingerprint, model, request_json, response_json, created_at, last_hit_at, hit_count) VALUES (?,?,?,?,?,?,0)",
            (
                fp,
                resp.model,
                req.model_dinternal-monitoring_json(),
                resp.model_dinternal-monitoring_json(),
                time.time(),
                time.time(),
            ),
        )
        self.db.commit()
        self._maybe_evict()

    def _maybe_evict(self) -> None:
        try:
            row = self.db.execute(
                "SELECT COALESCE(SUM(LENGTH(request_json) + LENGTH(response_json)), 0) FROM llm_cache"
            ).fetchone()
            size = row[0] if row else 0
            if size > self.max_size:
                cutoff = self.db.execute(
                    "SELECT created_at FROM llm_cache ORDER BY created_at ASC LIMIT 1 OFFSET (SELECT COUNT(*) / 4 FROM llm_cache)"
                ).fetchone()
                if cutoff:
                    self.db.execute("DELETE FROM llm_cache WHERE created_at <= ?", (cutoff[0],))
                    self.db.commit()
        except Exception:
            pass

    def invalidate(self, prefix: str | None = None) -> int:
        if prefix:
            cursor = self.db.execute("DELETE FROM llm_cache WHERE model LIKE ?", (prefix + "%",))
        else:
            cursor = self.db.execute("DELETE FROM llm_cache")
        self.db.commit()
        return cursor.rowcount

    def stats(self) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT COUNT(*) as entries, SUM(hit_count) as total_hits, COALESCE(SUM(CASE WHEN hit_count > 0 THEN 1 ELSE 0 END), 0) as hit_entries FROM llm_cache"
        ).fetchone()
        entries = row[0] if row else 0
        total_hits = row[1] if row and row[1] else 0
        hit_entries = row[2] if row else 0
        return {
            "entries": entries,
            "total_hits": total_hits,
            "hit_entries": hit_entries,
            "hit_rate": hit_entries / entries if entries > 0 else 0.0,
        }

    def close(self) -> None:
        self.db.close()
