"""
Mycosoft MAS - Tool Actions Module

This module provides typed tool/action definitions and audit logging
for all agent operations. It supports:

- Typed action definitions with Pydantic models
- Action audit logging to PostgreSQL
- Approval gates for risky operations
- Action categorization and risk assessment

Usage:
    from mycosoft_mas.tool_actions import (
        ActionRegistry,
        ActionAuditLog,
        ApprovalGate,
        action,
    )
    
    # Register a typed action
    @action(category="external_write", risk_level="high")
    async def send_email(to: str, subject: str, body: str) -> dict:
        ...
    
    # Log an action
    await ActionAuditLog.log(
        action_name="send_email",
        inputs={"to": "user@example.com", "subject": "Hello"},
        agent_id="email_agent_1",
        correlation_id=correlation_id,
    )
"""

from mycosoft_mas.tool_actions.registry import (
    ActionRegistry,
    ActionDefinition,
    ActionCategory,
    RiskLevel,
    action,
)
from mycosoft_mas.tool_actions.audit import ActionAuditLog, AuditEntry
from mycosoft_mas.tool_actions.approval import ApprovalGate, ApprovalPolicy, ApprovalStatus
from mycosoft_mas.tool_actions.types import (
    ActionInput,
    ActionOutput,
    ActionResult,
    ActionError,
)

__all__ = [
    # Registry
    "ActionRegistry",
    "ActionDefinition",
    "ActionCategory",
    "RiskLevel",
    "action",
    # Audit
    "ActionAuditLog",
    "AuditEntry",
    # Approval
    "ApprovalGate",
    "ApprovalPolicy",
    "ApprovalStatus",
    # Types
    "ActionInput",
    "ActionOutput",
    "ActionResult",
    "ActionError",
]
