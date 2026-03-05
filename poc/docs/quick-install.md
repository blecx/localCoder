# localCoder PoC — Quick-Install Guide

> **Status:** Experimental proof-of-concept. Not intended for production use.

This guide walks you through setting up the complete localCoder PoC stack on
your local machine, from installing prerequisites to running your first task.

---

## Requirements

### Required software

| Tool               | Minimum version | Where to get it                                      |
|--------------------|-----------------|------------------------------------------------------|
| **Docker**         | 24+             | https://docs.docker.com/get-docker/                  |
| **Docker Compose** | 2.20+ (v2 CLI)  | Bundled with Docker Desktop; standalone: https://docs.docker.com/compose/install/ |
| **Git**            | 2.x             | https://git-scm.com/downloads                        |
| **Python**         | 3.10+           | https://www.python.org/downloads/ (CLI only — not needed if you use `curl`) |

> **Docker Desktop** (macOS/Windows) bundles both Docker and Docker Compose v2.
> On Linux, install the Docker Engine package and the Compose plugin separately.

### Optional

| Tool    | Purpose                                          |
|---------|--------------------------------------------------|
| `curl`  | Quick API testing without installing the CLI     |
| `jq`    | Prettify JSON responses when using `curl`        |

### Hardware

- **RAM:** 2 GB free minimum (4 GB+ recommended if using a real LLM locally)
- **Disk:** ~1 GB for Docker images; more for cloned repositories
- **Network:** Only needed if you connect a real LLM API

---

## Step-by-Step Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/blecx/localCoder.git
cd localCoder
```

### Step 2 — Create your environment file

```bash
cd poc
cp .env.example .env
```

Open `.env` in any text editor. The defaults are sufficient to run in
**stub mode** (no LLM API required). See
[Adding API Keys](#adding-api-keys-optional) below if you want to connect a
real LLM.

`.env.example` reference:

```dotenv
# ── LLM Gateway ────────────────────────────────────────────────────────────
# Leave blank to run in stub mode (default).
OPENAI_API_KEY=

# Override base URL if using a compatible provider (Azure, LiteLLM, Ollama…)
# OPENAI_BASE_URL=https://api.openai.com

# Model to use in OpenAI mode.
# LLM_MODEL=gpt-4o-mini

# ── Hub ────────────────────────────────────────────────────────────────────
# DATABASE_URL=postgresql://hub:hub@db:5432/hub
# ARTIFACTS_DIR=/data/artifacts
# REPOS_DIR=/data/repos

# ── CLI (local only, not inside Docker) ────────────────────────────────────
# HUB_URL=http://localhost:8000
# LLM_GATEWAY_URL=http://localhost:8001
```

### Step 3 — Build and start the stack

```bash
# From the poc/ directory:
docker compose up --build
```

First run downloads base images (~300–500 MB) and builds the service images.
Subsequent runs skip the download step. You will see log output from all
services interleaved. Wait until you see lines similar to:

```
hub           | INFO:     Application startup complete.
llm-gateway   | INFO:     Application startup complete.
agent-generalist | INFO  polling hub every 5 s …
python-runner | INFO  polling hub every 10 s …
```

> **Tip:** To run in the background, add `-d`:
> ```bash
> docker compose up --build -d
> ```
> Then follow logs with `docker compose logs -f`.

### Step 4 — Verify the stack is healthy

In a new terminal window (or use `-d` mode):

```bash
# Hub health check
curl -s http://localhost:8000/health | python3 -m json.tool
# Expected: {"status": "ok"}

# LLM gateway health check
curl -s http://localhost:8001/health | python3 -m json.tool
# Expected (stub mode): {"status": "ok", "mode": "stub", "model": "stub", "stub_warning": true}
```

### Step 5 — Install the CLI (recommended)

```bash
cd poc/cli
pip install -e .
```

Verify:

```bash
localcoder --help
```

Expected output:

```
Usage: localcoder [OPTIONS] COMMAND [ARGS]...

  localCoder CLI — submit and manage coding tasks.

Options:
  --help  Show this message and exit.

Commands:
  submit          Submit a new coding task.
  list            List tasks.
  status          Get task details.
  patch           Print the generated patch for a task.
  artifacts       List artifacts for a task.
  download        Download an artifact file.
  gateway-health  Show LLM gateway status.
```

Alternatively, without installing:

```bash
cd poc/cli
python -m localcoder.main --help
```

---

## Adding API Keys (Optional)

To connect a **real LLM**, edit `poc/.env` before starting (or restart the
stack after editing):

### OpenAI

```dotenv
OPENAI_API_KEY=sk-proj-...yourkey...
LLM_MODEL=gpt-4o-mini
```

### Azure OpenAI

```dotenv
OPENAI_API_KEY=<your-azure-api-key>
OPENAI_BASE_URL=https://<your-resource>.openai.azure.com/openai/deployments/<deployment>
LLM_MODEL=gpt-4o
```

### Ollama (local open-source models)

Install Ollama from https://ollama.com, pull a model, then:

```dotenv
OPENAI_API_KEY=ollama           # any non-empty value
OPENAI_BASE_URL=http://host.docker.internal:11434
LLM_MODEL=codellama             # or any model you have pulled
```

> **Note:** `host.docker.internal` resolves to your host machine from inside
> Docker containers on macOS and Windows. On Linux, use your host's IP address
> (often `172.17.0.1` on the default Docker bridge network).

### LiteLLM proxy

```dotenv
OPENAI_API_KEY=<your-key>
OPENAI_BASE_URL=http://host.docker.internal:4000
LLM_MODEL=gpt-4o
```

After editing `.env`, restart the gateway:

```bash
docker compose restart llm-gateway
```

Verify the switch:

```bash
curl -s http://localhost:8001/health | python3 -m json.tool
# Expected (OpenAI mode): {"status": "ok", "mode": "openai", "model": "gpt-4o-mini", "stub_warning": false}
```

---

## Stopping and Cleaning Up

```bash
# Stop all containers (keeps data volumes)
docker compose down

# Stop and remove all data volumes (full clean slate)
docker compose down -v
```

---

## Troubleshooting

| Symptom                              | Likely cause / fix                                                    |
|--------------------------------------|-----------------------------------------------------------------------|
| `docker compose: command not found`  | Install Docker Compose v2 plugin; ensure `docker compose` (space, not hyphen) works |
| Hub returns 502 or not reachable     | PostgreSQL not yet healthy; wait a few seconds and retry             |
| Gateway `/health` shows `stub_warning: true` | No `OPENAI_API_KEY` in `.env` — this is normal for stub mode |
| `pip install -e .` fails             | Ensure Python 3.10+ is active: `python3 --version`                  |
| Containers exit immediately          | Run `docker compose logs <service>` to read the error output          |
| Port 8000 or 8001 already in use     | Change the host port mapping in `poc/docker-compose.yml`, e.g. `"8080:8000"` |
