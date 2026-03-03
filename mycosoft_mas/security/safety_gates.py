"""
3-Stage Safety Gates for MYCA

Checks actions for destructive potential and requires leadership
confirmation before executing high-risk operations.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SafetyResult:
    safe: bool
    requires_confirmation: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    reason: str = ""


@dataclass
class ConfirmationRequest:
    request_id: str
    action: str
    context: Dict[str, Any]
    approver_id: str
    created_at: float = field(default_factory=time.time)
    approved: Optional[bool] = None
    resolved_at: Optional[float] = None


DESTRUCTIVE_ACTIONS: Set[str] = {
    "delete", "modify", "bulk_update", "deploy", "restart",
    "drop_table", "truncate", "shutdown", "reboot",
    "rm", "rmdir", "format",
}

HIGH_RISK_PATTERNS = {
    "production", "main", "master", "live",
    "database", "credentials", "secrets",
}


class SafetyGates:
    """Enforce safety checks before destructive MYCA actions."""

    def __init__(self):
        self._pending_confirmations: Dict[str, ConfirmationRequest] = {}

    async def check_safety(
        self, action: str, context: Dict[str, Any],
    ) -> SafetyResult:
        """Evaluate action safety. Returns whether to proceed or require confirmation."""
        action_lower = action.lower()
        context_str = str(context).lower()

        if any(d in action_lower for d in DESTRUCTIVE_ACTIONS):
            if any(p in context_str for p in HIGH_RISK_PATTERNS):
                return SafetyResult(
                    safe=False,
                    requires_confirmation=True,
                    risk_level=RiskLevel.CRITICAL,
                    reason=f"Destructive action '{action}' targets high-risk resource",
                )
            return SafetyResult(
                safe=False,
                requires_confirmation=True,
                risk_level=RiskLevel.HIGH,
                reason=f"Destructive action '{action}' requires confirmation",
            )

        return SafetyResult(safe=True, risk_level=RiskLevel.LOW)

    async def request_confirmation(
        self,
        action: str,
        context: Dict[str, Any],
        approver_id: str,
    ) -> str:
        """Create a confirmation request and return its ID."""
        request_id = str(uuid.uuid4())
        self._pending_confirmations[request_id] = ConfirmationRequest(
            request_id=request_id,
            action=action,
            context=context,
            approver_id=approver_id,
        )
        logger.info(
            "Safety confirmation requested: %s (action=%s, approver=%s)",
            request_id, action, approver_id,
        )
        return request_id

    async def submit_confirmation(
        self, request_id: str, approved: bool,
    ) -> bool:
        req = self._pending_confirmations.get(request_id)
        if not req:
            return False
        req.approved = approved
        req.resolved_at = time.time()
        logger.info("Confirmation %s: %s", request_id, "approved" if approved else "denied")
        return True

    async def await_confirmation(
        self, request_id: str, timeout: int = 300,
    ) -> bool:
        """Wait for approval or denial. Returns True if approved."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            req = self._pending_confirmations.get(request_id)
            if req and req.approved is not None:
                self._pending_confirmations.pop(request_id, None)
                return req.approved
            await asyncio.sleep(2)
        self._pending_confirmations.pop(request_id, None)
        logger.warning("Confirmation %s timed out after %ds", request_id, timeout)
        return False

    def list_pending(self):
        return [
            {
                "request_id": r.request_id,
                "action": r.action,
                "approver": r.approver_id,
                "created_at": r.created_at,
            }
            for r in self._pending_confirmations.values()
            if r.approved is None
        ]
