# localCoder

AI coding assistant running entirely on your machine.

## PoC

The `poc/` directory contains a working proof-of-concept implementation.

```
poc/
├── cli/               CLI entry point (interactive REPL + single-shot)
├── db/                SQLite session/message store
├── docs/              Architecture and usage documentation
├── generalist-agent/  Multi-round reasoning agent
├── hub/               Orchestration hub
├── llm-gateway/       OpenAI-compatible gateway (Copilot + OpenAI + local)
├── python-runner/     Sandboxed Python execution service
├── tests/             Pytest test suite
└── docker-compose.yml
```

### Quick start

```bash
cd poc
pip install -r requirements.txt
export COPILOT_TOKEN=ghu_...   # or OPENAI_API_KEY or LLM_API_KEY+LLM_API_BASE
python cli/main.py
```

See [`poc/docs/usage.md`](poc/docs/usage.md) for the full guide and
[`poc/docs/architecture.md`](poc/docs/architecture.md) for the design.