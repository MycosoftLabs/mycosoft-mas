"""
MAS v2 Agent Factory

Creates new agents from templates with validation and approval workflow.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import (
    AgentConfig,
    AgentCategory,
    AgentState,
    AgentMessage,
    MessageType,
)


logger = logging.getLogger("AgentFactory")


class AgentTemplate:
    """Template for creating new agents"""
    
    def __init__(
        self,
        template_id: str,
        agent_type: str,
        category: AgentCategory,
        display_name: str,
        description: str = "",
        cpu_limit: float = 1.0,
        memory_limit: int = 512,
        capabilities: List[str] = None,
        settings: Dict[str, Any] = None,
    ):
        self.template_id = template_id
        self.agent_type = agent_type
        self.category = category
        self.display_name = display_name
        self.description = description
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self.capabilities = capabilities or []
        self.settings = settings or {}


class AgentFactory:
    """
    Factory for creating new agents.
    
    Provides:
    - Template-based agent creation
    - Validation before creation
    - Approval workflow for certain agent types
    - Event logging
    """
    
    # Pre-defined templates
    TEMPLATES = {
        "infrastructure": AgentTemplate(
            template_id="infrastructure",
            agent_type="infrastructure",
            category=AgentCategory.INFRASTRUCTURE,
            display_name="Infrastructure Agent",
            description="Manages infrastructure components",
            cpu_limit=1.0,
            memory_limit=512,
            capabilities=["vm-management", "container-management"],
        ),
        "data": AgentTemplate(
            template_id="data",
            agent_type="data",
            category=AgentCategory.DATA,
            display_name="Data Agent",
            description="Handles data operations",
            cpu_limit=2.0,
            memory_limit=1024,
            capabilities=["etl", "query", "transform"],
        ),
        "security": AgentTemplate(
            template_id="security",
            agent_type="security",
            category=AgentCategory.SECURITY,
            display_name="Security Agent",
            description="Monitors security",
            cpu_limit=1.0,
            memory_limit=512,
            capabilities=["threat-detection", "audit"],
        ),
        "device": AgentTemplate(
            template_id="device",
            agent_type="device",
            category=AgentCategory.DEVICE,
            display_name="Device Agent",
            description="Manages IoT device",
            cpu_limit=0.5,
            memory_limit=256,
            capabilities=["telemetry", "control"],
        ),
        "integration": AgentTemplate(
            template_id="integration",
            agent_type="integration",
            category=AgentCategory.INTEGRATION,
            display_name="Integration Agent",
            description="Handles external integration",
            cpu_limit=1.0,
            memory_limit=512,
            capabilities=["api-calls", "webhooks"],
        ),
        "route-monitor": AgentTemplate(
            template_id="route-monitor",
            agent_type="route-monitor",
            category=AgentCategory.DATA,
            display_name="Route Monitor Agent",
            description="Monitors API route",
            cpu_limit=0.5,
            memory_limit=256,
            capabilities=["monitoring", "alerting"],
        ),
    }
    
    # Agent types that require explicit approval
    APPROVAL_REQUIRED = [
        AgentCategory.CORPORATE,
        AgentCategory.FINANCIAL,
    ]
    
    def __init__(self, orchestrator=None, message_broker=None):
        self.orchestrator = orchestrator
        self.message_broker = message_broker
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
        self.creation_log: List[Dict[str, Any]] = []
    
    def get_template(self, template_id: str) -> Optional[AgentTemplate]:
        """Get a template by ID"""
        return self.TEMPLATES.get(template_id)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List available templates"""
        return [
            {
                "template_id": t.template_id,
                "agent_type": t.agent_type,
                "category": t.category.value,
                "display_name": t.display_name,
                "description": t.description,
            }
            for t in self.TEMPLATES.values()
        ]
    
    async def create_agent(
        self,
        template: AgentTemplate,
        agent_id: Optional[str] = None,
        reason: str = "manual",
        auto_approved: bool = False,
        custom_settings: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentState]:
        """
        Create a new agent from template.
        
        Args:
            template: Agent template to use
            agent_id: Custom agent ID (auto-generated if not provided)
            reason: Reason for creation
            auto_approved: Skip approval workflow
            custom_settings: Override template settings
            
        Returns:
            AgentState if created, None if pending approval
        """
        agent_id = agent_id or f"{template.agent_type}-{str(uuid4())[:8]}"
        
        # Check if approval required
        if template.category in self.APPROVAL_REQUIRED and not auto_approved:
            approval_id = str(uuid4())
            self.pending_approvals[approval_id] = {
                "approval_id": approval_id,
                "template": template,
                "agent_id": agent_id,
                "reason": reason,
                "custom_settings": custom_settings,
                "requested_at": datetime.utcnow().isoformat(),
            }
            
            # Notify for approval
            await self._notify_approval_required(approval_id)
            
            logger.info(f"Agent creation pending approval: {agent_id} (approval: {approval_id})")
            return None
        
        # Create config
        config = AgentConfig(
            agent_id=agent_id,
            agent_type=template.agent_type,
            category=template.category,
            display_name=template.display_name,
            description=template.description,
            cpu_limit=template.cpu_limit,
            memory_limit=template.memory_limit,
            capabilities=template.capabilities,
            settings={**template.settings, **(custom_settings or {})},
        )
        
        # Spawn agent
        if self.orchestrator:
            state = await self.orchestrator.spawn_agent(config)
            
            # Log creation
            self._log_creation(agent_id, template, reason, "created")
            
            return state
        
        return None
    
    async def approve_creation(self, approval_id: str) -> Optional[AgentState]:
        """Approve a pending agent creation"""
        pending = self.pending_approvals.pop(approval_id, None)
        if not pending:
            logger.warning(f"Approval {approval_id} not found")
            return None
        
        return await self.create_agent(
            template=pending["template"],
            agent_id=pending["agent_id"],
            reason=pending["reason"],
            auto_approved=True,
            custom_settings=pending["custom_settings"],
        )
    
    async def reject_creation(self, approval_id: str, reason: str = "rejected"):
        """Reject a pending agent creation"""
        pending = self.pending_approvals.pop(approval_id, None)
        if pending:
            self._log_creation(pending["agent_id"], pending["template"], reason, "rejected")
            logger.info(f"Agent creation rejected: {pending['agent_id']}")
    
    def list_pending_approvals(self) -> List[Dict[str, Any]]:
        """List pending approval requests"""
        return [
            {
                "approval_id": p["approval_id"],
                "agent_id": p["agent_id"],
                "agent_type": p["template"].agent_type,
                "category": p["template"].category.value,
                "reason": p["reason"],
                "requested_at": p["requested_at"],
            }
            for p in self.pending_approvals.values()
        ]
    
    async def _notify_approval_required(self, approval_id: str):
        """Notify that approval is required"""
        if self.message_broker:
            pending = self.pending_approvals.get(approval_id)
            if pending:
                message = AgentMessage(
                    from_agent="agent-factory",
                    to_agent="orchestrator",
                    message_type=MessageType.EVENT,
                    payload={
                        "event": "approval_required",
                        "approval_id": approval_id,
                        "agent_id": pending["agent_id"],
                        "agent_type": pending["template"].agent_type,
                    },
                )
                await self.message_broker.publish("mas:events", message.to_json())
    
    def _log_creation(self, agent_id: str, template: AgentTemplate, reason: str, status: str):
        """Log agent creation event"""
        self.creation_log.append({
            "agent_id": agent_id,
            "agent_type": template.agent_type,
            "category": template.category.value,
            "reason": reason,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    def get_creation_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent creation log entries"""
        return self.creation_log[-limit:]
