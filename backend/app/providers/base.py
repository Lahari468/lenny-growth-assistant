"""
Abstract Base Class for LLM Providers.
Defines the standard interface for local (Ollama) and cloud (Anthropic) model adapters.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = None

class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a complete text response from the model."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check whether this provider is currently reachable and configured."""
        pass

    @abstractmethod
    async def get_models(self) -> List[str]:
        """Return a list of available models for this provider."""
        pass
