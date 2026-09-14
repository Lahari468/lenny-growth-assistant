"""Shared fixtures for RAG pipeline tests. No test here talks to a real
Ollama server — embeddings are produced by FakeEmbeddingProvider below."""

from __future__ import annotations

import hashlib

import pytest

from app.db.models import EMBEDDING_DIMENSION


class FakeEmbeddingProvider:
    """Deterministic, dependency-free stand-in for OllamaEmbeddingProvider.

    Produces a fixed-dimension vector derived from a hash of the input
    text, so identical text always yields identical embeddings (useful for
    asserting on stored vectors) without ever calling a network.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.health_checks = 0

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Repeat/trim the digest bytes to exactly EMBEDDING_DIMENSION floats.
        values = [digest[i % len(digest)] / 255.0 for i in range(EMBEDDING_DIMENSION)]
        return values

    def health_check(self) -> None:
        self.health_checks += 1


@pytest.fixture()
def fake_embedding_provider() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


class StaticEmbeddingProvider:
    """Returns a fixed, caller-supplied vector regardless of input text.

    Used by retrieval tests that need precise control over the geometric
    relationship between a query embedding and stored chunk embeddings
    (e.g. "this query vector must be closest to chunk A, not chunk B"),
    which a content-hash-derived embedding can't guarantee.
    """

    def __init__(self, vector: list[float]) -> None:
        self.vector = vector
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return self.vector

    def health_check(self) -> None:
        pass
