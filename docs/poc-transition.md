# PoC Transition: blecx/AI-Agent-Framework → blecx/localCoder

All PoC-related work has been moved from **blecx/AI-Agent-Framework** to this
repository (**blecx/localCoder**). All further development continues here.

---

## What was moved

### Code scaffolding

The complete multi-agent coding framework PoC is now under `poc/` in this
repository. It covers:

| Component | Description |
|-----------|-------------|
| `poc/hub` | Orchestration hub — manages tasks, sessions, and artifact storage |
| `poc/llm-gateway` | LLM gateway — OpenAI-compatible proxy with stub/real provider modes |
| `poc/agent-generalist` | Generalist agent — polls hub, edits files in sandbox, returns diffs |
| `poc/python-runner` | Sandboxed `pytest` executor |
| `poc/cli` | CLI utility (`localcoder submit/list/status/…`) |
| `poc/docker-compose.yml` | Full stack wiring |
| `poc/.env.example` | Environment variable reference |
| `poc/README.md` | Architecture, quick-start, and configuration guide |

See **PR #1** and **PR #2** in this repository for the full PoC scaffolding
details.

### Infrastructure

| File | Description |
|------|-------------|
| `.editorconfig` | Consistent editor formatting rules |
| `.github/workflows/ci-poc.yml` | CI workflow — lints `poc/` on every push/PR touching it and validates the Compose file |

---

## AI-Agent-Framework PRs to close

The following draft PRs in **blecx/AI-Agent-Framework** have been superseded by
the work in this repository and should be **closed without merging**:

| PR | Title | Superseded by |
|----|-------|---------------|
| [#734](https://github.com/blecx/AI-Agent-Framework/pull/734) | fix(poc/hub): upgrade python-multipart + full PoC scaffold | localCoder PR #1, PR #2 |
| [#735](https://github.com/blecx/AI-Agent-Framework/pull/735) | feat(poc): LLM gateway PoC with GitHub Models/Copilot support | localCoder PR #1, PR #2 |
| [#736](https://github.com/blecx/AI-Agent-Framework/pull/736) | feat(poc): GitHub Copilot upstream support in PoC LLM gateway | localCoder PR #1 |
| [#737](https://github.com/blecx/AI-Agent-Framework/pull/737) | feat(poc): Provider-abstracted LLM gateway with OpenAI-compat and Copilot adapters | localCoder PR #1, PR #2 |
| [#738](https://github.com/blecx/AI-Agent-Framework/pull/738) | docs: PoC PR status investigation — open PRs summary | localCoder docs/poc-transition.md |

**Note:** None of these PRs were ever merged into `main` of AI-Agent-Framework,
so there is no code to remove from that repository's default branch.

---

## LLM gateway implementation note

PRs #735–#737 in AI-Agent-Framework each represented a competing LLM gateway
design. The canonical implementation chosen for localCoder is the one in
**PR #2** (`poc/llm-gateway/app/main.py`):

- **Stub mode by default** — works with no credentials; returns synthetic
  completions so the whole stack can be exercised locally.
- **OpenAI-compatible mode** — set `OPENAI_API_KEY` (and optionally
  `OPENAI_BASE_URL`) to route to real OpenAI or any compatible upstream
  (Azure, GitHub Models, Ollama, etc.).
- Prints a prominent box-art `WARNING` at startup when running in stub mode
  and exposes a `/health` endpoint with a `stub_warning` field.

---

## Future work

All further PoC development happens in **blecx/localCoder**. The
`blecx/AI-Agent-Framework` repository retains its non-PoC content and is no
longer the home for this work.
