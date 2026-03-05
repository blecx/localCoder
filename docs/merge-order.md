# PoC PR Merge Order — localCoder

All outstanding PoC pull requests from `blecx/localCoder` have been merged
into `main` via the consolidation branch
`copilot/merge-outstanding-poc-prs` (PR #5).

---

## Merge sequence

| Step | PR | Branch | Title | Rationale |
|------|----|--------|-------|-----------|
| 1 | [#1](https://github.com/blecx/localCoder/pull/1) | `copilot/fix-repository-target-for-poc` | Scaffold localCoder PoC under `poc/` | Foundation layer: SQLite session store, single-process hub, LLM gateway with Copilot adapter, generalist-agent, python-runner, CLI, docs, 26 pytest tests. Everything else builds on this scaffold. |
| 2 | [#2](https://github.com/blecx/localCoder/pull/2) | `copilot/scaffold-multi-agent-coding-framework` | Scaffold multi-agent coding framework PoC under `poc/` | Extends the foundation with a production-grade FastAPI + PostgreSQL hub, Docker Compose stack, LLM gateway stub/OpenAI mode, agent-generalist service, python-runner service. Depends on the directory layout established by PR #1. |
| 3 | [#3](https://github.com/blecx/localCoder/pull/3) | `copilot/transition-poc-work-to-localcoder` | Transition PoC work from AI-Agent-Framework to localCoder | Infrastructure layer on top of the code introduced by PRs #1 and #2: `.editorconfig`, CI workflow (lint + compose-validate), and `docs/poc-transition.md` referencing PRs #1 and #2. |
| 4 | [#4](https://github.com/blecx/localCoder/pull/4) | `copilot/migrate-poc-issues-prs` | Complete PoC migration from AI-Agent-Framework | Provider-abstracted `poc/llm_gateway/` library (config, gateway, providers), 32 unit tests, and migration tracking docs. Depends on the PoC layout and the `poc/llm_gateway/` package stub introduced by PR #1. |

---

## Conflict resolution notes

Two PRs introduced overlapping files; conflicts were resolved as follows:

| File | Resolution |
|------|------------|
| `poc/.env.example` | Merged both variable sets: PR #1's Copilot/generic-provider and SQLite DB vars were added to PR #2's stub/OpenAI and PostgreSQL vars. |
| `poc/.gitignore` | Union of both ignore patterns (`.db`, `*.py[cod]`, `.venv/`, etc.). |
| `poc/docker-compose.yml` | PR #2's PostgreSQL-based, multi-service compose is the canonical stack; PR #1's SQLite-only compose was superseded. |
| `poc/hub/Dockerfile` | PR #2's version (adds `git`, `uvicorn` entrypoint) supersedes PR #1's minimal stub. |
| `poc/python-runner/Dockerfile` | PR #2's version (adds `git`, `python -m app.main` entrypoint) supersedes PR #1's minimal stub. |
| `poc/llm_gateway/__init__.py` | PR #4's version (proper `LLMGateway`/`GatewayConfig` exports for the new library) supersedes PR #1's dynamic-import shim, since PR #4 delivers the complete `poc/llm_gateway/` package. |

---

## AI-Agent-Framework migration leftovers

All PoC work originated in `blecx/AI-Agent-Framework` before being migrated
here. The following draft PRs in that repository were **never merged to its
`main` branch** and have been fully superseded by the localCoder PRs above:

| AI-Agent-Framework PR | Title | Superseded by |
|-----------------------|-------|---------------|
| [#734](https://github.com/blecx/AI-Agent-Framework/pull/734) | fix(poc/hub): upgrade python-multipart + full PoC scaffold | localCoder PR #1, #2 |
| [#735](https://github.com/blecx/AI-Agent-Framework/pull/735) | feat(poc): LLM gateway PoC with GitHub Models/Copilot support | localCoder PR #1, #2 |
| [#736](https://github.com/blecx/AI-Agent-Framework/pull/736) | feat(poc): GitHub Copilot upstream support in PoC LLM gateway | localCoder PR #1 |
| [#737](https://github.com/blecx/AI-Agent-Framework/pull/737) | feat(poc): Provider-abstracted LLM gateway with OpenAI-compat and Copilot adapters | localCoder PR #4 |
| [#738](https://github.com/blecx/AI-Agent-Framework/pull/738) | docs: PoC PR status investigation | localCoder `docs/poc-transition.md`, `docs/poc-status.md` |

Because none of these PRs landed on `main` in AI-Agent-Framework, no code
needs to be removed from that repository's default branch.  The PRs themselves
should be **closed without merging** to complete the cleanup.

> **Action required:** close AI-Agent-Framework PRs #734–#738 (they are still
> open as of the time of this merge).

---

## Post-merge state

After this consolidation branch is merged into `main`, the repository contains:

```
poc/
├── __init__.py
├── .env.example            # unified env-var reference
├── .gitignore
├── README.md               # quick-start guide (from PR #2)
├── docker-compose.yml      # full PostgreSQL stack (from PR #2)
├── pytest.ini
├── requirements.txt
│
├── agent-generalist/       # PR #2 — service: polls hub, edits in sandbox
├── cli/                    # PR #1 + PR #2 — REPL + localcoder CLI
├── db/                     # PR #1 — SQLite session/message store
├── docs/                   # PR #1 — architecture, usage, copilot adapter notes
├── generalist-agent/       # PR #1 — single-process reasoning loop
├── hub/                    # PR #1 + PR #2 — orchestration hub (SQLite + FastAPI+PG)
├── llm-gateway/            # PR #1 + PR #2 — Docker service (stub / OpenAI)
├── llm_gateway/            # PR #4 — Python library (provider-abstracted)
├── python-runner/          # PR #1 + PR #2 — sandboxed executor
├── python_runner/          # PR #1 — standalone runner module
└── tests/                  # PR #1 — 26 pytest tests

tests/                      # PR #4 — 32 unit tests for poc/llm_gateway
docs/
├── poc-migration-status.md # PR #4
├── poc-status.md           # PR #4
├── poc-transition.md       # PR #3
└── merge-order.md          # this file
.editorconfig               # PR #3
.github/workflows/ci-poc.yml  # PR #3
.gitignore                  # PR #4
pytest.ini                  # PR #4
```
