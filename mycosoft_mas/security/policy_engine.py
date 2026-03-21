"""
Policy Engine for Agent Event Bus - February 9, 2026

Validates AgentEvent before execution. Tool whitelist per agent,
classification enforcement, rate limiting. Feature flag: MYCA_POLICY_ENGINE_ENABLED.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, Optional, Set

logger = logging.getLogger(__name__)

MYCA_POLICY_ENGINE_ENABLED = os.getenv("MYCA_POLICY_ENGINE_ENABLED", "false").lower() in (
    "1",
    "true",
    "yes",
)

ALLOWED_CLASSIFICATIONS: FrozenSet[str] = frozenset({"UNCLASS", "CUI", "ITAR"})
DEFAULT_TOOLS_ALLOWED: FrozenSet[str] = frozenset()
RATE_LIMIT_EVENTS_PER_MINUTE = 60
RATE_LIMIT_WINDOW = timedelta(minutes=1)


class PolicyResult:
    """Result of policy validation."""

    def __init__(self, allowed: bool, reason: str = "", details: Optional[Dict[str, Any]] = None):
        self.allowed = allowed
        self.reason = reason
        self.details = details or {}


def _load_tool_whitelist(agent_id: str) -> Set[str]:
    """Load tool whitelist from skill permissions JSON if available."""
    try:
        base = Path(__file__).resolve().parent.parent
        perms_dir = base / "myca" / "skill_permissions"
        if not perms_dir.exists():
            return set(DEFAULT_TOOLS_ALLOWED)
        tools: Set[str] = set()
        for p in perms_dir.rglob("PERMISSIONS.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                allow = data.get("tools", {}).get("allow", [])
                tools.update(allow)
            except Exception as e:
                logger.debug("Could not load %s: %s", p, e)
        return tools if tools else set(DEFAULT_TOOLS_ALLOWED)
    except Exception as e:
        logger.debug("Tool whitelist load failed: %s", e)
        return set(DEFAULT_TOOLS_ALLOWED)


class PolicyEngine:
    """Validates agent events against policy rules."""

    def __init__(
        self,
        rate_limit_per_minute: int = RATE_LIMIT_EVENTS_PER_MINUTE,
        enabled: bool = True,
    ):
        self.rate_limit_per_minute = rate_limit_per_minute
        env_enabled = os.getenv("MYCA_POLICY_ENGINE_ENABLED", "false").lower() in (
            "1",
            "true",
            "yes",
        )
        self.enabled = enabled and env_enabled
        self._event_counts: Dict[str, list] = defaultdict(list)
        self._tool_whitelists: Dict[str, Set[str]] = {}

    def _get_tool_whitelist(self, agent_id: str) -> Set[str]:
        if agent_id not in self._tool_whitelists:
            self._tool_whitelists[agent_id] = _load_tool_whitelist(agent_id)
        return self._tool_whitelists[agent_id]

    def _check_rate_limit(self, agent_id: str) -> bool:
        now = datetime.now(timezone.utc)
        cutoff = now - RATE_LIMIT_WINDOW
        self._event_counts[agent_id] = [t for t in self._event_counts[agent_id] if t > cutoff]
        if len(self._event_counts[agent_id]) >= self.rate_limit_per_minute:
            return False
        self._event_counts[agent_id].append(now)
        return True

    def validate_event(self, event: Any) -> PolicyResult:
        """
        Validate an AgentEvent against policy.
        Returns PolicyResult with allowed=True/False and reason.
        """
        if not self.enabled:
            return PolicyResult(allowed=True, reason="Policy engine disabled")

        try:

            def _safe_get(obj: Any, key: str, default: Any) -> Any:
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return getattr(obj, key, default)

            from_agent = _safe_get(event, "from_agent", "")
            event_type = _safe_get(event, "type", "")
            classification = _safe_get(event, "classification", "UNCLASS")
            payload = _safe_get(event, "payload", {}) or {}
            tool_name = payload.get("tool") or payload.get("tool_name")

            if classification not in ALLOWED_CLASSIFICATIONS:
                return PolicyResult(
                    allowed=False,
                    reason=f"Classification {classification} not allowed",
                    details={"classification": classification},
                )

            if not self._check_rate_limit(from_agent):
                return PolicyResult(
                    allowed=False,
                    reason="Rate limit exceeded",
                    details={"agent": from_agent},
                )

            if event_type == "tool_call" and tool_name:
                whitelist = self._get_tool_whitelist(from_agent)
                if whitelist and tool_name not in whitelist:
                    return PolicyResult(
                        allowed=False,
                        reason=f"Tool {tool_name} not in whitelist",
                        details={"tool": tool_name, "agent": from_agent},
                    )

            return PolicyResult(allowed=True, reason="ok")
        except Exception as e:
            logger.warning("Policy validation error: %s", e)
            return PolicyResult(allowed=False, reason=str(e))


_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get or create the global policy engine."""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine
