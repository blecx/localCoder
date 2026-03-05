"""Repo clone routes for Hub."""
from __future__ import annotations

import os
import pathlib
import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/repos", tags=["repos"])

REPOS_DIR = pathlib.Path(os.environ.get("REPOS_DIR", "/data/repos"))


class CloneRequest(BaseModel):
    repo_url: str
    branch: str = "main"


class CloneResponse(BaseModel):
    path: str
    already_existed: bool


@router.post("/clone", response_model=CloneResponse)
async def clone_repo(body: CloneRequest):
    """
    Canonical clone strategy: clone once into a bare mirror, then create
    a worktree checkout under /data/repos/<slug>/<branch>.
    Subsequent calls with the same repo/branch are no-ops (idempotent).
    """
    slug = _repo_slug(body.repo_url)
    mirror_path = REPOS_DIR / slug / ".mirror"
    worktree_path = REPOS_DIR / slug / body.branch

    already_existed = worktree_path.exists()

    if not already_existed:
        mirror_path.mkdir(parents=True, exist_ok=True)

        if not (mirror_path / "HEAD").exists():
            _run(["git", "clone", "--mirror", body.repo_url, str(mirror_path)])
        else:
            _run(["git", "-C", str(mirror_path), "remote", "update"])

        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        _run(
            [
                "git",
                "-C",
                str(mirror_path),
                "worktree",
                "add",
                "--detach",
                str(worktree_path),
                f"refs/heads/{body.branch}",
            ]
        )

    return CloneResponse(path=str(worktree_path), already_existed=already_existed)


# ──────────────────────────── helpers ────────────────────────────────────────

def _repo_slug(url: str) -> str:
    """Turn a git URL into a filesystem-safe directory name."""
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url.split("/")[-1].replace(" ", "_")


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Git command failed: {result.stderr.strip()}",
        )
