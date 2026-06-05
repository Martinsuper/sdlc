import asyncio
import time
from pathlib import Path

import pytest

from sdlc.llm.cache import LLMCache
from sdlc.llm.models import CompletionRequest, CompletionResponse, ContentBlock, Message, Role


def _req(
    model: str = "test-model",
    temperature: float = 0.7,
    metadata: dict | None = None,
    messages: list | None = None,
) -> CompletionRequest:
    return CompletionRequest(
        model=model,
        messages=messages or [Message(role=Role.USER, content="hello")],
        temperature=temperature,
        metadata=metadata or {},
    )


def _resp(model: str = "test-model") -> CompletionResponse:
    return CompletionResponse(
        id="resp-1",
        model=model,
        content=[ContentBlock(type="text", text="world")],
        stop_reason="end_turn",
    )


@pytest.fixture
def cache(tmp_path: Path) -> LLMCache:
    db = tmp_path / "cache.db"
    c = LLMCache(db)
    yield c
    c.close()


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_init_creates_db_and_table(cache: LLMCache, tmp_path: Path):
    assert (tmp_path / "cache.db").exists()
    row = cache.db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='llm_cache'"
    ).fetchone()
    assert row is not None


def test_put_get_hit(cache: LLMCache):
    req = _req()
    resp = _resp()
    run(cache.put(req, resp))
    result = run(cache.get(req))
    assert result is not None
    assert result.id == resp.id
    assert result.model == resp.model


def test_get_miss(cache: LLMCache):
    req1 = _req(model="model-a")
    req2 = _req(model="model-b")
    resp = _resp()
    run(cache.put(req1, resp))
    result = run(cache.get(req2))
    assert result is None


def test_ttl_expiry(cache: LLMCache, tmp_path: Path):
    cache.close()
    c = LLMCache(tmp_path / "cache.db", ttl_seconds=0)
    req = _req()
    resp = _resp()
    run(c.put(req, resp))
    time.sleep(0.01)
    result = run(c.get(req))
    assert result is None
    c.close()


def test_hit_count_increments(cache: LLMCache):
    req = _req()
    resp = _resp()
    run(cache.put(req, resp))
    run(cache.get(req))
    run(cache.get(req))
    row = cache.db.execute(
        "SELECT hit_count FROM llm_cache WHERE fingerprint=?", (cache._fingerprint(req),)
    ).fetchone()
    assert row[0] == 2


def test_stats(cache: LLMCache):
    req = _req()
    resp = _resp()
    run(cache.put(req, resp))
    s = cache.stats()
    assert s["entries"] == 1
    assert s["total_hits"] == 0
    assert s["hit_entries"] == 0
    assert s["hit_rate"] == 0.0
    run(cache.get(req))
    s = cache.stats()
    assert s["entries"] == 1
    assert s["total_hits"] == 1
    assert s["hit_entries"] == 1
    assert s["hit_rate"] == 1.0


def test_invalidate_all(cache: LLMCache):
    run(cache.put(_req(model="a"), _resp(model="a")))
    run(cache.put(_req(model="b"), _resp(model="b")))
    assert cache.stats()["entries"] == 2
    deleted = cache.invalidate()
    assert deleted == 2
    assert cache.stats()["entries"] == 0


def test_invalidate_prefix(cache: LLMCache):
    run(cache.put(_req(model="gpt-4"), _resp(model="gpt-4")))
    run(cache.put(_req(model="gpt-3.5"), _resp(model="gpt-3.5")))
    run(cache.put(_req(model="claude"), _resp(model="claude")))
    deleted = cache.invalidate(prefix="gpt")
    assert deleted == 2
    assert cache.stats()["entries"] == 1


def test_fingerprint_same_request_same_hash(cache: LLMCache):
    req1 = _req()
    req2 = _req()
    assert cache._fingerprint(req1) == cache._fingerprint(req2)


def test_fingerprint_different_request_different_hash(cache: LLMCache):
    req1 = _req(model="model-a")
    req2 = _req(model="model-b")
    assert cache._fingerprint(req1) != cache._fingerprint(req2)


def test_fingerprint_ignores_temperature(cache: LLMCache):
    req1 = _req(temperature=0.0)
    req2 = _req(temperature=1.0)
    assert cache._fingerprint(req1) == cache._fingerprint(req2)


def test_fingerprint_ignores_metadata(cache: LLMCache):
    req1 = _req(metadata={"trace": "a"})
    req2 = _req(metadata={"trace": "b"})
    assert cache._fingerprint(req1) == cache._fingerprint(req2)
