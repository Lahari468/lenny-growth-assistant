"""
Embedding generation.

Single source of truth for the embedding model: `nomic-embed-text` served
locally by Ollama, producing vectors of `EMBEDDING_DIMENSION` (768, defined
once in app.db.models). This module intentionally has no notion of the
chat provider (Ollama vs. Anthropic) — embeddings never depend on which
provider is answering a given chat, so the corpus never needs re-embedding
just because someone switches providers mid-project.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from app.db.models import EMBEDDING_DIMENSION


class EmbeddingError(RuntimeError):
    """Raised for any embedding failure: unreachable server, bad response,
    or a dimension mismatch against the fixed project-wide dimension."""


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...


class OllamaEmbeddingProvider:
    """Calls a local Ollama server's embeddings endpoint."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def embed(self, text: str) -> list[float]:
        try:
            response = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingError(
                f"Could not reach Ollama at {self.base_url} for embeddings. "
                f"Is Ollama running and is the '{self.model}' model pulled? "
                f"({exc.__class__.__name__})"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise EmbeddingError(
                f"Ollama returned a non-JSON response from {self.base_url}."
            ) from exc

        embedding = data.get("embedding")
        if not embedding:
            raise EmbeddingError(
                f"Ollama returned no embedding vector for model '{self.model}'."
            )
        if len(embedding) != EMBEDDING_DIMENSION:
            raise EmbeddingError(
                f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, "
                f"got {len(embedding)}. Check that '{self.model}' is the model "
                f"the project is configured for."
            )
        return embedding

    def health_check(self) -> None:
        """Raises EmbeddingError if the embedding backend isn't usable."""
        self.embed("healthcheck")
