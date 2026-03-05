"""Unit tests for poc/llm_gateway — provider selection, routing,
health/config validation, and fallback behavior.
"""

import pytest

from poc.llm_gateway.config import GatewayConfig
from poc.llm_gateway.gateway import LLMGateway
from poc.llm_gateway.providers.base import ConfigurationError, ProviderError
from poc.llm_gateway.providers.copilot import CopilotProvider, _STUB_REPLY
from poc.llm_gateway.providers.openai_compat import OpenAICompatProvider


# ---------------------------------------------------------------------------
# GatewayConfig tests
# ---------------------------------------------------------------------------


def test_gateway_config_defaults():
    cfg = GatewayConfig()
    assert cfg.get("provider") == "openai_compat"
    assert cfg.get("temperature") == 0.7
    assert cfg.get("max_tokens") == 4096
    assert cfg.get("fallback_to_stub") is False


def test_gateway_config_overrides():
    cfg = GatewayConfig(config={"provider": "copilot", "fallback_to_stub": True})
    assert cfg.get("provider") == "copilot"
    assert cfg.get("fallback_to_stub") is True
    # Defaults still present for unset keys
    assert cfg.get("temperature") == 0.7


def test_gateway_config_as_dict_contains_all_defaults():
    cfg = GatewayConfig()
    d = cfg.as_dict()
    for key in (
        "provider",
        "base_url",
        "api_key",
        "model",
        "temperature",
        "max_tokens",
        "timeout",
        "fallback_to_stub",
    ):
        assert key in d


def test_gateway_config_from_file(tmp_path):
    import json

    cfg_file = tmp_path / "gw.json"
    cfg_file.write_text(json.dumps({"provider": "copilot", "fallback_to_stub": True}))
    cfg = GatewayConfig(config_path=str(cfg_file))
    assert cfg.get("provider") == "copilot"
    assert cfg.get("fallback_to_stub") is True


def test_gateway_config_bad_file_raises(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json}")
    with pytest.raises(ValueError, match="Failed to load gateway config"):
        GatewayConfig(config_path=str(bad_file))


# ---------------------------------------------------------------------------
# LLMGateway — provider selection
# ---------------------------------------------------------------------------


def test_gateway_selects_openai_compat_by_default():
    gw = LLMGateway()
    assert isinstance(gw.provider, OpenAICompatProvider)


def test_gateway_selects_openai_compat_explicitly():
    gw = LLMGateway({"provider": "openai_compat"})
    assert isinstance(gw.provider, OpenAICompatProvider)


def test_gateway_selects_copilot_provider():
    gw = LLMGateway({"provider": "copilot"})
    assert isinstance(gw.provider, CopilotProvider)


def test_gateway_unknown_provider_raises():
    with pytest.raises(ConfigurationError, match="Unknown provider 'bogus'"):
        LLMGateway({"provider": "bogus"})


def test_gateway_supported_providers():
    providers = LLMGateway.supported_providers()
    assert "openai_compat" in providers
    assert "copilot" in providers


def test_gateway_accepts_gateway_config_object():
    cfg = GatewayConfig(config={"provider": "copilot", "fallback_to_stub": True})
    gw = LLMGateway(cfg)
    assert isinstance(gw.provider, CopilotProvider)


# ---------------------------------------------------------------------------
# OpenAICompatProvider — config validation
# ---------------------------------------------------------------------------


def test_openai_compat_validate_raises_on_empty_config():
    p = OpenAICompatProvider({})
    with pytest.raises(ConfigurationError) as exc_info:
        p.validate_config()
    msg = str(exc_info.value)
    assert "base_url" in msg
    assert "api_key" in msg
    assert "model" in msg


def test_openai_compat_validate_raises_on_placeholder_key():
    p = OpenAICompatProvider(
        {
            "base_url": "https://api.openai.com/v1",
            "api_key": "your-api-key-here",
            "model": "gpt-4o",
        }
    )
    with pytest.raises(ConfigurationError, match="api_key"):
        p.validate_config()


def test_openai_compat_validate_passes_with_valid_config():
    p = OpenAICompatProvider(
        {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-real-key",
            "model": "gpt-4o",
        }
    )
    p.validate_config()  # must not raise


def test_openai_compat_health_ok():
    p = OpenAICompatProvider(
        {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-real-key",
            "model": "gpt-4o",
        }
    )
    h = p.health()
    assert h["status"] == "ok"
    assert h["provider"] == "openai_compat"


def test_openai_compat_health_error_when_misconfigured():
    p = OpenAICompatProvider({})
    h = p.health()
    assert h["status"] == "error"
    assert "issues" in h


