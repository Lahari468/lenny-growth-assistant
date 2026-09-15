"""
Ollama Local LLM Provider.
Interacts with local Ollama instance via HTTP API without requiring external keys.
"""

import os
import logging
from typing import Optional, List, Dict, Any
import httpx
from app.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger("lenny_growth.providers.ollama")

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: Optional[str] = None, default_model: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.default_model = default_model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self.timeout = httpx.Timeout(180.0, connect=10.0)


    async def is_available(self) -> bool:
        """Check if Ollama server is up and responsive."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception as e:
            logger.debug("Ollama availability check failed: %s", e)
            return False

    async def get_models(self) -> List[str]:
        """Fetch models installed in local Ollama."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return models
        except Exception as e:
            logger.warning("Failed to fetch Ollama models: %s", e)
        return [self.default_model]

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        active_model = model or self.default_model
        endpoint = f"{self.base_url}/api/generate"

        payload: Dict[str, Any] = {
            "model": active_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        logger.info("Sending request to Ollama (%s) at %s", active_model, endpoint)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, json=payload)
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error("Ollama returned status %d: %s", response.status_code, error_text)
                    raise RuntimeError(f"Ollama error ({response.status_code}): {error_text}")

                data = response.json()
                content = data.get("response", "").strip()
                prompt_tokens = data.get("prompt_eval_count")
                completion_tokens = data.get("eval_count")
                total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

                return LLMResponse(
                    content=content,
                    model=active_model,
                    provider="ollama",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    raw_response=data,
                )
        except httpx.ConnectError as conn_err:
            logger.error("Connection to Ollama failed at %s: %s", self.base_url, conn_err)
            raise ConnectionError(
                f"Ollama server is unreachable at {self.base_url}. Please ensure Ollama is running (`ollama serve`)."
            )
        except Exception as exc:
            logger.error("Ollama generation exception: %s", exc)
            raise exc
