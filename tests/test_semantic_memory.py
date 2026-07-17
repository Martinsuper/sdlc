"""Tests for M-A4 semantic memory (embedding + vector store + MemoryL2)."""

from __future__ import annotations

from sdlc.kb.embedding import HashingEmbedder, OllamaEmbedder, cosine
from sdlc.kb.memory import MemoryL2
from sdlc.kb.vector_store import VectorStore

# --------------------------------------------------------------------------- #
# Embedding
# --------------------------------------------------------------------------- #

def test_hashing_embedder_deterministic():
    e = HashingEmbedder(dim=128)
    a = e.embed(["order pagination query"])[0]
    b = e.embed(["order pagination query"])[0]
    assert a == b
    assert len(a) == 128


def test_hashing_embedder_overlap_scores_higher():
    e = HashingEmbedder()
    q = e.embed(["authentication JWT token"])[0]
    related = e.embed(["user authentication with JWT tokens"])[0]
    unrelated = e.embed(["database migration column not null"])[0]
    assert cosine(q, related) > cosine(q, unrelated)


def test_cosine_degenerate_is_zero():
    assert cosine([], [1.0]) == 0.0
    assert cosine([0.0, 0.0], [0.0, 0.0]) == 0.0


def test_ollama_embedder_constructs_without_network():
    # Constructing must not require a running Ollama.
    emb = OllamaEmbedder()
    assert emb.model == "nomic-embed-text"
    assert emb.dim == 768


# --------------------------------------------------------------------------- #
# VectorStore (fallback backend always available)
# --------------------------------------------------------------------------- #

def test_vector_store_upsert_and_search(tmp_path):
    vs = VectorStore(tmp_path / "v.db", embedder=HashingEmbedder())
    vs.upsert("d1", "order pagination and status filter", {"type": "design"})
    vs.upsert("d2", "JWT authentication login flow", {"type": "design"})
    vs.upsert("d3", "terraform infra provisioning", {"type": "infra"})

    hits = vs.search("pagination status order", top_k=2)
    assert hits
    assert hits[0].doc_id == "d1"  # best token overlap ranks first


def test_vector_store_where_filter(tmp_path):
    vs = VectorStore(tmp_path / "v.db", embedder=HashingEmbedder())
    vs.upsert("d1", "authentication tokens", {"type": "design"})
    vs.upsert("d2", "authentication tokens", {"type": "infra"})
    hits = vs.search("authentication tokens", top_k=5, where={"type": "infra"})
    assert [h.doc_id for h in hits] == ["d2"]


def test_vector_store_upsert_replaces(tmp_path):
    vs = VectorStore(tmp_path / "v.db", embedder=HashingEmbedder())
    vs.upsert("d1", "first version", {})
    vs.upsert("d1", "second version", {})
    assert vs.count() == 1


def test_vector_store_backend_reported(tmp_path):
    vs = VectorStore(tmp_path / "v.db")
    # Either backend is acceptable; the store must work regardless.
    assert vs.backend in ("sqlite-vec", "fallback")


# --------------------------------------------------------------------------- #
# MemoryL2 integration + graceful degradation
# --------------------------------------------------------------------------- #

def test_memory_semantic_search(tmp_path):
    m = MemoryL2(kb_root=tmp_path)
    assert m.index_text("d1", "order pagination status filter", {"type": "design"})
    assert m.index_text("d2", "infra terraform modules", {"type": "infra"})
    res = m.semantic_search("pagination order filter", top_k=1)
    assert res and res[0]["doc_id"] == "d1"


def test_memory_semantic_disabled_degrades(tmp_path):
    # enable_semantic=False => index is a no-op and search returns empty,
    # so callers fall back to path/fingerprint retrieval.
    m = MemoryL2(kb_root=tmp_path, enable_semantic=False)
    assert m.index_text("d1", "x", {}) is False
    assert m.semantic_search("x") == []


def test_memory_no_kb_root_degrades():
    m = MemoryL2(kb_root=None)
    assert m.index_text("d1", "x", {}) is False
    assert m.semantic_search("x") == []
