"""
poc/tests/test_gateway.py – unit tests for the LLM gateway.

These tests mock HTTP calls so they run without real API credentials.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import llm_gateway  # noqa: E402  – loads the package


gateway = llm_gateway.gateway


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_openai_response(content: str = "Hello!") -> dict:
    return {
        "choices": [
            {"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
        ],
        "model": "gpt-4o-mini",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_no_providers_raises(monkeypatch):
    monkeypatch.delenv("COPILOT_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="No LLM provider configured"):
        asyncio.run(gateway.chat_completion([{"role": "user", "content": "hi"}]))


def test_openai_provider_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("COPILOT_TOKEN", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_openai_response("Hi from mock!")
    mock_resp.raise_for_status = MagicMock()

    async def mock_post(*args, **kwargs):
        return mock_resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(
            gateway.chat_completion([{"role": "user", "content": "hello"}])
        )

    assert result["choices"][0]["message"]["content"] == "Hi from mock!"


def test_fallback_to_second_provider(monkeypatch):
    """OpenAI configured but fails → should fall back to generic."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_API_KEY", "sk-generic")
    monkeypatch.delenv("COPILOT_TOKEN", raising=False)

    call_count = [0]

    async def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("OpenAI error")
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_openai_response("Fallback worked!")
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=side_effect)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(
            gateway.chat_completion([{"role": "user", "content": "hello"}])
        )

    assert call_count[0] == 2
    assert result["choices"][0]["message"]["content"] == "Fallback worked!"


def test_all_providers_fail_raises(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("COPILOT_TOKEN", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("network error"))
        mock_client_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            asyncio.run(
                gateway.chat_completion([{"role": "user", "content": "hello"}])
            )


def test_default_model_copilot():
    assert gateway._default_model("copilot") == "gpt-4o"


def test_default_model_openai():
    assert gateway._default_model("openai") == "gpt-4o-mini"


def test_default_model_env_override(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "my-custom-model")
    assert gateway._default_model("openai") == "my-custom-model"
