#!/usr/bin/env python3
"""
poc/cli/main.py – command-line interface for localCoder PoC.

Usage
-----
    python poc/cli/main.py [--session SESSION_ID] [--verbose]

Interactive REPL:
    Start without arguments and type your prompts.
    Type ``exit`` or ``quit`` to end the session.

Single-shot:
    echo "Write a bubble-sort in Python" | python poc/cli/main.py
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow sibling packages when running the CLI directly.
_POC_ROOT = Path(__file__).parent.parent
if str(_POC_ROOT) not in sys.path:
    sys.path.insert(0, str(_POC_ROOT))

from hub.hub import run_session  # noqa: E402
from db import store as db_store  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="localcoder",
        description="localCoder PoC – AI coding assistant CLI",
    )
    p.add_argument(
        "--session",
        metavar="SESSION_ID",
        help="Resume an existing session (omit to start a new one).",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print debug information.",
    )
    p.add_argument(
        "--list-sessions",
        action="store_true",
        help="List recent sessions and exit.",
    )
    p.add_argument(
        "prompt",
        nargs="?",
        help="Single-shot prompt (non-interactive mode).",
    )
    return p


async def _interactive(session_id: str | None, verbose: bool) -> None:
    """Run an interactive REPL loop."""
    print("localCoder PoC  –  type 'exit' to quit\n")
    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.lower() in {"exit", "quit", "q"}:
            break
        if not user_input:
            continue

        try:
            result = await run_session(
                user_input,
                session_id=session_id,
                verbose=verbose,
            )
            # Support both legacy `reply` return and new `(session_id, reply)` tuple.
            if isinstance(result, tuple) and len(result) == 2:
                session_id, reply = result
            else:
                reply = result
            print(f"\nAssistant> {reply}\n")
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {exc}", file=sys.stderr)


async def _single_shot(
    prompt: str,
    session_id: str | None,
    verbose: bool,
) -> None:
    result = await run_session(prompt, session_id=session_id, verbose=verbose)
    if isinstance(result, tuple) and len(result) == 2:
        _, reply = result
    else:
        reply = result
    print(reply)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.list_sessions:
        sessions = db_store.list_sessions()
        if not sessions:
            print("No sessions found.")
            return
        for s in sessions:
            print(f"{s['id']}  created={s['created_at']}  updated={s['updated_at']}")
        return

    if args.prompt:
        asyncio.run(_single_shot(args.prompt, args.session, args.verbose))
    else:
        asyncio.run(_interactive(args.session, args.verbose))


if __name__ == "__main__":
    main()
