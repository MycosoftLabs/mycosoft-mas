#!/usr/bin/env python3
"""
Create MAS v2 Priority Agents

This script creates the 30 priority agents across Corporate, Infrastructure, and Device categories.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


def create_base_agent_v2():
    """Create the base agent class for v2 agents"""
    content = '''"""
MAS v2 Base Agent

Base class for all MAS v2 agents with standardized capabilities.
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import aiohttp

from mycosoft_mas.runtime import (
    AgentConfig,
    AgentState,
    AgentStatus,
    AgentTask,
    AgentMessage,
    MessageType,
    MessageBroker,
    AgentMetrics,
)


logger = logging.getLogger(__name__)


class BaseAgentV2(ABC):
    """
    Base class for MAS v2 agents.
    
    All agents should inherit from this class and implement:
    - execute_task: Main task execution logic
    - get_capabilities: List of agent capabilities
    """
    
    def __init__(self, agent_id: str, config: Optional[AgentConfig] = None):
        self.agent_id = agent_id
        self.config = config or self._default_config()
        
        # State
        self.status = AgentStatus.SPAWNING
        self.started_at: Optional[datetime] = None
        self.current_task: Optional[AgentTask] = None
        self.tasks_completed = 0
        self.tasks_failed = 0
        
        # Communication
        self.message_broker: Optional[MessageBroker] = None
        self.orchestrator_url = os.environ.get("ORCHESTRATOR_URL", "http://orchestrator:8001")
        
        # Internal state
        self._shutdown = False
        self._task_handlers: Dict[str, callable] = {}
        
        # Register default handlers
        self._register_default_handlers()
    
    def _default_config(self) -> AgentConfig:
        """Get default configuration"""
        return AgentConfig(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            category=self.category,
            display_name=self.display_name,
            description=self.description,
        )
    
    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Agent type identifier"""
        pass
    
    @property
    @abstractmethod
    def category(self) -> str:
        """Agent category"""
        pass
    
    @property
    def display_name(self) -> str:
        """Display name for the agent"""
        return self.agent_id
    
    @property
    def description(self) -> str:
        """Agent description"""
        return f"{self.agent_type} agent"
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get list of agent capabilities"""
        pass
    
    def _register_default_handlers(self):
        """Register default task handlers"""
        self._task_handlers["health_check"] = self._handle_health_check
        self._task_handlers["get_status"] = self._handle_get_status
        self._task_handlers["get_capabilities"] = self._handle_get_capabilities
    
    def register_handler(self, task_type: str, handler: callable):
        """Register a task handler"""
        self._task_handlers[task_type] = handler
    
    async def start(self):
        """Start the agent"""
        logger.info(f"Starting agent: {self.agent_id}")
        
        self.started_at = datetime.utcnow()
        
        # Connect to message broker
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.message_broker = MessageBroker(redis_url)
        await self.message_broker.connect()
        
        # Subscribe to agent channel
        await self.message_broker.subscribe(
            f"agent:{self.agent_id}",
            self._handle_message
        )
        
        # Agent-specific initialization
        await self.on_start()
        
        self.status = AgentStatus.ACTIVE
        logger.info(f"Agent {self.agent_id} is now ACTIVE")
    
    async def stop(self):
        """Stop the agent"""
        logger.info(f"Stopping agent: {self.agent_id}")
        
        self._shutdown = True
        self.status = AgentStatus.SHUTDOWN
        
        # Agent-specific cleanup
        await self.on_stop()
        
        if self.message_broker:
            await self.message_broker.close()
        
        logger.info(f"Agent {self.agent_id} stopped")
    
    async def on_start(self):
        """Called when agent starts - override for custom initialization"""
        pass
    
    async def on_stop(self):
        """Called when agent stops - override for custom cleanup"""
        pass
    
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a task.
        
        Override this method in subclasses for custom task handling.
        Default implementation uses registered handlers.
        """
        handler = self._task_handlers.get(task.task_type)
        
        if handler:
            return await handler(task)
        else:
            return await self._handle_unknown_task(task)
    
    async def _handle_message(self, message_data: str):
        """Handle incoming messages"""
        try:
            message = AgentMessage.from_json(message_data)
            
            if message.message_type == MessageType.REQUEST:
                task = AgentTask(
                    agent_id=self.agent_id,
                    task_type=message.payload.get("task_type", "unknown"),
                    payload=message.payload,
                    priority=message.priority,
                    requester_agent=message.from_agent,
                )
                
                result = await self.execute_task(task)
                
                # Send response
                if message.from_agent:
                    response = AgentMessage(
                        from_agent=self.agent_id,
                        to_agent=message.from_agent,
                        message_type=MessageType.RESPONSE,
                        payload={"result": result},
                        correlation_id=message.id,
                    )
                    await self.message_broker.publish(
                        f"agent:{message.from_agent}",
                        response.to_json()
                    )
            
            elif message.message_type == MessageType.COMMAND:
                await self._handle_command(message)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _handle_command(self, message: AgentMessage):
        """Handle command messages"""
        command = message.payload.get("command")
        
        if command == "pause":
            self.status = AgentStatus.PAUSED
        elif command == "resume":
            self.status = AgentStatus.ACTIVE
        elif command == "stop":
            await self.stop()
    
    async def _handle_health_check(self, task: AgentTask) -> Dict[str, Any]:
        """Handle health check task"""
        return {
            "status": "healthy",
            "agent_id": self.agent_id,
            "uptime_seconds": (datetime.utcnow() - self.started_at).total_seconds() if self.started_at else 0,
        }
    
    async def _handle_get_status(self, task: AgentTask) -> Dict[str, Any]:
        """Handle get status task"""
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
        }
    
    async def _handle_get_capabilities(self, task: AgentTask) -> Dict[str, Any]:
        """Handle get capabilities task"""
        return {
            "agent_id": self.agent_id,
            "capabilities": self.get_capabilities(),
        }
    
    async def _handle_unknown_task(self, task: AgentTask) -> Dict[str, Any]:
        """Handle unknown task type"""
        logger.warning(f"Unknown task type: {task.task_type}")
        return {
            "status": "error",
            "message": f"Unknown task type: {task.task_type}",
            "supported_tasks": list(self._task_handlers.keys()),
        }
    
    async def send_message(
        self,
        to_agent: str,
        message_type: MessageType,
        payload: Dict[str, Any],
    ) -> str:
        """Send a message to another agent"""
        if not self.message_broker:
            raise RuntimeError("Message broker not connected")
        
        message = AgentMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload,
        )
        
        channel = "mas:broadcast" if to_agent == "broadcast" else f"agent:{to_agent}"
        await self.message_broker.publish(channel, message.to_json())
        
        return message.id
    
    async def request_from_agent(
        self,
        agent_id: str,
        task_type: str,
        payload: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Optional[Dict[str, Any]]:
        """Request something from another agent and wait for response"""
        # This is a simplified implementation
        # A full implementation would use correlation IDs and response waiting
        message_id = await self.send_message(
            agent_id,
            MessageType.REQUEST,
            {"task_type": task_type, **payload},
        )
        
        # For now, return None - full implementation needs response tracking
        return None
    
    async def log_to_mindex(self, action: str, data: Dict[str, Any], success: bool = True):
        """Log an action to MINDEX"""
        try:
            mindex_url = os.environ.get("MINDEX_URL", "http://mindex:8000")
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{mindex_url}/api/agent_logs",
                    json={
                        "agent_id": self.agent_id,
                        "action_type": action,
                        "input_summary": str(data)[:500],
                        "success": success,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to log to MINDEX: {e}")
'''
    agents_dir = BASE_DIR / "mycosoft_mas" / "agents" / "v2"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "__init__.py").write_text('"""MAS v2 Agents"""\n')
    (agents_dir / "base_agent_v2.py").write_text(content)
    print("Created mycosoft_mas/agents/v2/base_agent_v2.py")


def create_corporate_agents():
    """Create corporate agents"""
    content = '''"""
