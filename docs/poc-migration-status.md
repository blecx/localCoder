# PoC Work — Migration Status

> Generated: 2026-03-05
> Scope: complete migration record from `blecx/AI-Agent-Framework` → `blecx/localCoder`

---

## Summary

All PoC work originally created in `blecx/AI-Agent-Framework` has been fully
migrated to this repository (`blecx/localCoder`). No PoC code exists on the
`main` branch of AI-Agent-Framework (all work was in draft PRs that were never
merged).

---

## AI-Agent-Framework source PRs

Five draft PRs existed in `blecx/AI-Agent-Framework`. None were ever merged
into `main`. All are superseded by the work in this repository.

| PR | Title | Branch | +Lines | Superseded by |
|----|-------|--------|--------|---------------|
| [#734](https://github.com/blecx/AI-Agent-Framework/pull/734) | fix(poc/hub): upgrade python-multipart + full PoC scaffold | `copilot/implement-poc-framework` | +2,665 | localCoder PR #1, PR #2 |
| [#735](https://github.com/blecx/AI-Agent-Framework/pull/735) | feat(poc): LLM gateway PoC with GitHub Models/Copilot support | `copilot/update-llm-gateway-copilot-support` | +1,343 | localCoder PR #1, PR #2 |
| [#736](https://github.com/blecx/AI-Agent-Framework/pull/736) | feat(poc): GitHub Copilot upstream support in PoC LLM gateway | `copilot/add-copilot-upstream-support` | +1,161 | localCoder PR #1 |
| [#737](https://github.com/blecx/AI-Agent-Framework/pull/737) | feat(poc): Provider-abstracted LLM gateway with OpenAI-compat and Copilot adapters | `copilot/update-llm-gateway-copilot` | +1,111 | localCoder PR #4 (this PR) |
| [#738](https://github.com/blecx/AI-Agent-Framework/pull/738) | docs: PoC PR status investigation — open PRs summary | `copilot/investigate-open-prs-status` | +157 | `docs/poc-status.md` (this PR) |

**Action required:** Close all five PRs in `blecx/AI-Agent-Framework` without
merging (no code exists on their `main`, so no removal is needed beyond
closing).

---

## localCoder PRs

| PR | Title | What it covers |
|----|-------|----------------|
| [#1](https://github.com/blecx/localCoder/pull/1) | Scaffold localCoder PoC under poc/ | Full PoC stack: hub (SQLite), llm-gateway with Copilot OAuth adapter, generalist-agent, python-runner, cli, docs, 26 tests |
| [#2](https://github.com/blecx/localCoder/pull/2) | Scaffold multi-agent coding framework PoC under poc/ | Alternative full PoC: hub (Postgres + SQL migrations), llm-gateway (stub/OpenAI), agent-generalist, python-runner, cli |
| [#3](https://github.com/blecx/localCoder/pull/3) | Transition PoC work from blecx/AI-Agent-Framework to blecx/localCoder | `.editorconfig`, CI workflow, `docs/poc-transition.md` |
| [#4](https://github.com/blecx/localCoder/pull/4) | Migrate PoC issues and PRs to localCoder (this PR) | Provider-abstracted `poc/llm_gateway/` library + 32 unit tests (from AI-Agent-Framework PR #737); `docs/poc-status.md`; migration tracking |

---

## Code components ported to localCoder

### Provider-abstracted LLM gateway library (`poc/llm_gateway/`)

Ported from AI-Agent-Framework PR #737
(`copilot/update-llm-gateway-copilot`). This is a pure-Python library
(not a Docker service) that provides a clean provider abstraction on top
of the FastAPI gateway service already present in `poc/llm-gateway/`.

```
poc/llm_gateway/
├── __init__.py          # Public exports: LLMGateway, GatewayConfig
├── config.py            # Config resolution (dict → file → env → defaults)
├── gateway.py           # LLMGateway: selects and delegates to provider
└── providers/
    ├── __init__.py
    ├── base.py          # LLMProvider ABC, ProviderError, ConfigurationError
    ├── copilot.py       # Copilot adapter (error/stub — no real endpoint)
    └── openai_compat.py # Any OpenAI-compatible endpoint (recommended)
```

### Unit tests (`tests/unit/test_poc_llm_gateway.py`)

32 tests covering:
- `GatewayConfig` defaults, overrides, and file loading
- Provider selection and routing
- `OpenAICompatProvider` config validation and HTTP mocking
- `CopilotProvider` error messaging and stub fallback
- `LLMGateway` health endpoint

---

## PoC issues tracking

No GitHub issues were created in `blecx/AI-Agent-Framework` for the PoC work
(all PRs were opened directly from Copilot chat sessions). The following work
items from the AI-Agent-Framework PRs are now tracked here:

| Work item | Status | localCoder PR |
|-----------|--------|---------------|
| Full PoC Docker Compose stack | ✅ Done | PR #1, PR #2 |
| Hub service (task queue, artifact management) | ✅ Done | PR #1, PR #2 |
| LLM Gateway (stub / OpenAI-compatible) | ✅ Done | PR #1, PR #2 |
| Provider-abstracted LLM gateway library | ✅ Done | PR #4 |
| Generalist agent (polling, sandbox, diffs) | ✅ Done | PR #1, PR #2 |
| Python runner (pytest sandboxed execution) | ✅ Done | PR #1, PR #2 |
| CLI utility | ✅ Done | PR #1, PR #2 |
| CI workflow (`ci-poc.yml`) | ✅ Done | PR #3 |
| Editor config (`.editorconfig`) | ✅ Done | PR #3 |
| Transition documentation | ✅ Done | PR #3 |
| Migration tracking documentation | ✅ Done | PR #4 |

---

## Future work

All further PoC development continues in **blecx/localCoder**. The
`blecx/AI-Agent-Framework` repository retains its non-PoC content only.
