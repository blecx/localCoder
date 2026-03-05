# localCoder PoC — Architecture

> **Status:** Experimental proof-of-concept. Not intended for production use.

---

## Overview

localCoder is a proof-of-concept (PoC) **multi-agent coding framework** that
orchestrates autonomous code-editing agents entirely on a local machine.
A developer describes a coding task in plain English; the system clones the
target repository into an isolated sandbox, uses an LLM to generate a code
patch, applies and tests the patch, and returns the result — all without
manual intervention.

The system is designed to run with **zero external dependencies by default**:
an integrated stub LLM lets you exercise the full pipeline without any API keys
or network access. A single environment variable switches the gateway to real
OpenAI (or any compatible provider).

---

## High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│  Developer machine                                       │
│                                                          │
│  ┌──────────────────┐   HTTP/REST                        │
│  │  localcoder CLI  │────────────────────────────────►   │
│  └──────────────────┘                                    │
└──────────────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────┐
│  Hub  (FastAPI + PostgreSQL)                             │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Task Queue: pending → claimed → running →          │ │
│  │              done | failed                          │ │
│  ├─────────────────────────────────────────────────────┤ │
│  │  Repo Manager: git mirror + per-task worktrees      │ │
│  ├─────────────────────────────────────────────────────┤ │
│  │  Artifact Store: generated patches, test logs       │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────┬────────────────────────────────────┘
                      │  polls + pushes
          ┌───────────┴───────────┐
          ▼                       ▼
┌──────────────────────┐   ┌─────────────────────────┐
│  Generalist Agent    │   │  Python Runner           │
│  ─────────────────── │   │  ───────────────────     │
│  • Polls hub for     │   │  • Polls hub for         │
│    pending tasks     │   │    patch-ready tasks     │
│  • Clones repo into  │   │  • Copies repo into      │
│    sandbox           │   │    fresh sandbox         │
│  • Calls LLM gateway │   │  • Applies unified diff  │
│  • Returns unified   │   │  • Runs pytest           │
│    diff patch        │   │  • Reports pass/fail     │
└──────────┬───────────┘   └─────────────────────────┘
           │ POST /v1/chat/completions
           ▼
┌──────────────────────────────────────────────────┐
│  LLM Gateway                                     │
│  ──────────────────────────────────────────────  │
│  Stub mode  (default, no API key required)       │
│    → returns deterministic synthetic response    │
│  OpenAI mode  (set OPENAI_API_KEY)               │
│    → proxies to OpenAI (or any compatible URL)   │
└──────────────────────────────────────────────────┘
```

---

## Services

| Service             | Port  | Technology           | Responsibility                                    |
|---------------------|-------|----------------------|---------------------------------------------------|
| `hub`               | 8000  | FastAPI + PostgreSQL | Task queue, repo mirror management, artifact store |
| `llm-gateway`       | 8001  | FastAPI              | LLM proxy — stub or real OpenAI-compatible        |
| `agent-generalist`  | —     | Python worker        | Polls tasks, sandboxes repo, generates patches    |
| `python-runner`     | —     | Python worker        | Applies patches, runs pytest, reports results     |
| `db`                | 5432  | PostgreSQL 16        | Persistent task state and metadata                |

---

## Shared Docker Volumes

| Volume      | Mount Path         | Used By                         | Purpose                            |
|-------------|--------------------|---------------------------------|------------------------------------|
| `artifacts` | `/data/artifacts`  | hub                             | Uploaded artifact files            |
| `repos`     | `/data/repos`      | hub, agent-generalist, python-runner | Git mirrors and worktrees    |
| `sandbox`   | `/data/sandbox`    | agent-generalist                | Isolated sandbox per task          |
| `runner`    | `/data/runner`     | python-runner                   | Isolated run environment per task  |
| `db-data`   | (Postgres internal)| db                              | PostgreSQL data persistence        |

---

## Task Lifecycle

```
[POST /tasks]           Developer submits task description + repo URL
       │
       ▼
  pending            Task created in the database
       │
       ▼ (agent-generalist polls /tasks/next-pending)
  claimed            Agent has taken ownership
       │
       ▼ (agent generates patch via LLM gateway)
  running            Patch generated; python-runner picks it up
       │
       ├──► done     pytest passed (or no tests present)
       └──► failed   pytest failed or unrecoverable error
```

All state transitions are atomic (PostgreSQL row-level locking) to prevent
two workers from claiming the same task simultaneously.

---

## Component Details

### Hub

The hub is the central coordinator, implemented as a **FastAPI** application
backed by **PostgreSQL 16**.

Responsibilities:
- **Task queue** — CRUD endpoints for tasks; atomic `POST /tasks/{id}/claim`
  prevents double-claiming.
- **Repository management** — `POST /repos/clone` creates a bare git mirror for
  a target repository; subsequent calls do a `git fetch --prune` to keep the
  mirror up to date.
- **Artifact store** — Agents upload generated patches and test logs as named
  artifacts; the hub stores them on a shared Docker volume and serves them
  back on demand.

Interactive API documentation is available at `http://localhost:8000/docs` when
the stack is running.

