"""Factory for selecting the configured chat provider."""

from __future__ import annotations

from app.core.config import get_settings
from app.providers.anthropic import AnthropicChatProvider
from app.providers.base import ChatProvider, ProviderError
from app.providers.ollama import OllamaChatProvider

def build_chat_provider(provider_override: str | None = None) -> ChatProvider:
    settings = get_settings()

    provider = (
        provider_override.strip().lower()
        if provider_override
        else settings.chat_provider.strip().lower()
    )

    if provider == "ollama":
        return OllamaChatProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_chat_model,
        )

    if provider == "anthropic":
        if not settings.anthropic_api_key.strip():
            raise ProviderError(
                "Anthropic provider selected but "
                "ANTHROPIC_API_KEY is not configured."
            )

        return AnthropicChatProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )

    raise ProviderError(
        f"Unsupported chat provider '{provider}'. "
        "Use 'ollama' or 'anthropic'."
    )