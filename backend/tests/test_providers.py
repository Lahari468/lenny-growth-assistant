"""
LLM Provider Abstraction Tests.
Verifies Ollama error handling, Anthropic missing key handling, and ProviderFactory switching.
"""

import pytest
from app.providers.ollama import OllamaProvider
from app.providers.anthropic import AnthropicProvider
from app.providers.factory import ProviderFactory

@pytest.mark.asyncio
async def test_ollama_provider_unreachable_endpoint():
    # Pointing to an invalid unreachable port should raise ConnectionError with clear guidance
    provider = OllamaProvider(base_url="http://127.0.0.1:59999")
    with pytest.raises(ConnectionError) as exc_info:
        await provider.generate("test prompt")
    assert "unreachable" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_anthropic_missing_key():
    # Empty API key should raise ValueError informing user to set ANTHROPIC_API_KEY
    provider = AnthropicProvider(api_key="")
    assert await provider.is_available() is False
    with pytest.raises(ValueError) as exc_info:
        await provider.generate("test prompt")
    assert "ANTHROPIC_API_KEY" in str(exc_info.value)

def test_provider_factory_switching():
    factory = ProviderFactory()
    assert factory.get_active_provider_name() in ("ollama", "anthropic")

    factory.set_active_provider("anthropic")
    assert factory.get_active_provider_name() == "anthropic"

    factory.set_active_provider("ollama")
    assert factory.get_active_provider_name() == "ollama"

    with pytest.raises(ValueError):
        factory.set_active_provider("unsupported_provider_xyz")
