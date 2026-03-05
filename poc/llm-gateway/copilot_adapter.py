"""
poc/llm-gateway/copilot_adapter.py

Validated adapter for GitHub Copilot's chat API.

Responsibilities:
  1. Obtain / refresh a short-lived Copilot chat token from the GitHub
     OAuth token (COPILOT_TOKEN env var).
  2. Validate the token before use; refresh when close to expiry.
  3. Translate between the generic OpenAI-shaped payload and any
     Copilot-specific headers / quirks.
  4. Implement fallback: if the Copilot endpoint fails, signal the
     gateway to try the next provider.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

_TOKEN_REFRESH_BUFFER_SEC = 120  # refresh if fewer than 2 min remain


class CopilotTokenError(RuntimeError):
    """Raised when we cannot obtain or validate a Copilot chat token."""


class CopilotAdapter:
    """
    Wraps GitHub Copilot's chat completions endpoint.

    Usage::

        adapter = CopilotAdapter(oauth_token="ghu_...")
        response = await adapter.chat_completion(messages=[...])
    """

    _COPILOT_AUTH_URL = "https://api.github.com/copilot_internal/v2/token"
    _COPILOT_CHAT_BASE = "https://api.githubcopilot.com"

    def __init__(self, oauth_token: str | None = None) -> None:
        self._oauth_token: str = oauth_token or os.environ.get("COPILOT_TOKEN", "")
        self._chat_token: str | None = None
        self._token_expires_at: float = 0.0

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    async def _ensure_token(self) -> str:
        """Return a valid short-lived Copilot chat token, refreshing if needed."""
        now = time.time()
        if self._chat_token and now < self._token_expires_at - _TOKEN_REFRESH_BUFFER_SEC:
            return self._chat_token

        if not self._oauth_token:
            raise CopilotTokenError(
                "COPILOT_TOKEN is not set. "
                "Provide a GitHub OAuth token with Copilot access."
            )

        headers = {
            "Authorization": f"token {self._oauth_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self._COPILOT_AUTH_URL, headers=headers)
            if resp.status_code == 401:
                raise CopilotTokenError(
                    "GitHub OAuth token is invalid or missing Copilot access."
                )
            if resp.status_code == 403:
                raise CopilotTokenError(
                    "GitHub account does not have an active Copilot subscription."
                )
            resp.raise_for_status()

        data = resp.json()
        self._chat_token = data["token"]
        # The API returns an expiry timestamp in seconds since epoch.
        self._token_expires_at = float(data.get("expires_at", now + 1800))
        return self._chat_token  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Chat completion
    # ------------------------------------------------------------------

    async def chat_completion(
        self,
        messages: list[dict],
        model: str = "gpt-4o",
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send a chat-completion request via the Copilot endpoint.

        Raises:
          CopilotTokenError – credential / subscription problems.
          httpx.HTTPStatusError – non-2xx response after token is valid.
        """
        token = await self._ensure_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Copilot-Integration-Id": "vscode-chat",
            "Editor-Version": "vscode/1.85.0",
            "Editor-Plugin-Version": "copilot-chat/0.11.1",
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }
        url = f"{self._COPILOT_CHAT_BASE}/chat/completions"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Validation helper (used by gateway to probe liveness)
    # ------------------------------------------------------------------

    async def validate(self) -> bool:
        """
        Return True if the adapter can successfully obtain a chat token.
        Does NOT make a chat request – just verifies credentials.
        """
        try:
            await self._ensure_token()
            return True
        except CopilotTokenError:
            return False
