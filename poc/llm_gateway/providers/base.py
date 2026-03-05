"""Abstract base class and shared exceptions for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ProviderError(Exception):
    """Raised when an upstream provider request fails."""


class ConfigurationError(Exception):
    """Raised when provider configuration is missing or invalid."""


class LLMProvider(ABC):
    """Abstract interface that every upstream provider must implement.

    Implementations:
    - ``OpenAICompatProvider``: any OpenAI-compatible HTTP endpoint.
    - ``CopilotProvider``: validates config and errors/stubs Copilot use.
    """

    @abstractmethod
    def validate_config(self) -> None:
        """Validate provider configuration.

        Raises:
            ConfigurationError: if required fields are absent or invalid.
        """
        raise NotImplementedError

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a chat-completion request.

        Args:
            messages: List of ``{"role": ..., "content": ...}`` dicts.
            temperature: Optional sampling temperature override.
            max_tokens: Optional maximum output tokens override.

        Returns:
            The text content of the assistant reply.

        Raises:
            ConfigurationError: if the provider is misconfigured.
            ProviderError: if the upstream call fails.
        """
        raise NotImplementedError

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Return a dict describing the provider's health / config state.

        The dict must always include at least:
        - ``"provider"``: str — the provider name.
        - ``"status"``: str — ``"ok"``, ``"degraded"``, or ``"error"``.
        """
        raise NotImplementedError