### LLM Gateway

The LLM gateway presents an **OpenAI-compatible `/v1/chat/completions`**
interface, allowing the rest of the system to remain provider-agnostic.

Two modes:

| Mode       | Trigger                           | Behaviour                                             |
|------------|-----------------------------------|-------------------------------------------------------|
| **Stub**   | `OPENAI_API_KEY` not set (default) | Returns a deterministic synthetic patch; no network  |
| **OpenAI** | `OPENAI_API_KEY` set              | Proxies to OpenAI (or `OPENAI_BASE_URL` if overridden)|

A prominent `WARNING` is printed to gateway logs when running in stub mode.
The `/health` endpoint exposes `{ "mode": "stub"|"openai", "stub_warning": true|false }`.

### Generalist Agent

A long-running Python worker that:
1. Polls `GET /tasks/next-pending` every `POLL_INTERVAL` seconds.
2. Claims the task atomically.
3. Ensures the target repository is mirrored on the shared `repos` volume.
4. Creates an isolated sandbox copy of the repo in `SANDBOX_DIR`.
5. Calls the LLM gateway with the task description and relevant code context.
6. Parses the LLM response into a unified diff.
7. Uploads the patch as an artifact and transitions the task to `running`.

### Python Runner

A long-running Python worker that:
1. Polls for tasks in the `running` state.
2. Downloads the patch artifact from the hub.
3. Copies the repo into an isolated `RUNNER_DIR` sandbox.
4. Applies the patch with `git apply`.
5. Runs `pytest` (if tests are present).
6. Uploads test output as an artifact.
7. Transitions the task to `done` or `failed`.

### CLI (`localcoder`)

A lightweight Python CLI that wraps all hub HTTP endpoints:

```
localcoder submit     --repo <url> [--branch main] --desc "<description>"
localcoder list       [--status pending|claimed|running|done|failed]
localcoder status     <task_id>
localcoder patch      <task_id>
localcoder artifacts  <task_id>
localcoder download   <task_id> <artifact_name> [--out ./file]
localcoder gateway-health
```

---

## Key Design Decisions

### 1. Stub-first, zero-dependency default

**Decision:** The system works fully without an API key.

**Rationale:** Lowers the barrier to evaluating the PoC. Developers can
explore the entire task lifecycle — submit, claim, patch, test — without
registering for any external service or exposing credentials.

### 2. OpenAI-compatible LLM interface

**Decision:** The generalist agent talks to the gateway via the standard
OpenAI `/v1/chat/completions` API rather than provider-specific SDKs.

**Rationale:** Any OpenAI-compatible provider (Azure OpenAI, LiteLLM,
Ollama, GitHub Models, Anthropic via proxy) can be wired in simply by
changing `OPENAI_BASE_URL`. No agent code changes are required.

### 3. Isolated sandboxes per task

**Decision:** Each task gets its own filesystem copy of the repository.

**Rationale:** Prevents tasks from interfering with each other's file changes.
The canonical git mirror is read-only; agents always write to their own sandbox
directory.

### 4. Atomic task claiming

**Decision:** Task claiming uses a `POST /tasks/{id}/claim` endpoint backed by
a PostgreSQL row-level update.

**Rationale:** Supports running multiple agent workers in parallel without
race conditions or duplicate work.

### 5. Docker Compose for local orchestration

**Decision:** All services are containerised and wired together with Docker
Compose.

**Rationale:** Reproducible setup on any machine with Docker installed.
No global Python versions, no database installation — `docker compose up --build`
brings the full stack up in one command.

### 6. Patch-based output format

**Decision:** Agents return **unified diff patches** rather than full file
replacements.

**Rationale:** Diffs are smaller, auditable, and composable. They can be
reviewed, applied, or rejected without touching unmodified parts of the
codebase.

---

## Data Flow Summary

```
Developer
  │  localcoder submit --repo <url> --desc "Add foo()"
  ▼
Hub  ─────────────────── PostgreSQL
  │  task created (pending)
  ▼
Generalist Agent
  │  clone repo mirror → sandbox
  │  POST /v1/chat/completions → LLM Gateway
  │  parse diff from response
  │  POST /tasks/{id}/artifacts  (patch file)
  │  PATCH /tasks/{id}  status=running
  ▼
Python Runner
  │  download patch artifact
  │  git apply patch in runner sandbox
  │  pytest
  │  POST /tasks/{id}/artifacts  (test log)
  │  PATCH /tasks/{id}  status=done|failed
  ▼
Developer
  │  localcoder patch <task_id>     → view generated patch
  │  localcoder artifacts <task_id> → list logs
  └  localcoder download <task_id> <name> → save locally
```
