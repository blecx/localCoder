"""
LLM Gateway
===========
Provides an OpenAI-compatible `/v1/chat/completions` endpoint.

Routing logic
-------------
* If the environment variable ``OPENAI_API_KEY`` is set the gateway forwards
  every request to the real OpenAI API (or any OpenAI-compatible upstream
  configured via ``OPENAI_BASE_URL``).
* If ``OPENAI_API_KEY`` is **not** set the gateway uses the built-in **stub**
  provider which returns deterministic dummy responses so that the rest of the
  stack works without any external credentials.

A prominent warning is printed at startup when the stub is in use.
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

log = logging.getLogger("llm-gateway")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")

# ──────────────────────────── configuration ──────────────────────────────────

OPENAI_API_KEY: str | None = os.environ.get("OPENAI_API_KEY")
OPENAI_BASE_URL: str = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com")
DEFAULT_MODEL: str = os.environ.get("LLM_MODEL", "gpt-4o-mini")

MODE = "openai" if OPENAI_API_KEY else "stub"

# ──────────────────────────── startup / lifespan ─────────────────────────────

_STUB_WARNING = """
╔══════════════════════════════════════════════════════════════════════╗
║  ⚠  LLM GATEWAY RUNNING IN STUB (DUMMY) MODE                       ║
║                                                                      ║
║  No OPENAI_API_KEY was found.  All completions are synthetic and    ║
║  will NOT reflect real model reasoning.                             ║
║                                                                      ║
║  To enable real OpenAI calls set OPENAI_API_KEY in your .env file. ║
╚══════════════════════════════════════════════════════════════════════╝
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    if MODE == "stub":
        log.warning(_STUB_WARNING)
    else:
        log.info("LLM Gateway starting in OpenAI mode (model: %s)", DEFAULT_MODEL)
    yield


# ──────────────────────────── app ────────────────────────────────────────────

app = FastAPI(
    title="localCoder LLM Gateway",
    version="0.1.0",
    lifespan=lifespan,
)


# ──────────────────────────── stub provider ──────────────────────────────────

_STUB_SYSTEM_NOTE = (
    "[STUB MODE — no real LLM is connected; this response is a placeholder]\n\n"
)


def _stub_completion(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic dummy OpenAI chat-completion response."""
    messages: list[dict] = payload.get("messages", [])
    last_user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"),
        "(no user message)",
    )
    stub_text = (
        _STUB_SYSTEM_NOTE
        + f"Echo: {last_user}\n\n"
        "--- diff stub ---\n"
        "diff --git a/example.py b/example.py\n"
        "--- a/example.py\n"
        "+++ b/example.py\n"
        "@@ -0,0 +1,3 @@\n"
        "+# stub patch\n"
        "+def hello():\n"
        '+    return "hello from stub"\n'
    )
    completion_id = f"chatcmpl-stub-{uuid.uuid4().hex[:8]}"
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": payload.get("model", "stub"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": stub_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


# ──────────────────────────── OpenAI proxy ───────────────────────────────────

async def _openai_completion(payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{OPENAI_BASE_URL.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"OpenAI upstream error: {resp.text}",
        )
    return resp.json()


# ──────────────────────────── routes ─────────────────────────────────────────

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    payload = await request.json()
    if MODE == "stub":
        result = _stub_completion(payload)
    else:
        result = await _openai_completion(payload)
    return JSONResponse(content=result)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": MODE,
        "model": DEFAULT_MODEL if MODE == "openai" else "stub",
        "stub_warning": MODE == "stub",
    }
