"""LLM Gateway — provider router.

Selects and delegates to the appropriate upstream provider based on the
``provider`` key in the configuration.

Supported providers
-------------------
``openai_compat``
    Any HTTP server that implements the OpenAI chat-completions API.
    This is the recommended production-ready provider for the PoC.

``copilot``
    Copilot adapter.  In normal mode it raises a ``ConfigurationError``
    explaining that Copilot does not expose a standalone upstream
    endpoint.  Enable ``fallback_to_stub: true`` to keep the stack
    runnable without a real LLM.

Example
-------
.. code-block:: python

    from poc.llm_gateway import LLMGateway, GatewayConfig

    gw = LLMGateway(GatewayConfig(config={
        "provider": "openai_compat",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-...",
        "model": "gpt-4o",
    }))

    reply = await gw.chat_completion([
        {"role": "user", "content": "Hello, world!"}
    ])
"""

from typing import Any, Dict, List, Optional

from poc.llm_gateway.config import GatewayConfig
from poc.llm_gateway.providers.base import (
    ConfigurationError,
    LLMProvider,
)
from poc.llm_gateway.providers.copilot import CopilotProvider
from poc.llm_gateway.providers.openai_compat import OpenAICompatProvider

_PROVIDER_REGISTRY: Dict[str, type] = {
    "openai_compat": OpenAICompatProvider,
    "copilot": CopilotProvider,
}


class LLMGateway:
    """Provider-abstracted LLM gateway.

    Args:
        config: A :class:`GatewayConfig` instance or a plain ``dict``.
                If a ``dict`` is supplied it is wrapped automatically.
    """

    def __init__(self, config: Any = None) -> None:
        if isinstance(config, dict):
            config = GatewayConfig(config=config)
        elif config is None:
            config = GatewayConfig()
        self._config: GatewayConfig = config
        self._provider: LLMProvider = self._build_provider(config)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_provider(config: GatewayConfig) -> LLMProvider:
        provider_name = (config.get("provider") or "openai_compat").lower().strip()
        provider_cls = _PROVIDER_REGISTRY.get(provider_name)
        if provider_cls is None:
            known = ", ".join(sorted(_PROVIDER_REGISTRY))
            raise ConfigurationError(
                f"Unknown provider '{provider_name}'. " f"Supported providers: {known}."
            )
        return provider_cls(config.as_dict())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def provider(self) -> LLMProvider:
        """The active provider instance."""
        return self._provider

    def validate(self) -> None:
        """Validate the active provider configuration.

        Raises:
            ConfigurationError: if the provider is misconfigured.
        """
        self._provider.validate_config()

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Route a chat-completion request to the active provider.

        Args:
            messages: List of ``{"role": ..., "content": ...}`` dicts.
            temperature: Optional sampling temperature override.
            max_tokens: Optional maximum output-tokens override.

        Returns:
            The text content of the assistant reply.

        Raises:
            ConfigurationError: if the provider is misconfigured.
            ProviderError: if the upstream call fails.
        """
        return await self._provider.chat_completion(
            messages, temperature=temperature, max_tokens=max_tokens
        )

    def health(self) -> Dict[str, Any]:
        """Return a health/status dict from the active provider."""
        return self._provider.health()

    @staticmethod
    def supported_providers() -> List[str]:
        """Return the list of supported provider names."""
        return sorted(_PROVIDER_REGISTRY.keys())