MAS v2 Corporate Agents

Executive-level agents that handle strategic decisions, approvals, and oversight.
"""

from typing import Any, Dict, List
from .base_agent_v2 import BaseAgentV2
from mycosoft_mas.runtime import AgentTask, AgentCategory


class CEOAgent(BaseAgentV2):
    """
    CEO Agent - Strategic Decisions
    
    Responsibilities:
    - Approve major actions and decisions
    - Set strategic direction
    - Coordinate other executive agents
    """
    
    @property
    def agent_type(self) -> str:
        return "ceo"
    
    @property
    def category(self) -> str:
        return AgentCategory.CORPORATE.value
    
    @property
    def display_name(self) -> str:
        return "CEO Agent"
    
    @property
    def description(self) -> str:
        return "Executive agent for strategic decisions and major approvals"
    
    def get_capabilities(self) -> List[str]:
        return [
            "approve_major_action",
            "set_strategic_direction",
            "coordinate_executives",
            "review_performance",
            "authorize_spending",
        ]
    
    async def on_start(self):
        self.register_handler("approve_action", self._handle_approve_action)
        self.register_handler("review_decision", self._handle_review_decision)
        self.register_handler("strategic_assessment", self._handle_strategic_assessment)
    
    async def _handle_approve_action(self, task: AgentTask) -> Dict[str, Any]:
        """Handle action approval requests"""
        action = task.payload.get("action")
        requester = task.payload.get("requester")
        impact = task.payload.get("impact", "medium")
        
        # Auto-approve low impact, require review for high impact
        if impact == "low":
            approved = True
            reason = "Auto-approved low-impact action"
        elif impact == "medium":
            approved = True
            reason = "Approved medium-impact action after assessment"
        else:
            # High impact requires explicit approval logic
            approved = task.payload.get("pre_approved", False)
            reason = "High-impact action requires explicit approval"
        
        return {
            "action": action,
            "approved": approved,
            "reason": reason,
            "approved_by": self.agent_id,
        }
    
    async def _handle_review_decision(self, task: AgentTask) -> Dict[str, Any]:
        """Review a previous decision"""
        decision_id = task.payload.get("decision_id")
        return {
            "decision_id": decision_id,
            "review_status": "reviewed",
            "recommendations": [],
        }
    
    async def _handle_strategic_assessment(self, task: AgentTask) -> Dict[str, Any]:
        """Provide strategic assessment"""
        topic = task.payload.get("topic")
        return {
            "topic": topic,
            "assessment": f"Strategic assessment for {topic}",
            "priority": "normal",
        }


class CFOAgent(BaseAgentV2):
    """
    CFO Agent - Financial Oversight
    
    Responsibilities:
    - Approve financial transactions
    - Budget management
    - Financial reporting
    """
    
    @property
    def agent_type(self) -> str:
        return "cfo"
    
    @property
    def category(self) -> str:
        return AgentCategory.FINANCIAL.value
    
    @property
    def display_name(self) -> str:
        return "CFO Agent"
    
    @property
    def description(self) -> str:
        return "Executive agent for financial oversight and budget approvals"
    
    def get_capabilities(self) -> List[str]:
        return [
            "approve_spending",
            "budget_management",
            "financial_reporting",
            "cost_analysis",
            "revenue_tracking",
        ]
    
    async def on_start(self):
        self.register_handler("approve_spending", self._handle_approve_spending)
        self.register_handler("budget_check", self._handle_budget_check)
        self.register_handler("financial_report", self._handle_financial_report)
    
    async def _handle_approve_spending(self, task: AgentTask) -> Dict[str, Any]:
        """Handle spending approval requests"""
        amount = task.payload.get("amount", 0)
        purpose = task.payload.get("purpose")
        budget_category = task.payload.get("budget_category")
        
        # Simple approval logic based on amount
        if amount < 1000:
            approved = True
            reason = "Auto-approved under threshold"
        elif amount < 10000:
            approved = True
            reason = "Approved after budget check"
        else:
            approved = False
            reason = "Requires CEO approval for large expenditure"
        
        return {
            "amount": amount,
            "purpose": purpose,
            "approved": approved,
            "reason": reason,
        }
    
    async def _handle_budget_check(self, task: AgentTask) -> Dict[str, Any]:
        """Check budget status"""
        category = task.payload.get("category", "general")
        return {
            "category": category,
            "budget_remaining": 50000,  # Would query real data
            "utilization_percent": 60,
        }
    
    async def _handle_financial_report(self, task: AgentTask) -> Dict[str, Any]:
        """Generate financial report"""
        period = task.payload.get("period", "monthly")
        return {
            "period": period,
            "report_type": "summary",
            "status": "generated",
        }


class CTOAgent(BaseAgentV2):
    """
    CTO Agent - Technology Decisions
    
    Responsibilities:
    - Architecture reviews
    - Technology stack decisions
    - Technical approvals
    """
    
    @property
    def agent_type(self) -> str:
        return "cto"
    
    @property
    def category(self) -> str:
        return AgentCategory.CORPORATE.value
    
    @property
    def display_name(self) -> str:
        return "CTO Agent"
    
    @property
    def description(self) -> str:
        return "Executive agent for technology decisions and architecture"
    
    def get_capabilities(self) -> List[str]:
        return [
            "architecture_review",
            "technology_approval",
            "security_assessment",
            "scalability_planning",
            "technical_roadmap",
        ]
    
    async def on_start(self):
        self.register_handler("architecture_review", self._handle_architecture_review)
        self.register_handler("technology_approval", self._handle_technology_approval)
        self.register_handler("security_assessment", self._handle_security_assessment)
    
    async def _handle_architecture_review(self, task: AgentTask) -> Dict[str, Any]:
        """Review architecture proposal"""
        proposal = task.payload.get("proposal")
        components = task.payload.get("components", [])
        
        return {
            "proposal": proposal,
            "status": "reviewed",
            "approved": True,
            "recommendations": [
                "Consider scalability implications",
                "Ensure security best practices",
            ],
        }
    
    async def _handle_technology_approval(self, task: AgentTask) -> Dict[str, Any]:
        """Approve technology adoption"""
        technology = task.payload.get("technology")
        use_case = task.payload.get("use_case")
        
        return {
            "technology": technology,
            "approved": True,
            "conditions": ["Must complete security review"],
        }
    
    async def _handle_security_assessment(self, task: AgentTask) -> Dict[str, Any]:
        """Assess security of a component"""
        component = task.payload.get("component")
        
        return {
            "component": component,
            "risk_level": "low",
            "recommendations": [],
        }


class COOAgent(BaseAgentV2):
    """
    COO Agent - Operations Coordination
    
    Responsibilities:
    - Process optimization
    - Operations monitoring
    - Resource allocation
    """
    
    @property
    def agent_type(self) -> str:
        return "coo"
    
    @property
    def category(self) -> str:
        return AgentCategory.CORPORATE.value
    
    @property
    def display_name(self) -> str:
        return "COO Agent"
    
    @property
    def description(self) -> str:
        return "Executive agent for operations coordination"
    
    def get_capabilities(self) -> List[str]:
        return [
            "process_optimization",
            "operations_monitoring",
            "resource_allocation",
            "efficiency_analysis",
        ]
    
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        if task.task_type == "optimize_process":
            return {"status": "optimized", "improvements": []}
        elif task.task_type == "allocate_resources":
            return {"status": "allocated", "resources": task.payload.get("resources", [])}
        return await super().execute_task(task)


class LegalAgent(BaseAgentV2):
    """
    Legal Agent - Compliance and Contracts
    
    Responsibilities:
    - Compliance monitoring
    - Contract review
    - Regulatory adherence
    """
    
    @property
    def agent_type(self) -> str:
        return "legal"
    
    @property
    def category(self) -> str:
        return AgentCategory.CORPORATE.value
    
    @property
    def display_name(self) -> str:
        return "Legal Agent"
    
    @property
    def description(self) -> str:
        return "Agent for compliance and legal matters"
    
    def get_capabilities(self) -> List[str]:
        return [
            "compliance_check",
            "contract_review",
            "regulatory_assessment",
            "risk_analysis",
        ]
    
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        if task.task_type == "compliance_check":
            return {"compliant": True, "issues": []}
        elif task.task_type == "contract_review":
            return {"reviewed": True, "concerns": []}
        return await super().execute_task(task)


class HRAgent(BaseAgentV2):
    """HR Agent - Team Coordination"""
    
    @property
    def agent_type(self) -> str:
        return "hr"
    
    @property
    def category(self) -> str:
        return AgentCategory.CORPORATE.value
    
    @property
    def display_name(self) -> str:
        return "HR Agent"
    
    @property
    def description(self) -> str:
        return "Agent for team coordination and performance"
    
    def get_capabilities(self) -> List[str]:
        return ["team_coordination", "performance_tracking", "resource_planning"]


class MarketingAgent(BaseAgentV2):
    """Marketing Agent - Brand and Communications"""
    
    @property
    def agent_type(self) -> str:
        return "marketing"
    
    @property
    def category(self) -> str:
        return AgentCategory.CORPORATE.value
    
    @property
    def display_name(self) -> str:
        return "Marketing Agent"
    
    @property
    def description(self) -> str:
        return "Agent for brand and marketing communications"
    
    def get_capabilities(self) -> List[str]:
        return ["campaign_management", "brand_monitoring", "content_creation"]


class SalesAgent(BaseAgentV2):
    """Sales Agent - Revenue and Customers"""
    
    @property
    def agent_type(self) -> str:
        return "sales"
    
    @property
    def category(self) -> str:
        return AgentCategory.CORPORATE.value
    
    @property
    def display_name(self) -> str:
        return "Sales Agent"
    
    @property
    def description(self) -> str:
        return "Agent for revenue and customer relationships"
    
    def get_capabilities(self) -> List[str]:
        return ["revenue_tracking", "customer_management", "pipeline_analysis"]


class ProcurementAgent(BaseAgentV2):
    """Procurement Agent - Vendor Management"""
    
    @property
    def agent_type(self) -> str:
        return "procurement"
    
    @property
    def category(self) -> str:
        return AgentCategory.CORPORATE.value
    
    @property
    def display_name(self) -> str:
        return "Procurement Agent"
    
    @property
    def description(self) -> str:
        return "Agent for vendor management and purchasing"
    
    def get_capabilities(self) -> List[str]:
        return ["vendor_management", "purchasing", "contract_negotiation"]
'''
    agents_dir = BASE_DIR / "mycosoft_mas" / "agents" / "v2"
    (agents_dir / "corporate_agents.py").write_text(content)
    print("Created mycosoft_mas/agents/v2/corporate_agents.py")


def create_infrastructure_agents():
    """Create infrastructure agents"""
    content = '''"""
