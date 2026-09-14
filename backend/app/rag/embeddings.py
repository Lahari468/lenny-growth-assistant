"""
Embedding generation.

Uses the local Ollama embedding model configured for the project.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from app.db.models import EMBEDDING_DIMENSION


class EmbeddingError(RuntimeError):
    """Raised when embedding generation fails."""


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class OllamaEmbeddingProvider:
    """Calls Ollama's current /api/embed endpoint."""

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
        if not text.strip():
            raise EmbeddingError("Cannot generate an embedding for empty text.")

        try:
            response = httpx.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model,
                    "input": text,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise EmbeddingError(
                f"Ollama embedding request timed out after "
                f"{self.timeout_seconds:.0f}s."
            ) from exc
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

        embeddings = data.get("embeddings")

        if not isinstance(embeddings, list) or not embeddings:
            raise EmbeddingError(
                f"Ollama returned no embedding vector for model '{self.model}'."
            )

        embedding = embeddings[0]

        if not isinstance(embedding, list):
            raise EmbeddingError(
                f"Ollama returned an invalid embedding vector for model "
                f"'{self.model}'."
            )

        if len(embedding) != EMBEDDING_DIMENSION:
            raise EmbeddingError(
                f"Embedding dimension mismatch: expected "
                f"{EMBEDDING_DIMENSION}, got {len(embedding)}. "
                f"Check that '{self.model}' is the configured embedding model."
            )

        return [float(value) for value in embedding]

    def health_check(self) -> None:
        """Raises EmbeddingError if Ollama embeddings are unavailable."""
        self.embed("healthcheck")