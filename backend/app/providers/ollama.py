"""
Ollama chat provider.

Calls a local Ollama server's /api/chat endpoint using the configured
CHAT model (OLLAMA_CHAT_MODEL, default 'phi3:latest') — never the
embedding model (OLLAMA_EMBEDDING_MODEL, see app.rag.embeddings). Chat
and embedding models serve different purposes and are not
interchangeable, so this module has no notion of the embedding model at
all, and vice versa.
"""

from __future__ import annotations

import logging
import time

import httpx

from app.providers.base import ChatResponse, ProviderError

logger = logging.getLogger("app.providers.ollama")


class OllamaChatProvider:
    """Calls a local Ollama server's chat endpoint."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(self, system_prompt: str, user_prompt: str) -> ChatResponse:
        start = time.monotonic()
        logger.info("Chat request: provider=ollama model=%s", self.model)

        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.error(
                "Chat request failed: timeout provider=ollama model=%s timeout_seconds=%s",
                self.model,
                self.timeout_seconds,
            )
            raise ProviderError(
                f"Ollama did not respond within {self.timeout_seconds:.0f}s for model "
                f"'{self.model}'. Is Ollama overloaded or is the model still loading?"
            ) from exc
        except httpx.HTTPError as exc:
            logger.error(
                "Chat request failed: %s provider=ollama model=%s",
                exc.__class__.__name__,
                self.model,
            )
            raise ProviderError(
                f"Could not reach Ollama at {self.base_url} for chat generation. "
                f"Is Ollama running and is the '{self.model}' model pulled? "
                f"({exc.__class__.__name__})"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            logger.error("Chat request failed: non-JSON response provider=ollama model=%s", self.model)
            raise ProviderError(
                f"Ollama returned a non-JSON response from {self.base_url}."
            ) from exc

        if not isinstance(data, dict):
            logger.error("Chat request failed: malformed response provider=ollama model=%s", self.model)
            raise ProviderError(
                f"Ollama returned an unexpected response shape for model '{self.model}'."
            )

        message = data.get("message")
        if not isinstance(message, dict):
            logger.error(
                "Chat request failed: malformed response (missing 'message') "
                "provider=ollama model=%s",
                self.model,
            )
            raise ProviderError(
                f"Ollama returned a malformed response for model '{self.model}' "
                "(missing 'message' field)."
            )

        text = message.get("content")
        if text is None:
            logger.error(
                "Chat request failed: response missing content provider=ollama model=%s",
                self.model,
            )
            raise ProviderError(
                f"Ollama response for model '{self.model}' is missing message content."
            )
        if not text.strip():
            logger.error(
                "Chat request failed: empty response provider=ollama model=%s",
                self.model,
            )
            raise ProviderError(
                f"Ollama returned an empty response for model '{self.model}'."
            )

        usage: dict[str, int] | None = None
        prompt_tokens = data.get("prompt_eval_count")
        completion_tokens = data.get("eval_count")
        if prompt_tokens is not None or completion_tokens is not None:
            usage = {
                "prompt_tokens": prompt_tokens or 0,
                "completion_tokens": completion_tokens or 0,
            }

        duration = time.monotonic() - start
        logger.info(
            "Chat response: provider=ollama model=%s duration=%.3fs "
            "response_length=%d success=True",
            self.model,
            duration,
            len(text),
        )

        return ChatResponse(text=text, provider="ollama", model=self.model, usage=usage)
