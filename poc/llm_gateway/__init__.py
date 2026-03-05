"""
poc/llm_gateway – Python package re-exporting the LLM gateway.

The on-disk service directory is ``poc/llm-gateway/`` (hyphenated for
clarity), but Python requires underscores in module names.  This package
bridges that gap by re-exporting the gateway and copilot_adapter modules.
"""

from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import sys

_SVC_DIR = Path(__file__).parent.parent / "llm-gateway"


def _load_sibling(name: str):
    """Dynamically load a module from the hyphenated service directory."""
    src = _SVC_DIR / f"{name}.py"
    spec = spec_from_file_location(f"llm_gateway.{name}", src)
    mod = module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[f"llm_gateway.{name}"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


gateway = _load_sibling("gateway")
copilot_adapter = _load_sibling("copilot_adapter")

__all__ = ["gateway", "copilot_adapter"]
