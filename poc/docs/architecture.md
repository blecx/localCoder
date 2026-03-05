# localCoder PoC – Architecture

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                      CLI (poc/cli)                      │
│  Interactive REPL / single-shot prompt entry point      │
└────────────────────────┬────────────────────────────────┘
                         │ async run_session()
┌────────────────────────▼────────────────────────────────┐
│                     Hub (poc/hub)                       │
│  Orchestrates session state, LLM calls, and tool use    │
└──────┬──────────────────────────┬───────────────────────┘
       │                          │
       │ chat_completion()        │ run_agent()
┌──────▼──────────┐    ┌──────────▼──────────────────────┐
│  LLM Gateway    │    │  Generalist Agent               │
│  poc/llm-gateway│    │  poc/generalist-agent           │
│                 │    │  Agentic reasoning loop +       │
│  Providers:     │    │  tool-call extraction           │
│  1. Copilot ──► │    └──────────┬──────────────────────┘
│  2. OpenAI  ──► │               │ run_python()
│  3. Generic ──► │    ┌──────────▼──────────────────────┐
│  (with fallback)│    │  Python Runner                  │
└──────┬──────────┘    │  poc/python-runner              │
       │               │  Sandboxed subprocess execution │
       │               └─────────────────────────────────┘
       │
┌──────▼──────────┐
│  Database       │
│  poc/db         │
│  SQLite (WAL)   │
│  sessions /     │
│  messages /     │
│  tool_calls     │
└─────────────────┘
```

## Components

### `poc/hub`
Central orchestrator.  Manages session lifecycle (create / resume),
builds the message history, calls the LLM gateway, and persists all
turns to the database.

### `poc/db`
Thin SQLite wrapper with WAL mode enabled.  Provides helpers for
sessions, messages, and tool-call records.  Schema defined in
`poc/db/schema.sql`.

### `poc/llm-gateway`
OpenAI-compatible gateway that abstracts over multiple upstream LLM
providers.  Providers are tried in order:

1. **GitHub Copilot** (`COPILOT_TOKEN`) – validated via
   `copilot_adapter.py` which handles short-lived token exchange and
   automatic refresh.
2. **OpenAI** (`OPENAI_API_KEY`) – standard OpenAI API.
3. **Generic** (`LLM_API_KEY` + `LLM_API_BASE`) – any
   OpenAI-compatible endpoint (Ollama, vLLM, LM Studio, etc.).

If a provider fails (any exception), the gateway automatically falls
back to the next configured provider.

### `poc/generalist-agent`
A reasoning agent that runs a multi-round "think → act → observe" loop.
It extracts `<python>…</python>` code blocks from LLM replies and
executes them via the python-runner, feeding results back into the
conversation.

### `poc/python-runner`
Executes arbitrary Python code in an isolated subprocess with a
configurable timeout (default 10 s).  Captures stdout + stderr
(capped at 64 KiB) and returns exit code and timeout status.

### `poc/cli`
Interactive REPL and single-shot CLI.  Supports session resumption via
`--session SESSION_ID`.

## Data flow (single turn)

```
User input
   → CLI.main()
   → hub.run_session()
       → db.create_session() / db.add_message("user", …)
       → gateway.chat_completion(history)
           → try Copilot → try OpenAI → try Generic
       → db.add_message("assistant", …)
   → print response
```

## Environment variables

| Variable           | Required | Description                                  |
|--------------------|----------|----------------------------------------------|
| `COPILOT_TOKEN`    | optional | GitHub OAuth token with Copilot access       |
| `OPENAI_API_KEY`   | optional | OpenAI API key                               |
| `OPENAI_API_BASE`  | optional | Override OpenAI base URL                     |
| `LLM_API_KEY`      | optional | Generic provider API key                     |
| `LLM_API_BASE`     | optional | Generic provider base URL                    |
| `LLM_MODEL`        | optional | Override model name (all providers)          |
| `LOCALCODER_DB`    | optional | Path to SQLite DB (default: `poc/.localcoder.db`) |
| `PYTHON_RUNNER_TIMEOUT` | optional | Subprocess timeout in seconds (default: 10) |

At least one of `COPILOT_TOKEN`, `OPENAI_API_KEY`, or
`LLM_API_KEY + LLM_API_BASE` must be set.
