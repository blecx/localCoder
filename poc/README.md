# localCoder PoC

> ⚠️ **Experimental — not for production use.**
> APIs, data formats, and behaviour may change without notice.

---

## Project Summary

### Origin and Background

localCoder grew out of a recurring frustration: even well-scoped coding tasks
(add a function, write a test, fix a lint warning) force a developer to break
focus, context-switch to the right file, make the change, run the tests, and
verify the result. Large Language Models can perform exactly these tasks — but
wiring one up safely to a real codebase requires non-trivial glue: something to
call the model, manage the repository safely, apply the output, and validate it.

Most available tools are either cloud-hosted (code leaves the machine), tightly
coupled to a single LLM provider, or require significant setup before producing
useful output. The conversation that spawned this project asked: **what does the
simplest possible locally-runnable autonomous coding assistant look like?**

### Why Build a PoC First

Rather than designing a full production system upfront, a **Proof of Concept
(PoC)** was chosen deliberately:

- **Validate the core pipeline cheaply.** The key question is whether the
  end-to-end loop — submit task → clone repo → call LLM → apply patch → run
  tests → return result — actually works at all. A PoC answers that without
  investing in auth, scaling, or polished UX.
- **Discover real friction points.** Sandbox isolation, atomic task claiming,
  and LLM output parsing all have subtle failure modes that only emerge when
  running real code against real repositories. The PoC surfaces these cheaply.
- **Keep the blast radius small.** A PoC can be thrown away or radically
  restructured. Premature investment in infrastructure (Kubernetes, auth
  layers, rate limiting) would make pivoting expensive.
- **Provide a concrete artefact for discussion.** A running system communicates
  design intent more clearly than any specification document.

### Intended Path to MVP

The PoC establishes four foundational building blocks that an MVP will inherit
and harden:

| PoC building block    | MVP evolution                                                 |
|-----------------------|---------------------------------------------------------------|
| Task queue (PostgreSQL) | Add priority, retry logic, dead-letter queue                |
| Sandbox isolation     | Container-per-task (Docker-in-Docker or gVisor)              |
| Provider-agnostic LLM | Per-user API-key management, cost tracking, model selection  |
| Automated validation  | Richer test strategies, coverage gating, lint enforcement    |

The MVP will add authentication, multi-user access control, a web UI, and
horizontal scaling. None of those concerns are present in the PoC by design.

### User Motivations

The intended users in this early phase are developers who:

1. Want to offload repetitive, well-scoped coding tasks without sending code to
   a third-party cloud service.
2. Need to evaluate LLM output quality across multiple providers before
   committing to one.
3. Want an auditable record of every AI-generated change (who asked for what,
   what the model produced, whether the tests passed).
4. Prefer a composable pipeline they can inspect, modify, and extend rather than
   a black-box IDE plugin.

---

## Key Questions and Decisions

The following questions arose during the design conversations that shaped this
PoC. Each is answered with the decision taken and the rationale behind it.

### Q1 — Why not use an existing AI coding tool?

**Decision:** Build a minimal bespoke pipeline rather than wrapping an existing
product.

**Rationale:** Existing tools (GitHub Copilot, Cursor, Codeium) operate as IDE
plugins that require cloud connectivity and proprietary accounts. They do not
expose the raw pipeline (prompt → patch → test), making them unsuitable for
experimentation, comparison across providers, or integration into automated
workflows. The goal here is a system you fully own and can inspect.

---

### Q2 — Which LLM provider should be used?

**Decision:** Support any OpenAI-compatible provider via a single gateway,
with a built-in **stub mode** as the default.

**Rationale:** The conversation surfaced several provider candidates:
OpenAI, Azure OpenAI, Anthropic (via LiteLLM), Ollama (local open-source
models), and GitHub Models. Rather than picking one and hard-coding it,
the LLM gateway exposes a single `/v1/chat/completions` endpoint. All
internal agents talk only to that endpoint. Switching providers requires
changing two environment variables (`OPENAI_API_KEY`, `OPENAI_BASE_URL`) and
restarting the gateway — no agent code changes.

The fallback order for provider selection is: **Copilot → OpenAI → generic
OpenAI-compatible**. The Copilot adapter handles the OAuth-to-short-lived-token
exchange at `api.github.com/copilot_internal/v2/token`; see
[`poc/docs/copilot_adapter.md`](docs/copilot_adapter.md) for details.

Supported providers at a glance:

