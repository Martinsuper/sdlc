"""Embedding providers for semantic KB retrieval (M-A4).

Two implementations:
  - HashingEmbedder: dependency-free, deterministic bag-of-tokens hashing into a
    fixed-dim vector. The default, so semantic retrieval works (and is testable)
    with zero external services. Quality is modest but non-trivial for keyword-
    overlap queries.
  - OllamaEmbedder: local Ollama embedding model (nomic-embed-text by default).
    Higher quality, still fully local — honoring the "runs locally" constraint.

Both satisfy the Embedder protocol so VectorStore is agnostic to which is used.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, runtime_checkable

_TOKEN_RE = re.compile(r"[A-Za-z0-9_一-鿿]+")


@runtime_checkable
class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class HashingEmbedder:
    """Deterministic hashing embedder — no dependencies, no network.

    Maps tokens into a fixed number of buckets (the hashing trick) and
    L2-normalizes, so cosine similarity reflects token overlap. Good enough to
    make semantic retrieval usable offline; swap in OllamaEmbedder for quality.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in _tokenize(text):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            bucket = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


class OllamaEmbedder:
    """Local Ollama embedding model. Requires a running Ollama with the model
    pulled; raises on failure so callers can fall back to HashingEmbedder."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        dim: int = 768,
        timeout: float = 30.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.dim = dim
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        out: list[list[float]] = []
        with httpx.Client(timeout=self.timeout) as client:
            for t in texts:
                resp = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": t},
                )
                resp.raise_for_status()
                emb = resp.json().get("embedding", [])
                out.append([float(x) for x in emb])
        # Keep dim in sync with what the model actually returned.
        if out and out[0]:
            self.dim = len(out[0])
        return out


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity; 0.0 for degenerate/empty vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
