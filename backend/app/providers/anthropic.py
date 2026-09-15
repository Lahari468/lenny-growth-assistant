"""
Anthropic Claude Cloud LLM Provider.
Interacts with Anthropic Messages API when an API key is configured.
"""

import os
import logging
from typing import Optional, List, Dict, Any
import httpx
from app.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger("lenny_growth.providers.anthropic")

class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.default_model = default_model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        self.base_url = "https://api.anthropic.com/v1"
        self.timeout = httpx.Timeout(60.0, connect=5.0)

    async def is_available(self) -> bool:
        """Available only if an API key is provided and non-empty."""
        return bool(self.api_key and self.api_key.strip())

    async def get_models(self) -> List[str]:
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-haiku-20240307",
            "claude-3-opus-20240229",
        ]

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        if not await self.is_available():
            raise ValueError(
                "Anthropic API key is not configured. Set the ANTHROPIC_API_KEY environment variable or switch to Ollama."
            )

        active_model = model or self.default_model
        endpoint = f"{self.base_url}/messages"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": active_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        }
        if system_prompt:
            payload["system"] = system_prompt

        logger.info("Sending request to Anthropic (%s)", active_model)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error("Anthropic error %d: %s", response.status_code, error_text)
                    raise RuntimeError(f"Anthropic API error ({response.status_code}): {error_text}")

                data = response.json()
                content = ""
                for part in data.get("content", []):
                    if part.get("type") == "text":
                        content += part.get("text", "")

                usage = data.get("usage", {})
                prompt_tokens = usage.get("input_tokens")
                completion_tokens = usage.get("output_tokens")
                total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

                return LLMResponse(
                    content=content.strip(),
                    model=active_model,
                    provider="anthropic",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    raw_response=data,
                )
        except Exception as exc:
            logger.error("Anthropic generation exception: %s", exc)
            raise exc