| Provider       | How to enable                                                          |
|----------------|------------------------------------------------------------------------|
| Stub (default) | Leave `OPENAI_API_KEY` empty                                           |
| OpenAI         | Set `OPENAI_API_KEY`                                                   |
| Azure OpenAI   | Set `OPENAI_API_KEY` + `OPENAI_BASE_URL` to your Azure deployment URL  |
| Ollama (local) | Set `OPENAI_API_KEY=ollama` + `OPENAI_BASE_URL=http://host.docker.internal:11434` |
| LiteLLM proxy  | Set `OPENAI_API_KEY` + `OPENAI_BASE_URL` to your LiteLLM endpoint     |

---

### Q3 — Why is stub / dummy mode important?

**Decision:** The gateway defaults to stub mode when no API key is set.

**Rationale:** This was one of the most discussed points. The argument for
making stub mode the default:

- Anyone can evaluate the **full pipeline** — submit task, claim, generate
  patch, apply, test — without registering for any service or paying anything.
- It eliminates the "works on my machine (with my key)" problem for contributors
  and reviewers.
- It provides a deterministic baseline for automated tests.
- It makes the system safe to demo in environments with no internet access.

Stub mode is not hidden or silent: the gateway prints a prominent boxed
`WARNING` at startup and the `/health` endpoint returns `"stub_warning": true`.

---

### Q4 — How should the project be structured?

**Decision:** One directory per service under `poc/`, using hyphenated names
for directories and underscore aliases for Python packages.

**Rationale:** The conversation considered several layouts:

- **Monorepo, flat:** All services in one Python package. Rejected because
  import coupling between services makes them harder to deploy or replace
  independently.
- **Full microservice repos:** Separate git repositories per service. Rejected
  as overkill for a PoC; too much friction to develop and test cross-service
  changes.
- **Chosen: single `poc/` directory, service subdirectories.** Each service
  (`hub/`, `llm-gateway/`, `agent-generalist/`, `python-runner/`, `cli/`) has
  its own `Dockerfile` and entry point. Cross-service Python imports are
  handled via `importlib`-based package aliases (e.g., `poc/llm_gateway/`
  dynamically loads from `poc/llm-gateway/`). This keeps Docker Compose
  orchestration simple while preserving independent deployability.

```
poc/
├── docker-compose.yml
├── .env.example
├── hub/                   ← FastAPI + PostgreSQL
├── llm-gateway/           ← LLM proxy (stub or real)
├── agent-generalist/      ← code-editing agent worker
├── python-runner/         ← patch-apply + pytest worker
├── cli/                   ← localcoder CLI
└── docs/                  ← detailed documentation
```

---

### Q5 — Why run locally? What is the motivation for local development?

**Decision:** The system is designed to run entirely on a developer's machine
using Docker Compose, with no mandatory external dependencies.

**Rationale:** Three concerns dominated the local-first decision:

1. **Privacy.** Code is a sensitive asset. Sending proprietary source code to a
   third-party cloud service to get AI suggestions is a real concern for
   individuals and organisations. Local execution keeps code on the machine
   unless the developer explicitly configures an external LLM API key.

2. **Latency and reliability.** Local execution is faster and available offline.
   No network round-trips to a cloud orchestration layer; the hub, agents, and
   runner are all on the same machine.

3. **Developer control.** A local setup is fully inspectable and modifiable.
   Developers can read logs in real time, attach debuggers, swap out components,
   or run the services individually without going through a cloud console.

---

### Q6 — Why Docker Compose rather than plain Python scripts?

**Decision:** All services are containerised; `docker compose up --build`
brings the full stack up in one command.

**Rationale:** Running all five services (hub, gateway, two workers, database)
as plain Python processes requires managing five separate terminal windows,
correct Python virtual environments, a local PostgreSQL installation, and
correct environment variables for each process. Docker Compose eliminates all
of that: it declares the services, their dependencies, shared volumes, and
environment in one `docker-compose.yml`. The result is a reproducible
single-command setup on any machine with Docker installed, regardless of local
Python version, OS, or system packages.

---

### Q7 — How should documentation be organised?

**Decision:** A `poc/docs/` directory with one focused document per topic
(`architecture.md`, `motivation.md`, `quick-install.md`, `usage.md`).

**Rationale:** The conversation weighed a single large README against several
smaller documents. A single README becomes hard to navigate as it grows;
individual documents per topic allow readers to go directly to what they need.
The trade-off is that cross-references must be maintained — mitigated by a
master reference table in the top-level `README.md`.

| Document | Purpose |
|----------|---------|
| [`docs/architecture.md`](docs/architecture.md) | System design, services, data flows, design decisions |
| [`docs/motivation.md`](docs/motivation.md) | Why this project exists, problems it solves |
| [`docs/quick-install.md`](docs/quick-install.md) | Step-by-step local setup |
| [`docs/usage.md`](docs/usage.md) | Stub mode, API keys, provider selection, worked examples |
| [`docs/copilot_adapter.md`](docs/copilot_adapter.md) | GitHub Copilot OAuth token adapter details |

