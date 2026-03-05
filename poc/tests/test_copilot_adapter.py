"""
poc/tests/test_copilot_adapter.py – unit tests for the Copilot adapter.
"""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import llm_gateway  # noqa: E402

copilot_adapter_mod = llm_gateway.copilot_adapter
CopilotAdapter = copilot_adapter_mod.CopilotAdapter
CopilotTokenError = copilot_adapter_mod.CopilotTokenError


def _mock_token_response(token="chat_token_abc", expires_offset=1800):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "token": token,
        "expires_at": time.time() + expires_offset,
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _mock_chat_response(content="Done!"):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": content}}]
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_missing_token_raises():
    adapter = CopilotAdapter(oauth_token="")
    with pytest.raises(CopilotTokenError, match="COPILOT_TOKEN is not set"):
        asyncio.run(adapter._ensure_token())


def test_validate_returns_false_without_token():
    adapter = CopilotAdapter(oauth_token="")
    result = asyncio.run(adapter.validate())
    assert result is False


def test_validate_returns_true_with_valid_token():
    adapter = CopilotAdapter(oauth_token="ghu_fake")

    token_resp = _mock_token_response()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=token_resp)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(adapter.validate())

    assert result is True


def test_token_cached_until_expiry():
    adapter = CopilotAdapter(oauth_token="ghu_fake")

    token_resp = _mock_token_response()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=token_resp)
        mock_client_cls.return_value = mock_client

        asyncio.run(adapter._ensure_token())
        asyncio.run(adapter._ensure_token())  # second call – should use cache

        assert mock_client.get.call_count == 1  # only fetched once


def test_401_raises_token_error():
    adapter = CopilotAdapter(oauth_token="ghu_invalid")

    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        with pytest.raises(CopilotTokenError, match="invalid"):
            asyncio.run(adapter._ensure_token())


def test_403_raises_subscription_error():
    adapter = CopilotAdapter(oauth_token="ghu_no_subscription")

    mock_resp = MagicMock()
    mock_resp.status_code = 403

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        with pytest.raises(CopilotTokenError, match="subscription"):
            asyncio.run(adapter._ensure_token())


def test_chat_completion_success():
    adapter = CopilotAdapter(oauth_token="ghu_fake")
    # Pre-seed the token so we skip the fetch step
    adapter._chat_token = "chat_token_abc"
    adapter._token_expires_at = time.time() + 1800

    chat_resp = _mock_chat_response("The answer is 42.")

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=chat_resp)
        mock_client_cls.return_value = mock_client

        result = asyncio.run(
            adapter.chat_completion([{"role": "user", "content": "What is 6*7?"}])
        )

    assert "42" in result["choices"][0]["message"]["content"]
