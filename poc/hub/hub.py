"""
poc/hub/hub.py – central orchestration hub for localCoder PoC.

The hub wires together:
  • The LLM gateway (with Copilot adapter + fallback)
  • The generalist agent
  • The python-runner service
  • Persistent session storage (via poc/db)

It exposes an async ``run_session`` coroutine that drives a single
interactive session from start to finish.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow sibling packages to be imported when running the hub directly.
_POC_ROOT = Path(__file__).parent.parent
if str(_POC_ROOT) not in sys.path:
    sys.path.insert(0, str(_POC_ROOT))

from db import store as db_store  # noqa: E402
from llm_gateway import gateway  # type: ignore[import-not-found]  # noqa: E402


async def run_session(
    user_input: str,
    session_id: str | None = None,
    verbose: bool = False,
) -> str:
    """
    Drive one turn of a localCoder session.

    Parameters
    ----------
    user_input:
        The user's message / task description.
    session_id:
        Resume an existing session or create a new one if None.
    verbose:
        Print intermediate steps to stdout.

    Returns
    -------
    str
        The final assistant response.
    """
    # ── 1. Session bookkeeping ────────────────────────────────────────
    if session_id is None:
        session_id = db_store.create_session()
        if verbose:
            print(f"[hub] New session: {session_id}")
    else:
        session = db_store.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id!r} not found.")

    db_store.add_message(session_id, "user", user_input)

    # ── 2. Build message history for the LLM ─────────────────────────
    history = db_store.get_messages(session_id)
    llm_messages: list[dict[str, str]] = []

    # Inject system prompt on first turn
    if len(history) == 1:
        llm_messages.append({
            "role": "system",
            "content": _SYSTEM_PROMPT,
        })

    for msg in history:
        llm_messages.append({"role": msg["role"], "content": msg["content"]})

    # ── 3. Call the LLM gateway ───────────────────────────────────────
    if verbose:
        print("[hub] Calling LLM gateway …")

    response = await gateway.chat_completion(llm_messages)
    assistant_text: str = (
        response.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )

    # ── 4. Persist assistant response ────────────────────────────────
    db_store.add_message(session_id, "assistant", assistant_text)

    if verbose:
        print(f"[hub] Assistant: {assistant_text[:120]}…")

    return assistant_text


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are localCoder, an AI coding assistant running locally.
You help users write, debug, and understand code.
When you need to execute Python code, describe it clearly between
<python> and </python> tags and the python-runner will execute it.
Always be concise, accurate, and helpful.
"""