---

### Q8 — How should install and setup work?

**Decision:** Five-step setup: clone → copy `.env.example` → `docker compose up` → install CLI → submit first task.

**Rationale:** The goal was the shortest possible path from zero to a running
system. Detailed questions discussed during design:

- *Should there be a single install script?* Decided against it — a script adds
  a layer of indirection and can fail in platform-specific ways. Explicit steps
  are more debuggable.
- *What are the minimum requirements?* Docker 24+, Docker Compose v2, Git 2.x,
  and Python 3.10+ (for the CLI only — `curl` can replace it for API calls).
- *What if the user has no API key?* Stub mode means the stack is fully
  functional without one. The `.env.example` ships with `OPENAI_API_KEY` blank.
- *How does the CLI get installed?* `pip install -e poc/cli` from the repo root,
  or `pip install -e .` from inside `poc/cli/`. The `localcoder` command is
  then available system-wide (or in the active virtualenv).

Full step-by-step instructions: [`docs/quick-install.md`](docs/quick-install.md).

---

### Q9 — Why use unified diff patches rather than full file replacements?

**Decision:** Agents produce and return **unified diff patches**
(`git diff`-format).

**Rationale:** Full file replacements are simpler to generate but have
significant downsides: they overwrite developer changes outside the LLM's
intent, are much larger to store and transfer, and are hard to review at a
glance. Diffs are:

- **Auditable** — the reviewer sees exactly what changed and nothing else.
- **Composable** — multiple patches can be reviewed and applied independently.
- **Reversible** — `git apply --reverse` undoes any patch cleanly.
- **Smaller** — only changed lines are stored as artifacts.

---

### Q10 — How is concurrent task processing handled safely?

**Decision:** Task claiming is atomic, backed by a PostgreSQL row-level
`UPDATE ... WHERE status = 'pending'` wrapped in a dedicated
`POST /tasks/{id}/claim` endpoint.

**Rationale:** Multiple agent workers may run in parallel. Without
coordination, two workers could claim the same task simultaneously, leading to
duplicate work and conflicting patches. PostgreSQL row-level locking ensures
only one worker can transition a task from `pending` to `claimed`. The design
was explicitly chosen over an application-level lock or a separate queue
service (Redis, RabbitMQ) to keep the stack simple for the PoC: PostgreSQL is
already required for the hub, so no additional infrastructure is needed.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│  Developer machine                                       │
│                                                          │
│  ┌──────────────────┐   HTTP/REST                        │
│  │  localcoder CLI  │──────────────────────────────────► │
│  └──────────────────┘                                    │
└──────────────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────┐
│  Hub  (FastAPI + PostgreSQL)                             │
│  Task queue · Repo mirror manager · Artifact store       │
└──────────────────────┬───────────────────────────────────┘
                       │  polls + pushes
           ┌───────────┴───────────┐
           ▼                       ▼
┌──────────────────────┐   ┌─────────────────────────┐
│  Generalist Agent    │   │  Python Runner           │
│  polls pending tasks │   │  applies patches,        │
│  calls LLM gateway   │   │  runs pytest             │
│  returns unified diff│   │  reports pass/fail       │
└──────────┬───────────┘   └─────────────────────────┘
           │ POST /v1/chat/completions
           ▼
┌──────────────────────────────────────────────────┐
│  LLM Gateway                                     │
│  Stub (default) · OpenAI · any compatible URL    │
└──────────────────────────────────────────────────┘
```

Services:

| Service             | Port  | Responsibility                                    |
|---------------------|-------|---------------------------------------------------|
| `hub`               | 8000  | Task queue, repo mirror management, artifact store |
| `llm-gateway`       | 8001  | LLM proxy — stub or real OpenAI-compatible        |
| `agent-generalist`  | —     | Polls tasks, sandboxes repo, generates patches    |
| `python-runner`     | —     | Applies patches, runs pytest, reports results     |
| `db`                | 5432  | PostgreSQL 16 — task state and metadata           |

Full architecture details: [`docs/architecture.md`](docs/architecture.md).

---

## How to Run

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

For detailed instructions see [`docs/quick-install.md`](docs/quick-install.md)
and [`docs/usage.md`](docs/usage.md).

---

## CLI Reference

```
localcoder submit     --repo <git-url> [--branch <branch>] --desc "<description>"
localcoder list       [--status pending|claimed|running|done|failed]
localcoder status     <task_id>
localcoder patch      <task_id>
localcoder artifacts  <task_id>
localcoder download   <task_id> <artifact_name> [--out <path>]
localcoder gateway-health
```

Hub API interactive docs: `http://localhost:8000/docs` (when the stack is running).