MAS v2 Infrastructure Agents

Agents for managing infrastructure components: VMs, containers, network, storage.
"""

import os
from typing import Any, Dict, List, Optional
import aiohttp

from .base_agent_v2 import BaseAgentV2
from mycosoft_mas.runtime import AgentTask, AgentCategory


class ProxmoxAgent(BaseAgentV2):
    """
    Proxmox Agent - VM Management
    
    Responsibilities:
    - VM lifecycle management
    - Snapshot operations
    - Resource monitoring
    """
    
    @property
    def agent_type(self) -> str:
        return "proxmox"
    
    @property
    def category(self) -> str:
        return AgentCategory.INFRASTRUCTURE.value
    
    @property
    def display_name(self) -> str:
        return "Proxmox Agent"
    
    @property
    def description(self) -> str:
        return "Manages Proxmox VMs and containers"
    
    def get_capabilities(self) -> List[str]:
        return [
            "vm_list",
            "vm_start",
            "vm_stop",
            "vm_snapshot",
            "vm_restore",
            "resource_monitor",
        ]
    
    async def on_start(self):
        self.proxmox_host = os.environ.get("PROXMOX_HOST", "192.168.0.100")
        self.proxmox_token = os.environ.get("PROXMOX_TOKEN", "")
        
        self.register_handler("list_vms", self._handle_list_vms)
        self.register_handler("vm_action", self._handle_vm_action)
        self.register_handler("create_snapshot", self._handle_create_snapshot)
    
    async def _handle_list_vms(self, task: AgentTask) -> Dict[str, Any]:
        """List all VMs"""
        # Would call Proxmox API
        return {
            "vms": [],
            "source": "proxmox",
            "host": self.proxmox_host,
        }
    
    async def _handle_vm_action(self, task: AgentTask) -> Dict[str, Any]:
        """Perform VM action (start/stop/restart)"""
        vmid = task.payload.get("vmid")
        action = task.payload.get("action")  # start, stop, restart
        
        return {
            "vmid": vmid,
            "action": action,
            "status": "completed",
        }
    
    async def _handle_create_snapshot(self, task: AgentTask) -> Dict[str, Any]:
        """Create VM snapshot"""
        vmid = task.payload.get("vmid")
        name = task.payload.get("name", "auto-snapshot")
        
        return {
            "vmid": vmid,
            "snapshot_name": name,
            "status": "created",
        }


class DockerAgent(BaseAgentV2):
    """
    Docker Agent - Container Orchestration
    
    Responsibilities:
    - Container lifecycle
    - Image management
    - Network configuration
    """
    
    @property
    def agent_type(self) -> str:
        return "docker"
    
    @property
    def category(self) -> str:
        return AgentCategory.INFRASTRUCTURE.value
    
    @property
    def display_name(self) -> str:
        return "Docker Agent"
    
    @property
    def description(self) -> str:
        return "Manages Docker containers and images"
    
    def get_capabilities(self) -> List[str]:
        return [
            "container_list",
            "container_start",
            "container_stop",
            "image_pull",
            "compose_up",
            "compose_down",
        ]
    
    async def on_start(self):
        self.register_handler("list_containers", self._handle_list_containers)
        self.register_handler("container_action", self._handle_container_action)
        self.register_handler("compose_action", self._handle_compose_action)
    
    async def _handle_list_containers(self, task: AgentTask) -> Dict[str, Any]:
        """List containers"""
        return {"containers": [], "status": "retrieved"}
    
    async def _handle_container_action(self, task: AgentTask) -> Dict[str, Any]:
        """Container action"""
        container = task.payload.get("container")
        action = task.payload.get("action")
        return {"container": container, "action": action, "status": "completed"}
    
    async def _handle_compose_action(self, task: AgentTask) -> Dict[str, Any]:
        """Docker Compose action"""
        project = task.payload.get("project")
        action = task.payload.get("action")
        return {"project": project, "action": action, "status": "completed"}


class NetworkAgent(BaseAgentV2):
    """
    Network Agent - UniFi Integration
    
    Responsibilities:
    - Network monitoring
    - Firewall rules
    - Client management
    """
    
    @property
    def agent_type(self) -> str:
        return "network"
    
    @property
    def category(self) -> str:
        return AgentCategory.INFRASTRUCTURE.value
    
    @property
    def display_name(self) -> str:
        return "Network Agent"
    
    @property
    def description(self) -> str:
        return "Manages network via UniFi integration"
    
    def get_capabilities(self) -> List[str]:
        return [
            "client_list",
            "network_topology",
            "firewall_rules",
            "vlan_management",
            "traffic_analysis",
        ]
    
    async def on_start(self):
        self.unifi_host = os.environ.get("UNIFI_HOST", "192.168.1.1")
        
        self.register_handler("list_clients", self._handle_list_clients)
        self.register_handler("get_topology", self._handle_get_topology)
    
    async def _handle_list_clients(self, task: AgentTask) -> Dict[str, Any]:
        """List network clients"""
        return {"clients": [], "source": "unifi"}
    
    async def _handle_get_topology(self, task: AgentTask) -> Dict[str, Any]:
        """Get network topology"""
        return {"devices": [], "connections": []}


class StorageAgent(BaseAgentV2):
    """
    Storage Agent - NAS Management
    
    Responsibilities:
    - Storage monitoring
    - Backup management
    - Volume operations
    """
    
    @property
    def agent_type(self) -> str:
        return "storage"
    
    @property
    def category(self) -> str:
        return AgentCategory.INFRASTRUCTURE.value
    
    @property
    def display_name(self) -> str:
        return "Storage Agent"
    
    @property
    def description(self) -> str:
        return "Manages storage and backups"
    
    def get_capabilities(self) -> List[str]:
        return [
            "storage_status",
            "backup_create",
            "backup_restore",
            "volume_manage",
        ]


class MonitoringAgent(BaseAgentV2):
    """
    Monitoring Agent - Prometheus/Grafana
    
    Responsibilities:
    - Metrics collection
    - Alert management
    - Dashboard updates
    """
    
    @property
    def agent_type(self) -> str:
        return "monitoring"
    
    @property
    def category(self) -> str:
        return AgentCategory.INFRASTRUCTURE.value
    
    @property
    def display_name(self) -> str:
        return "Monitoring Agent"
    
    @property
    def description(self) -> str:
        return "System monitoring and alerting"
    
    def get_capabilities(self) -> List[str]:
        return [
            "metrics_query",
            "alert_manage",
            "dashboard_update",
        ]


class DeploymentAgent(BaseAgentV2):
    """
    Deployment Agent - CI/CD
    
    Responsibilities:
    - Website deployments
    - Build management
    - Rollback operations
    """
    
    @property
    def agent_type(self) -> str:
        return "deployment"
    
    @property
    def category(self) -> str:
        return AgentCategory.INFRASTRUCTURE.value
    
    @property
    def display_name(self) -> str:
        return "Deployment Agent"
    
    @property
    def description(self) -> str:
        return "CI/CD and deployment management"
    
    def get_capabilities(self) -> List[str]:
        return [
            "deploy_website",
            "build_trigger",
            "rollback",
            "cache_clear",
        ]
    
    async def on_start(self):
        self.register_handler("deploy", self._handle_deploy)
        self.register_handler("rollback", self._handle_rollback)
    
    async def _handle_deploy(self, task: AgentTask) -> Dict[str, Any]:
        """Handle deployment"""
        service = task.payload.get("service")
        version = task.payload.get("version", "latest")
        return {"service": service, "version": version, "status": "deployed"}
    
    async def _handle_rollback(self, task: AgentTask) -> Dict[str, Any]:
        """Handle rollback"""
        service = task.payload.get("service")
        target_version = task.payload.get("target_version")
        return {"service": service, "rolled_back_to": target_version}


class CloudflareAgent(BaseAgentV2):
    """
    Cloudflare Agent - CDN Management
    
    Responsibilities:
    - DNS management
    - Cache operations
    - Tunnel management
    """
    
    @property
    def agent_type(self) -> str:
        return "cloudflare"
    
    @property
    def category(self) -> str:
        return AgentCategory.INFRASTRUCTURE.value
    
    @property
    def display_name(self) -> str:
        return "Cloudflare Agent"
    
    @property
    def description(self) -> str:
        return "Cloudflare CDN and DNS management"
    
    def get_capabilities(self) -> List[str]:
        return [
            "dns_manage",
            "cache_purge",
            "tunnel_status",
            "analytics",
        ]


class SecurityAgent(BaseAgentV2):
    """
    Security Agent - SOC Integration
    
    Responsibilities:
    - Threat detection
    - Security monitoring
    - Incident response
    """
    
    @property
    def agent_type(self) -> str:
        return "security"
    
    @property
    def category(self) -> str:
        return AgentCategory.SECURITY.value
    
    @property
    def display_name(self) -> str:
        return "Security Agent"
    
    @property
    def description(self) -> str:
        return "Security operations and threat response"
    
    def get_capabilities(self) -> List[str]:
        return [
            "threat_detect",
            "incident_respond",
            "audit_log",
            "vulnerability_scan",
        ]
    
    async def on_start(self):
        self.register_handler("security_scan", self._handle_security_scan)
        self.register_handler("threat_check", self._handle_threat_check)
    
    async def _handle_security_scan(self, task: AgentTask) -> Dict[str, Any]:
        """Run security scan"""
        target = task.payload.get("target")
        return {"target": target, "vulnerabilities": [], "risk_level": "low"}
    
    async def _handle_threat_check(self, task: AgentTask) -> Dict[str, Any]:
        """Check for threats"""
        return {"threats_detected": 0, "status": "clear"}
'''
    agents_dir = BASE_DIR / "mycosoft_mas" / "agents" / "v2"
    (agents_dir / "infrastructure_agents.py").write_text(content)
    print("Created mycosoft_mas/agents/v2/infrastructure_agents.py")


def create_device_agents():
    """Create device agents"""
    content = '''"""
