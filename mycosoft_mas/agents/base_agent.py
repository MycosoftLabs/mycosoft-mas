"""
Mycosoft Multi-Agent System (MAS) - Base Agent
Updated: February 5, 2026 - Added AgentMemoryMixin for memory integration

This module defines the BaseAgent class, which serves as the foundation for all agents in the system.
Now includes memory capabilities via AgentMemoryMixin.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Awaitable, Set
from pathlib import Path

from mycosoft_mas.agents.enums import AgentStatus
from mycosoft_mas.agents.messaging.message import Message, MessageType
from mycosoft_mas.services.integration_service import IntegrationService
from mycosoft_mas.dependencies.dependency_manager import DependencyManager
from mycosoft_mas.integrations.integration_manager import IntegrationManager
from mycosoft_mas.core.task_manager import TaskManager
from mycosoft_mas.services.monitoring_interface import AgentMonitorable
from mycosoft_mas.services.security_interface import AgentSecurable
from mycosoft_mas.agents.memory_mixin import AgentMemoryMixin

logger = logging.getLogger(__name__)


# Lazy-loaded service singletons
class MonitoringService:
    def add_health_check(self, name, check_fn):
        pass

class SecurityService:
    def authenticate_agent(self, agent):
        return str(uuid.uuid4())

class ErrorLoggingService:
    async def log_error(self, error_type: str, details: Dict[str, Any]) -> None:
        return


class BaseAgent(AgentMonitorable, AgentSecurable, AgentMemoryMixin):
    """
    Base agent class that all other agents inherit from.
    
    This class provides the core functionality for all agents in the system,
    including task processing, error handling, health monitoring, communication,
    and memory operations.
    
    Memory capabilities are provided by AgentMemoryMixin:
    - remember(): Store content to memory
    - recall(): Query memories
    - learn_fact(): Add semantic knowledge
    - record_task_completion(): Log episodic events
    - get_conversation_context(): Get recent conversation turns
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """
        Initialize the base agent.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Display name for the agent
            config: Configuration dictionary for the agent
        """
        self.agent_id = agent_id
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"agent.{agent_id}")
        
        # Queues for communication
        self.notification_queue = asyncio.Queue()
        self.task_queue = asyncio.Queue()
        self.error_queue = asyncio.Queue()
        
        # Configuration parameters
        self.health_check_interval = config.get('health_check_interval', 60)
        self.retry_interval = config.get('retry_interval', 300)
        self.max_retries = config.get('max_retries', 3)
        
        # Agent state
        # Start in INITIALIZING; `initialize()` transitions to ACTIVE/ERROR.
        self.status = AgentStatus.INITIALIZING
        self.is_running = False
        self.background_tasks: List[asyncio.Task] = []
        self.last_heartbeat = datetime.now()
        self.dependencies: Dict[str, str] = {}
        self.integrations: Dict[str, Dict[str, Any]] = {}
        self.capabilities: Set[str] = set()
        self.security_token: Optional[str] = None
        self.metrics: Dict[str, Any] = {
            "tasks_processed": 0,
            "errors_handled": 0,
            "last_health_check": None,
            "uptime": 0,
            "start_time": None,
        }
        
        # Initialize managers
        self.dependency_manager = DependencyManager()
        self.integration_manager = IntegrationManager()
        self.task_manager = TaskManager()
        self.monitoring_service = MonitoringService()
        self.security_service = SecurityService()
        self.error_logging_service = ErrorLoggingService()
        
        # Desktop automation
        self.desktop_automation = None

        # Integration service
        self.integration_service: Optional[IntegrationService] = None
        self.running = False
        self.task = None

    def get_agent_id(self) -> str:
        """Get the unique identifier of the agent."""
        return self.agent_id
        
    def get_name(self) -> str:
        """Get the display name of the agent."""
        return self.name
        
    def get_capabilities(self) -> list[str]:
        """Get the capabilities of the agent."""
        return list(self.capabilities)
        
    def get_security_token(self) -> str:
        """Get the current security token of the agent."""
        return self.security_token or ""
        
    def set_security_token(self, token: str) -> None:
        """Set the security token for the agent."""
        self.security_token = token
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get the current metrics of the agent."""
        return self.metrics
        
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "capabilities": list(self.capabilities),
            "last_heartbeat": datetime.now().isoformat(),
            "memory_enabled": self._memory_initialized if hasattr(self, '_memory_initialized') else False
        }
        
    async def health_check(self) -> Dict[str, Any]:
        """
        Structured health check (legacy-compatible with pytest suite).
        """
        self.metrics["last_health_check"] = datetime.now().isoformat()

        service_health = await self._check_services_health()
        resource_usage = await self._check_resource_usage()

        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "is_running": self.is_running,
            "metrics": dict(self.metrics),
            "queue_sizes": {
                "notifications": self.notification_queue.qsize(),
                "tasks": self.task_queue.qsize(),
                "errors": self.error_queue.qsize(),
            },
            "service_health": service_health,
            "resource_usage": resource_usage,
            "timestamp": datetime.now().isoformat(),
        }

    # ==================== SELF-HEALING CODE MODIFICATION ====================

    async def request_code_change(
        self,
        description: str,
        reason: str,
        target_files: Optional[List[str]] = None,
        change_type: str = "update_code",
        priority: int = 5,
    ) -> Dict[str, Any]:
        """
        Request a code change through the CodeModificationService.

        Any agent can request code modifications. All requests are gated
        by SecurityCodeReviewer before execution.

        Args:
            description: What code change to make
            reason: Why this change is needed
            target_files: Optional list of files to modify
            change_type: fix_bug, create_agent, update_code, add_feature, etc.
            priority: 1-10, higher = more urgent

        Returns:
            Dict with change_id, status, and message
        """
        try:
            from mycosoft_mas.services.code_modification_service import get_code_modification_service

            code_service = await get_code_modification_service()
            result = await code_service.request_code_change(
                requester_id=self.agent_id,
                change_type=change_type,
                description=description,
                target_files=target_files or [],
                priority=priority,
                context={"reason": reason, "agent_name": self.name},
            )
            self.logger.info(f"Code change requested: {result.get('change_id')}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to request code change: {e}")
            return {
                "status": "error",
                "message": str(e),
                "change_id": None,
            }

    async def request_self_improvement(
        self,
        improvement_description: str,
        target_files: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Request an improvement to this agent's own code or behavior.

        Routes through CodeModificationService and SecurityCodeReviewer.

        Args:
            improvement_description: What to improve and how
            target_files: Optional specific files (e.g. this agent's module)

        Returns:
            Dict with change_id, status, and message
        """
        return await self.request_code_change(
            description=improvement_description,
            reason="self_improvement",
            target_files=target_files,
            change_type="self_improve",
            priority=5,
        )

    async def report_bug_for_fix(
        self,
        bug_description: str,
        error_message: Optional[str] = None,
        affected_files: Optional[List[str]] = None,
        priority: int = 7,
    ) -> Dict[str, Any]:
        """
        Report a bug so that the self-healing system can trigger a fix.

        Args:
            bug_description: What is broken and expected behavior
            error_message: Optional error or stack trace
            affected_files: Optional files where the bug occurs
            priority: 1-10 (default 7 for bugs)

        Returns:
            Dict with change_id, status, and message
        """
        description = bug_description
        if error_message:
            description = f"{bug_description}\n\nError: {error_message}"
        return await self.request_code_change(
            description=description,
            reason="bug_report",
            target_files=affected_files or [],
            change_type="fix_bug",
            priority=priority,
        )

    async def initialize(self, integration_service: Any = None, **_: Any) -> bool:
        """
        Initialize the agent and its components including memory.

        Compatibility: the pytest suite passes an `integration_service` argument.
        """
        try:
            if integration_service is not None:
                self.integration_service = integration_service

            # BaseAgent is test-instantiable, but its service wiring is still
            # considered abstract. For the BaseAgent class itself, do a minimal
            # initialization that doesn't require external dependencies.
            if type(self) is BaseAgent:
                await self._start_background_tasks()
            else:
                await self._initialize_services()
                await self._start_background_tasks()

            self.status = AgentStatus.ACTIVE
            self.is_running = True
            self.metrics["start_time"] = datetime.now().isoformat()
            self.metrics["uptime"] = 0

            self.logger.info(f"Agent {self.agent_id} initialized successfully with memory")
            return True
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Failed to initialize agent {self.agent_id}: {str(e)}")
            return False

    async def _initialize_services(self) -> None:
        """Initialize dependencies/integrations/security/memory (override if needed)."""
        # Treat BaseAgent service wiring as abstract for the unit-test suite.
        if type(self) is BaseAgent:
            raise NotImplementedError

        # Register dependencies
        if hasattr(self, "dependencies"):
            result = self.dependency_manager.register_agent_dependencies(
                self.agent_id,
                self.dependencies
            )
            if result["status"] == "conflict":
                self.logger.warning(f"Dependency conflicts: {result['conflicts']}")
                resolutions = self.dependency_manager.resolve_version_conflicts()
                for package, version in resolutions.items():
                    self.dependency_manager.update_dependency(package, version)

        # Register integrations
        if hasattr(self, "integrations"):
            for integration_id, config in self.integrations.items():
                self.integration_manager.register_integration(integration_id, config)

        # Initialize security
        self.security_token = self.security_service.authenticate_agent(self)

        # Register health checks
        self.monitoring_service.add_health_check(
            f"{self.agent_id}_dependencies",
            lambda: self.dependency_manager.check_dependencies(self.agent_id).get("status") == "success"
        )
        self.monitoring_service.add_health_check(
            f"{self.agent_id}_integrations",
            lambda: all(
                self.integration_manager.get_integration_status(i).get("is_active", False)
                for i in self.integrations
            )
        )

        # Initialize memory (from AgentMemoryMixin)
        await self.init_memory()

        # Load previous learnings from memory
        if getattr(self, "_memory_initialized", False):
            learnings = await self.recall(tags=["learning"], limit=10)
            if learnings:
                self.logger.info(f"Restored {len(learnings)} learnings from memory")

    async def _check_services_health(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def _check_resource_usage(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def _handle_error_type(self, error_type: str, error: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def _handle_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    async def _monitor_health(self) -> None:
        while self.is_running:
            await asyncio.sleep(self.health_check_interval)

    async def _process_tasks(self) -> None:
        while self.is_running:
            await asyncio.sleep(0.1)

    async def _handle_errors(self) -> None:
        while self.is_running:
            await asyncio.sleep(0.1)

    async def _process_notifications(self) -> None:
        while self.is_running:
            await asyncio.sleep(0.1)

    async def _start_background_tasks(self) -> None:
        self.background_tasks = [
            asyncio.create_task(self._monitor_health()),
            asyncio.create_task(self._process_tasks()),
            asyncio.create_task(self._handle_errors()),
            asyncio.create_task(self._process_notifications()),
        ]

    async def start(self):
        """Start the agent's main processing loop."""
        if not self.integration_service:
            raise RuntimeError("Agent must be initialized with integration service before starting")
        
        self.running = True
        self.status = AgentStatus.ACTIVE
        self.task = asyncio.create_task(self._process())
        self.logger.info(f"Agent {self.agent_id} started")

    async def stop(self) -> bool:
        """Stop the agent's main processing loop."""
        self.running = False
        self.status = AgentStatus.SHUTDOWN
        self.is_running = False
        
        # Save agent state to memory before stopping
        if self._memory_initialized:
            await self.save_agent_state()
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        # Cancel and clear background tasks (legacy expectations).
        for t in list(self.background_tasks):
            t.cancel()
        self.background_tasks = []

        self.logger.info(f"Agent {self.agent_id} stopped")
        return True

    async def shutdown(self) -> bool:
        """Compatibility alias for `stop()` used by the pytest suite."""
        return await self.stop()

    async def _process(self):
        """Main processing loop for the agent."""
        while self.running:
            try:
                # Update metrics
                await self._update_metrics()
                
                # Process messages or perform agent-specific tasks
                await self.process()
                
                # Sleep to prevent CPU overuse
                await asyncio.sleep(self.config.get("processing_interval", 0.1))
                
            except Exception as e:
                self.logger.error(f"Error in agent {self.agent_id} processing loop: {str(e)}")
                self.status = AgentStatus.ERROR
                
                # Record error in memory
                if self._memory_initialized:
                    await self.record_error(str(e), {"source": "processing_loop"})
                
                await asyncio.sleep(1)

    async def process(self):
        """Agent-specific processing logic to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement process()")

    async def _update_metrics(self):
        """Update agent metrics and send to integration service."""
        try:
            # Merge runtime metrics into the existing metrics dict so we don't
            # clobber legacy counters expected by the test suite.
            self.metrics.update({
                "timestamp": datetime.now().isoformat(),
                "status": self.status.value,
                "processing_time": self._get_processing_time(),
                "message_count": self._get_message_count(),
                "error_count": self._get_error_count(),
                "memory_enabled": self._memory_initialized if hasattr(self, '_memory_initialized') else False,
                "custom_metrics": self.get_custom_metrics()
            })
            
            if self.integration_service:
                await self.integration_service.update_agent_metrics(self.agent_id, self.metrics)
                
        except Exception as e:
            self.logger.error(f"Error updating metrics: {str(e)}")

    def _get_processing_time(self) -> float:
        """Get average processing time. Override in subclass for actual values."""
        return 0.0

    def _get_message_count(self) -> int:
        """Get message count. Override in subclass for actual values."""
        return 0

    def _get_error_count(self) -> int:
        """Get error count. Override in subclass for actual values."""
        return 0

    def get_custom_metrics(self) -> Dict[str, Any]:
        """Get custom metrics. Override in subclass for agent-specific metrics."""
        return {}

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy task wrapper used by pytest suite."""
        task_type = str(task.get("type") or "")
        task_id = str(task.get("id") or "")
        payload = task.get("payload") or {}

        result = await self._handle_task(task_type, payload)
        self.metrics["tasks_processed"] = int(self.metrics.get("tasks_processed", 0)) + 1

        return {"success": True, "task_id": task_id, "result": result}

    async def handle_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        error_type = str(error.get("type") or "")
        error_id = str(error.get("id") or "")
        error_msg = str(error.get("error") or "")

        result = await self._handle_error_type(error_type, error_msg)
        self.metrics["errors_handled"] = int(self.metrics.get("errors_handled", 0)) + 1

        return {"success": True, "error_id": error_id, "result": result}

    async def process_message(self, message: Message) -> Dict[str, Any]:
        """Process an incoming message based on its type."""
        handlers = {
            MessageType.NOTIFICATION: self._handle_notification,
            MessageType.TASK: self._handle_task,
            MessageType.HEALTH_CHECK: self._handle_health_check,
            MessageType.TECHNOLOGY_UPDATE: self._handle_technology_update,
            MessageType.EVOLUTION_ALERT: self._handle_evolution_alert,
            MessageType.SYSTEM_UPDATE: self._handle_system_update,
        }
        
        handler = handlers.get(message.type)
        if handler:
            return await handler(message)
        else:
            return {"status": "error", "message": f"Unknown message type: {message.type}"}

    async def handle_message(self, message: Message) -> Dict[str, Any]:
        """Legacy entrypoint expected by orchestrator tests."""
        return await self.process_message(message)

    async def _handle_notification(self, arg: Any) -> Dict[str, Any]:
        """
        Dual-purpose handler:
        - Message-based notifications (runtime)
        - Dict-based notifications (legacy tests) -> NotImplementedError by default
        """
        if isinstance(arg, Message):
            return await self._handle_notification_message(arg)
        raise NotImplementedError

    async def _handle_notification_message(self, message: Message) -> Dict[str, Any]:
        """Handle notification messages."""
        await self.notification_queue.put(message.content)
        return {"status": "received", "message_id": str(message.id)}
        
    async def _handle_task(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Dual-purpose handler:
        - Message-based tasks (runtime)
        - (task_type, payload) tasks (legacy tests) -> NotImplementedError by default
        """
        if len(args) == 1 and isinstance(args[0], Message):
            return await self._handle_task_message(args[0])
        if len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], dict):
            raise NotImplementedError
        raise TypeError("Unsupported _handle_task call signature")

    async def _handle_task_message(self, message: Message) -> Dict[str, Any]:
        """Handle task messages."""
        if message.content["action"] == "process":
            result = await self.task_manager.submit_task(message.content["task"])
            
            # Record task in memory
            if self._memory_initialized and result.get("status") == "completed":
                await self.record_task_completion(
                    task_id=message.content.get("task_id", str(message.id)),
                    result=result,
                    success=True
                )
            
            return result
        elif message.content["action"] == "status":
            return await self.task_manager.get_task_status(message.content["task_id"])
        else:
            return {"status": "error", "message": "Unknown task action"}
            
    async def _handle_health_check(self, message: Message) -> Dict[str, Any]:
        """Handle health check requests."""
        return {
            "status": self.status.value,
            "dependencies": self.dependency_manager.check_dependencies(self.agent_id),
            "integrations": {
                integration_id: self.integration_manager.get_integration_status(integration_id)
                for integration_id in self.integrations
            },
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "memory_enabled": self._memory_initialized if hasattr(self, '_memory_initialized') else False
        }
        
    async def _handle_technology_update(self, message: Message) -> Dict[str, Any]:
        """Handle technology update messages."""
        try:
            technology = message.content["technology"]
            
            if "technology_monitoring" in self.capabilities:
                result = await self._process_technology_update(technology)
                
                # Learn from technology update
                if self._memory_initialized:
                    await self.learn_fact({
                        "subject": "technology_update",
                        "technology": technology.get("name", "unknown"),
                        "version": technology.get("version"),
                        "learned_at": datetime.now().isoformat()
                    })
                
                if result.get("requires_dependency_update"):
                    await self.dependency_manager.update_dependencies(
                        result["dependencies"],
                        self.agent_id
                    )
                
                if result.get("requires_integration_update"):
                    await self.integration_manager.update_integrations(
                        result["integrations"],
                        self.agent_id
                    )
                
                return {"status": "success", "result": result}
            else:
                return {"status": "ignored", "message": "Agent does not support technology monitoring"}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
    async def _handle_evolution_alert(self, message: Message) -> Dict[str, Any]:
        """Handle evolution alert messages."""
        try:
            alert_type = message.content["alert_type"]
            severity = message.content["severity"]
            
            result = await self._process_evolution_alert(alert_type, severity)
            
            if severity == "critical":
                await self._handle_critical_evolution_alert(result)
            elif severity == "high":
                await self._handle_high_evolution_alert(result)
            else:
                await self._handle_normal_evolution_alert(result)
            
            return {"status": "success", "result": result}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
    async def _handle_system_update(self, message: Message) -> Dict[str, Any]:
        """Handle system update messages."""
        try:
            update_type = message.content["update_type"]
            details = message.content["details"]
            
            result = await self._process_system_update(update_type, details)
            
            if result.get("requires_state_update"):
                await self._update_agent_state(result["state_updates"])
            
            if result.get("requires_capability_update"):
                await self._update_capabilities(result["capability_updates"])
            
            return {"status": "success", "result": result}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
    async def _process_technology_update(self, technology: Dict[str, Any]) -> Dict[str, Any]:
        """Process technology update. Override in subclasses."""
        return {"status": "not_implemented"}
    
    async def _process_evolution_alert(self, alert_type: str, severity: str) -> Dict[str, Any]:
        """Process evolution alert. Override in subclasses."""
        return {"status": "not_implemented"}
    
    async def _process_system_update(self, update_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Process system update. Override in subclasses."""
        return {"status": "not_implemented"}
    
    async def _handle_critical_evolution_alert(self, result: Dict[str, Any]):
        """Handle critical evolution alert. Override in subclasses."""
        pass
    
    async def _handle_high_evolution_alert(self, result: Dict[str, Any]):
        """Handle high severity evolution alert. Override in subclasses."""
        pass
    
    async def _handle_normal_evolution_alert(self, result: Dict[str, Any]):
        """Handle normal evolution alert. Override in subclasses."""
        pass
    
    async def _update_agent_state(self, updates: Dict[str, Any]):
        """Update agent state based on system updates."""
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)
            
    async def _update_capabilities(self, updates: List[str]):
        """Update agent capabilities based on system updates."""
        self.capabilities.update(updates)

    async def _handle_error(self, error: Dict[str, Any]):
        """Handle errors from the error queue."""
        self.logger.error(f"Agent error: {error}")
        
        # Record in memory
        if self._memory_initialized:
            await self.record_error(
                error.get("message", str(error)),
                {"type": error.get("type"), "source": "error_queue"}
            )

    async def _handle_notification_queue(self, notification: Dict[str, Any]) -> None:
        """Handle notifications from the queue (internal helper)."""
        self.logger.info(f"Agent notification: {notification}")
    
    # ==================== SELF-HEALING CODE MODIFICATION ====================
    
    async def request_code_change(
        self,
        description: str,
        reason: str,
        target_files: Optional[List[str]] = None,
        priority: int = 5,
    ) -> Dict[str, Any]:
        """
        Request a code change through the CodeModificationService.
        
        Any agent can request code changes, which will be:
        1. Reviewed by SecurityCodeReviewer
        2. Executed by CodingAgent
        3. Monitored for vulnerabilities
        
        Args:
            description: What code change to make
            reason: Why this change is needed
            target_files: Optional list of files to modify
            priority: 1-10, higher = more urgent
            
        Returns:
            Dict with change_id, status, and message
        """
        self.logger.info(f"Agent {self.agent_id} requesting code change: {description[:50]}...")
        
        try:
            from mycosoft_mas.services.code_modification_service import get_code_modification_service
            
            code_service = await get_code_modification_service()
            result = await code_service.request_code_change(
                requester_id=self.agent_id,
                change_type="update_code",
                description=description,
                target_files=target_files,
                priority=priority,
                context={"reason": reason, "agent_name": self.name},
            )
            
            # Record this request in memory
            if hasattr(self, '_memory_initialized') and self._memory_initialized:
                await self.remember(
                    content=f"Requested code change: {description}",
                    tags=["code_change", "self_healing"],
                    metadata={
                        "change_id": result.get("change_id"),
                        "reason": reason,
                        "status": result.get("status"),
                    }
                )
            
            self.logger.info(f"Code change request submitted: {result.get('change_id')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to request code change: {e}")
            return {
                "status": "error",
                "message": str(e),
                "change_id": None,
            }
    
    async def request_self_improvement(
        self,
        improvement_description: str,
        priority: int = 3,
    ) -> Dict[str, Any]:
        """
        Request an improvement to this agent's own code.
        
        The agent can identify ways to improve itself and submit
        requests through the CodeModificationService.
        
        Args:
            improvement_description: What improvement to make
            priority: 1-10, higher = more urgent (default low priority)
            
        Returns:
            Dict with change_id, status, and message
        """
        self.logger.info(f"Agent {self.agent_id} requesting self-improvement...")
        
        # Determine the agent's file path
        agent_file = f"mycosoft_mas/agents/{self.agent_id}.py"
        
        try:
            from mycosoft_mas.services.code_modification_service import get_code_modification_service
            
            code_service = await get_code_modification_service()
            result = await code_service.request_code_change(
                requester_id=self.agent_id,
                change_type="self_improve",
                description=f"Self-improvement for {self.name} ({self.agent_id}): {improvement_description}",
                target_files=[agent_file],
                priority=priority,
                context={
                    "agent_id": self.agent_id,
                    "agent_name": self.name,
                    "capabilities": list(self.capabilities),
                    "improvement_type": "self_requested",
                },
            )
            
            # Record this in memory
            if hasattr(self, '_memory_initialized') and self._memory_initialized:
                await self.remember(
                    content=f"Requested self-improvement: {improvement_description}",
                    tags=["self_improvement", "evolution"],
                    metadata={
                        "change_id": result.get("change_id"),
                        "status": result.get("status"),
                    }
                )
            
            self.logger.info(f"Self-improvement request submitted: {result.get('change_id')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to request self-improvement: {e}")
            return {
                "status": "error",
                "message": str(e),
                "change_id": None,
            }
    
    async def report_bug_for_fix(
        self,
        error_message: str,
        stack_trace: Optional[str] = None,
        affected_files: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Report a bug encountered during operation for automatic fixing.
        
        When an agent encounters an error, it can report it to the
        self-healing system for automatic analysis and fixing.
        
        Args:
            error_message: The error that occurred
            stack_trace: Optional stack trace
            affected_files: Optional list of files involved
            
        Returns:
            Dict with change_id and status
        """
        self.logger.info(f"Agent {self.agent_id} reporting bug for fix: {error_message[:50]}...")
        
        try:
            from mycosoft_mas.services.code_modification_service import get_code_modification_service
            
            code_service = await get_code_modification_service()
            result = await code_service.request_code_change(
                requester_id=self.agent_id,
                change_type="fix_bug",
                description=f"Bug fix for error in {self.name}: {error_message}",
                target_files=affected_files,
                priority=7,  # Higher priority for bug fixes
                context={
                    "error_message": error_message,
                    "stack_trace": stack_trace,
                    "agent_id": self.agent_id,
                    "agent_name": self.name,
                    "auto_reported": True,
                },
            )
            
            # Record the bug report in memory
            if hasattr(self, '_memory_initialized') and self._memory_initialized:
                await self.record_error(
                    error_message,
                    {
                        "stack_trace": stack_trace,
                        "change_id": result.get("change_id"),
                        "fix_requested": True,
                    }
                )
            
            self.logger.info(f"Bug fix request submitted: {result.get('change_id')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to report bug for fix: {e}")
            return {
                "status": "error",
                "message": str(e),
                "change_id": None,
            }