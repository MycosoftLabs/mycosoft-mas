"""KVTC serving lane configuration loader.

Reads config/kvtc_serving.yaml and provides typed access to serving config.

Date: 2026-03-21
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

_config_cache: Optional[dict] = None


def _expand_env(s: str) -> str:
    """Replace ${VAR:-default} placeholders."""
    if not s or not isinstance(s, str) or "${" not in s:
        return s
    import re
    def replacer(m):
        expr = m.group(1)
        if ":-" in expr:
            var, default = expr.split(":-", 1)
            return os.getenv(var.strip(), default.strip())
        return os.getenv(expr.strip(), "")
    return re.sub(r'\$\{([^}]+)\}', replacer, s)


def load_kvtc_config(force_reload: bool = False) -> dict[str, Any]:
    """Load KVTC serving configuration from config/kvtc_serving.yaml."""
    global _config_cache
    if _config_cache is not None and not force_reload:
        return _config_cache

    for base in (Path.cwd(), Path(__file__).resolve().parent.parent.parent):
        path = base / "config" / "kvtc_serving.yaml"
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            # Expand env vars in string values
            data["artifact_storage"] = _expand_env(data.get("artifact_storage", ""))
            _config_cache = data
            logger.info("Loaded KVTC config from %s", path)
            return data

    logger.warning("config/kvtc_serving.yaml not found — using defaults")
    _config_cache = _default_config()
    return _config_cache


def _default_config() -> dict[str, Any]:
    return {
        "default_cache_mode": "baseline",
        "hot_window_tokens": 128,
        "sink_tokens": 4,
        "artifact_storage": "/opt/mycosoft/artifacts/kvtc",
        "calibration": {
            "default_profile": "mixed_fineweb_openr1",
            "default_tokens": 160000,
            "pca_rank_cap": 10000,
        },
        "promotion": {
            "max_ttft_p95_ms": 500.0,
            "min_compression_ratio": 1.5,
        },
        "alias_defaults": {},
    }


def get_alias_defaults(alias: str) -> dict[str, Any]:
    """Get default serving config for a target alias."""
    cfg = load_kvtc_config()
    return cfg.get("alias_defaults", {}).get(alias, {})


def get_calibration_defaults() -> dict[str, Any]:
    """Get default calibration parameters."""
    cfg = load_kvtc_config()
    return cfg.get("calibration", {})


def get_promotion_thresholds() -> dict[str, Any]:
    """Get promotion eval thresholds."""
    cfg = load_kvtc_config()
    return cfg.get("promotion", {})