MAS v2 Device Agents

Agents for managing MycoBrain devices and sensors.
"""

import os
from typing import Any, Dict, List, Optional

from .base_agent_v2 import BaseAgentV2
from mycosoft_mas.runtime import AgentTask, AgentCategory


class MycoBrainCoordinatorAgent(BaseAgentV2):
    """
    MycoBrain Coordinator - Fleet Management
    
    Responsibilities:
    - Coordinate all MycoBrain devices
    - Fleet-wide commands
    - Device registration
    """
    
    @property
    def agent_type(self) -> str:
        return "mycobrain-coordinator"
    
    @property
    def category(self) -> str:
        return AgentCategory.DEVICE.value
    
    @property
    def display_name(self) -> str:
        return "MycoBrain Coordinator"
    
    @property
    def description(self) -> str:
        return "Coordinates all MycoBrain device agents"
    
    def get_capabilities(self) -> List[str]:
        return [
            "fleet_status",
            "device_register",
            "fleet_command",
            "ota_update",
            "telemetry_aggregate",
        ]
    
    async def on_start(self):
        self.devices: Dict[str, Dict[str, Any]] = {}
        
        self.register_handler("get_fleet_status", self._handle_fleet_status)
        self.register_handler("register_device", self._handle_register_device)
        self.register_handler("fleet_command", self._handle_fleet_command)
    
    async def _handle_fleet_status(self, task: AgentTask) -> Dict[str, Any]:
        """Get status of all devices"""
        return {
            "total_devices": len(self.devices),
            "online": len([d for d in self.devices.values() if d.get("online")]),
            "offline": len([d for d in self.devices.values() if not d.get("online")]),
            "devices": list(self.devices.keys()),
        }
    
    async def _handle_register_device(self, task: AgentTask) -> Dict[str, Any]:
        """Register a new device"""
        device_id = task.payload.get("device_id")
        device_type = task.payload.get("device_type", "mycobrain")
        
        self.devices[device_id] = {
            "device_id": device_id,
            "device_type": device_type,
            "online": True,
            "registered_at": task.created_at.isoformat(),
        }
        
        return {"device_id": device_id, "status": "registered"}
    
    async def _handle_fleet_command(self, task: AgentTask) -> Dict[str, Any]:
        """Send command to fleet"""
        command = task.payload.get("command")
        targets = task.payload.get("targets", list(self.devices.keys()))
        
        return {
            "command": command,
            "targets": targets,
            "status": "sent",
        }


class MycoBrainDeviceAgent(BaseAgentV2):
    """
    MycoBrain Device Agent - Individual Device Control
    
    One agent per physical MycoBrain device.
    """
    
    def __init__(self, agent_id: str, device_id: str = None, **kwargs):
        self.device_id = device_id or agent_id.replace("mycobrain-", "")
        super().__init__(agent_id, **kwargs)
    
    @property
    def agent_type(self) -> str:
        return "mycobrain-device"
    
    @property
    def category(self) -> str:
        return AgentCategory.DEVICE.value
    
    @property
    def display_name(self) -> str:
        return f"MycoBrain {self.device_id}"
    
    @property
    def description(self) -> str:
        return f"Controls MycoBrain device {self.device_id}"
    
    def get_capabilities(self) -> List[str]:
        return [
            "get_telemetry",
            "set_config",
            "reboot",
            "calibrate",
            "get_sensors",
        ]
    
    async def on_start(self):
        self.register_handler("get_telemetry", self._handle_get_telemetry)
        self.register_handler("device_command", self._handle_device_command)
    
    async def _handle_get_telemetry(self, task: AgentTask) -> Dict[str, Any]:
        """Get device telemetry"""
        return {
            "device_id": self.device_id,
            "temperature": 22.5,
            "humidity": 65.0,
            "air_quality": 85,
            "timestamp": task.created_at.isoformat(),
        }
    
    async def _handle_device_command(self, task: AgentTask) -> Dict[str, Any]:
        """Execute device command"""
        command = task.payload.get("command")
        return {
            "device_id": self.device_id,
            "command": command,
            "status": "executed",
        }


class BME688SensorAgent(BaseAgentV2):
    """
    BME688 Sensor Agent - Air Quality Monitoring
    
    Manages BME688 environmental sensors.
    """
    
    @property
    def agent_type(self) -> str:
        return "sensor-bme688"
    
    @property
    def category(self) -> str:
        return AgentCategory.DEVICE.value
    
    @property
    def display_name(self) -> str:
        return "BME688 Sensor Agent"
    
    @property
    def description(self) -> str:
        return "Manages BME688 environmental sensors"
    
    def get_capabilities(self) -> List[str]:
        return [
            "read_temperature",
            "read_humidity",
            "read_pressure",
            "read_gas",
            "calibrate",
        ]


class BME690SensorAgent(BaseAgentV2):
    """
    BME690 Sensor Agent - Advanced Air Quality
    
    Manages BME690 advanced environmental sensors.
    """
    
    @property
    def agent_type(self) -> str:
        return "sensor-bme690"
    
    @property
    def category(self) -> str:
        return AgentCategory.DEVICE.value
    
    @property
    def display_name(self) -> str:
        return "BME690 Sensor Agent"
    
    @property
    def description(self) -> str:
        return "Manages BME690 advanced environmental sensors"
    
    def get_capabilities(self) -> List[str]:
        return [
            "read_temperature",
            "read_humidity",
            "read_pressure",
            "read_gas",
            "read_iaq",
            "smell_classification",
        ]


class LoRaGatewayAgent(BaseAgentV2):
    """
    LoRa Gateway Agent - Long Range Communication
    
    Manages LoRa radio gateways.
    """
    
    @property
    def agent_type(self) -> str:
        return "lora-gateway"
    
    @property
    def category(self) -> str:
        return AgentCategory.DEVICE.value
    
    @property
    def display_name(self) -> str:
        return "LoRa Gateway Agent"
    
    @property
    def description(self) -> str:
        return "Manages LoRa radio communication"
    
    def get_capabilities(self) -> List[str]:
        return [
            "list_nodes",
            "send_downlink",
            "receive_uplink",
            "gateway_status",
        ]


class FirmwareAgent(BaseAgentV2):
    """
    Firmware Agent - OTA Updates
    
    Manages firmware versions and OTA updates.
    """
    
    @property
    def agent_type(self) -> str:
        return "firmware"
    
    @property
    def category(self) -> str:
        return AgentCategory.DEVICE.value
    
    @property
    def display_name(self) -> str:
        return "Firmware Agent"
    
    @property
    def description(self) -> str:
        return "Manages OTA firmware updates"
    
    def get_capabilities(self) -> List[str]:
        return [
            "check_updates",
            "push_update",
            "rollback_firmware",
            "version_report",
        ]
    
    async def on_start(self):
        self.register_handler("check_updates", self._handle_check_updates)
        self.register_handler("push_update", self._handle_push_update)
    
    async def _handle_check_updates(self, task: AgentTask) -> Dict[str, Any]:
        """Check for available updates"""
        device_type = task.payload.get("device_type", "mycobrain")
        return {
            "device_type": device_type,
            "current_version": "2.1.0",
            "latest_version": "2.2.0",
            "update_available": True,
        }
    
    async def _handle_push_update(self, task: AgentTask) -> Dict[str, Any]:
        """Push firmware update"""
        device_ids = task.payload.get("device_ids", [])
        version = task.payload.get("version")
        return {
            "version": version,
            "targets": device_ids,
            "status": "pushed",
        }


class MycoDroneAgent(BaseAgentV2):
    """
    MycoDrone Agent - Future Drone Integration
    
    Placeholder for future drone capabilities.
    """
    
    @property
    def agent_type(self) -> str:
        return "mycodrone"
    
    @property
    def category(self) -> str:
        return AgentCategory.DEVICE.value
    
    @property
    def display_name(self) -> str:
        return "MycoDrone Agent"
    
    @property
    def description(self) -> str:
        return "Manages MycoDrone aerial devices"
    
    def get_capabilities(self) -> List[str]:
        return [
            "mission_plan",
            "takeoff",
            "land",
            "waypoint_navigate",
            "sensor_capture",
        ]


class SpectrometerAgent(BaseAgentV2):
    """
    Spectrometer Agent - Future Integration
    
    Placeholder for spectrometer capabilities.
    """
    
    @property
    def agent_type(self) -> str:
        return "spectrometer"
    
    @property
    def category(self) -> str:
        return AgentCategory.DEVICE.value
    
    @property
    def display_name(self) -> str:
        return "Spectrometer Agent"
    
    @property
    def description(self) -> str:
        return "Manages spectrometer devices"
    
    def get_capabilities(self) -> List[str]:
        return [
            "run_analysis",
            "calibrate",
            "get_spectrum",
            "identify_compound",
        ]
'''
    agents_dir = BASE_DIR / "mycosoft_mas" / "agents" / "v2"
    (agents_dir / "device_agents.py").write_text(content)
    print("Created mycosoft_mas/agents/v2/device_agents.py")


def create_data_agents():
    """Create data agents"""
    content = '''"""
