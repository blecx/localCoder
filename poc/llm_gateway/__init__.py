"""PoC LLM Gateway — provider-abstracted OpenAI-compatible chat gateway.

This package serves two purposes:

1. New library API: ``LLMGateway`` / ``GatewayConfig`` from the
   provider-abstracted ``poc/llm_gateway/`` package.

2. Legacy shim: exposes ``gateway`` and ``copilot_adapter`` attributes that
   dynamically load the corresponding modules from the ``poc/llm-gateway/``
   Docker-service directory.  Tests written against the original shim continue
   to work without modification.
"""

from __future__ import annotations

from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
import sys

from poc.llm_gateway.gateway import LLMGateway
from poc.llm_gateway.config import GatewayConfig

__all__ = ["LLMGateway", "GatewayConfig", "gateway", "copilot_adapter"]

_SVC_DIR = Path(__file__).parent.parent / "llm-gateway"


def _load_sibling(name: str):
    """Dynamically load a module from the hyphenated service directory."""
    fq_name = f"llm_gateway.{name}"
    if fq_name in sys.modules:
        return sys.modules[fq_name]
    src = _SVC_DIR / f"{name}.py"
    spec = spec_from_file_location(fq_name, src)
    mod = module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[fq_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


gateway = _load_sibling("gateway")
copilot_adapter = _load_sibling("copilot_adapter")
