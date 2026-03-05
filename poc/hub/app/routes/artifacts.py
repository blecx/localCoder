"""Artifact routes for Hub."""
from __future__ import annotations

import os
import pathlib

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.database import get_pool
from app.schemas import ArtifactOut

router = APIRouter(prefix="/tasks/{task_id}/artifacts", tags=["artifacts"])

ARTIFACTS_DIR = pathlib.Path(os.environ.get("ARTIFACTS_DIR", "/data/artifacts"))


@router.post("", response_model=ArtifactOut, status_code=201)
async def upload_artifact(
    task_id: int,
    file: UploadFile,
    pool: asyncpg.Pool = Depends(get_pool),
):
    task_row = await pool.fetchrow("SELECT id FROM tasks WHERE id = $1", task_id)
    if task_row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task_dir = ARTIFACTS_DIR / str(task_id)
    task_dir.mkdir(parents=True, exist_ok=True)

    dest = task_dir / (file.filename or "artifact")
    content = await file.read()
    dest.write_bytes(content)

    row = await pool.fetchrow(
        """
        INSERT INTO artifacts (task_id, name, path)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        task_id,
        file.filename or "artifact",
        str(dest),
    )
    return dict(row)


@router.get("", response_model=list[ArtifactOut])
async def list_artifacts(task_id: int, pool: asyncpg.Pool = Depends(get_pool)):
    rows = await pool.fetch(
        "SELECT * FROM artifacts WHERE task_id = $1 ORDER BY id", task_id
    )
    return [dict(r) for r in rows]


@router.get("/{name}")
async def download_artifact(
    task_id: int,
    name: str,
    pool: asyncpg.Pool = Depends(get_pool),
):
    row = await pool.fetchrow(
        "SELECT * FROM artifacts WHERE task_id = $1 AND name = $2",
        task_id,
        name,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(row["path"], filename=name)
