"""
poc/generalist-agent/agent.py

A generalist coding agent that:
  1. Receives a task from the hub.
  2. Reasons about it using the LLM gateway.
  3. Optionally invokes the python-runner for code execution.
  4. Returns a structured response.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

_POC_ROOT = Path(__file__).parent.parent
if str(_POC_ROOT) not in sys.path:
    sys.path.insert(0, str(_POC_ROOT))

from llm_gateway import gateway  # noqa: E402  # type: ignore[import-not-found]

_AGENT_SYSTEM_PROMPT = """\
You are a generalist software engineering agent.
You reason step by step before producing a final answer.
When you want to run Python code, wrap it in <python>...</python> tags.
After reasoning, provide your final answer after the token: FINAL:
"""


async def run_agent(
    task: str,
    context: list[dict] | None = None,
    max_rounds: int = 5,
    python_runner_fn=None,
) -> dict[str, Any]:
    """
    Run the generalist agent on a task.

    Parameters
    ----------
    task : str
        The task description from the user.
    context : list[dict] | None
        Prior conversation turns as OpenAI message dicts.
    max_rounds : int
        Maximum agentic reasoning rounds before returning.
    python_runner_fn : callable | None
        An async callable ``(code: str) -> dict`` used to execute Python.
        If None, code blocks are noted but not executed.

    Returns
    -------
    dict with keys:
        - ``answer``: the final answer string
        - ``reasoning``: accumulated reasoning text
        - ``code_results``: list of execution results
    """
    messages: list[dict] = [{"role": "system", "content": _AGENT_SYSTEM_PROMPT}]
    if context:
        messages.extend(context)
    messages.append({"role": "user", "content": task})

    reasoning_parts: list[str] = []
    code_results: list[dict] = []

    for _round in range(max_rounds):
        response = await gateway.chat_completion(messages, temperature=0.1)
        reply: str = (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        messages.append({"role": "assistant", "content": reply})
        reasoning_parts.append(reply)

        # Check for code blocks
        code_blocks = re.findall(r"<python>(.*?)</python>", reply, re.DOTALL)
        if code_blocks and python_runner_fn is not None:
            for code in code_blocks:
                result = await python_runner_fn(code.strip())
                code_results.append(result)
                # Feed result back into the conversation
                messages.append({
                    "role": "user",
                    "content": f"Code execution result:\n```\n{result.get('output', '')}\n```",
                })

        # Check for final answer
        if "FINAL:" in reply:
            final = reply.split("FINAL:", 1)[1].strip()
            return {
                "answer": final,
                "reasoning": "\n\n".join(reasoning_parts),
                "code_results": code_results,
            }

    # If we exhausted rounds, return the last reply as the answer
    return {
        "answer": reasoning_parts[-1] if reasoning_parts else "",
        "reasoning": "\n\n".join(reasoning_parts),
        "code_results": code_results,
    }
