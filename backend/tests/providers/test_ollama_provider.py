"""
Tests for OllamaChatProvider (app.providers.ollama).

The HTTP boundary (httpx.post) is mocked throughout -- none of these tests
require a live Ollama server.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.providers.base import ProviderError
from app.providers.ollama import OllamaChatProvider


def _make_response(json_data, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    else:
        response.raise_for_status.return_value = None
    return response


@pytest.fixture()
def provider() -> OllamaChatProvider:
    return OllamaChatProvider(base_url="http://localhost:11434", model="phi3:latest")


def test_generate_success(provider):
    response_json = {
        "model": "phi3:latest",
        "message": {"role": "assistant", "content": "Product-market fit means retention holds."},
        "done": True,
        "prompt_eval_count": 42,
        "eval_count": 17,
    }

    with patch("app.providers.ollama.httpx.post", return_value=_make_response(response_json)):
        result = provider.generate(system_prompt="Be concise.", user_prompt="What is PMF?")

    assert result.text == "Product-market fit means retention holds."
    assert result.provider == "ollama"
    assert result.model == "phi3:latest"
    assert result.usage == {"prompt_tokens": 42, "completion_tokens": 17}


def test_generate_uses_configured_chat_model_not_embedding_model():
    provider = OllamaChatProvider(base_url="http://localhost:11434", model="phi3:latest")
    response_json = {"message": {"content": "hello"}}

    with patch("app.providers.ollama.httpx.post", return_value=_make_response(response_json)) as mock_post:
        provider.generate(system_prompt="sys", user_prompt="hi")

    sent_payload = mock_post.call_args.kwargs["json"]
    assert sent_payload["model"] == "phi3:latest"
    assert sent_payload["model"] != "nomic-embed-text"


def test_generate_sends_system_and_user_messages(provider):
    response_json = {"message": {"content": "hi"}}

    with patch("app.providers.ollama.httpx.post", return_value=_make_response(response_json)) as mock_post:
        provider.generate(system_prompt="You are helpful.", user_prompt="Explain growth loops.")

    sent_payload = mock_post.call_args.kwargs["json"]
    assert sent_payload["messages"] == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Explain growth loops."},
    ]
    assert sent_payload["stream"] is False


def test_generate_raises_on_connection_error(provider):
    with patch("app.providers.ollama.httpx.post", side_effect=httpx.ConnectError("refused")):
        with pytest.raises(ProviderError, match="Could not reach Ollama"):
            provider.generate(system_prompt="sys", user_prompt="hi")


def test_generate_raises_on_timeout(provider):
    with patch("app.providers.ollama.httpx.post", side_effect=httpx.TimeoutException("timed out")):
        with pytest.raises(ProviderError, match="did not respond within"):
            provider.generate(system_prompt="sys", user_prompt="hi")


def test_generate_never_hangs_indefinitely_uses_finite_timeout(provider):
    with patch("app.providers.ollama.httpx.post", return_value=_make_response({"message": {"content": "ok"}})) as mock_post:
        provider.generate(system_prompt="sys", user_prompt="hi")

    assert mock_post.call_args.kwargs["timeout"] == provider.timeout_seconds
    assert provider.timeout_seconds < float("inf")


def test_generate_raises_on_non_json_response(provider):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("not json")

    with patch("app.providers.ollama.httpx.post", return_value=response):
        with pytest.raises(ProviderError, match="non-JSON response"):
            provider.generate(system_prompt="sys", user_prompt="hi")


def test_generate_raises_on_malformed_response_missing_message(provider):
    with patch("app.providers.ollama.httpx.post", return_value=_make_response({"done": True})):
        with pytest.raises(ProviderError, match="malformed response"):
            provider.generate(system_prompt="sys", user_prompt="hi")


def test_generate_raises_on_response_missing_content_key(provider):
    with patch(
        "app.providers.ollama.httpx.post",
        return_value=_make_response({"message": {"role": "assistant"}}),
    ):
        with pytest.raises(ProviderError, match="missing message content"):
            provider.generate(system_prompt="sys", user_prompt="hi")


def test_generate_raises_on_empty_response_content(provider):
    with patch(
        "app.providers.ollama.httpx.post",
        return_value=_make_response({"message": {"content": "   "}}),
    ):
        with pytest.raises(ProviderError, match="empty response"):
            provider.generate(system_prompt="sys", user_prompt="hi")


def test_generate_raises_on_unexpected_top_level_shape(provider):
    with patch("app.providers.ollama.httpx.post", return_value=_make_response(["not", "a", "dict"])):
        with pytest.raises(ProviderError, match="unexpected response shape"):
            provider.generate(system_prompt="sys", user_prompt="hi")


def test_generate_success_without_usage_fields(provider):
    with patch(
        "app.providers.ollama.httpx.post",
        return_value=_make_response({"message": {"content": "hello"}}),
    ):
        result = provider.generate(system_prompt="sys", user_prompt="hi")

    assert result.usage is None


def test_logging_never_includes_prompt_or_response_content(provider, caplog):
    secret_prompt = "SECRET_API_KEY=abcd1234 tell me about transcript XYZ"
    response_content = "This response also has SENSITIVE transcript content in it."

    with caplog.at_level(logging.INFO):
        with patch(
            "app.providers.ollama.httpx.post",
            return_value=_make_response({"message": {"content": response_content}}),
        ):
            provider.generate(system_prompt="sys", user_prompt=secret_prompt)

    assert secret_prompt not in caplog.text
    assert response_content not in caplog.text
    assert "provider=ollama" in caplog.text
    assert "model=phi3:latest" in caplog.text


def test_error_logging_never_includes_prompt_content(provider, caplog):
    secret_prompt = "SECRET_API_KEY=abcd1234"

    with caplog.at_level(logging.ERROR):
        with patch("app.providers.ollama.httpx.post", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(ProviderError):
                provider.generate(system_prompt="sys", user_prompt=secret_prompt)

    assert secret_prompt not in caplog.text


def test_error_message_never_includes_prompt_content(provider):
    secret_prompt = "SECRET_API_KEY=abcd1234"

    with patch("app.providers.ollama.httpx.post", side_effect=httpx.ConnectError("refused")):
        with pytest.raises(ProviderError) as exc_info:
            provider.generate(system_prompt="sys", user_prompt=secret_prompt)

    assert secret_prompt not in str(exc_info.value)
