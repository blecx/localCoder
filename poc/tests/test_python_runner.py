"""
poc/tests/test_python_runner.py – tests for the sandboxed Python runner.
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from python_runner.runner import run_python  # type: ignore[import-not-found]


def test_hello_world():
    result = asyncio.run(run_python('print("hello world")'))
    assert result["exit_code"] == 0
    assert "hello world" in result["output"]
    assert result["timed_out"] is False
    assert result["error"] is None


def test_arithmetic():
    result = asyncio.run(run_python("print(2 ** 10)"))
    assert "1024" in result["output"]


def test_syntax_error():
    result = asyncio.run(run_python("def broken("))
    assert result["exit_code"] != 0


def test_timeout():
    result = asyncio.run(run_python("import time; time.sleep(30)", timeout=1))
    assert result["timed_out"] is True


def test_stderr_captured():
    result = asyncio.run(run_python("import sys; sys.stderr.write('oops\\n')"))
    assert "oops" in result["output"]


def test_multiline_code():
    code = """
x = [i ** 2 for i in range(5)]
print(x)
"""
    result = asyncio.run(run_python(code))
    assert "[0, 1, 4, 9, 16]" in result["output"]