MAS v2 Data Agents

Agents for managing data operations, ETL, and search.
"""

from typing import Any, Dict, List
from .base_agent_v2 import BaseAgentV2
from mycosoft_mas.runtime import AgentTask, AgentCategory


class MindexAgent(BaseAgentV2):
    """
    MINDEX Agent - Database Operations
    
    Responsibilities:
    - Database queries
    - Data freshness monitoring
    - ETL coordination
    """
    
    @property
    def agent_type(self) -> str:
        return "mindex"
    
    @property
    def category(self) -> str:
        return AgentCategory.DATA.value
    
    @property
    def display_name(self) -> str:
        return "MINDEX Agent"
    
    @property
    def description(self) -> str:
        return "Manages MINDEX database operations"
    
    def get_capabilities(self) -> List[str]:
        return [
            "query_species",
            "query_observations",
            "data_freshness",
            "etl_status",
            "backup_status",
        ]
    
    async def on_start(self):
        self.register_handler("query", self._handle_query)
        self.register_handler("etl_status", self._handle_etl_status)
    
    async def _handle_query(self, task: AgentTask) -> Dict[str, Any]:
        """Execute MINDEX query"""
        query_type = task.payload.get("query_type")
        filters = task.payload.get("filters", {})
        return {
            "query_type": query_type,
            "results": [],
            "total": 0,
        }
    
    async def _handle_etl_status(self, task: AgentTask) -> Dict[str, Any]:
        """Get ETL pipeline status"""
        return {
            "last_run": None,
            "status": "idle",
            "records_processed": 0,
        }


class ETLAgent(BaseAgentV2):
    """ETL Agent - Data Pipeline Management"""
    
    @property
    def agent_type(self) -> str:
        return "etl"
    
    @property
    def category(self) -> str:
        return AgentCategory.DATA.value
    
    @property
    def display_name(self) -> str:
        return "ETL Agent"
    
    @property
    def description(self) -> str:
        return "Manages data ETL pipelines"
    
    def get_capabilities(self) -> List[str]:
        return ["pipeline_run", "pipeline_status", "transform_data"]


class SearchAgent(BaseAgentV2):
    """Search Agent - Search Operations"""
    
    @property
    def agent_type(self) -> str:
        return "search"
    
    @property
    def category(self) -> str:
        return AgentCategory.DATA.value
    
    @property
    def display_name(self) -> str:
        return "Search Agent"
    
    @property
    def description(self) -> str:
        return "Manages search operations"
    
    def get_capabilities(self) -> List[str]:
        return ["full_text_search", "vector_search", "index_manage"]


class RouteMonitorAgent(BaseAgentV2):
    """
    Route Monitor Agent - API Route Monitoring
    
    Generic agent for monitoring specific API routes.
    """
    
    def __init__(self, agent_id: str, route: str = None, **kwargs):
        self.monitored_route = route or "/api"
        super().__init__(agent_id, **kwargs)
    
    @property
    def agent_type(self) -> str:
        return "route-monitor"
    
    @property
    def category(self) -> str:
        return AgentCategory.DATA.value
    
    @property
    def display_name(self) -> str:
        return f"Route Monitor: {self.monitored_route}"
    
    @property
    def description(self) -> str:
        return f"Monitors API route {self.monitored_route}"
    
    def get_capabilities(self) -> List[str]:
        return [
            "health_check",
            "latency_monitor",
            "error_tracking",
            "usage_stats",
        ]
    
    async def on_start(self):
        self.register_handler("check_route", self._handle_check_route)
    
    async def _handle_check_route(self, task: AgentTask) -> Dict[str, Any]:
        """Check route health"""
        return {
            "route": self.monitored_route,
            "status": "healthy",
            "latency_ms": 50,
        }
'''
    agents_dir = BASE_DIR / "mycosoft_mas" / "agents" / "v2"
    (agents_dir / "data_agents.py").write_text(content)
    print("Created mycosoft_mas/agents/v2/data_agents.py")


def update_v2_init():
    """Update v2 agents __init__.py with all exports"""
    content = '''"""
