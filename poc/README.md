# localCoder PoC — Multi-Agent Coding Framework

A proof-of-concept (PoC) for an autonomous, multi-agent coding framework that
runs locally with zero external dependencies, or can be wired to the real
OpenAI API by setting a single environment variable.

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│  Developer                                       │
│  ┌──────────┐  HTTP                              │
│  │ localcoder│──────────────────────────────────►│
│  │   CLI    │                                    │
│  └──────────┘                                    │
└──────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────┐
│  Hub  (FastAPI + PostgreSQL)                     │
│  - task queue (pending → claimed → done/failed)  │
│  - canonical repo clone strategy                 │
│  - artifacts stored on disk (/data/artifacts)    │
└─────────────────────┬────────────────────────────┘
                      │ polls / pushes
          ┌───────────┴───────────┐
          ▼                       ▼
┌─────────────────┐    ┌──────────────────────┐
│ Generalist Agent│    │  Python Runner       │
│ - sandbox clone │    │  - fresh sandbox     │
│ - calls LLM gw  │    │  - applies patch     │
│ - returns patch │    │  - runs pytest       │
└────────┬────────┘    └──────────────────────┘
         │ POST /v1/chat/completions
         ▼
┌─────────────────────────────────────────────┐
│  LLM Gateway                                │
│  stub mode  OR  openai mode                 │
└─────────────────────────────────────────────┘
```

### Services

| Service           | Port  | Description                                         |
|-------------------|-------|-----------------------------------------------------|
| `hub`             | 8000  | FastAPI hub — task queue, repo clones, artifacts    |
| `llm-gateway`     | 8001  | OpenAI-compatible gateway (stub or real)            |
| `agent-generalist`| —     | Long-running worker: polls tasks, writes code       |
| `python-runner`   | —     | Long-running worker: applies patches, runs pytest   |
| `db`              | 5432  | PostgreSQL 16                                       |

### Shared Docker volumes

| Volume       | Mount path       | Purpose                              |
|--------------|------------------|--------------------------------------|
| `artifacts`  | `/data/artifacts`| Hub artifact files                   |
| `repos`      | `/data/repos`    | Canonical git mirrors + worktrees    |
| `sandbox`    | `/data/sandbox`  | Generalist agent sandbox copies      |
| `runner`     | `/data/runner`   | Python-runner sandbox copies         |

---

## Quick Start

### 1. Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/)
- Python 3.10+ (for the CLI)

### 2. Configure

```bash
cd poc/
cp .env.example .env
# Edit .env — at minimum, decide whether to use stub or OpenAI mode (see below)
```

### 3. Start the stack

```bash
docker compose up --build
```

All services will start. The hub waits for PostgreSQL to be healthy before
accepting connections, and agents wait for the hub.

### 4. Install the CLI (optional but recommended)

```bash
cd poc/cli
pip install -e .
```

Or run directly:

```bash
python -m localcoder.main --help
```

---

## LLM Gateway — Stub vs OpenAI mode

### Stub mode (default)

If `OPENAI_API_KEY` is **not set** (or is an empty string), the gateway starts
in **stub mode**:

- All `/v1/chat/completions` requests return a deterministic dummy response.
- The dummy response always contains a minimal placeholder diff so that the
  rest of the pipeline can run end-to-end without any external API calls.
- **No secrets or network access required.**

A prominent warning is printed to the gateway logs at startup:

```
WARNING  llm-gateway
╔══════════════════════════════════════════════════════════════════════╗
║  ⚠  LLM GATEWAY RUNNING IN STUB (DUMMY) MODE                       ║
║                                                                      ║
║  No OPENAI_API_KEY was found.  All completions are synthetic and    ║
║  will NOT reflect real model reasoning.                             ║
║                                                                      ║
║  To enable real OpenAI calls set OPENAI_API_KEY in your .env file. ║
╚══════════════════════════════════════════════════════════════════════╝
```

The `/health` endpoint also advertises the mode:

```json
{ "status": "ok", "mode": "stub", "model": "stub", "stub_warning": true }
```

### OpenAI mode

Set `OPENAI_API_KEY` in your `.env` (or shell environment):

```dotenv
OPENAI_API_KEY=sk-...
```

The gateway will forward every request to `https://api.openai.com/v1/chat/completions`
(or the URL set in `OPENAI_BASE_URL`) using your key.  The `/health` endpoint
will show:

```json
{ "status": "ok", "mode": "openai", "model": "gpt-4o-mini", "stub_warning": false }
```

You can also point the gateway at any OpenAI-compatible upstream (Azure OpenAI,
LiteLLM, Ollama, etc.) by setting `OPENAI_BASE_URL`.

---

## CLI Usage

```
localcoder submit   --repo <git-url> [--branch main] --desc "<description>"
localcoder list     [--status pending|claimed|running|done|failed]
localcoder status   <task_id>
localcoder patch    <task_id>
localcoder artifacts <task_id>
localcoder download <task_id> <artifact_name> [--out ./file]
localcoder gateway-health
```

### Examples

```bash
# Submit a task
localcoder submit \
  --repo https://github.com/my-org/my-repo \
  --branch main \
  --desc "Add a hello_world() function to utils.py"

# Watch tasks
localcoder list
localcoder list --status pending

# Get the generated patch
localcoder patch 1

# Check gateway mode
localcoder gateway-health
```

By default the CLI connects to `http://localhost:8000` (hub) and
`http://localhost:8001` (gateway).  Override with:

```bash
export HUB_URL=http://my-hub:8000
export LLM_GATEWAY_URL=http://my-gateway:8001
```

---

## Hub API (summary)

| Method | Path                                    | Description                    |
|--------|-----------------------------------------|--------------------------------|
| GET    | `/health`                               | Liveness check                 |
| POST   | `/tasks`                                | Create a task                  |
| GET    | `/tasks`                                | List tasks (filter by status)  |
| GET    | `/tasks/next-pending`                   | Oldest pending task            |
| GET    | `/tasks/{id}`                           | Get task details               |
| PATCH  | `/tasks/{id}`                           | Update task (status, patch, …) |
| POST   | `/tasks/{id}/claim`                     | Atomically claim a task        |
| POST   | `/tasks/{id}/artifacts`                 | Upload an artifact file        |
| GET    | `/tasks/{id}/artifacts`                 | List artifacts for a task      |
| GET    | `/tasks/{id}/artifacts/{name}`          | Download an artifact           |
| POST   | `/repos/clone`                          | Clone/update a repo (mirror)   |

Full interactive docs at `http://localhost:8000/docs`.

---

## Development

### Run hub tests

```bash
cd poc/hub
pip install -r requirements.txt
# (requires a running Postgres — use docker compose up db)
DATABASE_URL=postgresql://hub:hub@localhost:5432/hub uvicorn app.main:app --reload
```

### Run gateway in isolation

```bash
cd poc/llm-gateway
pip install -r requirements.txt
uvicorn app.main:app --port 8001
# In stub mode by default — set OPENAI_API_KEY to switch to OpenAI mode
```

### Run the CLI against the stack

```bash
cd poc/cli && pip install -e .
export HUB_URL=http://localhost:8000
localcoder list
```
