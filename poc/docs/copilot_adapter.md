# GitHub Copilot Adapter – Integration Notes

## Overview

`poc/llm-gateway/copilot_adapter.py` implements a validated adapter
for GitHub Copilot's internal chat completions API.

## Token exchange flow

```
GitHub OAuth token (ghu_…)
   ↓  GET https://api.github.com/copilot_internal/v2/token
Short-lived chat token (valid ~30 min)
   ↓  POST https://api.githubcopilot.com/chat/completions
OpenAI-compatible response
```

## Validation

Before every request the adapter checks whether the cached chat token
has more than 2 minutes remaining.  If not, it automatically re-fetches
it.  The `validate()` method performs a dry-run token fetch without
making a chat request – useful for health checks.

### Error mapping

| HTTP status | Meaning                          | Exception raised        |
|-------------|----------------------------------|-------------------------|
| 401         | OAuth token invalid / expired    | `CopilotTokenError`     |
| 403         | No active Copilot subscription   | `CopilotTokenError`     |
| other 4xx   | Unexpected error                 | `httpx.HTTPStatusError` |

## Fallback behaviour

`CopilotTokenError` and any `httpx` exceptions are caught by the
gateway's provider loop in `gateway.py`.  The gateway then tries the
next configured provider (OpenAI or generic) transparently.

## Required scopes

The GitHub OAuth token (`COPILOT_TOKEN`) must have the
`copilot` (or `read:copilot`) scope.  Tokens obtained via the GitHub
Device Flow with the VS Code Copilot extension automatically carry
the correct scopes.

## Headers sent to the Copilot API

```
Authorization:         Bearer <chat_token>
Content-Type:          application/json
Accept:                application/json
Copilot-Integration-Id: vscode-chat
Editor-Version:        vscode/1.85.0
Editor-Plugin-Version: copilot-chat/0.11.1
```

These mimic the VS Code Copilot Chat extension so that the API
accepts requests from the PoC client.
