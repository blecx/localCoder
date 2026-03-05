"""
Generalist Agent
================
Polls the hub for pending tasks, works in a sandbox clone, calls the LLM
gateway to produce edits, and returns a unified git-diff patch to the hub.

Loop:
  1. Poll GET /tasks/next-pending
  2. Claim the task (POST /tasks/{id}/claim)
  3. Ask hub to clone the repo (POST /repos/clone) → local worktree path
  4. Create a sandbox copy of the worktree
  5. Send task description + file tree to LLM gateway
  6. Apply the patch the LLM returns (best-effort)
  7. Generate a unified diff against the original
  8. PATCH /tasks/{id} with status=done and the patch
  9. Upload the patch as an artifact
  10. Sleep and repeat
"""
from __future__ import annotations

import asyncio
import logging
import os
import pathlib
import shutil
import subprocess
import tempfile

import httpx

HUB_URL = os.environ.get("HUB_URL", "http://hub:8000")
LLM_GATEWAY_URL = os.environ.get("LLM_GATEWAY_URL", "http://llm-gateway:8001")
AGENT_ID = os.environ.get("AGENT_ID", f"generalist-{os.getpid()}")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "5"))
REPOS_DIR = pathlib.Path(os.environ.get("REPOS_DIR", "/data/repos"))
SANDBOX_DIR = pathlib.Path(os.environ.get("SANDBOX_DIR", "/data/sandbox"))

log = logging.getLogger("agent-generalist")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")


# ──────────────────────────── LLM helpers ────────────────────────────────────

async def _call_llm(description: str, file_tree: str, client: httpx.AsyncClient) -> str:
    system_prompt = (
        "You are a coding assistant. "
        "Given a task description and a file tree, produce a unified diff patch "
        "(git diff format) that implements the requested change. "
        "Output ONLY the raw diff text, nothing else."
    )
    user_msg = f"Task: {description}\n\nFile tree:\n{file_tree}"

    resp = await client.post(
        f"{LLM_GATEWAY_URL}/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ──────────────────────────── git helpers ────────────────────────────────────

def _file_tree(path: pathlib.Path, max_lines: int = 200) -> str:
    lines: list[str] = []
    for p in sorted(path.rglob("*")):
        if ".git" in p.parts:
            continue
        rel = p.relative_to(path)
        indent = "  " * (len(rel.parts) - 1)
        lines.append(f"{indent}{rel.name}{'/' if p.is_dir() else ''}")
        if len(lines) >= max_lines:
            lines.append("... (truncated)")
            break
    return "\n".join(lines)


def _apply_patch(patch: str, sandbox: pathlib.Path) -> bool:
    """Try to apply a unified diff patch; return True on success."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
        f.write(patch)
        patch_file = f.name
    try:
        result = subprocess.run(
            ["git", "apply", "--ignore-whitespace", patch_file],
            cwd=str(sandbox),
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    finally:
        os.unlink(patch_file)


def _make_diff(original: pathlib.Path, modified: pathlib.Path) -> str:
    """Generate a unified diff between two directory trees."""
    result = subprocess.run(
        ["diff", "-urN", str(original), str(modified)],
        capture_output=True,
        text=True,
    )
    return result.stdout  # returncode 1 just means there are diffs


# ──────────────────────────── task processing ────────────────────────────────

async def _process_task(task: dict, client: httpx.AsyncClient) -> None:
    task_id = task["id"]
    log.info("Processing task %d: %s", task_id, task["description"][:60])

    # Mark as running
    await client.patch(
        f"{HUB_URL}/tasks/{task_id}",
        json={"status": "running"},
        timeout=10,
    )

    try:
        # Ask hub to clone the repo
        clone_resp = await client.post(
            f"{HUB_URL}/repos/clone",
            json={"repo_url": task["repo_url"], "branch": task["branch"]},
            timeout=300,
        )
        clone_resp.raise_for_status()
        worktree_path = pathlib.Path(clone_resp.json()["path"])

        # Create a sandbox copy
        sandbox = SANDBOX_DIR / str(task_id) / "work"
        if sandbox.exists():
            shutil.rmtree(sandbox)
        shutil.copytree(worktree_path, sandbox, symlinks=True)

        # Keep an unmodified copy for diff
        original = SANDBOX_DIR / str(task_id) / "original"
        if original.exists():
            shutil.rmtree(original)
        shutil.copytree(worktree_path, original, symlinks=True)

        # Call LLM
        tree = _file_tree(sandbox)
        llm_patch = await _call_llm(task["description"], tree, client)

        # Apply patch
        applied = _apply_patch(llm_patch, sandbox)
        log.info("Patch apply %s for task %d", "succeeded" if applied else "failed", task_id)

        # Generate final diff
        final_diff = _make_diff(original, sandbox)

        # Update task
        await client.patch(
            f"{HUB_URL}/tasks/{task_id}",
            json={
                "status": "done",
                "patch": final_diff,
                "result": f"Patch applied: {applied}",
            },
            timeout=10,
        )

        # Upload patch as artifact
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".patch", delete=False, prefix=f"task_{task_id}_"
        ) as f:
            f.write(final_diff)
            patch_file = f.name

        with open(patch_file, "rb") as fh:
            await client.post(
                f"{HUB_URL}/tasks/{task_id}/artifacts",
                files={"file": (f"task_{task_id}.patch", fh, "text/plain")},
                timeout=30,
            )
        os.unlink(patch_file)

        log.info("Task %d done", task_id)

    except Exception as exc:  # noqa: BLE001
        log.exception("Task %d failed: %s", task_id, exc)
        await client.patch(
            f"{HUB_URL}/tasks/{task_id}",
            json={"status": "failed", "result": str(exc)},
            timeout=10,
        )


# ──────────────────────────── main loop ──────────────────────────────────────

async def _main() -> None:
    log.info("Generalist agent %s starting (poll interval %ds)", AGENT_ID, POLL_INTERVAL)
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient() as client:
        while True:
            try:
                resp = await client.get(
                    f"{HUB_URL}/tasks/next-pending", timeout=10
                )
                resp.raise_for_status()
                task = resp.json()
                if task:
                    # Claim it
                    claim_resp = await client.post(
                        f"{HUB_URL}/tasks/{task['id']}/claim",
                        params={"claimed_by": AGENT_ID},
                        timeout=10,
                    )
                    if claim_resp.status_code == 200:
                        await _process_task(claim_resp.json(), client)
                    else:
                        log.debug("Could not claim task %d (race), skipping", task["id"])
            except Exception as exc:  # noqa: BLE001
                log.warning("Poll error: %s", exc)

            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(_main())
