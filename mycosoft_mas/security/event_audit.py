"""
Event Audit for Agent Bus - February 9, 2026

Security event logging for blocked events, policy violations, and anomalies.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def audit_blocked_event(
    event: Any,
    reason: str,
    policy_details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log a blocked event for security audit.
    Called when policy engine rejects an event.
    """
    try:
        from_agent = getattr(event, "from_agent", None) or (event.get("from_agent") if isinstance(event, dict) else "unknown")
        to_agent = getattr(event, "to_agent", None) or (event.get("to_agent") if isinstance(event, dict) else "unknown")
        event_type = getattr(event, "type", None) or (event.get("type") if isinstance(event, dict) else "unknown")
        trace_id = getattr(event, "trace_id", None) or (event.get("trace_id") if isinstance(event, dict) else None)

        logger.warning(
            "event_audit_blocked from=%s to=%s type=%s reason=%s trace_id=%s details=%s",
            from_agent,
            to_agent,
            event_type,
            reason,
            trace_id,
            policy_details or {},
        )
    except Exception as e:
        logger.warning("Event audit log failed: %s", e)


def audit_policy_violation(
    agent_id: str,
    violation_type: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a policy violation for security audit."""
    logger.warning(
        "event_audit_violation agent=%s violation=%s details=%s",
        agent_id,
        violation_type,
        details or {},
    )
