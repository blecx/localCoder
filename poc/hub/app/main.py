"""Hub FastAPI application entry-point."""
from __future__ import annotations

import os
import pathlib
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from app.database import get_pool, close_pool
from app.routes.tasks import router as tasks_router
from app.routes.artifacts import router as artifacts_router
from app.routes.repos import router as repos_router

MIGRATIONS_DIR = pathlib.Path(__file__).parent.parent / "migrations"


async def _run_migrations(pool: asyncpg.Pool) -> None:
    """Apply SQL migration files in order (idempotent)."""
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        sql = sql_file.read_text()
        await pool.execute(sql)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await get_pool()
    await _run_migrations(pool)
    yield
    await close_pool()


app = FastAPI(title="localCoder Hub", version="0.1.0", lifespan=lifespan)

app.include_router(tasks_router)
app.include_router(artifacts_router)
app.include_router(repos_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
