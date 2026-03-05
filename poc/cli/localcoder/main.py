"""
localcoder CLI
==============
A command-line client for the localCoder Hub API.

Usage
-----
  localcoder submit --repo https://github.com/org/repo --desc "Add hello world"
  localcoder list [--status pending]
  localcoder status <task_id>
  localcoder patch <task_id>
  localcoder artifacts <task_id>
  localcoder download <task_id> <artifact_name> [--out ./output]
  localcoder gateway-health
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import httpx

HUB_URL = os.environ.get("HUB_URL", "http://localhost:8000")
LLM_GATEWAY_URL = os.environ.get("LLM_GATEWAY_URL", "http://localhost:8001")


# ──────────────────────────── helpers ────────────────────────────────────────

def _hub(path: str, method: str = "GET", **kwargs) -> dict:
    url = HUB_URL.rstrip("/") + path
    try:
        resp = httpx.request(method, url, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        print(f"Error {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as exc:
        print(f"Connection error: {exc}", file=sys.stderr)
        sys.exit(1)


def _print_json(data) -> None:
    print(json.dumps(data, indent=2, default=str))


def _print_task(task: dict) -> None:
    print(
        f"[{task['id']:>4}] {task['status']:>8}  {task['repo_url']}  "
        f"branch={task['branch']}  "
        f"\"{task['description'][:60]}\""
    )


# ──────────────────────────── commands ───────────────────────────────────────

def cmd_submit(args: argparse.Namespace) -> None:
    """Submit a new coding task to the hub."""
    payload = {
        "repo_url": args.repo,
        "branch": args.branch,
        "description": args.desc,
    }
    task = _hub("/tasks", method="POST", json=payload)
    print(f"Task created: id={task['id']}")
    _print_task(task)


def cmd_list(args: argparse.Namespace) -> None:
    """List tasks, optionally filtered by status."""
    params = {}
    if args.status:
        params["status"] = args.status
    tasks = _hub("/tasks" + (f"?status={args.status}" if args.status else ""))
    if not tasks:
        print("No tasks found.")
        return
    for t in tasks:
        _print_task(t)


def cmd_status(args: argparse.Namespace) -> None:
    """Show full details for a task."""
    task = _hub(f"/tasks/{args.task_id}")
    _print_json(task)


def cmd_patch(args: argparse.Namespace) -> None:
    """Print the git diff patch stored on a task."""
    task = _hub(f"/tasks/{args.task_id}")
    patch = task.get("patch")
    if not patch:
        print("No patch available for this task.", file=sys.stderr)
        sys.exit(1)
    print(patch)


def cmd_artifacts(args: argparse.Namespace) -> None:
    """List artifacts attached to a task."""
    artifacts = _hub(f"/tasks/{args.task_id}/artifacts")
    if not artifacts:
        print("No artifacts found.")
        return
    for a in artifacts:
        print(f"  {a['name']:40s}  id={a['id']}  task={a['task_id']}")


def cmd_download(args: argparse.Namespace) -> None:
    """Download a named artifact to disk."""
    url = f"{HUB_URL.rstrip('/')}/tasks/{args.task_id}/artifacts/{args.name}"
    try:
        resp = httpx.get(url, timeout=60)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print(f"Error {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
        sys.exit(1)
    out_path = args.out or args.name
    with open(out_path, "wb") as f:
        f.write(resp.content)
    print(f"Saved to {out_path}")


def cmd_gateway_health(args: argparse.Namespace) -> None:
    """Check LLM gateway health and show current mode (stub vs openai)."""
    url = LLM_GATEWAY_URL.rstrip("/") + "/health"
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"Gateway unreachable: {exc}", file=sys.stderr)
        sys.exit(1)
    _print_json(data)
    if data.get("stub_warning"):
        print(
            "\n⚠  Gateway is running in STUB mode — responses are synthetic.\n"
            "   Set OPENAI_API_KEY to enable real OpenAI completions.",
            file=sys.stderr,
        )


# ──────────────────────────── parser ─────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="localcoder",
        description="CLI client for the localCoder multi-agent coding framework.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # submit
    p_submit = sub.add_parser("submit", help="Submit a new coding task")
    p_submit.add_argument("--repo", required=True, help="Git repository URL")
    p_submit.add_argument("--branch", default="main", help="Branch (default: main)")
    p_submit.add_argument("--desc", required=True, help="Task description")
    p_submit.set_defaults(func=cmd_submit)

    # list
    p_list = sub.add_parser("list", help="List tasks")
    p_list.add_argument("--status", help="Filter by status (pending/claimed/running/done/failed)")
    p_list.set_defaults(func=cmd_list)

    # status
    p_status = sub.add_parser("status", help="Show details of a task")
    p_status.add_argument("task_id", type=int)
    p_status.set_defaults(func=cmd_status)

    # patch
    p_patch = sub.add_parser("patch", help="Print the git diff patch for a task")
    p_patch.add_argument("task_id", type=int)
    p_patch.set_defaults(func=cmd_patch)

    # artifacts
    p_art = sub.add_parser("artifacts", help="List artifacts for a task")
    p_art.add_argument("task_id", type=int)
    p_art.set_defaults(func=cmd_artifacts)

    # download
    p_dl = sub.add_parser("download", help="Download an artifact to disk")
    p_dl.add_argument("task_id", type=int)
    p_dl.add_argument("name", help="Artifact name")
    p_dl.add_argument("--out", help="Output file path (default: artifact name)")
    p_dl.set_defaults(func=cmd_download)

    # gateway-health
    p_gw = sub.add_parser("gateway-health", help="Check LLM gateway health")
    p_gw.set_defaults(func=cmd_gateway_health)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
