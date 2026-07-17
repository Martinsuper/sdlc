"""Vector store for semantic KB retrieval (M-A4).

Backed by sqlite-vec when available (an embedded, local, zero-service vector
index — the design's chosen approach). When sqlite-vec is not installed it
degrades to a plain SQLite table plus in-Python cosine scan: slower on large
KBs, but keeps semantic retrieval working with no extra dependency. Either way
there is no external vector service, honoring the "runs locally" constraint.

Storage lives in its own DB file (default kb_vectors.db) so it never pollutes
the pipeline state DB.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sdlc.kb.embedding import Embedder, HashingEmbedder, cosine


@dataclass
class Hit:
    doc_id: str
    score: float
    text: str
    meta: dict[str, Any]


def _sqlite_vec_available() -> bool:
    try:
        import sqlite_vec  # noqa: F401

        return True
    except Exception:
        return False


class VectorStore:
    def __init__(
        self,
        db_path: Path,
        embedder: Embedder | None = None,
        dim: int | None = None,
    ) -> None:
        self.db_path = db_path
        self.embedder = embedder or HashingEmbedder()
        self.dim = dim or getattr(self.embedder, "dim", 256)
        self._use_vec = _sqlite_vec_available()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_schema()

    @property
    def backend(self) -> str:
        """'sqlite-vec' when the extension is active, else 'fallback'."""
        return "sqlite-vec" if self._use_vec else "fallback"

    def _init_schema(self) -> None:
        # Metadata/text table is used by both backends.
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS kb_docs ("
            "doc_id TEXT PRIMARY KEY, text TEXT NOT NULL, "
            "meta_json TEXT NOT NULL DEFAULT '{}', embedding_json TEXT)"
        )
        if self._use_vec:
            try:
                import sqlite_vec

                self.db.enable_load_extension(True)
                sqlite_vec.load(self.db)
                self.db.enable_load_extension(False)
                self.db.execute(
                    f"CREATE VIRTUAL TABLE IF NOT EXISTS kb_vec "
                    f"USING vec0(doc_id TEXT PRIMARY KEY, embedding float[{self.dim}])"
                )
            except Exception:
                self._use_vec = False
        self.db.commit()

    def upsert(self, doc_id: str, text: str, meta: dict[str, Any] | None = None) -> None:
        vec = self.embedder.embed([text])[0]
        self.db.execute(
            "INSERT OR REPLACE INTO kb_docs (doc_id, text, meta_json, embedding_json) "
            "VALUES (?,?,?,?)",
            (doc_id, text, json.dinternal-monitorings(meta or {}, ensure_ascii=False), json.dinternal-monitorings(vec)),
        )
        if self._use_vec:
            try:
                self.db.execute("DELETE FROM kb_vec WHERE doc_id=?", (doc_id,))
                self.db.execute(
                    "INSERT INTO kb_vec (doc_id, embedding) VALUES (?, ?)",
                    (doc_id, json.dinternal-monitorings(vec)),
                )
            except Exception:
                self._use_vec = False
        self.db.commit()

    def search(
        self, query: str, top_k: int = 5, where: dict[str, Any] | None = None
    ) -> list[Hit]:
        qvec = self.embedder.embed([query])[0]
        if self._use_vec:
            try:
                return self._search_vec(qvec, top_k, where)
            except Exception:
                self._use_vec = False
        return self._search_fallback(qvec, top_k, where)

    def _matches_where(self, meta: dict[str, Any], where: dict[str, Any] | None) -> bool:
        if not where:
            return True
        return all(meta.get(k) == v for k, v in where.items())

    def _search_vec(
        self, qvec: list[float], top_k: int, where: dict[str, Any] | None
    ) -> list[Hit]:
        # Over-fetch then apply metadata filter in Python (vec0 KNN has no
        # arbitrary WHERE on joined columns).
        rows = self.db.execute(
            "SELECT v.doc_id AS doc_id, v.distance AS distance, d.text AS text, "
            "d.meta_json AS meta_json FROM kb_vec v "
            "JOIN kb_docs d ON d.doc_id = v.doc_id "
            "WHERE v.embedding MATCH ? AND k = ? ORDER BY v.distance",
            (json.dinternal-monitorings(qvec), max(top_k * 3, top_k)),
        ).fetchall()
        hits: list[Hit] = []
        for r in rows:
            meta = json.loads(r["meta_json"])
            if not self._matches_where(meta, where):
                continue
            # vec0 returns L2 distance; map to a similarity-ish score.
            hits.append(Hit(r["doc_id"], 1.0 / (1.0 + r["distance"]), r["text"], meta))
            if len(hits) >= top_k:
                break
        return hits

    def _search_fallback(
        self, qvec: list[float], top_k: int, where: dict[str, Any] | None
    ) -> list[Hit]:
        rows = self.db.execute(
            "SELECT doc_id, text, meta_json, embedding_json FROM kb_docs"
        ).fetchall()
        scored: list[Hit] = []
        for r in rows:
            if not r["embedding_json"]:
                continue
            meta = json.loads(r["meta_json"])
            if not self._matches_where(meta, where):
                continue
            score = cosine(qvec, json.loads(r["embedding_json"]))
            scored.append(Hit(r["doc_id"], score, r["text"], meta))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM kb_docs").fetchone()[0])

    def close(self) -> None:
        self.db.close()
