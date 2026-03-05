"""
Python Runner
=============
Polls the hub for tasks that are in 'done' state and have a patch attached,
applies the patch to a fresh sandbox clone, runs pytest if present, and
reports results back to the hub as an artifact.

Loop:
  1. Poll GET /tasks?status=done  (finds tasks not yet run through python-runner)
  2. Pull the patch artifact
  3. Apply patch to a fresh sandbox copy
  4. Run `pytest` if tests exist
  5. Upload pytest output as artifact
  6. Mark task with runner result
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
RUNNER_ID = os.environ.get("RUNNER_ID", f"python-runner-{os.getpid()}")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "10"))
REPOS_DIR = pathlib.Path(os.environ.get("REPOS_DIR", "/data/repos"))
RUNNER_DIR = pathlib.Path(os.environ.get("RUNNER_DIR", "/data/runner"))

log = logging.getLogger("python-runner")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")

# Track which tasks we have already processed so we don't repeat.
_processed: set[int] = set()


async def _fetch_artifact_text(
    task_id: int, name: str, client: httpx.AsyncClient
) -> str | None:
    resp = await client.get(
        f"{HUB_URL}/tasks/{task_id}/artifacts/{name}", timeout=30
    )
    if resp.status_code == 200:
        return resp.text
    return None


async def _process_task(task: dict, client: httpx.AsyncClient) -> None:
    task_id = task["id"]
    log.info("Runner processing task %d", task_id)

    patch_text = task.get("patch") or await _fetch_artifact_text(
        task_id, f"task_{task_id}.patch", client
    )
    if not patch_text:
        log.warning("Task %d has no patch, skipping", task_id)
        return

    # Clone snapshot from hub
    clone_resp = await client.post(
        f"{HUB_URL}/repos/clone",
        json={"repo_url": task["repo_url"], "branch": task["branch"]},
        timeout=300,
    )
    clone_resp.raise_for_status()
    worktree_path = pathlib.Path(clone_resp.json()["path"])

    # Fresh sandbox
    sandbox = RUNNER_DIR / str(task_id)
    if sandbox.exists():
        shutil.rmtree(sandbox)
    shutil.copytree(worktree_path, sandbox, symlinks=True)

    # Apply patch
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".patch", delete=False
    ) as f:
        f.write(patch_text)
        patch_file = f.name

    try:
        apply = subprocess.run(
            ["git", "apply", "--ignore-whitespace", patch_file],
            cwd=str(sandbox),
            capture_output=True,
            text=True,
        )
        apply_ok = apply.returncode == 0
        if not apply_ok:
            log.warning("Patch apply failed for task %d: %s", task_id, apply.stderr)
    finally:
        os.unlink(patch_file)

    # Run pytest if tests are present
    has_tests = any(sandbox.rglob("test_*.py")) or any(sandbox.rglob("*_test.py"))
    if has_tests:
        log.info("Running pytest for task %d", task_id)
        pytest_result = subprocess.run(
            ["python", "-m", "pytest", "--tb=short", "-q"],
            cwd=str(sandbox),
            capture_output=True,
            text=True,
            timeout=300,
        )
        pytest_output = pytest_result.stdout + pytest_result.stderr
        pytest_passed = pytest_result.returncode == 0
    else:
        pytest_output = "No test files found — pytest skipped.\n"
        pytest_passed = True

    summary = (
        f"patch_applied={apply_ok}\n"
        f"pytest_passed={pytest_passed}\n"
        f"---\n{pytest_output}"
    )

    # Upload result artifact
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix=f"runner_{task_id}_"
    ) as f:
        f.write(summary)
        result_file = f.name

    try:
        with open(result_file, "rb") as fh:
            await client.post(
                f"{HUB_URL}/tasks/{task_id}/artifacts",
                files={
                    "file": (f"runner_{task_id}_result.txt", fh, "text/plain")
                },
                timeout=30,
            )
    finally:
        os.unlink(result_file)

    log.info("Task %d runner done (pytest_passed=%s)", task_id, pytest_passed)


async def _main() -> None:
    log.info("Python runner %s starting (poll interval %ds)", RUNNER_ID, POLL_INTERVAL)
    RUNNER_DIR.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient() as client:
        while True:
            try:
                resp = await client.get(
                    f"{HUB_URL}/tasks", params={"status": "done"}, timeout=10
                )
                resp.raise_for_status()
                tasks = resp.json()
                for task in tasks:
                    tid = task["id"]
                    if tid not in _processed:
                        _processed.add(tid)
                        await _process_task(task, client)
            except Exception as exc:  # noqa: BLE001
                log.warning("Runner poll error: %s", exc)

            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(_main())
