#!/usr/bin/env python3
"""
localCoder CLI – HTTP REST client for the microservices.
"""
import argparse
import json
import sys
import urllib.request
from urllib.error import URLError

HUB_URL = "http://localhost:8000"
GATEWAY_URL = "http://localhost:8001"

def _request(method, url, data=None):
    req = urllib.request.Request(url, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except URLError as e:
        print(f"Error connecting to {url}: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_gateway_health(args):
    result = _request("GET", f"{GATEWAY_URL}/health")
    print(f"LLM Gateway  {GATEWAY_URL}")
    print(f"  status : {result.get('status')}")
    print(f"  mode   : {result.get('mode')}")
    print(f"  model  : {result.get('model')}")
    if result.get("stub_warning"):
        print(f"  ⚠ stub_warning: true — running without a real LLM")

def cmd_submit(args):
    data = {
        "repo_url": args.repo,
        "branch": args.branch,
        "description": args.desc
    }
    result = _request("POST", f"{HUB_URL}/tasks", data)
    print(f"Task created: id={result['id']}  status={result['status']}")

def cmd_list(args):
    tasks = _request("GET", f"{HUB_URL}/tasks")
    if not tasks:
        print("No tasks found.")
        return
    for t in tasks:
        print(f"id={t['id']:<3} status={t['status']:<10} repo={t['repo_url']}")

def cmd_status(args):
    task = _request("GET", f"{HUB_URL}/tasks/{args.id}")
    print(f"id={task['id']:<3} status={task['status']:<10} repo={task['repo_url']}")

def main():
    parser = argparse.ArgumentParser(prog="localcoder", description="localCoder CLI over REST.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # gateway-health
    subparsers.add_parser("gateway-health", help="Check LLM gateway status")

    # submit
    p_submit = subparsers.add_parser("submit", help="Submit a new task")
    p_submit.add_argument("--repo", required=True, help="Repository URL")
    p_submit.add_argument("--branch", default="main", help="Branch name (default: main)")
    p_submit.add_argument("--desc", required=True, help="Task description")
    p_submit.set_defaults(func=cmd_submit)

    # list
    p_list = subparsers.add_parser("list", help="List all tasks")
    p_list.set_defaults(func=cmd_list)

    # status
    p_status = subparsers.add_parser("status", help="Get status of a specific task")
    p_status.add_argument("id", type=int, help="Task ID")
    p_status.set_defaults(func=cmd_status)

    p_health = subparsers.choices["gateway-health"]
    p_health.set_defaults(func=cmd_gateway_health)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
