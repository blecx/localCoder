"""
poc/python_runner – Python package alias for the python-runner service.

The on-disk directory is ``poc/python-runner/`` (hyphenated), but Python
requires underscores.  This package re-exports from that directory.
"""

from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import sys

_SVC_DIR = Path(__file__).parent.parent / "python-runner"


def _load_sibling(name: str):
    src = _SVC_DIR / f"{name}.py"
    spec = spec_from_file_location(f"python_runner.{name}", src)
    mod = module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[f"python_runner.{name}"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


runner = _load_sibling("runner")

__all__ = ["runner"]
