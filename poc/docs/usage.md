# localCoder PoC — Usage Guide

> **Status:** Experimental proof-of-concept. Not intended for production use.

This guide covers how to use the localCoder PoC system, from basic dummy-mode
testing to multi-provider LLM workflows and practical end-to-end examples.

---

## Table of Contents

1. [Using localCoder Without an LLM (Stub / Dummy Mode)](#1-using-localcoder-without-an-llm-stub--dummy-mode)
2. [Adding API Keys and Selecting LLM Models](#2-adding-api-keys-and-selecting-llm-models)
3. [Worked Examples](#3-worked-examples)
   - [Example 1 — Novice: Simple Demo](#example-1--novice-simple-demo)
   - [Example 2 — Intermediate: TODO Management](#example-2--intermediate-todo-management)
   - [Example 3 — Advanced: Prototype Note-Taking App UI](#example-3--advanced-prototype-note-taking-app-ui)

---

## 1. Using localCoder Without an LLM (Stub / Dummy Mode)

### What is stub mode?

By default, when `OPENAI_API_KEY` is not set (or is empty), the LLM gateway
starts in **stub mode**. Instead of calling an external API, the gateway
returns a deterministic synthetic response containing a minimal placeholder
diff. This lets you exercise the complete pipeline — submit task → agent claims
→ patch generated → runner applies → tests run — without any network access or
credentials.

### Starting the stack in stub mode

```bash
cd poc
cp .env.example .env      # OPENAI_API_KEY is blank by default
docker compose up --build
```

You will see this in the `llm-gateway` logs at startup:

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

### Verifying stub mode

Check the gateway health endpoint:

```bash
curl -s http://localhost:8001/health | python3 -m json.tool
```

Expected response:

```json
{
    "status": "ok",
    "mode": "stub",
    "model": "stub",
    "stub_warning": true
}
```

Or via the CLI:

```bash
localcoder gateway-health
```

Expected output:

```
LLM Gateway  http://localhost:8001
  status : ok
  mode   : stub
  model  : stub
  ⚠ stub_warning: true — running without a real LLM
```

### Submitting a test task in stub mode

```bash
localcoder submit \
  --repo https://github.com/blecx/localCoder \
  --branch main \
  --desc "Add a hello_world() function to utils.py"
```

Expected output:

```
Task created: id=1  status=pending
```

### Monitoring task progress

```bash
# Watch all tasks
localcoder list

# Poll until done (run a few times)
localcoder status 1
```

Typical status progression:

```
id=1  status=pending   ...
id=1  status=claimed   ...
id=1  status=running   ...
id=1  status=done      ...
```

### Viewing the generated patch (stub output)

```bash
localcoder patch 1
```

In stub mode this produces a synthetic placeholder diff. It demonstrates the
pipeline works end-to-end even without a real model.

### Viewing artifacts

```bash
localcoder artifacts 1
# Lists: patch.diff, test-output.txt

localcoder download 1 test-output.txt --out /tmp/test-output.txt
cat /tmp/test-output.txt
```

---

## 2. Adding API Keys and Selecting LLM Models

### OpenAI

Edit `poc/.env`:

```dotenv
OPENAI_API_KEY=sk-proj-...yourkey...
LLM_MODEL=gpt-4o-mini
```

Restart the gateway:

```bash
docker compose restart llm-gateway
```

Verify:

```bash
curl -s http://localhost:8001/health | python3 -m json.tool
```

Expected:

```json
{
    "status": "ok",
    "mode": "openai",
    "model": "gpt-4o-mini",
    "stub_warning": false
}
```

#### Available OpenAI models

| Model            | Notes                                          |
|------------------|------------------------------------------------|
| `gpt-4o-mini`    | Default. Fast and cost-effective.              |
| `gpt-4o`         | Higher quality; slower and more expensive.     |
| `gpt-4-turbo`    | Older GPT-4 variant with 128k context.         |
| `gpt-3.5-turbo`  | Fastest/cheapest; lower code quality.          |

Change model at any time by updating `LLM_MODEL` in `.env` and restarting the
gateway.

### Anthropic Claude (via LiteLLM proxy)

LiteLLM ([https://litellm.ai](https://litellm.ai)) provides an
OpenAI-compatible proxy for many providers including Anthropic.

1. Start a LiteLLM proxy:
   ```bash
   pip install litellm
   litellm --model claude-3-5-sonnet-20241022 --port 4000
   ```

2. Update `poc/.env`:
   ```dotenv
   OPENAI_API_KEY=<your-anthropic-key>
   OPENAI_BASE_URL=http://host.docker.internal:4000
   LLM_MODEL=claude-3-5-sonnet-20241022
   ```

3. Restart the gateway:
   ```bash
   docker compose restart llm-gateway
   ```

### Ollama (local open-source models)

Ollama ([https://ollama.com](https://ollama.com)) runs open-source models
locally with no cloud dependency.

1. Install Ollama and pull a coding model:
   ```bash
   ollama pull codellama
   # or: ollama pull deepseek-coder
   # or: ollama pull mistral
   ```

2. Update `poc/.env`:
   ```dotenv
   OPENAI_API_KEY=ollama
   OPENAI_BASE_URL=http://host.docker.internal:11434
   LLM_MODEL=codellama
   ```

   > **Linux note:** Replace `host.docker.internal` with your Docker bridge
   > IP (usually `172.17.0.1`) or use `--network=host` in the gateway
   > service.

3. Restart:
   ```bash
   docker compose restart llm-gateway
   ```

### Multi-provider workflow

You can switch between providers by updating `.env` and restarting the gateway.
The hub, agents, and CLI are unaffected — they always talk to the gateway on
`http://localhost:8001`.

Example: run your first pass with OpenAI, compare with an Ollama model:

```bash
# OpenAI pass
OPENAI_API_KEY=sk-... LLM_MODEL=gpt-4o-mini docker compose restart llm-gateway
localcoder submit --repo <url> --desc "Write unit tests for utils.py"
localcoder patch <id>  # review OpenAI output

# Switch to Ollama
OPENAI_API_KEY=ollama OPENAI_BASE_URL=http://host.docker.internal:11434 \
  LLM_MODEL=codellama docker compose restart llm-gateway
localcoder submit --repo <url> --desc "Write unit tests for utils.py"
localcoder patch <id>  # compare Ollama output
```

> **Tip:** Export vars in your shell instead of editing `.env` each time:
> ```bash
> export OPENAI_API_KEY=sk-...
> export LLM_MODEL=gpt-4o
> docker compose restart llm-gateway
> ```

---

## 3. Worked Examples

---

### Example 1 — Novice: Simple Demo

**Goal:** Run the entire pipeline end-to-end for the first time using stub mode
and a toy repository.

**Prerequisites:** Stack running (see [Quick-Install Guide](./quick-install.md)).
CLI installed.

#### Step 1: Verify the stack

```bash
localcoder gateway-health
# Should show mode: stub
```

#### Step 2: Submit a simple task

```bash
localcoder submit \
  --repo https://github.com/blecx/localCoder \
  --branch main \
  --desc "Add a greet(name) function to a new file greetings.py"
```

Note the task ID printed (e.g., `id=1`).

#### Step 3: Watch the task progress

```bash
# Run every few seconds until status=done
localcoder status 1
```

#### Step 4: See the generated patch

```bash
localcoder patch 1
```

You will see a unified diff. In stub mode this is synthetic. With a real LLM
it would contain a plausible implementation of `greet()`.

#### Step 5: See what artifacts were produced

```bash
localcoder artifacts 1
```

#### Step 6: Download the test log

```bash
localcoder download 1 test-output.txt
cat test-output.txt
```

**What you learned:** The full pipeline — submit, agent claim, LLM call, patch
upload, test run, result — works in under a minute on any machine with Docker.

---

### Example 2 — Intermediate: TODO Management Use Case

**Goal:** Use localCoder to implement a simple TODO CLI tool in a real
repository, driven by a real LLM.

**Prerequisites:** OpenAI API key configured, CLI installed.

#### Context

You have a small Python project with no existing TODO utilities and want to
add a command-line TODO manager. Instead of writing the boilerplate yourself,
you submit tasks to localCoder and review the results.

#### Task A: Create the TODO data model

```bash
localcoder submit \
  --repo https://github.com/<your-org>/<your-repo> \
  --branch main \
  --desc "Create a Todo dataclass in todo/models.py with fields: id (int), \
title (str), done (bool, default False), created_at (datetime). \
Include a __repr__ method. Add a module docstring."
```

Wait for completion:

```bash
localcoder list --status done
localcoder patch <task_id_A>
```

Review the diff. If it looks correct, apply it to your local checkout:

```bash
localcoder download <task_id_A> patch.diff
git apply patch.diff
```

#### Task B: Add a JSON file-based persistence layer

```bash
localcoder submit \
  --repo https://github.com/<your-org>/<your-repo> \
  --branch main \
  --desc "Create todo/storage.py with two functions: load_todos(path: str) \
-> list[Todo] and save_todos(path: str, todos: list[Todo]) -> None. \
Use json module. Handle missing file by returning empty list. \
Add type hints and docstrings."
```

#### Task C: Build the CLI

```bash
localcoder submit \
  --repo https://github.com/<your-org>/<your-repo> \
  --branch main \
  --desc "Create a CLI in todo/cli.py using argparse. Commands: \
'add <title>' (adds a todo), 'list' (prints all todos with index and status), \
'done <id>' (marks todo done), 'delete <id>' (removes a todo). \
Use models.py and storage.py. Store data in ~/.todos.json."
```

#### Task D: Add unit tests

```bash
localcoder submit \
  --repo https://github.com/<your-org>/<your-repo> \
  --branch main \
  --desc "Write pytest tests in tests/test_storage.py. \
Test: load_todos with missing file returns empty list; \
save_todos then load_todos round-trips a list of Todo objects; \
marking done sets done=True."
```

Check test results:

```bash
localcoder download <task_id_D> test-output.txt
cat test-output.txt
```

**What you learned:** You can decompose a feature into discrete tasks,
review each patch independently, and apply only the ones that look correct.
The test runner gives you confidence before you apply any diff.

---

### Example 3 — Advanced: Prototype Note-Taking App UI

**Goal:** Use localCoder iteratively to scaffold a Flask-based web UI for
note management, demonstrating multi-step generation with a capable model.

**Prerequisites:** OpenAI API key with `gpt-4o` or `gpt-4o-mini` configured.

#### Context

You want a simple web app where you can create, view, and delete notes. Each
note has a title, body, and creation timestamp. The app should use Flask with
an in-memory store (no database needed for the prototype).

#### Task 1: Flask app skeleton

```bash
localcoder submit \
  --repo https://github.com/<your-org>/<your-repo> \
  --branch main \
  --desc "Create notes_app/app.py: a Flask application with an in-memory \
list of notes. Each note is a dict with keys: id, title, body, created_at \
(ISO string). Implement routes: \
GET / — HTML page listing all notes with title and date; \
POST /notes — create a note from form fields title and body, redirect to /; \
DELETE /notes/<id> — delete a note by id, return 204. \
Use render_template_string for inline HTML (no templates file needed). \
Include a simple CSS style block in the HTML for readability."
```

Review and apply:

```bash
localcoder patch <task1_id>
localcoder download <task1_id> patch.diff
git apply patch.diff
```

#### Task 2: Add note editing

```bash
localcoder submit \
  --repo https://github.com/<your-org>/<your-repo> \
  --branch main \
  --desc "Extend notes_app/app.py to support editing notes. \
Add routes: GET /notes/<id>/edit — HTML form pre-filled with note title and body; \
POST /notes/<id>/edit — update the note in the in-memory list, redirect to /. \
Add an Edit button next to each note on the index page."
```

#### Task 3: Search functionality

```bash
localcoder submit \
  --repo https://github.com/<your-org>/<your-repo> \
  --branch main \
  --desc "Add a search box to the notes app index page (GET /). \
Accept an optional query parameter q. When q is set, filter the displayed \
notes to those whose title or body contains the search string \
(case-insensitive). Show the current search term in the search box."
```

#### Task 4: Persist notes to a JSON file

```bash
localcoder submit \
  --repo https://github.com/<your-org>/<your-repo> \
  --branch main \
  --desc "Update notes_app/app.py to persist notes to notes.json in the \
working directory instead of an in-memory list. Load notes from the file on \
startup (create empty file if missing). Save notes to the file after every \
create, update, and delete operation."
```

#### Task 5: Write integration tests

```bash
localcoder submit \
  --repo https://github.com/<your-org>/<your-repo> \
  --branch main \
  --desc "Write pytest tests in tests/test_notes_app.py using Flask test client. \
Tests: \
(1) GET / returns 200 and renders note list; \
(2) POST /notes creates a note visible on GET /; \
(3) DELETE /notes/<id> removes the note; \
(4) GET / with ?q=foo returns only matching notes. \
Use tmp_path fixture to avoid polluting the filesystem."
```

Check the results:

```bash
localcoder list --status done
for id in <task1_id> <task2_id> <task3_id> <task4_id> <task5_id>; do
  echo "=== Task $id ===" && localcoder download $id test-output.txt && cat test-output.txt
done
```

#### Running the app locally

After applying all patches:

```bash
pip install flask
cd notes_app
flask run
# Open http://localhost:5000 in your browser
```

**What you learned:** localCoder can be used iteratively to build a
non-trivial application incrementally. Each task is small and reviewable.
The test task gives you a suite you can run locally before merging any
generated code. The approach scales to any number of features — just keep
the task descriptions focused and self-contained.

---

## CLI Quick Reference

```
localcoder submit     --repo <git-url> [--branch <branch>] --desc "<desc>"
localcoder list       [--status pending|claimed|running|done|failed]
localcoder status     <task_id>
localcoder patch      <task_id>
localcoder artifacts  <task_id>
localcoder download   <task_id> <artifact_name> [--out <path>]
localcoder gateway-health
```

### Environment variables for the CLI

| Variable          | Default                    | Purpose                       |
|-------------------|----------------------------|-------------------------------|
| `HUB_URL`         | `http://localhost:8000`    | Hub service URL               |
| `LLM_GATEWAY_URL` | `http://localhost:8001`    | Gateway service URL           |

Override in your shell:

```bash
export HUB_URL=http://my-hub:8000
export LLM_GATEWAY_URL=http://my-gateway:8001
```
