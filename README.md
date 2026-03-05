# localCoder

> ⚠️ **Experimental — not for production use.**
> This is an early proof-of-concept. APIs, data formats, and behaviour may
> change without notice. It has not been security-hardened or performance-tested.

localCoder is a **locally-runnable, multi-agent coding framework** that
orchestrates autonomous code-editing agents on your own machine. You describe
a coding task in plain English; the system clones the target repository into an
isolated sandbox, uses an LLM to generate a code patch, applies and tests the
patch, and returns the result — no manual intervention required.

It works **entirely offline by default** using a built-in stub LLM, and can
be wired to OpenAI, Ollama, or any OpenAI-compatible provider by setting a
single environment variable.

---

## Current Scope

The PoC (`poc/`) implements:

- **Hub** — FastAPI + PostgreSQL task queue, repository mirror manager, and artifact store.
- **LLM Gateway** — OpenAI-compatible proxy supporting stub mode (default) and real LLM providers.
- **Generalist Agent** — Long-running worker that claims tasks, sandboxes the repo, calls the LLM, and returns a unified-diff patch.
- **Python Runner** — Long-running worker that applies patches and runs `pytest` in an isolated sandbox.
- **CLI (`localcoder`)** — Command-line interface for submitting tasks and retrieving results.
- **Full Docker Compose stack** — One command to bring everything up locally.

## Known Limitations

- **Not production-ready.** No authentication, no access control, no rate limiting.
- **Single-node only.** No horizontal scaling or high-availability design.
- **Stub output is synthetic.** In stub mode the agent returns a placeholder diff, not real code.
- **No cross-file refactoring.** Complex multi-file changes may produce incomplete patches.
- **Requires Docker.** The full stack only runs via Docker Compose (local dev without Docker is partial).
- **LLM quality varies.** Generated code must always be reviewed before merging.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](poc/docs/architecture.md) | System design, services, data flows, and key design decisions |
| [Project Motivation](poc/docs/motivation.md) | Why this project exists and what problems it solves |
| [Quick-Install Guide](poc/docs/quick-install.md) | Step-by-step local setup instructions with requirements |
| [Usage Guide](poc/docs/usage.md) | Stub mode, API keys, LLM selection, and three worked examples |
| [PoC README](poc/README.md) | Architecture diagram, CLI reference, and hub API summary |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/blecx/localCoder.git
cd localCoder/poc

# 2. Configure (defaults work for stub mode — no API key needed)
cp .env.example .env

# 3. Start the full stack
docker compose up --build

# 4. Install the CLI
cd cli && pip install -e . && cd ..

# 5. Submit a task
localcoder submit \
  --repo https://github.com/blecx/localCoder \
  --branch main \
  --desc "Add a hello_world() function to a new file hello.py"

# 6. Watch progress and get the patch
localcoder list
localcoder patch 1
```

For detailed instructions, see the [Quick-Install Guide](poc/docs/quick-install.md)
and [Usage Guide](poc/docs/usage.md).

---

## Repository Structure

```
localCoder/
├── README.md                  ← this file
└── poc/                       ← proof-of-concept implementation
    ├── docker-compose.yml
    ├── .env.example
    ├── README.md              ← PoC architecture & CLI reference
    ├── hub/                   ← FastAPI + PostgreSQL orchestration hub
    ├── llm-gateway/           ← LLM proxy (stub or OpenAI-compatible)
    ├── agent-generalist/      ← Code-editing agent worker
    ├── python-runner/         ← Patch-apply + pytest worker
    ├── cli/                   ← localcoder CLI tool
    └── docs/                  ← detailed documentation
        ├── architecture.md
        ├── motivation.md
        ├── quick-install.md
        └── usage.md
```