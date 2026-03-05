"""
poc/llm-gateway – OpenAI-compatible LLM gateway.

Supports:
  • Any OpenAI-compatible upstream (set via OPENAI_API_BASE / OPENAI_API_KEY)
  • GitHub Copilot as an upstream provider (COPILOT_TOKEN)
  • Automatic fallback: tries providers in order and falls back on error.

Exposes a single async function ``chat_completion`` that returns the
standard OpenAI ChatCompletion dict.
"""

from __future__ import annotations

import os
from typing import Any, AsyncIterator

import httpx

# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------

PROVIDERS_ENV_ORDER = ["copilot", "openai", "generic"]


def _copilot_headers() -> dict[str, str] | None:
    token = os.environ.get("COPILOT_TOKEN")
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Copilot-Integration-Id": "vscode-chat",
        "Editor-Version": "vscode/1.85.0",
        "Editor-Plugin-Version": "copilot-chat/0.11.1",
    }


def _openai_headers() -> dict[str, str] | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _generic_headers() -> dict[str, str] | None:
    key = os.environ.get("LLM_API_KEY")
    if not key:
        return None
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _providers() -> list[tuple[str, str, dict[str, str]]]:
    """
    Return an ordered list of (name, base_url, headers) for configured
    providers.  Only providers with sufficient credentials are included.
    """
    candidates: list[tuple[str, str, dict[str, str]]] = []

    copilot_hdrs = _copilot_headers()
    if copilot_hdrs:
        base = os.environ.get(
            "COPILOT_API_BASE",
            "https://api.githubcopilot.com",
        )
        candidates.append(("copilot", base, copilot_hdrs))

    openai_hdrs = _openai_headers()
    if openai_hdrs:
        base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
        candidates.append(("openai", base, openai_hdrs))

    generic_hdrs = _generic_headers()
    if generic_hdrs:
        base = os.environ.get("LLM_API_BASE", "http://localhost:11434/v1")
        candidates.append(("generic", base, generic_hdrs))

    return candidates


# ---------------------------------------------------------------------------
# Core request function
# ---------------------------------------------------------------------------

async def chat_completion(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    stream: bool = False,
    **extra_kwargs: Any,
) -> dict[str, Any]:
    """
    Send a chat-completion request to the first available provider.
    Falls back to the next provider on any HTTP/network error.

    Returns the raw OpenAI-compatible response dict.
    Raises ``RuntimeError`` if all providers fail.
    """
    providers = _providers()
    if not providers:
        raise RuntimeError(
            "No LLM provider configured. Set COPILOT_TOKEN, OPENAI_API_KEY, or "
            "LLM_API_KEY + LLM_API_BASE."
        )

    last_exc: Exception | None = None
    for name, base_url, headers in providers:
        resolved_model = model or _default_model(name)
        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **extra_kwargs,
        }
        if stream:
            payload["stream"] = True

        url = f"{base_url.rstrip('/')}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue  # try next provider

    raise RuntimeError(
        f"All LLM providers failed. Last error: {last_exc}"
    ) from last_exc


async def stream_chat_completion(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    **extra_kwargs: Any,
) -> AsyncIterator[str]:
    """
    Streaming variant – yields raw SSE lines from the first available provider.
    Falls back to the next provider on connection errors.
    Raises ``RuntimeError`` if all providers fail.
    """
    providers = _providers()
    if not providers:
        raise RuntimeError("No LLM provider configured.")

    last_exc: Exception | None = None
    for name, base_url, headers in providers:
        resolved_model = model or _default_model(name)
        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **extra_kwargs,
        }
        url = f"{base_url.rstrip('/')}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        yield line
            return  # success – stop iterating providers
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue

    raise RuntimeError(
        f"All LLM providers failed. Last error: {last_exc}"
    ) from last_exc


def _default_model(provider_name: str) -> str:
    env_model = os.environ.get("LLM_MODEL")
    if env_model:
        return env_model
    defaults = {
        "copilot": "gpt-4o",
        "openai": "gpt-4o-mini",
        "generic": "llama3",
    }
    return defaults.get(provider_name, "gpt-4o-mini")
