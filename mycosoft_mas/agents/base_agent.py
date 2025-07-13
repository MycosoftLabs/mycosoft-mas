"""
Mycosoft Multi-Agent System (MAS) - Base Agent

This module defines the BaseAgent class, which serves as the foundation for all agents in the system.
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
from mycosoft_mas.services.monitoring import MonitoringService
from mycosoft_mas.services.security_interface import AgentSecurable
from mycosoft_mas.services.security import SecurityService

logger = logging.getLogger(__name__)

class BaseAgent(AgentMonitorable, AgentSecurable):
    """
    Base agent class that all other agents inherit from.
    
    This class provides the core functionality for all agents in the system,
    including task processing, error handling, health monitoring, and communication.
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
        self.status = AgentStatus.INITIALIZED
        self.is_running = False
        self.background_tasks: List[asyncio.Task] = []
        self.last_heartbeat = datetime.now()
        self.dependencies: Dict[str, str] = {}
        self.integrations: Dict[str, Dict[str, Any]] = {}
        self.capabilities: Set[str] = set()
        self.security_token: Optional[str] = None
        self.metrics: Dict[str, Any] = {}
        
        # Initialize managers
        self.dependency_manager = DependencyManager()
        self.integration_manager = IntegrationManager()
        self.task_manager = TaskManager()
        self.monitoring_service = MonitoringService()
        self.security_service = SecurityService()
        
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
            "last_heartbeat": datetime.now().isoformat()
        }
        
    async def health_check(self) -> bool:
        """Perform a health check on the agent."""
        try:
            # Check basic agent state
            if self.status == AgentStatus.ERROR:
                return False
                
            # Check security token
            if not self.security_token:
                return False
                
            # Check capabilities
            if not self.capabilities:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Health check failed for agent {self.name}: {str(e)}")
            return False

    async def initialize(
        self, integration_service: Optional[IntegrationService] | None = None
    ) -> None:
        """Initialize the agent and its components.

        Args:
            integration_service: Optional external integration service to use.
        """
        try:
            # Integration service is required for initialization
            if integration_service is None and self.integration_service is None:
                raise ValueError("integration_service is required for initialization")
            if integration_service is not None:
                self.integration_service = integration_service
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
                    self.integration_manager.register_integration(
                        integration_id, config
                    )
                    
            # Initialize security
            self.security_token = self.security_service.authenticate_agent(self)
            
            # Register health checks
            self.monitoring_service.add_health_check(
                f"{self.agent_id}_dependencies",
                lambda: self.dependency_manager.check_dependencies(self.agent_id)["status"] == "success"
            )
            self.monitoring_service.add_health_check(
                f"{self.agent_id}_integrations",
                lambda: all(
                    self.integration_manager.get_integration_status(i)["is_active"]
                    for i in self.integrations
                )
            )
            
            self.status = AgentStatus.ACTIVE
            self.logger.info(f"Agent {self.agent_id} initialized successfully")
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Failed to initialize agent {self.agent_id}: {str(e)}")
            raise

    async def start(self):
        """Start the agent's main processing loop."""
        if not self.integration_service:
            raise RuntimeError("Agent must be initialized with integration service before starting")
        
        self.running = True
        self.status = AgentStatus.ACTIVE
        self.task = asyncio.create_task(self._process())
        self.logger.info(f"Agent {self.agent_id} started")

    async def stop(self):
        """Stop the agent's main processing loop."""
        self.running = False
        self.status = AgentStatus.STOPPED
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.logger.info(f"Agent {self.agent_id} stopped")

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
                await asyncio.sleep(1)  # Prevent tight error loop

    async def process(self):
        """Agent-specific processing logic to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement process()")

    async def _update_metrics(self):
        """Update agent metrics and send to integration service."""
        try:
            self.metrics = {
                "timestamp": datetime.now().isoformat(),
                "status": self.status.value,
                "processing_time": self._get_processing_time(),
                "message_count": self._get_message_count(),
                "error_count": self._get_error_count(),
                "custom_metrics": self.get_custom_metrics()
            }
            
            if self.integration_service:
                await self.integration_service.update_agent_metrics(self.agent_id, self.metrics)
                
        except Exception as e:
            self.logger.error(f"Error updating metrics for agent {self.agent_id}: {str(e)}")

    def _get_processing_time(self) -> float:
        """Get average processing time for the agent."""
        return self.metrics.get("processing_time", 0.0)

    def _get_message_count(self) -> int:
        """Get total message count processed by the agent."""
        return self.metrics.get("message_count", 0)

    def _get_error_count(self) -> int:
        """Get total error count for the agent."""
        return self.metrics.get("error_count", 0)

    def get_custom_metrics(self) -> Dict[str, Any]:
        """Get agent-specific metrics to be implemented by subclasses."""
        return {}

    async def _initialize_services(self) -> None:
        """Initialize agent services."""
        try:
            # Initialize data directory
            data_dir = self.config.get('data_directory')
            if data_dir:
                Path(data_dir).mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Initialized data directory: {data_dir}")
            
            # Initialize output directory
            output_dir = self.config.get('output_directory')
            if output_dir:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Initialized output directory: {output_dir}")
            
            # Initialize any agent-specific services
            await self._initialize_agent_services()
            
        except Exception as e:
            self.logger.error(f"Error initializing services: {str(e)}")
            raise

    async def _initialize_agent_services(self) -> None:
        """Initialize agent-specific services. Override in subclasses."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the agent and clean up resources."""
        try:
            # Unregister dependencies
            self.dependency_manager.remove_dependency(self.agent_id)
            
            # Unregister integrations
            for integration_id in self.integrations:
                self.integration_manager.unregister_integration(integration_id)
                
            # Revoke security token
            if self.security_token:
                self.security_service.revoke_token(self.security_token)
                
            self.status = AgentStatus.STOPPED
            self.logger.info(f"Agent {self.agent_id} shut down successfully")
        except Exception as e:
            self.logger.error(f"Error shutting down agent {self.agent_id}: {str(e)}")
            raise

    async def process_task(self, task: Dict) -> Dict:
        """
        Process a task from the orchestrator.
        
        Args:
            task: Task dictionary containing task details
            
        Returns:
            Dict: Result of task processing
        """
        try:
            task_type = task.get('type')
            task_id = task.get('id', str(uuid.uuid4()))
            payload = task.get('payload', {})

            self.logger.info(f"Processing task {task_id} of type {task_type}")
            
            # Add task to queue
            await self.task_queue.put({
                'id': task_id,
                'type': task_type,
                'payload': payload,
                'timestamp': datetime.now().isoformat()
            })

            # Process task based on type
            result = await self._handle_task(task_type, payload)
            
            # Update metrics
            self.metrics["tasks_processed"] += 1
            
            # Send notification about task completion
            await self.notification_queue.put({
                'type': 'task_completed',
                'task_id': task_id,
                'result': result,
                'timestamp': datetime.now().isoformat()
            })

            return {
                'success': True,
                'task_id': task_id,
                'result': result
            }

        except Exception as e:
            error_msg = f"Failed to process task: {str(e)}"
            self.logger.error(error_msg)
            await self.error_queue.put({
                'type': 'task_error',
                'task_id': task_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return {
                'success': False,
                'error': error_msg
            }

    async def _handle_task(self, task_type: str, payload: Dict) -> Dict:
        """Handle a task. Override in subclasses."""
        return {"status": "not_implemented"}

    async def _handle_error(self, error: Dict) -> None:
        """Handle an error."""
        try:
            error_type = error.get('type', 'unknown')
            error_msg = error.get('error', 'Unknown error')
            self.logger.error(f"Handling error {error.get('id', 'unknown')} of type {error_type}: {error_msg}")
            self.metrics["errors_handled"] += 1
        except Exception as e:
            self.logger.error(f"Error handling error: {str(e)}")

    async def _handle_notification(self, notification: Dict) -> None:
        """Handle a notification. Override in subclasses."""
        pass

    async def handle_message(self, message: Message) -> Dict[str, Any]:
        """Handle incoming messages."""
        # Verify message security
        if not self.security_service.validate_token(message.token):
            return {"status": "error", "message": "Invalid token"}
            
        # Check access control
        if not self.security_service.check_access(message.token, "message", "receive"):
            return {"status": "error", "message": "Access denied"}
            
        # Process message based on type
        if message.type == MessageType.DEPENDENCY_REQUEST:
            return await self._handle_dependency_request(message)
        elif message.type == MessageType.INTEGRATION_REQUEST:
            return await self._handle_integration_request(message)
        elif message.type == MessageType.TASK_REQUEST:
            return await self._handle_task_request(message)
        elif message.type == MessageType.HEALTH_CHECK:
            return await self._handle_health_check(message)
        elif message.type == MessageType.TECHNOLOGY_UPDATE:
            return await self._handle_technology_update(message)
        elif message.type == MessageType.EVOLUTION_ALERT:
            return await self._handle_evolution_alert(message)
        elif message.type == MessageType.SYSTEM_UPDATE:
            return await self._handle_system_update(message)
        else:
            return {"status": "error", "message": "Unknown message type"}
            
    async def _handle_dependency_request(self, message: Message) -> Dict[str, Any]:
        """Handle dependency-related requests."""
        if message.content["action"] == "add":
            return self.dependency_manager.add_dependency(
                message.content["package"],
                message.content["version"],
                self.agent_id
            )
        elif message.content["action"] == "remove":
            return self.dependency_manager.remove_dependency(
                message.content["package"],
                self.agent_id
            )
        elif message.content["action"] == "check":
            return self.dependency_manager.check_dependencies(self.agent_id)
        else:
            return {"status": "error", "message": "Unknown dependency action"}
            
    async def _handle_integration_request(self, message: Message) -> Dict[str, Any]:
        """Handle integration-related requests."""
        if message.content["action"] == "register":
            return self.integration_manager.register_integration(
                message.content["integration_id"],
                message.content["config"]
            )
        elif message.content["action"] == "execute":
            return self.integration_manager.execute_integration(
                message.content["integration_id"],
                message.content["data"]
            )
        else:
            return {"status": "error", "message": "Unknown integration action"}
            
    async def _handle_task_request(self, message: Message) -> Dict[str, Any]:
        """Handle task-related requests."""
        if message.content["action"] == "submit":
            return await self.task_manager.submit_task(message.content["task"])
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
            "last_heartbeat": self.last_heartbeat.isoformat()
        }
        
    async def _handle_technology_update(self, message: Message) -> Dict[str, Any]:
        """Handle technology update messages."""
        try:
            technology = message.content["technology"]
            
            # Check if agent has technology monitoring capability
            if "technology_monitoring" in self.capabilities:
                # Process technology update
                result = await self._process_technology_update(technology)
                
                # Update dependencies if needed
                if result.get("requires_dependency_update"):
                    await self.dependency_manager.update_dependencies(
                        result["dependencies"],
                        self.agent_id
                    )
                
                # Update integrations if needed
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
            
            # Process evolution alert
            result = await self._process_evolution_alert(alert_type, severity)
            
            # Take appropriate action based on severity
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
            
            # Process system update
            result = await self._process_system_update(update_type, details)
            
            # Update agent state if needed
            if result.get("requires_state_update"):
                await self._update_agent_state(result["state_updates"])
            
            # Update capabilities if needed
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

    async def _start_background_tasks(self) -> None:
        """Start background tasks."""
        try:
            # Start health check task
            health_check_task = asyncio.create_task(self._monitor_health())
            self.background_tasks.append(health_check_task)
            
            # Start queue processing tasks
            task_queue_task = asyncio.create_task(self._process_task_queue())
            error_queue_task = asyncio.create_task(self._process_error_queue())
            notification_queue_task = asyncio.create_task(self._process_notifications())
            
            self.background_tasks.extend([
                task_queue_task,
                error_queue_task,
                notification_queue_task
            ])
            
        except Exception as e:
            self.logger.error(f"Error starting background tasks: {str(e)}")
            raise

    async def _monitor_health(self) -> None:
        """Monitor agent health."""
        while self.is_running:
            try:
                await self.health_check()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Health check error: {str(e)}")
                await self.error_queue.put({
                    'type': 'health_check_error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                await asyncio.sleep(self.retry_interval)

    async def _process_task_queue(self) -> None:
        """Process tasks in the task queue."""
        while self.is_running:
            try:
                task = await self.task_queue.get()
                await self.process_task(task)
                self.task_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing task: {str(e)}")
                await asyncio.sleep(1)

    async def _process_error_queue(self) -> None:
        """Process errors in the error queue."""
        while self.is_running:
            try:
                error = await self.error_queue.get()
                await self._handle_error(error)
                self.error_queue.task_done()
            except Exception as e:
                self.logger.error(f"Failed to handle error: {str(e)}")
                await asyncio.sleep(1)

    async def _process_notifications(self) -> None:
        """Process notifications in the notification queue."""
        while self.is_running:
            try:
                notification = await self.notification_queue.get()
                await self._handle_notification(notification)
                self.notification_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing notification: {str(e)}")
                await asyncio.sleep(1)

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