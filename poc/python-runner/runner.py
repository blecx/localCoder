"""
poc/python-runner/runner.py

Sandboxed Python execution service for the localCoder PoC.

Uses subprocess with a timeout and resource limits to safely execute
user/agent-supplied Python code and return stdout + stderr.
"""

from __future__ import annotations

import asyncio
import os
import sys
import textwrap
from pathlib import Path
from typing import Any

_DEFAULT_TIMEOUT = int(os.environ.get("PYTHON_RUNNER_TIMEOUT", "10"))
_MAX_OUTPUT_BYTES = 65_536  # 64 KiB cap on output


async def run_python(
    code: str,
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """
    Execute ``code`` in an isolated subprocess and return a result dict.

    Returns
    -------
    dict with keys:
        - ``output``  : combined stdout + stderr (truncated to 64 KiB)
        - ``exit_code``: process exit code
        - ``timed_out``: True if the process was killed due to timeout
        - ``error``   : error message if the runner itself failed
    """
    # Write code to a temp file to avoid shell-injection risks
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir="/tmp"
    ) as f:
        f.write(textwrap.dedent(code))
        tmp_path = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        try:
            stdout_bytes, _ = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            timed_out = False
        except asyncio.TimeoutError:
            proc.kill()
            stdout_bytes = b""
            timed_out = True

        output = stdout_bytes[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
        if timed_out:
            output += f"\n[python-runner] Process killed after {timeout}s timeout."

        return {
            "output": output,
            "exit_code": proc.returncode if not timed_out else -1,
            "timed_out": timed_out,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "output": "",
            "exit_code": -1,
            "timed_out": False,
            "error": str(exc),
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
