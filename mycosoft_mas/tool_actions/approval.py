"""
Approval Gate Module

Provides approval gates for risky action execution.
Supports configurable policies and automatic approval for low-risk operations.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from mycosoft_mas.tool_actions.registry import ActionCategory, RiskLevel, get_registry
from mycosoft_mas.tool_actions.audit import ActionAuditLog, AuditEntry

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    EXPIRED = "expired"


@dataclass
class ApprovalPolicy:
    """
    Policy for determining when approval is required.
    
    Policies can match on action category, type, name patterns,
    or agent patterns. They specify whether approval is required
    and under what conditions auto-approval is allowed.
    """
    policy_name: str
    policy_description: str = ""
    
    # Matching criteria
    action_category: Optional[ActionCategory] = None
    action_type: Optional[str] = None
    action_name_pattern: Optional[str] = None
    agent_id_pattern: Optional[str] = None
    
    # Policy rules
    requires_approval: bool = True
    auto_approve_conditions: dict[str, Any] = field(default_factory=dict)
    
    # Approval workflow
    min_approvers: int = 1
    approval_timeout_minutes: int = 60
    escalation_after_minutes: Optional[int] = None
    escalation_to: Optional[str] = None
    
    # Risk classification
    risk_level: RiskLevel = RiskLevel.MEDIUM
    
    # Policy status
    is_active: bool = True
    priority: int = 100
    
    def matches(
        self,
        action_name: str,
        action_category: Optional[str] = None,
        action_type: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> bool:
        """Check if this policy matches the given action."""
        if not self.is_active:
            return False
        
        # Check category match
        if self.action_category:
            if action_category != self.action_category.value:
                return False
        
        # Check type match
        if self.action_type:
            if action_type != self.action_type:
                return False
        
        # Check name pattern match
        if self.action_name_pattern:
            if not re.match(self.action_name_pattern, action_name):
                return False
        
        # Check agent pattern match
        if self.agent_id_pattern and agent_id:
            if not re.match(self.agent_id_pattern, agent_id):
                return False
        
        return True


class ApprovalGate:
    """
    Approval gate for action execution.
    
    Checks whether actions require approval based on configured policies
    and the action's risk level. Supports automatic approval for low-risk
    operations when conditions are met.
    
    Usage:
        gate = ApprovalGate()
        
        # Check if approval is needed
        if await gate.requires_approval("send_email", category="email"):
            # Request approval
            entry = await gate.request_approval(
                action_name="send_email",
                inputs={"to": "user@example.com"},
                agent_id="email_agent",
            )
            
            # Wait for approval
            if await gate.wait_for_approval(entry.id, timeout=300):
                # Execute action
                ...
        else:
            # Execute directly
            ...
    """
    
    _instance: Optional["ApprovalGate"] = None
    
    def __new__(cls) -> "ApprovalGate":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._policies: list[ApprovalPolicy] = []
            self._load_default_policies()
            self._initialized = True
    
    def _load_default_policies(self) -> None:
        """Load default approval policies."""
        # Check environment variable
        approval_required = os.getenv("APPROVAL_REQUIRED", "false").lower() == "true"
        
        if not approval_required:
            # Add a policy that auto-approves everything
            self._policies.append(ApprovalPolicy(
                policy_name="auto_approve_all",
                policy_description="Auto-approve all actions when APPROVAL_REQUIRED=false",
                requires_approval=False,
                priority=0,
            ))
            return
        
        # Default policies when approval is enabled
        self._policies = [
            # External write operations require approval
            ApprovalPolicy(
                policy_name="external_write_approval",
                policy_description="Require approval for external write operations",
                action_category=ActionCategory.EXTERNAL_WRITE,
                requires_approval=True,
                risk_level=RiskLevel.HIGH,
                priority=100,
            ),
            
            # Financial operations require approval
            ApprovalPolicy(
                policy_name="financial_approval",
                policy_description="Require approval for financial operations",
                action_category=ActionCategory.FINANCIAL,
                requires_approval=True,
                risk_level=RiskLevel.CRITICAL,
                priority=90,
            ),
            
            ApprovalPolicy(
                policy_name="payment_approval",
                policy_description="Require approval for payment operations",
                action_category=ActionCategory.PAYMENT,
                requires_approval=True,
                risk_level=RiskLevel.CRITICAL,
                priority=90,
            ),
            
            # Data deletion requires approval
            ApprovalPolicy(
                policy_name="data_deletion_approval",
                policy_description="Require approval for data deletion",
                action_category=ActionCategory.DATA_DELETION,
                requires_approval=True,
                risk_level=RiskLevel.HIGH,
                priority=95,
            ),
            
            # System config requires approval
            ApprovalPolicy(
                policy_name="system_config_approval",
                policy_description="Require approval for system configuration changes",
                action_category=ActionCategory.SYSTEM_CONFIG,
                requires_approval=True,
                risk_level=RiskLevel.CRITICAL,
                priority=85,
            ),
            
            # Email requires approval
            ApprovalPolicy(
                policy_name="email_approval",
                policy_description="Require approval for email sending",
                action_category=ActionCategory.EMAIL,
                requires_approval=True,
                risk_level=RiskLevel.HIGH,
                priority=100,
            ),
            
            # Read operations auto-approved
            ApprovalPolicy(
                policy_name="read_auto_approve",
                policy_description="Auto-approve read operations",
                action_category=ActionCategory.READ,
                requires_approval=False,
                risk_level=RiskLevel.LOW,
                priority=200,
            ),
            
            # LLM calls auto-approved
            ApprovalPolicy(
                policy_name="llm_auto_approve",
                policy_description="Auto-approve LLM calls",
                action_category=ActionCategory.LLM_CALL,
                requires_approval=False,
                risk_level=RiskLevel.LOW,
                priority=200,
            ),
        ]
    
    def add_policy(self, policy: ApprovalPolicy) -> None:
        """Add a custom approval policy."""
        self._policies.append(policy)
        # Sort by priority (lower = higher priority)
        self._policies.sort(key=lambda p: p.priority)
    
    def remove_policy(self, policy_name: str) -> bool:
        """Remove a policy by name."""
        original_len = len(self._policies)
        self._policies = [p for p in self._policies if p.policy_name != policy_name]
        return len(self._policies) < original_len
    
    def get_matching_policy(
        self,
        action_name: str,
        action_category: Optional[str] = None,
        action_type: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Optional[ApprovalPolicy]:
        """Find the highest-priority matching policy."""
        for policy in self._policies:
            if policy.matches(action_name, action_category, action_type, agent_id):
                return policy
        return None
    
    async def requires_approval(
        self,
        action_name: str,
        action_category: Optional[str] = None,
        action_type: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> bool:
        """
        Check if an action requires approval.
        
        Args:
            action_name: Name of the action
            action_category: Category of the action
            action_type: Type of the action
            agent_id: ID of the executing agent
            
        Returns:
            True if approval is required
        """
        # Check registry for action-level setting
        registry = get_registry()
        action_def = registry.get(action_name)
        
        if action_def and action_def.requires_approval:
            return True
        
        # Check policies
        policy = self.get_matching_policy(
            action_name, action_category, action_type, agent_id
        )
        
        if policy:
            return policy.requires_approval
        
        # Default: check risk level from registry
        if action_def:
            return action_def.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        
        return False
    
    async def request_approval(
        self,
        action_name: str,
        inputs: dict[str, Any],
        agent_id: str,
        correlation_id: Optional[UUID] = None,
        action_category: Optional[str] = None,
        action_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEntry:
        """
        Request approval for an action.
        
        Creates an audit log entry with pending approval status.
        
        Args:
            action_name: Name of the action
            inputs: Action inputs (will be logged)
            agent_id: ID of the requesting agent
            correlation_id: Correlation ID for tracing
            action_category: Category of the action
            action_type: Type of the action
            metadata: Additional metadata
            
        Returns:
            AuditEntry with pending approval status
        """
        entry = await ActionAuditLog.log(
            action_name=action_name,
            action_type=action_type or "",
            action_category=action_category,
            inputs=inputs,
            agent_id=agent_id,
            correlation_id=correlation_id,
            status="pending",
            requires_approval=True,
            metadata=metadata,
        )
        
        logger.info(
            f"Approval requested for action '{action_name}' "
            f"(id={entry.id}, agent={agent_id})"
        )
        
        return entry
    
    async def approve(
        self,
        entry_id: UUID,
        approved_by: str,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Approve a pending action.
        
        Args:
            entry_id: ID of the audit entry
            approved_by: Who is approving
            notes: Optional approval notes
            
        Returns:
            True if approval succeeded
        """
        success = await ActionAuditLog.update(
            entry_id=entry_id,
            approval_status=ApprovalStatus.APPROVED.value,
            approved_by=approved_by,
            approval_notes=notes,
        )
        
        if success:
            logger.info(f"Action {entry_id} approved by {approved_by}")
        
        return success
    
    async def reject(
        self,
        entry_id: UUID,
        rejected_by: str,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Reject a pending action.
        
        Args:
            entry_id: ID of the audit entry
            rejected_by: Who is rejecting
            reason: Rejection reason
            
        Returns:
            True if rejection succeeded
        """
        success = await ActionAuditLog.update(
            entry_id=entry_id,
            status="rejected",
            approval_status=ApprovalStatus.REJECTED.value,
            approved_by=rejected_by,
            approval_notes=reason,
        )
        
        if success:
            logger.info(f"Action {entry_id} rejected by {rejected_by}: {reason}")
        
        return success
    
    async def auto_approve(
        self,
        entry_id: UUID,
        reason: str = "Automatic approval per policy",
    ) -> bool:
        """
        Automatically approve an action.
        
        Args:
            entry_id: ID of the audit entry
            reason: Reason for auto-approval
            
        Returns:
            True if auto-approval succeeded
        """
        success = await ActionAuditLog.update(
            entry_id=entry_id,
            approval_status=ApprovalStatus.AUTO_APPROVED.value,
            approved_by="system",
            approval_notes=reason,
        )
        
        if success:
            logger.debug(f"Action {entry_id} auto-approved: {reason}")
        
        return success
    
    async def check_approval_status(self, entry_id: UUID) -> Optional[ApprovalStatus]:
        """
        Check the approval status of an entry.
        
        Args:
            entry_id: ID of the audit entry
            
        Returns:
            Current ApprovalStatus or None if not found
        """
        entries = await ActionAuditLog.get_recent(limit=1)
        # This is a simplified implementation
        # In production, you'd query by ID
        return None
    
    async def wait_for_approval(
        self,
        entry_id: UUID,
        timeout: int = 300,
        poll_interval: int = 5,
    ) -> bool:
        """
        Wait for an action to be approved.
        
        Args:
            entry_id: ID of the audit entry
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            True if approved, False if rejected/expired
        """
        import asyncio
        
        start = datetime.now()
        timeout_delta = timedelta(seconds=timeout)
        
        while datetime.now() - start < timeout_delta:
            status = await self.check_approval_status(entry_id)
            
            if status == ApprovalStatus.APPROVED or status == ApprovalStatus.AUTO_APPROVED:
                return True
            
            if status == ApprovalStatus.REJECTED:
                return False
            
            await asyncio.sleep(poll_interval)
        
        # Timeout - mark as expired
        await ActionAuditLog.update(
            entry_id=entry_id,
            approval_status=ApprovalStatus.EXPIRED.value,
        )
        
        return False


# Global instance
def get_approval_gate() -> ApprovalGate:
    """Get the global approval gate instance."""
    return ApprovalGate()
