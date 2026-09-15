"""
Provider factory and dynamic model manager.
Allows runtime provider selection with graceful fallback.
"""

import os
import logging
from typing import Optional, Dict, List
from app.providers.base import LLMProvider
from app.providers.ollama import OllamaProvider
from app.providers.anthropic import AnthropicProvider
from app.schemas.common import ModelInfo

logger = logging.getLogger("lenny_growth.providers.factory")

class ProviderFactory:
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {
            "ollama": OllamaProvider(),
            "anthropic": AnthropicProvider(),
        }
        self._active_provider_name = os.getenv("LLM_PROVIDER", "ollama").lower()

    def get_provider(self, provider_name: Optional[str] = None) -> LLMProvider:
        """Get specified or active LLM provider."""
        target = (provider_name or self._active_provider_name).lower()
        if target not in self._providers:
            logger.warning("Unknown provider '%s' requested. Defaulting to 'ollama'.", target)
            target = "ollama"
        return self._providers[target]

    def set_active_provider(self, provider_name: str):
        """Switch active provider at runtime."""
        target = provider_name.lower()
        if target in self._providers:
            self._active_provider_name = target
            logger.info("Switched active provider to: %s", target)
        else:
            raise ValueError(f"Unsupported provider: {provider_name}")

    def get_active_provider_name(self) -> str:
        return self._active_provider_name

    async def list_available_models(self) -> List[ModelInfo]:
        """List all models across local and cloud providers with their status."""
        models = []
        
        # Check Ollama
        ollama = self._providers["ollama"]
        ollama_avail = await ollama.is_available()
        ollama_models = await ollama.get_models() if ollama_avail else [os.getenv("OLLAMA_MODEL", "llama3.1:8b")]
        for m in ollama_models:
            models.append(ModelInfo(
                id=f"ollama:{m}",
                name=f"Ollama • {m}",
                provider="ollama",
                is_active=(self._active_provider_name == "ollama"),
                is_available=ollama_avail,
                description="Local private inference via Ollama"
            ))

        # Check Anthropic
        anthropic = self._providers["anthropic"]
        anthropic_avail = await anthropic.is_available()
        for m in await anthropic.get_models():
            models.append(ModelInfo(
                id=f"anthropic:{m}",
                name=f"Claude • {m}",
                provider="anthropic",
                is_active=(self._active_provider_name == "anthropic"),
                is_available=anthropic_avail,
                description="Cloud frontier model via Anthropic API"
            ))

        return models

# Global factory instance
provider_factory = ProviderFactory()
