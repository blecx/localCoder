# PoC Work — Pull Request Status

> Ported from `blecx/AI-Agent-Framework` (original: 2026-03-05).
> Updated for `blecx/localCoder`.

---

## Summary

All PoC scaffolding was originally pushed as draft PRs in
`blecx/AI-Agent-Framework` (none were ever merged into its `main`).
Those PRs have been superseded by the work in this repository.

---

## Original AI-Agent-Framework draft PRs

The table below captures the point-in-time state of the five PRs that
existed in `blecx/AI-Agent-Framework` before migration.

| PR | Title | Branch | Files | +Lines | Status |
|----|-------|--------|-------|--------|--------|
| [#734](https://github.com/blecx/AI-Agent-Framework/pull/734) | fix(poc/hub): upgrade python-multipart 0.0.9 → 0.0.22 | `copilot/implement-poc-framework` | 30 | +2,665 | Draft (closed) |
| [#735](https://github.com/blecx/AI-Agent-Framework/pull/735) | feat(poc): LLM gateway PoC with GitHub Models/Copilot support | `copilot/update-llm-gateway-copilot-support` | 12 | +1,343 | Draft (closed) |
| [#736](https://github.com/blecx/AI-Agent-Framework/pull/736) | feat(poc): GitHub Copilot upstream support in PoC LLM gateway | `copilot/add-copilot-upstream-support` | 11 | +1,161 | Draft (closed) |
| [#737](https://github.com/blecx/AI-Agent-Framework/pull/737) | feat(poc): Provider-abstracted LLM gateway with OpenAI-compat and Copilot adapters | `copilot/update-llm-gateway-copilot` | 10 | +1,111 | Draft (closed) |
| [#738](https://github.com/blecx/AI-Agent-Framework/pull/738) | docs: PoC PR status investigation — open PRs summary | `copilot/investigate-open-prs-status` | 1 | +157 | Draft (closed) |

**All five PRs were drafts and were never merged into `main` of
AI-Agent-Framework.** That repository's `main` branch has no `poc/` directory.

---

## PR content details

### PR #734 — Full PoC Scaffold (S1)

**Scope:** The most comprehensive PR — implements the full S1 PoC stack.

```
poc/
├── .env.example
├── README.md                          (336 lines)
├── docker-compose.yml                 (98 lines — full multi-service stack)
├── hub/
│   ├── Dockerfile
│   ├── alembic.ini + alembic/         (Postgres migrations)
│   ├── database.py, main.py, models.py, schemas.py
│   └── routers/
│       ├── artifacts.py, config.py, repos.py, runs.py, tasks.py
├── agent-generalist/
│   ├── Dockerfile
│   └── agent.py                       (318 lines — polling agent)
├── cli/
│   ├── agentctl.py                    (297 lines — Typer CLI)
│   └── pyproject.toml, requirements.txt
└── llm-gateway/
    └── Dockerfile
```

**Superseded by:** localCoder PR #1, PR #2.

---

### PR #735 — LLM Gateway v1 (GitHub Models + Copilot stub)

**Scope:** Standalone LLM gateway under `poc/gateway/` with:
- `LLMProvider` ABC → `GitHubModelsProvider` + `CopilotProvider` (stub) + `StubProvider`
- Model policy routing (logical roles: `planning`, `coding`, `review` → model IDs)
- `GET /health`, `POST /v1/chat/completions` FastAPI endpoints
- 34 unit tests

**Superseded by:** localCoder PR #1, PR #2 (and PR #4 for the library layer).

---

### PR #736 — LLM Gateway v2 (Copilot provider with fallback)

**Scope:** Refactored gateway with:
```
poc/
├── main.py, routing.py, requirements.txt, README.md
└── providers/
    ├── base.py     (LLMProvider ABC)
    ├── copilot.py  (httpx; resolves key from env or Docker secret)
    ├── factory.py  (selection + fallback logic)
    └── stub.py
```
39 unit tests.

**Superseded by:** localCoder PR #1 (Copilot OAuth adapter), PR #4 (`poc/llm_gateway/`).

---

### PR #737 — LLM Gateway v3 (Provider abstraction, openai_compat primary)

**Scope:** Most opinionated version — acknowledges that Copilot has no public
standalone API-key endpoint and promotes `openai_compat` as the primary
production upstream.

```
poc/llm_gateway/
├── __init__.py
├── config.py         (GatewayConfig resolution)
├── gateway.py        (LLMGateway router)
└── providers/
    ├── base.py       (LLMProvider, ProviderError, ConfigurationError)
    ├── openai_compat.py   (any OpenAI-compatible endpoint)
    └── copilot.py    (ConfigurationError with instructions; fallback_to_stub)
```
32 unit tests.

**Superseded by:** localCoder PR #4 (ported verbatim as `poc/llm_gateway/`).

---

### PR #738 — PoC Status Investigation

**Scope:** `docs/poc-status.md` — point-in-time summary of the four draft PRs,
scaffolding confirmation, and recommended next steps.

**Superseded by:** `docs/poc-status.md` in localCoder (this file).

---

## Scaffolding confirmation

All components from the original PoC requirements are present in localCoder:

| Component | PR | Present in localCoder? |
|-----------|----|------------------------|
| PoC Docker Compose stack | #734 | ✅ PR #1, PR #2 |
| Hub service (FastAPI + Postgres + Alembic) | #734 | ✅ PR #2 |
| Hub service (FastAPI + SQLite) | — | ✅ PR #1 |
| Generalist agent (polling) | #734 | ✅ PR #1, PR #2 |
| CLI (`agentctl` / `localcoder`) | #734 | ✅ PR #1, PR #2 |
| LLM gateway (stub mode) | #734 | ✅ PR #2 |
| LLM gateway (GitHub Models provider) | #735 | ✅ PR #1 (Copilot OAuth) |
| LLM gateway (Copilot provider w/ fallback) | #736 | ✅ PR #1, PR #4 |
| LLM gateway (openai_compat + Copilot adapter) | #737 | ✅ PR #4 |
| PoC CI workflow | #734 | ✅ PR #3 |
| python-runner service | #734 | ✅ PR #1, PR #2 |

---

## Canonical LLM gateway choice

PRs #735, #736, and #737 in AI-Agent-Framework each represented a competing
gateway design. The implementations chosen for localCoder are:

1. **`poc/llm-gateway/`** (Docker service, PR #2) — FastAPI service with
   stub/OpenAI modes, box-art `WARNING` at startup, `/health` endpoint.
2. **`poc/llm_gateway/`** (Python library, PR #4) — Provider-abstracted library
   from PR #737: `openai_compat` as primary, `copilot` as error-surfacing
   adapter, full unit-test coverage.
