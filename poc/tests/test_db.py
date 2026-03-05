"""
poc/tests/test_db.py – unit tests for the SQLite store.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.store import (
    create_session,
    get_session,
    list_sessions,
    add_message,
    get_messages,
    add_tool_call,
    update_tool_call_result,
    get_tool_calls,
)


@pytest.fixture()
def db(tmp_path):
    """Return a fresh temporary database path for each test."""
    return str(tmp_path / "test.db")


def test_create_and_get_session(db):
    sid = create_session(metadata={"user": "test"}, db_path=db)
    session = get_session(sid, db_path=db)
    assert session is not None
    assert session["id"] == sid


def test_list_sessions_empty(db):
    assert list_sessions(db_path=db) == []


def test_list_sessions(db):
    s1 = create_session(db_path=db)
    s2 = create_session(db_path=db)
    sessions = list_sessions(db_path=db)
    ids = [s["id"] for s in sessions]
    assert s1 in ids
    assert s2 in ids


def test_add_and_get_messages(db):
    sid = create_session(db_path=db)
    add_message(sid, "user", "Hello!", db_path=db)
    add_message(sid, "assistant", "Hi there!", db_path=db)
    msgs = get_messages(sid, db_path=db)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["content"] == "Hi there!"


def test_tool_call_lifecycle(db):
    sid = create_session(db_path=db)
    mid = add_message(sid, "assistant", "Let me run that code.", db_path=db)
    tc_id = add_tool_call(mid, "python_runner", {"code": "print(1+1)"}, db_path=db)
    calls = get_tool_calls(mid, db_path=db)
    assert len(calls) == 1
    assert calls[0]["result"] is None

    update_tool_call_result(tc_id, {"output": "2\n"}, db_path=db)
    calls = get_tool_calls(mid, db_path=db)
    assert calls[0]["result"] is not None


def test_get_nonexistent_session(db):
    result = get_session("nonexistent-id", db_path=db)
    assert result is None
