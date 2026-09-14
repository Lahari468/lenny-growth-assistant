"""
Provider-agnostic chat interface.

Any LLM backend (Ollama today, Anthropic later) implements `ChatProvider`
so the future application/agent layer can call `generate()` without
knowing or caring which backend is behind it. This module intentionally
has no dependency on FastAPI, PostgreSQL, RAG, or any agent framework —
it's a plain Python contract, mirroring how app.rag.embeddings.EmbeddingProvider
is kept independent of everything that calls it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ProviderError(RuntimeError):
    """Raised for any chat-provider failure: unreachable backend, timeout,
    malformed response, missing/empty content, etc.

    Messages must never include secrets, credentials, full prompts, or
    transcript content — only safe, actionable operational detail (which
    backend, which model, what kind of failure).
    """


@dataclass(frozen=True)
class ChatResponse:
    """The result of a single chat generation call."""

    text: str
    provider: str
    model: str
    usage: dict[str, int] | None = None


class ChatProvider(Protocol):
    """Implemented by every chat backend (Ollama, Anthropic, ...)."""

    def generate(self, system_prompt: str, user_prompt: str) -> ChatResponse: ...
