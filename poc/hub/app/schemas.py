"""Pydantic schemas for Hub API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ──────────────────────────── Task schemas ────────────────────────────────────

class TaskCreate(BaseModel):
    repo_url: str
    branch: str = "main"
    description: str


class TaskPatch(BaseModel):
    status: Optional[str] = None
    result: Optional[str] = None
    patch: Optional[str] = None
    claimed_by: Optional[str] = None


class TaskOut(BaseModel):
    id: int
    repo_url: str
    branch: str
    description: str
    status: str
    claimed_by: Optional[str]
    result: Optional[str]
    patch: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────── Artifact schemas ────────────────────────────────

class ArtifactOut(BaseModel):
    id: int
    task_id: int
    name: str
    path: str
    created_at: datetime

    class Config:
        from_attributes = True
