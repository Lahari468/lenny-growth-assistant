"""
Anthropic cloud chat provider.

Implements the same provider contract as Ollama so the RAG answer
generation layer remains provider-agnostic.
"""

from __future__ import annotations

import logging
import time

from anthropic import APIConnectionError
from anthropic import APIStatusError
from anthropic import APITimeoutError
from anthropic import Anthropic

from app.providers.base import ChatResponse, ProviderError

logger = logging.getLogger("app.providers.anthropic")


class AnthropicChatProvider:
    """Generate grounded answers using Anthropic's Messages API."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-5",
        timeout_seconds: float = 60.0,
    ) -> None:
        if not api_key.strip():
            raise ProviderError(
                "Anthropic API key is not configured."
            )

        self.model = model
        self.timeout_seconds = timeout_seconds

        self.client = Anthropic(
            api_key=api_key,
            timeout=timeout_seconds,
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> ChatResponse:
        started = time.monotonic()

        logger.info(
            "Starting Anthropic generation: model=%s",
            self.model,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ],
            )

        except APITimeoutError as exc:
            logger.error(
                "Anthropic request timed out: model=%s",
                self.model,
            )
            raise ProviderError(
                "Anthropic request timed out."
            ) from exc

        except APIConnectionError as exc:
            logger.error(
                "Anthropic connection failed: model=%s",
                self.model,
            )
            raise ProviderError(
                "Could not connect to Anthropic."
            ) from exc

        except APIStatusError as exc:
            logger.error(
                "Anthropic API error: model=%s status=%s",
                self.model,
                exc.status_code,
            )
            raise ProviderError(
                f"Anthropic request failed with status "
                f"{exc.status_code}."
            ) from exc

        except Exception as exc:
            logger.error(
                "Unexpected Anthropic error: model=%s type=%s",
                self.model,
                type(exc).__name__,
            )
            raise ProviderError(
                "Anthropic generation failed."
            ) from exc

        text_parts: list[str] = []

        for block in response.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)

        text = "".join(text_parts).strip()

        if not text:
            raise ProviderError(
                "Anthropic returned an empty response."
            )

        usage = None

        if response.usage is not None:
            usage = {
                "prompt_tokens": int(
                    getattr(
                        response.usage,
                        "input_tokens",
                        0,
                    )
                ),
                "completion_tokens": int(
                    getattr(
                        response.usage,
                        "output_tokens",
                        0,
                    )
                ),
            }

        logger.info(
            "Anthropic generation completed: model=%s "
            "duration=%.2fs response_length=%d",
            self.model,
            time.monotonic() - started,
            len(text),
        )

        return ChatResponse(
            text=text,
            provider="anthropic",
            model=self.model,
            usage=usage,
        )