# ---------------------------------------------------------------------------
# CopilotProvider — validation & fallback
# ---------------------------------------------------------------------------


def test_copilot_validate_raises_without_fallback():
    p = CopilotProvider({})
    with pytest.raises(ConfigurationError) as exc_info:
        p.validate_config()
    msg = str(exc_info.value)
    assert "openai_compat" in msg
    assert "fallback_to_stub" in msg


def test_copilot_validate_passes_with_fallback():
    p = CopilotProvider({"fallback_to_stub": True})
    p.validate_config()  # must not raise


def test_copilot_health_error_without_fallback():
    p = CopilotProvider({})
    h = p.health()
    assert h["status"] == "error"
    assert h["provider"] == "copilot"


def test_copilot_health_degraded_with_fallback():
    p = CopilotProvider({"fallback_to_stub": True})
    h = p.health()
    assert h["status"] == "degraded"
    assert h["mode"] == "stub"


@pytest.mark.asyncio
async def test_copilot_chat_completion_raises_without_fallback():
    p = CopilotProvider({})
    with pytest.raises(ConfigurationError):
        await p.chat_completion([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_copilot_chat_completion_returns_stub_with_fallback():
    p = CopilotProvider({"fallback_to_stub": True})
    reply = await p.chat_completion([{"role": "user", "content": "hi"}])
    assert reply == _STUB_REPLY


# ---------------------------------------------------------------------------
# LLMGateway — routing + fallback integration
# ---------------------------------------------------------------------------


def test_gateway_validate_openai_compat_raises_without_config():
    gw = LLMGateway({"provider": "openai_compat"})
    with pytest.raises(ConfigurationError):
        gw.validate()


def test_gateway_validate_copilot_raises_without_fallback():
    gw = LLMGateway({"provider": "copilot"})
    with pytest.raises(ConfigurationError, match="openai_compat"):
        gw.validate()


def test_gateway_validate_copilot_passes_with_fallback():
    gw = LLMGateway({"provider": "copilot", "fallback_to_stub": True})
    gw.validate()  # must not raise


@pytest.mark.asyncio
async def test_gateway_chat_completion_copilot_stub():
    gw = LLMGateway({"provider": "copilot", "fallback_to_stub": True})
    reply = await gw.chat_completion([{"role": "user", "content": "hello"}])
    assert reply == _STUB_REPLY


@pytest.mark.asyncio
async def test_gateway_chat_completion_copilot_raises_without_fallback():
    gw = LLMGateway({"provider": "copilot"})
    with pytest.raises(ConfigurationError):
        await gw.chat_completion([{"role": "user", "content": "hello"}])


@pytest.mark.asyncio
async def test_gateway_chat_completion_openai_compat_raises_on_bad_config():
    """OpenAICompatProvider raises ConfigurationError before any network call."""
    gw = LLMGateway({"provider": "openai_compat"})
    with pytest.raises(ConfigurationError):
        await gw.chat_completion([{"role": "user", "content": "hello"}])


@pytest.mark.asyncio
async def test_gateway_chat_completion_openai_compat_calls_upstream(httpx_mock):
    """Successful upstream response is returned verbatim."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.example.com/v1/chat/completions",
        json={"choices": [{"message": {"content": "Hello from upstream!"}}]},
    )

    gw = LLMGateway(
        {
            "provider": "openai_compat",
            "base_url": "https://api.example.com/v1",
            "api_key": "sk-test-key",
            "model": "gpt-4o-test",
        }
    )
    reply = await gw.chat_completion([{"role": "user", "content": "hello"}])
    assert reply == "Hello from upstream!"


@pytest.mark.asyncio
async def test_gateway_chat_completion_openai_compat_http_error(httpx_mock):
    """HTTP 4xx/5xx from upstream raises ProviderError."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.example.com/v1/chat/completions",
        status_code=401,
        text="Unauthorized",
    )

    gw = LLMGateway(
        {
            "provider": "openai_compat",
            "base_url": "https://api.example.com/v1",
            "api_key": "sk-test-key",
            "model": "gpt-4o-test",
        }
    )
    with pytest.raises(ProviderError, match="HTTP 401"):
        await gw.chat_completion([{"role": "user", "content": "hello"}])


def test_gateway_health_copilot_stub():
    gw = LLMGateway({"provider": "copilot", "fallback_to_stub": True})
    h = gw.health()
    assert h["status"] == "degraded"
    assert h["provider"] == "copilot"


def test_gateway_health_openai_compat_no_config():
    gw = LLMGateway({"provider": "openai_compat"})
    h = gw.health()
    assert h["status"] == "error"
    assert h["provider"] == "openai_compat"