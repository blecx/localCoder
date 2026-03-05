"""Task routes for Hub."""
from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_pool
from app.schemas import TaskCreate, TaskOut, TaskPatch

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _get_task_or_404(task_id: int, pool: asyncpg.Pool) -> asyncpg.Record:
    row = await pool.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return row


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskCreate, pool: asyncpg.Pool = Depends(get_pool)):
    row = await pool.fetchrow(
        """
        INSERT INTO tasks (repo_url, branch, description)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        body.repo_url,
        body.branch,
        body.description,
    )
    return dict(row)


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    status: str | None = None,
    pool: asyncpg.Pool = Depends(get_pool),
):
    if status:
        rows = await pool.fetch("SELECT * FROM tasks WHERE status = $1 ORDER BY id", status)
    else:
        rows = await pool.fetch("SELECT * FROM tasks ORDER BY id")
    return [dict(r) for r in rows]


@router.get("/next-pending", response_model=TaskOut | None)
async def next_pending(pool: asyncpg.Pool = Depends(get_pool)):
    """Return the oldest pending task (for agents to poll)."""
    row = await pool.fetchrow(
        "SELECT * FROM tasks WHERE status = 'pending' ORDER BY id LIMIT 1"
    )
    return dict(row) if row else None


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, pool: asyncpg.Pool = Depends(get_pool)):
    row = await _get_task_or_404(task_id, pool)
    return dict(row)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    body: TaskPatch,
    pool: asyncpg.Pool = Depends(get_pool),
):
    await _get_task_or_404(task_id, pool)

    # Build updates from non-None fields; whitelist columns against the schema
    # to prevent SQL injection from maliciously crafted field names.
    allowed_columns = set(TaskPatch.model_fields.keys())
    updates = {
        k: v
        for k, v in body.model_dump().items()
        if v is not None and k in allowed_columns
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    values = list(updates.values())

    row = await pool.fetchrow(
        f"UPDATE tasks SET {set_clause} WHERE id = $1 RETURNING *",
        task_id,
        *values,
    )
    return dict(row)


@router.post("/{task_id}/claim", response_model=TaskOut)
async def claim_task(
    task_id: int,
    claimed_by: str,
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Atomically claim a pending task for an agent."""
    row = await pool.fetchrow(
        """
        UPDATE tasks
        SET status = 'claimed', claimed_by = $2
        WHERE id = $1 AND status = 'pending'
        RETURNING *
        """,
        task_id,
        claimed_by,
    )
    if row is None:
        raise HTTPException(
            status_code=409,
            detail="Task not found or already claimed",
        )
    return dict(row)
