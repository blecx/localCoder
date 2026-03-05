"""Copilot provider adapter.

GitHub Copilot does **not** expose a publicly documented, standalone
chat-completions endpoint that arbitrary third-party gateways can call
with a personal API key.  This provider adapter exists to:

1.  Validate the configuration and surface a clear, actionable error
    message when a user selects ``provider: copilot`` without supplying
    a valid enterprise endpoint and auth token.

2.  Support a ``fallback_to_stub: true`` mode so that the rest of the
    PoC stack remains usable end-to-end without a real LLM backend.

What would be required to use a real Copilot endpoint
------------------------------------------------------
If your organisation has access to an enterprise-managed GitHub Copilot
endpoint that exposes an OpenAI-compatible API, set the following
configuration keys and switch to ``provider: openai_compat`` instead:

``base_url``
    The base URL of your Copilot enterprise endpoint
    (e.g. ``https://api.githubcopilot.com/v1`` or an Azure-hosted URL
    provided by your organisation).

``api_key``
    The authentication token.  GitHub Copilot enterprise endpoints
    typically use a short-lived OAuth bearer token obtained via the
    GitHub OAuth device-flow or a service-account token configured by
    your enterprise admin.

``model``
    The Copilot model ID (e.g. ``gpt-4o``, ``claude-3.5-sonnet``).

Until such an endpoint is available, use ``provider: openai_compat``
pointing at OpenAI, Azure OpenAI, GitHub Models, or a local server
such as LM Studio or Ollama.
"""

from typing import Any, Dict, List, Optional

from poc.llm_gateway.providers.base import (
    ConfigurationError,
    LLMProvider,
)

_STUB_REPLY = (
    "[stub] Copilot provider is running in fallback_to_stub mode. "
    "Configure a real OpenAI-compatible endpoint to get live responses."
)

_COPILOT_ERROR_MESSAGE = (
    "The 'copilot' provider cannot be used as a standalone LLM gateway "
    "upstream: GitHub Copilot does not provide a publicly documented "
    "API-key-authenticated chat-completions endpoint for arbitrary "
    "third-party gateways.\n\n"
    "To use a live LLM with this gateway, switch to "
    "'provider: openai_compat' and supply:\n"
    "  - base_url: your OpenAI-compatible endpoint "
    "(e.g. https://api.openai.com/v1)\n"
    "  - api_key:  your API key or bearer token\n"
    "  - model:    the model ID (e.g. gpt-4o)\n\n"
    "If your organisation manages a GitHub Copilot enterprise endpoint "
    "that exposes an OpenAI-compatible API, you can point "
    "'provider: openai_compat' at that base_url with the appropriate "
    "auth token.\n\n"
    "To keep the PoC stack runnable without a real LLM, set "
    "'fallback_to_stub: true' in the gateway config."
)


class CopilotProvider(LLMProvider):
    """Copilot provider adapter.

    In normal mode, ``validate_config`` and ``chat_completion`` raise a
    ``ConfigurationError`` with a detailed explanation of why Copilot
    cannot be used as a direct upstream and what to configure instead.

    When ``fallback_to_stub`` is ``True`` in the config, the provider
    returns a static stub reply instead of raising an error, allowing
    the rest of the stack to function end-to-end.
    """

    PROVIDER_NAME = "copilot"

    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._fallback_to_stub: bool = bool(config.get("fallback_to_stub", False))

    # ------------------------------------------------------------------
    # LLMProvider interface
    # ------------------------------------------------------------------

    def validate_config(self) -> None:
        """Raise ConfigurationError unless fallback_to_stub is enabled."""
        if not self._fallback_to_stub:
            raise ConfigurationError(_COPILOT_ERROR_MESSAGE)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Return a stub reply or raise ConfigurationError.

        Args:
            messages: Chat messages (ignored in stub mode).
            temperature: Ignored.
            max_tokens: Ignored.

        Returns:
            Stub reply string when ``fallback_to_stub`` is ``True``.

        Raises:
            ConfigurationError: When ``fallback_to_stub`` is ``False``.
        """
        if self._fallback_to_stub:
            return _STUB_REPLY

        raise ConfigurationError(_COPILOT_ERROR_MESSAGE)

    def health(self) -> Dict[str, Any]:
        if self._fallback_to_stub:
            return {
                "provider": self.PROVIDER_NAME,
                "status": "degraded",
                "mode": "stub",
                "note": (
                    "Running in fallback_to_stub mode. "
                    "Responses are synthetic — configure a real upstream."
                ),
            }
        return {
            "provider": self.PROVIDER_NAME,
            "status": "error",
            "mode": "unconfigured",
            "note": (
                "GitHub Copilot does not expose a publicly documented "
                "standalone chat-completions endpoint for third-party gateways. "
                "Switch to provider: openai_compat or enable fallback_to_stub."
            ),
        }