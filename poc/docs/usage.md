# localCoder PoC – Usage Guide

## Prerequisites

- Python 3.11+
- At least one LLM provider credential (see below)

## Installation

```bash
cd poc
pip install -r requirements.txt
```

## Configuration

Copy the example and fill in your credentials:

```bash
cp .env.example .env
# Edit .env and set at least one of:
#   COPILOT_TOKEN, OPENAI_API_KEY, or LLM_API_KEY + LLM_API_BASE
```

### Using GitHub Copilot (recommended)

```bash
export COPILOT_TOKEN=ghu_your_github_oauth_token
```

Your GitHub account must have an active Copilot subscription.
The adapter will automatically exchange the OAuth token for a
short-lived chat token and refresh it before expiry.

### Using OpenAI

```bash
export OPENAI_API_KEY=sk-your-openai-key
# Optional: override the base URL for Azure OpenAI or proxies
export OPENAI_API_BASE=https://your-endpoint.openai.azure.com/openai/deployments/gpt-4o/
```

### Using a local model (Ollama, LM Studio, vLLM, …)

```bash
export LLM_API_KEY=ollama          # any non-empty string for key-less servers
export LLM_API_BASE=http://localhost:11434/v1
export LLM_MODEL=llama3
```

### Provider priority & fallback

When multiple providers are configured, they are tried in this order:

1. GitHub Copilot
2. OpenAI
3. Generic (local)

If a provider fails, the gateway transparently falls back to the next one.

## Running the CLI

### Interactive REPL

```bash
python poc/cli/main.py
```

```
localCoder PoC  –  type 'exit' to quit

You> Write a Python function that checks if a number is prime.

Assistant> Here is a simple primality-test function:
...

You> exit
```

### Single-shot mode

```bash
python poc/cli/main.py "Explain async/await in Python in 3 sentences."
```

### Resume a session

```bash
# List existing sessions
python poc/cli/main.py --list-sessions

# Resume
python poc/cli/main.py --session <SESSION_ID>
```

### Verbose mode

```bash
python poc/cli/main.py --verbose
```

## Running with Docker Compose

```bash
cd poc
docker compose up
```

## Running tests

```bash
cd poc
pip install -r requirements.txt
pytest tests/ -v
```

## Project layout

```
poc/
├── cli/                # CLI entry point
├── db/                 # SQLite store + schema
├── docs/               # Documentation (you are here)
├── generalist-agent/   # Agentic reasoning loop
├── hub/                # Orchestration hub
├── llm-gateway/        # Multi-provider LLM gateway + Copilot adapter
├── llm_gateway/        # Python package alias (llm-gateway → llm_gateway)
├── python-runner/      # Sandboxed Python execution
├── python_runner/      # Python package alias (python-runner → python_runner)
├── tests/              # Pytest suite
├── docker-compose.yml
└── requirements.txt
```
