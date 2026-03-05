# localCoder PoC — Project Motivation

> **Status:** Experimental proof-of-concept. Not intended for production use.

---

## Why localCoder Exists

Modern software development increasingly involves repetitive, well-scoped
coding tasks: adding a function, writing a test, fixing a linting issue,
updating a dependency. These tasks are conceptually straightforward yet still
require a developer to switch context, locate the right file, make the change,
run the tests, and verify the result.

Large Language Models (LLMs) have demonstrated genuine ability to perform
exactly these kinds of tasks — but using them effectively in a local workflow
requires glue code: something to call the model, manage the codebase safely,
apply the output, and validate it. Most available tools are either cloud-hosted
(raising privacy and latency concerns), tightly coupled to a single LLM
provider, or require significant configuration before they produce useful output.

**localCoder is an attempt to answer the question:**

> *What does a minimal, self-contained, locally-runnable autonomous coding
> assistant look like?*

---

## Problems It Aims to Solve

### 1. Friction in AI-assisted local development

Existing AI coding tools typically require:
- Cloud connectivity (your code leaves your machine).
- Accounts and API keys before you can try anything.
- IDE plugins or proprietary tooling.

localCoder runs entirely on your local machine with Docker. No code leaves
the machine unless you explicitly connect an external LLM. The stub mode
means you can evaluate the full workflow with zero credentials.

### 2. Provider lock-in

If a tool is hardcoded to OpenAI, switching to an open-source model (Ollama,
LM Studio) or a different provider (Azure, Anthropic) requires rewriting
integration code.

localCoder's LLM gateway presents a single OpenAI-compatible interface to
all internal agents. Switching providers is a one-line environment variable
change (`OPENAI_BASE_URL`). No agent code needs to change.

### 3. Unsafe code execution

Applying LLM-generated code directly to a working checkout is risky — a bad
patch can break builds, corrupt history, or overwrite local changes.

localCoder uses **isolated sandboxes**: every task gets its own fresh copy of
the repository. The original source is never modified. Developers review the
generated patch before deciding to apply it.

### 4. No audit trail

Without structure, AI-generated changes are opaque: where did this code come
from, what prompt produced it, did the tests pass?

localCoder creates a **persistent task record** for every piece of work,
including the original description, the generated patch, and the test run
output. Everything is stored as retrievable artifacts.

### 5. Hard to evaluate AI coding quality without running the code

Reading a patch is not the same as knowing whether it works. localCoder
**runs the test suite** in a sandboxed environment and surfaces pass/fail
results alongside the generated code — giving an immediate quality signal.

---

## Utility and Impact on Local Development Workflows

| Workflow               | Without localCoder                          | With localCoder                              |
|------------------------|---------------------------------------------|----------------------------------------------|
| Routine code change    | Context-switch, write code, test manually   | Submit description, review patch, apply      |
| Evaluating LLM quality | Run ad-hoc prompts, manually inspect output | Submit tasks, compare patches, check test results |
| Multi-provider comparison | Re-implement integrations for each model | Change `OPENAI_BASE_URL`, resubmit           |
| Onboarding new contributors | Explain codebase, wait for first PR    | Submit small starter tasks, share patches    |
| Staying focused        | Break flow to handle small issues           | Queue tasks and process results asynchronously|

---

## What It Does NOT Claim to Do

localCoder is a **proof-of-concept**, not a production system:

- It does not handle large, cross-file refactors reliably.
- It does not replace human code review.
- It does not guarantee correctness — LLM-generated code must always be
  reviewed before merging.
- It has no authentication or multi-user access control.
- It is not optimised for performance or large repositories.

The goal is to demonstrate the **concept**: a composable, locally-runnable
pipeline that connects an LLM to a real code repository with proper sandboxing
and test validation. Everything else is left for future iterations.

---

## How It Fits Into a Broader Vision

The longer-term vision is a developer assistant that:

1. Understands the structure and conventions of a codebase.
2. Can be assigned tasks of increasing complexity — from one-liners to
   multi-file feature additions.
3. Runs locally, keeping code private by default.
4. Integrates with existing tools (git, CI, IDEs) without replacing them.

localCoder's PoC establishes the foundational building blocks:

- **Task queue** — a durable store of work to be done.
- **Sandbox isolation** — safe, reversible code changes.
- **Provider-agnostic LLM access** — flexibility without lock-in.
- **Automated validation** — immediate feedback from tests.

Each of these building blocks is individually replaceable and improvable as the
project matures.
