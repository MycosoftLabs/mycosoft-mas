"""
Plasticity Forge Phase 1 — security and governance sandbox for model development.

- No production secrets in plasticity or candidate artifacts.
- No direct promotion authority from plasticity service (approval tiers).
- Signed artifacts and auditable promotion decisions.
- Sandbox checker used before promote when PLASTICITY_SANDBOX_CHECK=1.

Created: March 14, 2026
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class SandboxCheckResult:
    """Result of a sandbox pre-promotion check."""
    passed: bool
    checks: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# Keys/phrases that must not appear in candidate config or eval payloads (prod secrets).
_SECRET_INDICATORS = [
    "password", "secret", "api_key", "apikey", "token", "credential",
    "private_key", "aws_secret", "openai_key", "anthropic_key",
]


def _contains_secret_like(value: Any) -> bool:
    """Heuristic: detect secret-like keys in nested dict/list (not values, to avoid false positives)."""
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str) and any(s in k.lower() for s in _SECRET_INDICATORS):
                return True
            if _contains_secret_like(v):
                return True
    elif isinstance(value, list):
        for item in value:
            if _contains_secret_like(item):
                return True
    return False


def check_no_production_secrets(candidate: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Ensure candidate (and optional eval payload) do not contain production secrets.
    Returns (passed, list of failure messages).
    """
    failures = []
    if _contains_secret_like(candidate):
        failures.append("Candidate or linked payload contains secret-like keys or values")
    return (len(failures) == 0, failures)


def check_signed_artifact(candidate: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Require signed artifact if PLASTICITY_REQUIRE_SIGNED_ARTIFACT=1.
    Returns (passed, list of failure messages).
    """
    if os.getenv("PLASTICITY_REQUIRE_SIGNED_ARTIFACT", "").strip() not in ("1", "true", "yes"):
        return (True, [])
    failures = []
    if not candidate.get("artifact_signature"):
        failures.append("artifact_signature required but missing")
    if not candidate.get("artifact_checksum"):
        failures.append("artifact_checksum required but missing")
    return (len(failures) == 0, failures)


def check_approval_tier(candidate: Dict[str, Any], min_tier: int = 1) -> tuple[bool, List[str]]:
    """
    Require approval tier >= min_tier (1 = sandbox, 2 = canary, 3 = production).
    No direct promotion authority: plasticity only suggests; human or policy approves.
    """
    failures = []
    tier = candidate.get("approval_tier")
    if tier is None:
        tier = 1
    if tier < min_tier:
        failures.append(f"approval_tier {tier} < min_tier {min_tier}")
    return (len(failures) == 0, failures)


def run_sandbox_check(
    candidate: Dict[str, Any],
    require_signed: Optional[bool] = None,
    min_approval_tier: int = 1,
) -> SandboxCheckResult:
    """
    Run full sandbox check: no prod secrets, optional signed artifact, approval tier.
    Used before promote when PLASTICITY_SANDBOX_CHECK=1.
    """
    checks = []
    failures = []

    ok, msgs = check_no_production_secrets(candidate)
    checks.append("no_production_secrets")
    if not ok:
        failures.extend(msgs)

    require_signed = require_signed if require_signed is not None else (
        os.getenv("PLASTICITY_REQUIRE_SIGNED_ARTIFACT", "").strip() in ("1", "true", "yes")
    )
    if require_signed:
        ok, msgs = check_signed_artifact(candidate)
        checks.append("signed_artifact")
        if not ok:
            failures.extend(msgs)

    ok, msgs = check_approval_tier(candidate, min_tier=min_approval_tier)
    checks.append("approval_tier")
    if not ok:
        failures.extend(msgs)

    return SandboxCheckResult(
        passed=len(failures) == 0,
        checks=checks,
        failures=failures,
    )


def sandbox_check_required() -> bool:
    """True if promote path should run sandbox check (env PLASTICITY_SANDBOX_CHECK=1)."""
    return os.getenv("PLASTICITY_SANDBOX_CHECK", "").strip() in ("1", "true", "yes")
