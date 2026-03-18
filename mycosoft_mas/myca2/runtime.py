"""
MYCA2 sandbox runtime boundaries (Mar 17, 2026).

Separate alias family from production MYCA (myca_core / myca_edge).
PSILO and Plasticity Forge mutations target MYCA2 aliases first.
Production orchestrator traffic MUST NOT set MYCA2 runtime unless explicitly testing.

Env:
  MYCA2_RUNTIME=1 — message carries myca2 execution path (executive + overlay + myca2_core backend).
  MYCA2_DEFAULT_NEMOTRON_URL — optional separate Nemotron endpoint for sandbox (else same as prod stack).
"""

from __future__ import annotations

import os

# Registry / YAML role names (must match config/models.yaml model_roles)
ALIAS_MYCA2_CORE = "myca2_core"
ALIAS_MYCA2_EDGE = "myca2_edge"
ALIAS_MYCA2_SANDBOX = "myca2_sandbox"
ALIAS_PSILO_OVERLAY = "psilo_overlay"

MYCA2_ALIASES = frozenset(
    {ALIAS_MYCA2_CORE, ALIAS_MYCA2_EDGE, ALIAS_MYCA2_SANDBOX, ALIAS_PSILO_OVERLAY}
)

PRODUCTION_PLASTICITY_ALIASES = frozenset({"myca_core", "myca_edge"})


def is_myca2_runtime_message(msg: dict) -> bool:
    """True if this message should use MYCA2 sandbox path (overlay + myca2_core routing)."""
    if not msg:
        return False
    if msg.get("myca2") is True or msg.get("runtime") == "myca2":
        return True
    if os.getenv("MYCA2_RUNTIME", "").strip().lower() in ("1", "true", "yes"):
        return True
    return bool(msg.get("psilo_session_id"))


def myca2_enabled_globally() -> bool:
    return os.getenv("MYCA2_RUNTIME", "").strip().lower() in ("1", "true", "yes")
