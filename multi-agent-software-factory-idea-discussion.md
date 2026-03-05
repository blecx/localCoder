# Multi-Agent Software Factory — Idea Discussion

> **Purpose:** This document is a historical and technical record for the team.
> It captures the motivations, design decisions, and rationale that shaped the
> localCoder proof-of-concept (PoC) and outlines the planned path toward an
> MVP. It is written in an interview-style Q&A format to preserve the reasoning
> behind every significant decision.

---

## Table of Contents

1. [Background and Motivation](#1-background-and-motivation)
2. [Interview-Style Q&A Transcript](#2-interview-style-qa-transcript)
   - 2.1 [What problem are we actually solving?](#21-what-problem-are-we-actually-solving)
   - 2.2 [Why build this ourselves instead of using an existing tool?](#22-why-build-this-ourselves-instead-of-using-an-existing-tool)
   - 2.3 [What is the "software factory" concept?](#23-what-is-the-software-factory-concept)
   - 2.4 [Why start with a PoC rather than going straight to MVP?](#24-why-start-with-a-poc-rather-than-going-straight-to-mvp)
   - 2.5 [Why is there only one generalist agent in the PoC?](#25-why-is-there-only-one-generalist-agent-in-the-poc)
   - 2.6 [What is wrong with a single generalist agent at scale?](#26-what-is-wrong-with-a-single-generalist-agent-at-scale)
   - 2.7 [What does the target multi-agent architecture look like?](#27-what-does-the-target-multi-agent-architecture-look-like)
   - 2.8 [How do "slim/dumb" coding agents differ from the generalist?](#28-how-do-slimdumb-coding-agents-differ-from-the-generalist)
   - 2.9 [How does the orchestrator decompose and assign tasks?](#29-how-does-the-orchestrator-decompose-and-assign-tasks)
   - 2.10 [What are the PoC success criteria?](#210-what-are-the-poc-success-criteria)
   - 2.11 [What are the MVP success criteria?](#211-what-are-the-mvp-success-criteria)
   - 2.12 [What is the rationale for keeping the LLM behind a gateway?](#212-what-is-the-rationale-for-keeping-the-llm-behind-a-gateway)
   - 2.13 [Why unified-diff patches instead of full file replacements?](#213-why-unified-diff-patches-instead-of-full-file-replacements)
   - 2.14 [How does sandboxing protect the developer's working copy?](#214-how-does-sandboxing-protect-the-developers-working-copy)
   - 2.15 [What is the role of the Python Runner?](#215-what-is-the-role-of-the-python-runner)
   - 2.16 [Why Docker Compose for local orchestration?](#216-why-docker-compose-for-local-orchestration)
   - 2.17 [What are the known limitations we are intentionally deferring?](#217-what-are-the-known-limitations-we-are-intentionally-deferring)
3. [PoC Goals and Scope](#3-poc-goals-and-scope)
4. [MVP Goals and Scope](#4-mvp-goals-and-scope)
5. [Roadmap](#5-roadmap)
6. [Architecture Deep-Dive](#6-architecture-deep-dive)
   - 6.1 [PoC: Single Generalist Agent (current state)](#61-poc-single-generalist-agent-current-state)
   - 6.2 [MVP: Orchestrator + Slim Coding Agents (target state)](#62-mvp-orchestrator--slim-coding-agents-target-state)
   - 6.3 [Why the design must evolve](#63-why-the-design-must-evolve)
7. [Key Decisions Log](#7-key-decisions-log)
8. [Glossary](#8-glossary)

---

## 1. Background and Motivation

Modern software development involves large amounts of repetitive, well-scoped
coding work: adding functions, writing tests, fixing lint errors, updating
dependencies. These tasks are conceptually simple but still pull developers
away from higher-order thinking. LLMs have demonstrated the ability to handle
exactly these kinds of tasks — yet making them work reliably in a local
workflow requires significant glue code.

**localCoder** was started to answer a single focused question:

> *What does a minimal, self-contained, locally-runnable autonomous coding
> assistant look like — one that respects the developer's privacy, keeps code
> off the cloud by default, and validates its own output?*

The project is not trying to replace developers. It is trying to give
developers a way to delegate the mechanical parts of coding to autonomous agents
while retaining full review authority over every change before it lands in the
repository.

The broader vision — a **multi-agent software factory** — imagines a
pipeline where one intelligent orchestrator breaks a large engineering goal
into fine-grained tasks, dispatches each task to a specialized agent, and
assembles the results into a coherent, reviewed, and tested pull request.
The PoC is step one on that path.

---

## 2. Interview-Style Q&A Transcript

### 2.1 What problem are we actually solving?

**Q:** In one sentence, what is the core problem?

**A:** Developers spend too much time on mechanical coding work that an LLM
could do faster — but no lightweight, privacy-preserving, locally-runnable
tool exists to automate that loop end-to-end.

**Q:** What does "end-to-end" mean here?

**A:** Taking a plain-English task description all the way through to a
reviewed, tested patch that the developer can inspect and apply with a single
command. That includes: calling the LLM, applying the generated code to a
safe sandbox, running the test suite, and surfacing a pass/fail verdict
alongside the patch — without the developer having to touch any of that
manually.

---

### 2.2 Why build this ourselves instead of using an existing tool?

**Q:** There are tools like GitHub Copilot, Cursor, and Devin. Why build yet
another one?

**A:** Three reasons:

1. **Privacy.** Every hosted AI coding tool sends your source code to a
   cloud service. For teams working on proprietary or sensitive codebases,
   that is a non-starter. localCoder runs entirely on the developer's machine.
   Nothing leaves the box unless the developer explicitly configures an
   external LLM endpoint.

2. **Provider agnosticism.** Existing tools are tightly coupled to one LLM
   provider. Switching from OpenAI to Ollama or a local model requires
   rewiring integrations. Our LLM gateway exposes one OpenAI-compatible
   interface to all internal agents; the entire provider stack can be swapped
   by changing a single environment variable.

3. **Auditability.** When a hosted tool makes a change, it is often opaque —
   you see a diff but not the prompt that produced it, and you certainly
   do not know whether it ran the tests. We wanted every task to leave a
   durable, retrievable record: what was asked, what was generated, and
   whether the tests passed.

---

### 2.3 What is the "software factory" concept?

**Q:** What do you mean by "multi-agent software factory"?

**A:** Think of it as a production line for code changes. A developer (or a
planning agent) defines a high-level engineering goal — for example, "add
pagination to the user-listing endpoint". That goal gets decomposed into
a set of fine-grained tasks: create the query parameter, update the SQL
query, update the serialiser, update the OpenAPI spec, write a test.

Each task is then dispatched to a specialized coding agent. Each agent
operates in isolation — it receives a task description, a repository
snapshot, and permission to write to exactly the files it needs. It
produces a patch. The patches are assembled, tested, and eventually
merged.

The factory metaphor captures two key ideas:
- **Specialization:** different agents are good at different things.
- **Assembly:** the output of many agents is assembled into a coherent
  whole, rather than one agent producing a monolithic change.

---

### 2.4 Why start with a PoC rather than going straight to MVP?

**Q:** Why not just build the full thing from the start?

**A:** We needed to validate several assumptions before investing in a
complex multi-agent architecture:

1. Can we reliably round-trip a task description through an LLM and get a
   valid, apply-able unified-diff patch back?
2. Can we sandbox the repository safely enough that concurrent agents do not
   interfere with each other?
3. Can we wire together a task queue, an LLM proxy, and a test runner with
   minimal friction?
4. Can a developer get the whole stack running in one command?

If any of these assumptions turned out to be wrong, a complex multi-agent
design would just amplify the failure. The PoC tests the pipeline
plumbing with the simplest possible agent design — one generalist — so
we can iterate quickly. Only once the PoC validates the end-to-end loop
does it make sense to invest in the more complex agent specialization that
the MVP requires.

---

### 2.5 Why is there only one generalist agent in the PoC?

**Q:** Why did you choose to have a single generalist agent rather than
specialized agents from the start?

**A:** Several deliberate reasons:

**Simplicity of validation.** The PoC's primary goal is to prove that the
pipeline works at all — that a task goes in, gets processed, and a
reviewed, tested patch comes out the other end. One agent is the minimum
viable pipeline. Adding agent specialization before the pipeline is proven
would conflate two separate problems.

**Reduced surface area.** A single agent type means a single worker
implementation, a single Docker service, a single set of environment
variables, and a single failure mode to debug. This drastically reduces the
time to first working demo.

**Flexibility of the generalist approach at small scale.** At the scale
of the PoC — one or two tasks at a time, small repositories — a
generalist agent that does everything is actually fine. It clones the repo,
calls the LLM with the full file tree as context, and returns a patch.
The overhead of decomposition and coordination is not justified for tasks
that simple.

**Learning what specialization is actually needed.** Until we have run
the pipeline on a meaningful variety of real tasks, we do not know
*which* specializations will add the most value. Observing a generalist
agent work (and fail) on diverse tasks is the best way to learn what
sub-agents to build for the MVP.

---

### 2.6 What is wrong with a single generalist agent at scale?

**Q:** So why not just keep the generalist approach in the MVP?

**A:** Several problems emerge as task complexity and volume increase:

**Context window saturation.** The generalist agent sends the entire file
tree (and sometimes file contents) to the LLM in a single prompt. For a
small toy repository, the context fits comfortably. For a production
codebase with hundreds of files, the relevant context for a single change
represents a tiny fraction of the total, but the generalist agent has no
principled way to select just the right context. Token limits become a
hard ceiling on task complexity.

**Prompt complexity and reliability.** A prompt that asks the LLM to
"understand the architecture, identify the right files, write the code,
format it as a unified diff" is doing many things at once. Each additional
responsibility in the prompt reduces the reliability of each individual
step. Specialized agents can have lean, focused prompts that are easier
to tune.

**Throughput.** A single generalist agent processes one task at a time.
A software factory needs to process many tasks in parallel, potentially
with different SLAs for different task types (a test-writing task is
cheaper and faster than a feature implementation task). A pool of slim
coding agents, each handling one type of task, scales horizontally much
more naturally.

**Error isolation.** When a generalist agent fails, the failure could be
in any of a dozen steps. With specialized agents, a failure localizes
immediately to its agent type, making diagnosis faster.

---

### 2.7 What does the target multi-agent architecture look like?

**Q:** Describe the MVP architecture.

**A:** At a high level:

```
Developer / CI trigger
        │
        ▼
  Orchestrator Agent
  ─────────────────────────────────────────────────
  • Receives a high-level engineering goal
  • Analyses the repository (file tree, existing tests, conventions)
  • Decomposes the goal into a list of fine-grained tasks
  • For each task, selects the appropriate agent type
  • Dispatches tasks to the Hub's queue
  • Monitors task completion
  • Assembles individual patches into a coherent branch
        │
        ├─── task: "write implementation" ──► Coding Agent (implementation)
        ├─── task: "write unit tests"     ──► Coding Agent (test-writing)
        ├─── task: "update docs"          ──► Coding Agent (documentation)
        └─── task: "lint/format fixes"    ──► Coding Agent (formatter)
                        │
                        ▼
              Python Runner (validates each patch)
                        │
                        ▼
              Orchestrator assembles branch, opens PR
```

The **Orchestrator** is the only agent that needs broad reasoning and deep
context. The **Coding Agents** are intentionally narrow. Each coding agent
receives a single, focused instruction with only the context it needs —
typically the diff of a few target files — and returns a patch.

---

### 2.8 How do "slim/dumb" coding agents differ from the generalist?

**Q:** What exactly makes a coding agent "slim" or "dumb"?

**A:** By "slim" and "dumb" we mean agents that are deliberately constrained
to do less:

| Dimension            | Generalist Agent (PoC)              | Slim Coding Agent (MVP)               |
|----------------------|-------------------------------------|---------------------------------------|
| **Context given**    | Full file tree + description        | Specific file(s) + targeted instruction|
| **Prompt complexity**| Multi-step: understand, plan, code  | Single-step: implement this change    |
| **Task scope**       | Any coding task                     | One narrow task type                  |
| **Decision-making**  | Chooses which files to modify       | Told exactly which files to modify    |
| **LLM call**         | One large call per task             | One small focused call per sub-task   |
| **Error handling**   | Must recover from planning mistakes | Failures are narrow and diagnosable   |

"Dumb" is not pejorative — it reflects a deliberate architectural choice.
The intelligence (planning, decomposition, context selection) is concentrated
in the Orchestrator. The coding agents are intentionally thin so that:
- Their prompts are easy to tune and test in isolation.
- They are cheap to run (small prompts = fewer tokens = lower cost).
- They are easy to replace (swap one agent implementation without touching
  the others).
- They can be run in large parallel pools without coordination overhead.

---

### 2.9 How does the orchestrator decompose and assign tasks?

**Q:** Walk through how the orchestrator would handle a real task.

**A:** Example goal: *"Add pagination to GET /users".*

**Step 1 — Repository analysis.** The orchestrator calls the LLM with the
full file tree and asks it to identify the files relevant to the `/users`
endpoint: `routes/users.py`, `models/user.py`, `schemas/user.py`,
`tests/test_users.py`, and `openapi.yaml`.

**Step 2 — Decomposition.** The orchestrator asks the LLM to break the
goal into sub-tasks. A typical decomposition:

1. Add `?page` and `?per_page` query parameters to `GET /users` in `routes/users.py`.
2. Update the SQL query in `models/user.py` to use `LIMIT`/`OFFSET`.
3. Add a `PaginatedUserList` response schema to `schemas/user.py`.
4. Update `openapi.yaml` to document the new parameters and response shape.
5. Write a pytest test in `tests/test_users.py` covering pagination behavior.

**Step 3 — Dispatch.** Each sub-task is posted to the Hub's task queue,
tagged with its type (implementation, schema, docs, test). The orchestrator
picks the appropriate coding agent type for each tag.

**Step 4 — Monitoring.** The orchestrator polls the Hub for sub-task
completion. As patches arrive, it checks for conflicts between patches
touching the same file.

**Step 5 — Assembly.** Once all sub-tasks are done and tested, the
orchestrator applies the patches in dependency order to a clean branch
and opens a pull request (or hands the branch back to the developer).

---

### 2.10 What are the PoC success criteria?

**Q:** How do we know when the PoC is done?

**A:** The PoC is successful when:

1. `docker compose up --build` starts the entire stack reliably on a clean
   machine with only Docker installed.
2. A developer can submit a plain-English task via the CLI and get a
   valid, apply-able unified-diff patch back.
3. The Python Runner successfully applies the patch in an isolated sandbox
   and returns a `pytest` pass/fail result.
4. The task lifecycle (pending → claimed → running → done/failed) is
   correctly reflected in the Hub's database and surfaced through the CLI.
5. The full pipeline works in stub mode (no API keys required) and
   switches to real OpenAI by setting a single environment variable.
6. A CI pipeline (GitHub Actions) runs the test suite and linter on every
   pull request with no manual steps.

---

### 2.11 What are the MVP success criteria?

**Q:** And for the MVP?

**A:** The MVP is successful when:

1. An orchestrator agent can receive a multi-file feature request, decompose
   it into sub-tasks, dispatch them to coding agents, and assemble the results.
2. At least two specialized coding agent types exist (e.g. implementation
   and test-writing) and are dispatched selectively.
3. The system handles task parallelism: multiple coding agents run concurrently
   without interfering with each other's sandboxes or patches.
4. Patch conflict detection prevents the orchestrator from assembling
   incompatible patches.
5. The assembled branch passes the full test suite.
6. A developer can review the work of each sub-agent individually before
   the final branch is assembled.
7. Horizontal scaling: adding more coding agent workers increases throughput
   without any configuration changes.

---

### 2.12 What is the rationale for keeping the LLM behind a gateway?

**Q:** Why not have agents call the LLM directly?

**A:** Three reasons:

1. **Provider swappability.** All agents call `POST /v1/chat/completions`
   on `http://llm-gateway:8001`. The gateway is the only component that knows
   which actual provider to use. Switching from OpenAI to Ollama to GitHub
   Models is a one-line environment variable change (`OPENAI_BASE_URL`).
   No agent code changes.

2. **Stub mode.** For development and CI, the gateway can return a
   deterministic synthetic response without any network call. Every agent
   works correctly against the stub — which means the full pipeline is
   testable without API keys or internet access.

3. **Centralized observability.** All LLM traffic flows through one service.
   Future features like cost tracking, rate limiting, request logging, and
   model routing can be added to the gateway without touching agent code.

---

### 2.13 Why unified-diff patches instead of full file replacements?

**Q:** Why return diffs rather than complete rewritten files?

**A:** Diffs are:

- **Smaller.** A ten-line change in a thousand-line file is ten lines in
  a patch, not a thousand.
- **Auditable.** A reviewer can see exactly what changed without diffing
  two large files manually.
- **Composable.** In the MVP, multiple agents each produce a patch for
  different parts of the codebase. Diffs can be applied independently
  and checked for conflicts. Full file replacements from different agents
  touching the same file would silently overwrite each other.
- **Reversible.** `git apply --reverse` undoes a patch cleanly. Restoring
  a full file from a backup requires knowing what the original looked like.

---

### 2.14 How does sandboxing protect the developer's working copy?

**Q:** What exactly does sandboxing mean here?

**A:** Every task gets its own complete copy of the repository filesystem.
The canonical git mirror on the shared `repos` Docker volume is treated as
read-only. Agents always write to their own directory under `SANDBOX_DIR`.

Consequences:
- A bad patch, a runaway subprocess, or a mid-task crash cannot corrupt
  the source repository.
- Multiple tasks on the same repository can run concurrently — they each
  have their own isolated copy.
- The developer's local checkout is never touched. The sandbox lives
  entirely inside Docker volumes.

---

### 2.15 What is the role of the Python Runner?

**Q:** Why is the Python Runner a separate service rather than part of the agent?

**A:** Separation of concerns. The generalist agent's job is to produce a
patch. Whether that patch actually works is a separate question, and answering
it requires:

- Applying the patch to a clean copy of the repository.
- Installing dependencies.
- Running `pytest`.
- Capturing and storing the output.

These steps are slow (minutes, not seconds), require a different execution
environment (a full Python environment with the project's dependencies), and
could in principle be parallelized across multiple runner workers.

Keeping the runner separate means:
- The agent is not blocked waiting for tests to finish.
- The runner can be replaced with a more capable runner (e.g. one that
  runs in a Docker container per test suite) without touching agent code.
- Runner failures do not prevent the agent from processing additional tasks.

---

### 2.16 Why Docker Compose for local orchestration?

**Q:** Why Docker Compose rather than Kubernetes or just running processes
directly?

**A:** Docker Compose hits the right point on the simplicity/power curve
for local development:

- **One command.** `docker compose up --build` gives a fully running stack
  with no prior environment setup beyond Docker.
- **Reproducibility.** Every developer gets the same versions of PostgreSQL,
  Python, and dependencies. No "works on my machine" problems.
- **Networking.** Services find each other by service name (`hub`, `llm-gateway`,
  etc.) without any manual port configuration.
- **Volume sharing.** The shared `repos`, `sandbox`, and `artifacts` volumes
  give multiple services access to the same filesystem without network
  file-transfer overhead.

Kubernetes is the right answer for production deployment but is far too much
operational overhead for a PoC that needs to run on a developer's laptop.

---

### 2.17 What are the known limitations we are intentionally deferring?

**Q:** What will not be fixed in the PoC?

**A:** The following are known limitations that are out of scope for the PoC
and will be addressed (partially or fully) in the MVP or later:

| Limitation | Deferred reason |
|------------|-----------------|
| No authentication or access control | Single-user local tool; not exposed to the network |
| No horizontal scaling | Single-node PoC; MVP will address parallelism |
| Stub output is synthetic | Good enough to validate pipeline; real LLM is one env var away |
| No cross-file refactoring | Generalist agent has no planning step; MVP orchestrator will |
| No patch conflict detection | Not needed with a single agent; MVP must handle this |
| No PR integration | Out of scope for PoC; MVP assembles branches |
| No real context selection | Generalist sends the full file tree; MVP uses targeted context |
| Single language support (Python) | PoC validates concept; runner can be extended for other languages |

---

## 3. PoC Goals and Scope

### Primary Goal

Validate that a minimal, locally-runnable, end-to-end autonomous coding
pipeline is feasible:

> *Submit a task in plain English → get a valid, tested patch back.*

### Scope

**In scope:**
- FastAPI Hub with PostgreSQL task queue and artifact store.
- LLM Gateway with stub mode and OpenAI-compatible proxy mode.
- Single generalist coding agent (polls, clones, calls LLM, returns patch).
- Python Runner (applies patch, runs pytest, reports pass/fail).
- CLI (`localcoder`) for all developer interactions.
- Full Docker Compose stack (one-command startup).
- CI pipeline (GitHub Actions) running tests and linter on every PR.
- Documentation (architecture, motivation, quick-install, usage guide).

**Out of scope:**
- Multi-agent orchestration and task decomposition.
- Specialized coding agent types.
- Patch conflict detection.
- PR/branch integration.
- Authentication, access control, rate limiting.
- Production deployment or horizontal scaling.

### Acceptance Criteria

See [Section 2.10](#210-what-are-the-poc-success-criteria).

---

## 4. MVP Goals and Scope

### Primary Goal

Extend the PoC into a genuine multi-agent software factory capable of
handling multi-file feature requests through decomposition and parallel
specialized agents:

> *Describe a feature → get a complete, reviewed, tested branch back.*

### Scope

**In scope:**
- Orchestrator Agent: receives high-level goals, decomposes into sub-tasks,
  dispatches to the Hub, assembles results.
- At least two specialized coding agent types (implementation, test-writing).
- Parallel task execution across multiple agent workers.
- Patch conflict detection and resolution hints.
- Branch assembly and PR creation (GitHub API integration).
- Per-agent result visibility in the CLI/UI.
- Context selection: orchestrator identifies the minimal relevant file set
  for each sub-task rather than sending the full tree.
- Horizontal scaling: adding agent worker containers increases throughput
  automatically.

**Deferred to post-MVP:**
- Authentication and access control.
- Support for languages other than Python in the runner.
- Real-time streaming of agent progress.
- Agent self-evaluation and retry logic.
- IDE integration.

### Acceptance Criteria

See [Section 2.11](#211-what-are-the-mvp-success-criteria).

---

## 5. Roadmap

```
Phase 0 — PoC (current)
├── Hub (FastAPI + PostgreSQL task queue + artifact store)
├── LLM Gateway (stub + OpenAI-compatible proxy)
├── Generalist Agent (single worker, full file tree context)
├── Python Runner (patch apply + pytest)
├── CLI (submit, list, status, patch, artifacts)
└── Docker Compose stack + CI

Phase 1 — MVP Foundation
├── Introduce orchestrator agent service
├── Task type taxonomy (implementation, test, docs, lint)
├── Orchestrator: LLM-driven task decomposition
├── Orchestrator: dispatch sub-tasks to Hub queue by type
└── Hub: task type field + routing

Phase 2 — Specialized Agents
├── Coding Agent: implementation type (slim, focused prompt)
├── Coding Agent: test-writing type (slim, focused prompt)
├── Refactor generalist agent as fallback only
└── Context selection: orchestrator identifies target files

Phase 3 — Assembly and Validation
├── Patch conflict detection in orchestrator
├── Branch assembly (apply patches in dependency order)
├── GitHub API integration: create PR from assembled branch
└── Per-agent result visibility in CLI

Phase 4 — Scale and Robustness
├── Horizontal agent pool (N workers per type)
├── Agent retry logic and self-evaluation
├── Cost and latency tracking in LLM gateway
└── Streaming progress updates
```

---

## 6. Architecture Deep-Dive

### 6.1 PoC: Single Generalist Agent (current state)

```
┌─────────────────────────────────────────────────────────┐
│  Hub  (FastAPI + PostgreSQL)                            │
│  Task queue · Repo mirror manager · Artifact store      │
└──────────────────┬──────────────────────────────────────┘
                   │  polls + claims tasks
         ┌─────────┴──────────┐
         ▼                    ▼
┌─────────────────┐   ┌───────────────────┐
│ Generalist      │   │ Python Runner     │
│ Agent           │   │                   │
│ ─────────────── │   │ ─────────────────  │
│ • polls hub     │   │ • polls hub       │
│ • clones repo   │   │ • applies patch   │
│ • sends full    │   │ • runs pytest     │
│   file tree to  │   │ • reports result  │
│   LLM           │   └───────────────────┘
│ • returns diff  │
└────────┬────────┘
         │ POST /v1/chat/completions
         ▼
┌────────────────────────┐
│ LLM Gateway            │
│ stub | OpenAI-compat   │
└────────────────────────┘
```

**Why this design was chosen for the PoC:**

The generalist agent is a single Python worker with one responsibility:
take a task off the queue, make a code change with LLM help, and return
a patch. It encodes all the intelligence needed to go from task description
to patch in one place, making it easy to understand, debug, and iterate on.

The design deliberately avoids premature abstraction. A pipeline with one
agent type has:
- One Dockerfile to maintain.
- One set of environment variables.
- One worker process to monitor.
- One code path to debug when something goes wrong.

This allowed the team to get to a working end-to-end demo quickly and to
focus energy on proving the pipeline fundamentals rather than the agent
coordination layer.

---

### 6.2 MVP: Orchestrator + Slim Coding Agents (target state)

```
┌──────────────────────────────────────────────────────────┐
│  Hub  (FastAPI + PostgreSQL)                             │
│  Task queue (with task_type field) · Artifact store      │
└───────────────────┬──────────────────────────────────────┘
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
┌─────────────────────┐   ┌─────────────────────────────┐
│ Orchestrator Agent  │   │ Python Runner               │
│ ─────────────────── │   │ (unchanged from PoC)        │
│ • receives goal     │   └─────────────────────────────┘
│ • analyses repo     │
│ • decomposes into   │
│   sub-tasks         │
│ • dispatches each   │◄──────────────────────────────┐
│   sub-task to Hub   │                               │
│ • monitors progress │  sub-task queues (by type)    │
│ • assembles branch  │                               │
└─────────────────────┘  ┌──────────────────────┐     │
                          │ Coding Agent         │     │
                          │ (implementation)     │─────┘
                          │ slim prompt, ~3 files│
                          └──────────────────────┘
                          ┌──────────────────────┐
                          │ Coding Agent         │
                          │ (test-writing)       │
                          │ slim prompt, ~2 files│
                          └──────────────────────┘
                          ┌──────────────────────┐
                          │ Coding Agent         │
                          │ (documentation)      │
                          │ slim prompt, 1 file  │
                          └──────────────────────┘
                                    │
                          POST /v1/chat/completions
                                    │
                          ┌─────────▼───────────┐
                          │  LLM Gateway        │
                          │  (unchanged)        │
                          └─────────────────────┘
```

---

### 6.3 Why the design must evolve

The single generalist agent is a deliberate starting point, not a final
answer. The table below captures the specific reasons why the PoC design
cannot be the long-term architecture:

| Concern | PoC behavior | Why it breaks at scale | MVP solution |
|---------|--------------|------------------------|--------------|
| **Context size** | Full file tree in every prompt | Token limit hit on real codebases | Orchestrator selects minimal file set per sub-task |
| **Prompt reliability** | One prompt does plan + code | Complex prompts degrade reliability non-linearly | Slim agents have single-step focused prompts |
| **Throughput** | Sequential, one task at a time | Blocks on LLM latency per task | Parallel pool of slim agents |
| **Specialization** | Generalist handles everything | Test-writing requires different context and style than implementation | Separate agent types with tuned prompts |
| **Cost** | Large prompt for every task | Complex tasks are expensive regardless of actual complexity | Small prompts for small tasks |
| **Error diagnosis** | Failure could be in planning or coding | Hard to know which step failed | Orchestrator failures vs. coding agent failures are distinct |
| **Patch conflicts** | Single agent, no conflicts possible | Multiple agents touching same files will conflict | Orchestrator manages patch dependency ordering |

---

## 7. Key Decisions Log

| # | Decision | Rationale | Phase |
|---|----------|-----------|-------|
| D-01 | Single generalist agent for PoC | Minimize surface area; validate pipeline before investing in agent specialization | PoC |
| D-02 | LLM access via OpenAI-compatible gateway | Provider agnosticism; stub mode for offline testing; centralized observability | PoC |
| D-03 | Unified-diff patches as agent output format | Smaller, auditable, composable, reversible; essential for multi-agent assembly in MVP | PoC |
| D-04 | Per-task isolated sandbox copy of repository | Prevents concurrent task interference; protects developer's working copy | PoC |
| D-05 | Atomic task claiming via PostgreSQL row-lock | Allows multiple agent workers without race conditions | PoC |
| D-06 | Stub mode default (no API key required) | Zero-friction onboarding; full pipeline testable in CI without secrets | PoC |
| D-07 | Docker Compose for local orchestration | One-command startup; reproducible across machines; right abstraction for local PoC | PoC |
| D-08 | Python Runner as separate service | Separation of concerns; runner can be slow without blocking agent throughput | PoC |
| D-09 | Orchestrator handles decomposition and context selection | Intelligence concentrated in one place; coding agents kept slim and cheap | MVP |
| D-10 | Slim coding agents are intentionally narrow ("dumb") | Focused prompts are more reliable, cheaper, and easier to tune than generalist prompts | MVP |
| D-11 | Patch conflict detection in orchestrator | Multi-agent patches must be assembled in dependency order; conflicts surfaced early | MVP |
| D-12 | Branch assembly + PR creation in orchestrator | Full automation of the developer-review cycle without replacing human review | MVP |

---

## 8. Glossary

| Term | Definition |
|------|------------|
| **Artifact** | A file produced by an agent or runner and stored by the Hub — typically a patch file or test log. |
| **Claim** | The atomic operation by which an agent takes exclusive ownership of a task, preventing other agents from processing the same task. |
| **Coding Agent** | In the MVP, a slim, specialized worker that receives a focused instruction and a small set of files, and returns a unified-diff patch. |
| **Generalist Agent** | The PoC's single worker type, which handles any coding task from end to end. |
| **Hub** | The FastAPI + PostgreSQL service that manages the task queue, repository mirrors, and artifact store. |
| **LLM Gateway** | The OpenAI-compatible proxy that decouples agents from the actual LLM provider. Supports stub mode. |
| **Orchestrator Agent** | The MVP's planning agent, which receives high-level goals, decomposes them, dispatches sub-tasks, and assembles results. |
| **Patch** | A unified diff (git diff format) representing a code change. Agents produce patches; the Python Runner applies them. |
| **PoC** | Proof-of-Concept — the current implementation in `poc/`. |
| **Sandbox** | An isolated filesystem copy of the repository used by a single task. Never shared between tasks. |
| **Stub mode** | LLM Gateway mode where a deterministic synthetic response is returned without any real LLM call. Used for offline development and CI. |
| **Sub-task** | In the MVP, a fine-grained task produced by the Orchestrator as part of decomposing a larger goal. |
| **Task** | A unit of work tracked by the Hub: a description, a repository URL, a status, and associated artifacts. |
| **Unified diff** | The standard patch format produced by `git diff` or `diff -u`. Lines starting with `+` are additions, `-` are removals. |
