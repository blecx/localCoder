"""Configuration helpers for the PoC LLM Gateway."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


_DEFAULT_CONFIG: Dict[str, Any] = {
    "provider": "openai_compat",
    "base_url": "",
    "api_key": "",
    "model": "",
    "temperature": 0.7,
    "max_tokens": 4096,
    "timeout": 120,
    "fallback_to_stub": False,
}


class GatewayConfig:
    """Load and merge gateway configuration from a JSON file or dict.

    Resolution order for the config file path:
    1. Explicit ``config_path`` argument.
    2. ``LLM_GATEWAY_CONFIG`` environment variable.
    3. ``poc/llm_gateway/config.json`` (repo-local override, gitignored).
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
    ) -> None:
        if config is not None:
            self._data = {**_DEFAULT_CONFIG, **config}
            return

        self._data = {**_DEFAULT_CONFIG, **self._load_file(config_path)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_path(config_path: Optional[str]) -> Optional[Path]:
        if config_path:
            return Path(config_path)
        env_path = os.environ.get("LLM_GATEWAY_CONFIG", "").strip()
        if env_path:
            return Path(env_path)
        local = Path(__file__).resolve().parent / "config.json"
        if local.exists():
            return local
        return None

    @classmethod
    def _load_file(cls, config_path: Optional[str]) -> Dict[str, Any]:
        path = cls._resolve_path(config_path)
        if path is None:
            return {}
        try:
            with open(path) as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Failed to load gateway config from {path}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]