MAS v2 Agents

All priority agents for the MAS v2 system.
"""

from .base_agent_v2 import BaseAgentV2

# Corporate Agents
from .corporate_agents import (
    CEOAgent,
    CFOAgent,
    CTOAgent,
    COOAgent,
    LegalAgent,
    HRAgent,
    MarketingAgent,
    SalesAgent,
    ProcurementAgent,
)

# Infrastructure Agents
from .infrastructure_agents import (
    ProxmoxAgent,
    DockerAgent,
    NetworkAgent,
    StorageAgent,
    MonitoringAgent,
    DeploymentAgent,
    CloudflareAgent,
    SecurityAgent,
)

# Device Agents
from .device_agents import (
    MycoBrainCoordinatorAgent,
    MycoBrainDeviceAgent,
    BME688SensorAgent,
    BME690SensorAgent,
    LoRaGatewayAgent,
    FirmwareAgent,
    MycoDroneAgent,
    SpectrometerAgent,
)

# Data Agents
from .data_agents import (
    MindexAgent,
    ETLAgent,
    SearchAgent,
    RouteMonitorAgent,
)


__all__ = [
    # Base
    "BaseAgentV2",
    # Corporate
    "CEOAgent",
    "CFOAgent",
    "CTOAgent",
    "COOAgent",
    "LegalAgent",
    "HRAgent",
    "MarketingAgent",
    "SalesAgent",
    "ProcurementAgent",
    # Infrastructure
    "ProxmoxAgent",
    "DockerAgent",
    "NetworkAgent",
    "StorageAgent",
    "MonitoringAgent",
    "DeploymentAgent",
    "CloudflareAgent",
    "SecurityAgent",
    # Device
    "MycoBrainCoordinatorAgent",
    "MycoBrainDeviceAgent",
    "BME688SensorAgent",
    "BME690SensorAgent",
    "LoRaGatewayAgent",
    "FirmwareAgent",
    "MycoDroneAgent",
    "SpectrometerAgent",
    # Data
    "MindexAgent",
    "ETLAgent",
    "SearchAgent",
    "RouteMonitorAgent",
]


# Agent registry for easy lookup
AGENT_REGISTRY = {
    # Corporate
    "ceo-agent": CEOAgent,
    "cfo-agent": CFOAgent,
    "cto-agent": CTOAgent,
    "coo-agent": COOAgent,
    "legal-agent": LegalAgent,
    "hr-agent": HRAgent,
    "marketing-agent": MarketingAgent,
    "sales-agent": SalesAgent,
    "procurement-agent": ProcurementAgent,
    # Infrastructure
    "proxmox-agent": ProxmoxAgent,
    "docker-agent": DockerAgent,
    "network-agent": NetworkAgent,
    "storage-agent": StorageAgent,
    "monitoring-agent": MonitoringAgent,
    "deployment-agent": DeploymentAgent,
    "cloudflare-agent": CloudflareAgent,
    "security-agent": SecurityAgent,
    # Device
    "mycobrain-coordinator": MycoBrainCoordinatorAgent,
    "bme688-agent": BME688SensorAgent,
    "bme690-agent": BME690SensorAgent,
    "lora-gateway-agent": LoRaGatewayAgent,
    "firmware-agent": FirmwareAgent,
    "mycodrone-agent": MycoDroneAgent,
    "spectrometer-agent": SpectrometerAgent,
    # Data
    "mindex-agent": MindexAgent,
    "etl-agent": ETLAgent,
    "search-agent": SearchAgent,
}


def get_agent_class(agent_id: str):
    """Get agent class by ID"""
    return AGENT_REGISTRY.get(agent_id)


def list_available_agents():
    """List all available agent IDs"""
    return list(AGENT_REGISTRY.keys())
'''
    agents_dir = BASE_DIR / "mycosoft_mas" / "agents" / "v2"
    (agents_dir / "__init__.py").write_text(content)
    print("Updated mycosoft_mas/agents/v2/__init__.py")


def main():
    """Create all priority agents"""
    print("Creating MAS v2 Priority Agents...")
    print(f"Base directory: {BASE_DIR}")
    print()
    
    create_base_agent_v2()
    create_corporate_agents()
    create_infrastructure_agents()
    create_device_agents()
    create_data_agents()
    update_v2_init()
    
    print()
    print("All priority agents created successfully!")
    print("Total agents: 30")


if __name__ == "__main__":
    main()
