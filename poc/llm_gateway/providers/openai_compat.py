"""OpenAI-compatible upstream provider.

Connects to any HTTP endpoint that implements the OpenAI chat-completions API
(``POST /chat/completions``).  This covers:

- OpenAI (api.openai.com)
- Azure OpenAI (with ``/openai/deployments/<name>`` base URL)
- LM Studio / Ollama local servers
- GitHub Models (models.github.ai/inference)
- Any other OpenAI-compatible inference server

Required configuration keys
----------------------------
``base_url``
    Full base URL for the API (e.g. ``https://api.openai.com/v1``).
``api_key``
    Bearer token / API key.
``model``
    Model ID string (e.g. ``gpt-4o``, ``openai/gpt-4o``).

Optional configuration keys
----------------------------
``temperature``   (default 0.7)
``max_tokens``    (default 4096)
``timeout``       (default 120 s)
"""

from typing import Any, Dict, List, Optional

import httpx

from poc.llm_gateway.providers.base import (
    ConfigurationError,
    LLMProvider,
    ProviderError,
)

_PLACEHOLDER_API_KEYS = frozenset(
    {"", "your-api-key-here", "your-token-here", "changeme"}
)


def _is_placeholder(value: str) -> bool:
    lowered = value.lower().strip()
    return lowered in _PLACEHOLDER_API_KEYS or "your_token_here" in lowered


class OpenAICompatProvider(LLMProvider):
    """Provider that calls any OpenAI-compatible ``/chat/completions`` endpoint."""

    PROVIDER_NAME = "openai_compat"

    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._base_url: str = (config.get("base_url") or "").rstrip("/")
        self._api_key: str = config.get("api_key") or ""
        self._model: str = config.get("model") or ""
        self._temperature: float = float(config.get("temperature", 0.7))
        self._max_tokens: int = int(config.get("max_tokens", 4096))
        self._timeout: float = float(config.get("timeout", 120))

    # ------------------------------------------------------------------
    # LLMProvider interface
    # ------------------------------------------------------------------

    def validate_config(self) -> None:
        """Raise ConfigurationError if required fields are missing/invalid."""
        missing = []
        if not self._base_url:
            missing.append("base_url")
        if _is_placeholder(self._api_key):
            missing.append("api_key")
        if not self._model:
            missing.append("model")
        if missing:
            raise ConfigurationError(
                f"OpenAICompatProvider is missing required configuration: "
                f"{', '.join(missing)}.  "
                f"Set these fields in the gateway config or via environment variables."
            )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        self.validate_config()

        url = f"{self._base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": (
                temperature if temperature is not None else self._temperature
            ),
            "max_tokens": max_tokens if max_tokens is not None else self._max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"Upstream returned HTTP {exc.response.status_code}: "
                f"{exc.response.text[:200]}"
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(
                f"Network error reaching upstream at {self._base_url}: {exc}"
            ) from exc
        except (KeyError, IndexError) as exc:
            raise ProviderError(
                f"Unexpected response shape from upstream: {exc}"
            ) from exc

    def health(self) -> Dict[str, Any]:
        issues = []
        if not self._base_url:
            issues.append("base_url not set")
        if _is_placeholder(self._api_key):
            issues.append("api_key is placeholder/missing")
        if not self._model:
            issues.append("model not set")

        status = "ok" if not issues else "error"
        result: Dict[str, Any] = {
            "provider": self.PROVIDER_NAME,
            "status": status,
            "base_url": self._base_url or "(not set)",
            "model": self._model or "(not set)",
        }
        if issues:
            result["issues"] = issues
        return result