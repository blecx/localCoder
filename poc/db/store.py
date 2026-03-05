"""
poc/db/store.py – thin SQLite wrapper for the localCoder PoC.

Provides Session and Message persistence that all services can share
via a common SQLite file (default: poc/.localcoder.db).
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

_DEFAULT_DB = Path(__file__).parent.parent / ".localcoder.db"
_SCHEMA = Path(__file__).parent / "schema.sql"

_local = threading.local()


def _get_conn(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Return a thread-local SQLite connection, creating the schema on first use."""
    path = str(db_path or os.environ.get("LOCALCODER_DB", _DEFAULT_DB))
    if not hasattr(_local, "conn") or getattr(_local, "db_path", None) != path:
        if hasattr(_local, "conn"):
            try:
                _local.conn.close()
            except Exception:
                pass
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        schema = _SCHEMA.read_text()
        conn.executescript(schema)
        conn.commit()
        _local.conn = conn
        _local.db_path = path
    return _local.conn


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def create_session(metadata: dict[str, Any] | None = None, db_path=None) -> str:
    """Create a new session and return its ID."""
    conn = _get_conn(db_path)
    sid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO sessions (id, metadata) VALUES (?, ?)",
        (sid, json.dumps(metadata or {})),
    )
    conn.commit()
    return sid


def get_session(session_id: str, db_path=None) -> Optional[dict]:
    conn = _get_conn(db_path)
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return dict(row) if row else None


def list_sessions(db_path=None) -> list[dict]:
    conn = _get_conn(db_path)
    rows = conn.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------

def add_message(
    session_id: str,
    role: str,
    content: str,
    db_path=None,
) -> int:
    conn = _get_conn(db_path)
    cursor = conn.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content),
    )
    conn.execute(
        "UPDATE sessions SET updated_at = datetime('now') WHERE id = ?",
        (session_id,),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def get_messages(session_id: str, db_path=None) -> list[dict]:
    conn = _get_conn(db_path)
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Tool-call helpers
# ---------------------------------------------------------------------------

def add_tool_call(
    message_id: int,
    tool_name: str,
    arguments: dict,
    db_path=None,
) -> int:
    conn = _get_conn(db_path)
    cursor = conn.execute(
        "INSERT INTO tool_calls (message_id, tool_name, arguments) VALUES (?, ?, ?)",
        (message_id, tool_name, json.dumps(arguments)),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def update_tool_call_result(tool_call_id: int, result: Any, db_path=None) -> None:
    conn = _get_conn(db_path)
    conn.execute(
        "UPDATE tool_calls SET result = ? WHERE id = ?",
        (json.dumps(result), tool_call_id),
    )
    conn.commit()


def get_tool_calls(message_id: int, db_path=None) -> list[dict]:
    conn = _get_conn(db_path)
    rows = conn.execute(
        "SELECT * FROM tool_calls WHERE message_id = ? ORDER BY id",
        (message_id,),
    ).fetchall()
    return [dict(r) for r in rows]
