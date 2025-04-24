from typing import Dict, Any, List, Optional, Type, Set
import asyncio
import logging
import importlib
import pkgutil
from datetime import datetime
from pathlib import Path
import yaml
import semver
import aiohttp
from aiohttp import ClientSession, ClientTimeout

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.desktop_automation_agent import DesktopAutomationAgent
from mycosoft_mas.agents.messaging.message import Message, MessageType
from .services.integration_service import IntegrationService
from .agents.project_manager_agent import ProjectManagerAgent
from .agents.myco_dao_agent import MycoDAOAgent
from .agents.ip_tokenization_agent import IPTokenizationAgent
from .agents.dashboard_agent import DashboardAgent
from .agents.opportunity_scout import OpportunityScout
from mycosoft_mas.dependencies.dependency_manager import DependencyManager
from mycosoft_mas.integrations.integration_manager import IntegrationManager
from mycosoft_mas.core.task_manager import TaskManager
from mycosoft_mas.services.monitoring import MonitoringService
from mycosoft_mas.services.security import SecurityService
from mycosoft_mas.services.evolution_monitor import EvolutionMonitor
from mycosoft_mas.services.security_monitor import SecurityMonitor
from mycosoft_mas.services.system_updates import SystemUpdates
from mycosoft_mas.services.technology_tracker import TechnologyTracker

class MCPServer:
    def __init__(self, config: Dict[str, Any]):
        self.name = config["name"]
        self.host = config["host"]
        self.port = config["port"]
        self.protocol = config["protocol"]
        self.api_key = config["api_key"]
        self.capabilities = config["capabilities"]
        self.backup_servers = config["backup_servers"]
        self.health_check_interval = config["health_check_interval"]
        self.retry_count = config["retry_count"]
        self.timeout = config["timeout"]
        self.session: Optional[ClientSession] = None
        self.is_healthy = False
        self.last_health_check = datetime.now()
        self.logger = logging.getLogger(f"mcp.{self.name}")
        self.metrics = {
            "requests": 0,
            "errors": 0,
            "response_time": 0,
            "last_error": None
        }
        self.load_balancer = None
        self.security_context = None

    async def initialize(self):
        """Initialize the MCP server connection with security and load balancing"""
        try:
            # Initialize security context
            self.security_context = await self._initialize_security()
            
            # Initialize load balancer if needed
            if self.backup_servers:
                self.load_balancer = await self._initialize_load_balancer()
            
            timeout = ClientTimeout(total=self.timeout)
            self.session = ClientSession(
                base_url=f"{self.protocol}://{self.host}:{self.port}",
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "X-Security-Token": self.security_context["token"]
                } if self.api_key else {}
            )
            
            # Start health monitoring
            asyncio.create_task(self._monitor_health())
            
            await self.health_check()
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP server {self.name}: {str(e)}")
            raise

    async def _initialize_security(self) -> Dict[str, Any]:
        """Initialize security context for the MCP server"""
        try:
            # Generate security token
            token = await self._generate_security_token()
            
            # Initialize encryption keys
            encryption_keys = await self._initialize_encryption()
            
            return {
                "token": token,
                "encryption_keys": encryption_keys,
                "last_rotation": datetime.now()
            }
        except Exception as e:
            self.logger.error(f"Failed to initialize security context: {str(e)}")
            raise

    async def _initialize_load_balancer(self) -> Dict[str, Any]:
        """Initialize load balancer for backup servers"""
        return {
            "current_index": 0,
            "servers": self.backup_servers,
            "weights": [1.0] * len(self.backup_servers),
            "last_used": datetime.now()
        }

    async def _monitor_health(self):
        """Continuously monitor server health"""
        while True:
            try:
                await self.health_check()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Health monitoring error: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

    async def health_check(self) -> bool:
        """Check the health of the MCP server"""
        try:
            if not self.session:
                return False

            async with self.session.get("/api/v1/health") as response:
                self.is_healthy = response.status == 200
                self.last_health_check = datetime.now()
                return self.is_healthy
        except Exception as e:
            self.logger.error(f"Health check failed for MCP server {self.name}: {str(e)}")
            self.is_healthy = False
            return False

    async def shutdown(self):
        """Shutdown the MCP server connection"""
        if self.session:
            await self.session.close()
            self.session = None

    async def execute_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a command with load balancing and security"""
        start_time = datetime.now()
        try:
            if not self.is_healthy and self.load_balancer:
                return await self._execute_with_failover(command, params)
            
            if not self.is_healthy:
                raise RuntimeError(f"MCP server {self.name} is not healthy")

            # Encrypt sensitive parameters
            if params:
                params = await self._encrypt_parameters(params)

            async with self.session.post(f"/api/v1/command/{command}", json=params) as response:
                if response.status != 200:
                    raise RuntimeError(f"Command {command} failed with status {response.status}")
                
                result = await response.json()
                
                # Update metrics
                self.metrics["requests"] += 1
                self.metrics["response_time"] = (datetime.now() - start_time).total_seconds()
                
                # Decrypt response if needed
                return await self._decrypt_response(result)
        except Exception as e:
            self.metrics["errors"] += 1
            self.metrics["last_error"] = str(e)
            self.logger.error(f"Error executing command {command} on MCP server {self.name}: {str(e)}")
            raise

    async def _execute_with_failover(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute command with failover to backup servers"""
        for _ in range(self.retry_count):
            try:
                # Get next server from load balancer
                server = self._get_next_backup_server()
                
                # Create temporary session for backup server
                async with ClientSession(
                    base_url=f"{self.protocol}://{server}",
                    timeout=ClientTimeout(total=self.timeout),
                    headers={"Authorization": f"Bearer {self.api_key}"}
                ) as session:
                    async with session.post(f"/api/v1/command/{command}", json=params) as response:
                        if response.status == 200:
                            return await response.json()
            except Exception as e:
                self.logger.warning(f"Failed to execute on backup server: {str(e)}")
                continue
        
        raise RuntimeError("All backup servers failed")

    def _get_next_backup_server(self) -> str:
        """Get next server from load balancer using weighted round-robin"""
        if not self.load_balancer:
            raise RuntimeError("No backup servers configured")
        
        lb = self.load_balancer
        total_weight = sum(lb["weights"])
        current_weight = 0
        
        for i in range(len(lb["servers"])):
            current_weight += lb["weights"][i]
            if current_weight >= total_weight * (lb["current_index"] / len(lb["servers"])):
                lb["current_index"] = (lb["current_index"] + 1) % len(lb["servers"])
                lb["last_used"] = datetime.now()
                return lb["servers"][i]
        
        return lb["servers"][0]

    async def _encrypt_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive parameters"""
        # Implementation of parameter encryption
        return params

    async def _decrypt_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive response data"""
        # Implementation of response decryption
        return response

    async def _generate_security_token(self) -> str:
        """Generate a security token for authentication"""
        # Implementation of token generation
        return "generated_token"

    async def _initialize_encryption(self) -> Dict[str, Any]:
        """Initialize encryption keys"""
        # Implementation of encryption key initialization
        return {"public_key": "public", "private_key": "private"}

    def get_metrics(self) -> Dict[str, Any]:
        """Get server metrics"""
        return {
            **self.metrics,
            "uptime": (datetime.now() - self.last_health_check).total_seconds(),
            "is_healthy": self.is_healthy
        }

class Orchestrator:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.agents: Dict[str, BaseAgent] = {}
        self.modules: Dict[str, Any] = {}
        self.tools: Dict[str, Any] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        self.mcp_servers: Dict[str, MCPServer] = {}
        self.desktop_automation: Optional[DesktopAutomationAgent] = None
        self.logger = logging.getLogger("orchestrator")
        self.is_running = False
        self.tool_deployment_queue = asyncio.Queue()
        self.agent_update_queue = asyncio.Queue()
        self.deployment_workers = []
        self.update_workers = []
        self.integration_service: Optional[IntegrationService] = None
        self.dependency_manager = DependencyManager()
        self.integration_manager = IntegrationManager()
        self.task_manager = TaskManager()
        self.monitoring_service = MonitoringService()
        self.security_service = SecurityService()
        self.evolution_monitor = EvolutionMonitor()
        self.security_monitor = SecurityMonitor()
        self.system_updates = SystemUpdates()
        self.technology_tracker = TechnologyTracker()
        
        # Security-related attributes
        self.security_tokens: Dict[str, str] = {}
        self.access_control: Dict[str, Dict[str, List[str]]] = {}
        self.security_policies: Dict[str, Dict[str, Any]] = {}
        self.encryption_keys: Dict[str, Dict[str, str]] = {}
        self.audit_log: List[Dict[str, Any]] = []
        self.security_alerts: List[Dict[str, Any]] = []
        self.vulnerability_scans: Dict[str, Dict[str, Any]] = {}
        self.security_updates: List[Dict[str, Any]] = []
        self.incident_response: Dict[str, Dict[str, Any]] = {}
        self.security_metrics: Dict[str, Any] = {
            "total_alerts": 0,
            "critical_alerts": 0,
            "vulnerabilities_found": 0,
            "security_updates_applied": 0,
            "incidents_handled": 0,
            "last_scan": None
        }

    async def initialize(self):
        """Initialize the orchestrator and all components."""
        try:
            # Load configuration
            self.config = self._load_config()
            
            # Initialize security services
            await self._initialize_security_services()
            
            # Initialize integration service
            self.integration_service = IntegrationService(self.config)
            await self.integration_service.initialize()
            
            # Initialize agents
            await self._initialize_agents()
            
            # Load MCP server configurations
            await self._load_mcp_servers()
            
            # Load dependencies
            await self._load_dependencies()
            
            # Initialize modules
            await self._initialize_modules()
            
            # Initialize tools
            await self._initialize_tools()
            
            # Start deployment workers
            await self._start_deployment_workers()
            
            # Start agent update workers
            await self._start_update_workers()
            
            # Initialize desktop automation
            if self.config.get("enable_global_desktop_automation", False):
                desktop_config = self.config.get("desktop_automation", {})
                self.desktop_automation = DesktopAutomationAgent(
                    "global_desktop_automation",
                    "Global Desktop Automation",
                    desktop_config
                )
                await self.desktop_automation.initialize()
                self.logger.info("Global desktop automation initialized")

            # Initialize dependency manager
            await self._initialize_dependency_manager()
            
            # Initialize integration manager
            await self._initialize_integration_manager()
            
            # Initialize task manager
            await self._initialize_task_manager()
            
            # Initialize monitoring service
            await self._initialize_monitoring_service()
            
            # Initialize security service
            await self._initialize_security_service()
            
            self.is_running = True
            self.logger.info("Orchestrator initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing orchestrator: {str(e)}")
            raise

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            raise

    async def _initialize_security_services(self):
        """Initialize security-related services and components."""
        try:
            # Load security policies
            await self._load_security_policies()
            
            # Initialize encryption keys
            await self._initialize_encryption()
            
            # Set up access control
            await self._setup_access_control()
            
            # Start security monitoring
            await self._start_security_monitoring()
            
            # Initialize incident response
            await self._initialize_incident_response()
            
            self.logger.info("Security services initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing security services: {str(e)}")
            raise

    async def _load_security_policies(self):
        """Load security policies from configuration."""
        try:
            security_config = self.config.get("security", {})
            self.security_policies = security_config.get("policies", {})
            
            # Validate security policies
            await self._validate_security_policies()
            
            self.logger.info("Security policies loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading security policies: {str(e)}")
            raise

    async def _initialize_encryption(self):
        """Initialize encryption keys and certificates."""
        try:
            # Generate or load encryption keys
            self.encryption_keys = await self.security_service.generate_encryption_keys()
            
            # Validate encryption setup
            await self._validate_encryption()
            
            self.logger.info("Encryption initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing encryption: {str(e)}")
            raise

    async def _setup_access_control(self):
        """Set up access control lists and permissions."""
        try:
            # Load access control configuration
            access_config = self.config.get("security", {}).get("access_control", {})
            
            # Set up role-based access control
            for role, permissions in access_config.items():
                self.access_control[role] = permissions
            
            # Validate access control setup
            await self._validate_access_control()
            
            self.logger.info("Access control initialized successfully")
        except Exception as e:
            self.logger.error(f"Error setting up access control: {str(e)}")
            raise

    async def _start_security_monitoring(self):
        """Start security monitoring tasks."""
        try:
            # Start vulnerability scanning
            asyncio.create_task(self._monitor_vulnerabilities())
            
            # Start security alert monitoring
            asyncio.create_task(self._monitor_security_alerts())
            
            # Start security update monitoring
            asyncio.create_task(self._monitor_security_updates())
            
            self.logger.info("Security monitoring started successfully")
        except Exception as e:
            self.logger.error(f"Error starting security monitoring: {str(e)}")
            raise

    async def _initialize_incident_response(self):
        """Initialize incident response procedures."""
        try:
            # Load incident response procedures
            incident_config = self.config.get("security", {}).get("incident_response", {})
            
            # Set up incident response procedures
            for incident_type, procedure in incident_config.items():
                self.incident_response[incident_type] = procedure
            
            # Validate incident response setup
            await self._validate_incident_response()
            
            self.logger.info("Incident response initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing incident response: {str(e)}")
            raise

    async def _monitor_vulnerabilities(self):
        """Monitor for vulnerabilities."""
        while self.is_running:
            try:
                # Perform vulnerability scan
                scan_results = await self.security_service.scan_for_vulnerabilities()
                
                # Process scan results
                await self._process_vulnerability_scan(scan_results)
                
                # Update metrics
                self.security_metrics["vulnerabilities_found"] = len(scan_results)
                self.security_metrics["last_scan"] = datetime.now().isoformat()
                
                await asyncio.sleep(3600)  # Scan every hour
            except Exception as e:
                self.logger.error(f"Error in vulnerability monitoring: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    async def _monitor_security_alerts(self):
        """Monitor for security alerts."""
        while self.is_running:
            try:
                # Check for security alerts
                alerts = await self.security_service.check_security_alerts()
                
                # Process alerts
                await self._process_security_alerts(alerts)
                
                # Update metrics
                self.security_metrics["total_alerts"] += len(alerts)
                self.security_metrics["critical_alerts"] += len(
                    [a for a in alerts if a.get("severity") == "critical"]
                )
                
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                self.logger.error(f"Error in security alert monitoring: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _monitor_security_updates(self):
        """Monitor for security updates."""
        while self.is_running:
            try:
                # Check for security updates
                updates = await self.security_service.check_security_updates()
                
                # Process updates
                await self._process_security_updates(updates)
                
                # Update metrics
                self.security_metrics["security_updates_applied"] += len(updates)
                
                await asyncio.sleep(3600)  # Check every hour
            except Exception as e:
                self.logger.error(f"Error in security update monitoring: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    async def _process_vulnerability_scan(self, scan_results: List[Dict[str, Any]]):
        """Process vulnerability scan results."""
        try:
            for vulnerability in scan_results:
                # Log vulnerability
                self.vulnerability_scans[vulnerability["id"]] = vulnerability
                
                # Check if immediate action is required
                if vulnerability.get("severity") == "critical":
                    await self._handle_critical_vulnerability(vulnerability)
                
                # Update security metrics
                self.security_metrics["vulnerabilities_found"] += 1
                
        except Exception as e:
            self.logger.error(f"Error processing vulnerability scan: {str(e)}")

    async def _process_security_alerts(self, alerts: List[Dict[str, Any]]):
        """Process security alerts."""
        try:
            for alert in alerts:
                # Log alert
                self.security_alerts.append(alert)
                
                # Check if immediate action is required
                if alert.get("severity") == "critical":
                    await self._handle_critical_alert(alert)
                
                # Update security metrics
                self.security_metrics["total_alerts"] += 1
                if alert.get("severity") == "critical":
                    self.security_metrics["critical_alerts"] += 1
                
        except Exception as e:
            self.logger.error(f"Error processing security alerts: {str(e)}")

    async def _process_security_updates(self, updates: List[Dict[str, Any]]):
        """Process security updates."""
        try:
            for update in updates:
                # Log update
                self.security_updates.append(update)
                
                # Apply update if required
                if update.get("requires_immediate_update"):
                    await self._apply_security_update(update)
                
                # Update security metrics
                self.security_metrics["security_updates_applied"] += 1
                
        except Exception as e:
            self.logger.error(f"Error processing security updates: {str(e)}")

    async def _handle_critical_vulnerability(self, vulnerability: Dict[str, Any]):
        """Handle critical vulnerabilities."""
        try:
            # Log incident
            self.audit_log.append({
                "type": "critical_vulnerability",
                "vulnerability": vulnerability,
                "timestamp": datetime.now().isoformat()
            })
            
            # Notify security team
            await self._notify_security_team(vulnerability)
            
            # Apply emergency patches if available
            if vulnerability.get("has_patch"):
                await self._apply_emergency_patch(vulnerability)
            
            # Update incident response
            self.incident_response["vulnerability"] = {
                "status": "handled",
                "vulnerability_id": vulnerability["id"],
                "handled_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error handling critical vulnerability: {str(e)}")

    async def _handle_critical_alert(self, alert: Dict[str, Any]):
        """Handle critical security alerts."""
        try:
            # Log incident
            self.audit_log.append({
                "type": "critical_alert",
                "alert": alert,
                "timestamp": datetime.now().isoformat()
            })
            
            # Notify security team
            await self._notify_security_team(alert)
            
            # Take immediate action if required
            if alert.get("requires_immediate_action"):
                await self._take_immediate_action(alert)
            
            # Update incident response
            self.incident_response["alert"] = {
                "status": "handled",
                "alert_id": alert["id"],
                "handled_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error handling critical alert: {str(e)}")

    async def _apply_security_update(self, update: Dict[str, Any]):
        """Apply security updates."""
        try:
            # Log update
            self.audit_log.append({
                "type": "security_update",
                "update": update,
                "timestamp": datetime.now().isoformat()
            })
            
            # Apply update
            await self.security_service.apply_security_update(update)
            
            # Verify update
            await self._verify_security_update(update)
            
        except Exception as e:
            self.logger.error(f"Error applying security update: {str(e)}")

    async def _notify_security_team(self, incident: Dict[str, Any]):
        """Notify security team about incidents."""
        try:
            # Create notification message
            message = Message.create_security_alert(
                sender="orchestrator",
                receiver="security_team",
                alert_type=incident.get("type", "unknown"),
                message=incident.get("description", "Unknown incident"),
                severity=incident.get("severity", "critical")
            )
            
            # Send notification
            await self._send_notification(message)
            
        except Exception as e:
            self.logger.error(f"Error notifying security team: {str(e)}")

    async def _take_immediate_action(self, alert: Dict[str, Any]):
        """Take immediate action for critical alerts."""
        try:
            # Determine action based on alert type
            action = self.incident_response.get(alert["type"], {}).get("immediate_action")
            
            if action:
                # Execute action
                await self.security_service.execute_security_action(action, alert)
                
                # Log action
                self.audit_log.append({
                    "type": "immediate_action",
                    "alert": alert,
                    "action": action,
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            self.logger.error(f"Error taking immediate action: {str(e)}")

    async def _apply_emergency_patch(self, vulnerability: Dict[str, Any]):
        """Apply emergency patches for critical vulnerabilities."""
        try:
            # Get patch
            patch = await self.security_service.get_emergency_patch(vulnerability)
            
            if patch:
                # Apply patch
                await self.security_service.apply_emergency_patch(patch)
                
                # Verify patch
                await self._verify_emergency_patch(patch)
                
                # Log patch application
                self.audit_log.append({
                    "type": "emergency_patch",
                    "vulnerability": vulnerability,
                    "patch": patch,
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            self.logger.error(f"Error applying emergency patch: {str(e)}")

    async def _verify_security_update(self, update: Dict[str, Any]):
        """Verify security update application."""
        try:
            # Verify update
            verification = await self.security_service.verify_security_update(update)
            
            if not verification.get("success"):
                raise RuntimeError(f"Security update verification failed: {verification.get('error')}")
                
        except Exception as e:
            self.logger.error(f"Error verifying security update: {str(e)}")
            raise

    async def _verify_emergency_patch(self, patch: Dict[str, Any]):
        """Verify emergency patch application."""
        try:
            # Verify patch
            verification = await self.security_service.verify_emergency_patch(patch)
            
            if not verification.get("success"):
                raise RuntimeError(f"Emergency patch verification failed: {verification.get('error')}")
                
        except Exception as e:
            self.logger.error(f"Error verifying emergency patch: {str(e)}")
            raise

    async def _validate_security_policies(self):
        """Validate security policies."""
        try:
            # Validate policies
            validation = await self.security_service.validate_security_policies(self.security_policies)
            
            if not validation.get("success"):
                raise RuntimeError(f"Security policy validation failed: {validation.get('error')}")
                
        except Exception as e:
            self.logger.error(f"Error validating security policies: {str(e)}")
            raise

    async def _validate_encryption(self):
        """Validate encryption setup."""
        try:
            # Validate encryption
            validation = await self.security_service.validate_encryption(self.encryption_keys)
            
            if not validation.get("success"):
                raise RuntimeError(f"Encryption validation failed: {validation.get('error')}")
                
        except Exception as e:
            self.logger.error(f"Error validating encryption: {str(e)}")
            raise

    async def _validate_access_control(self):
        """Validate access control setup."""
        try:
            # Validate access control
            validation = await self.security_service.validate_access_control(self.access_control)
            
            if not validation.get("success"):
                raise RuntimeError(f"Access control validation failed: {validation.get('error')}")
                
        except Exception as e:
            self.logger.error(f"Error validating access control: {str(e)}")
            raise

    async def _validate_incident_response(self):
        """Validate incident response setup."""
        try:
            # Validate incident response
            validation = await self.security_service.validate_incident_response(self.incident_response)
            
            if not validation.get("success"):
                raise RuntimeError(f"Incident response validation failed: {validation.get('error')}")
                
        except Exception as e:
            self.logger.error(f"Error validating incident response: {str(e)}")
            raise

    async def get_security_status(self) -> Dict[str, Any]:
        """Get current security status."""
        return {
            "security_alerts": len(self.security_alerts),
            "vulnerabilities": len(self.vulnerability_scans),
            "security_updates": len(self.security_updates),
            "incidents_handled": len(self.incident_response),
            "metrics": self.security_metrics,
            "last_scan": self.security_metrics["last_scan"]
        }

    async def _initialize_agents(self):
        """Initialize all agents with the integration service."""
        agent_classes = {
            "desktop_automation": DesktopAutomationAgent,
            "project_manager": ProjectManagerAgent,
            "myco_dao": MycoDAOAgent,
            "ip_tokenization": IPTokenizationAgent,
            "dashboard": DashboardAgent,
            "opportunity_scout": OpportunityScout
        }
        
        for agent_type, agent_config in self.config.get("agents", {}).items():
            if agent_type in agent_classes:
                try:
                    agent = agent_classes[agent_type](
                        agent_id=agent_config["agent_id"],
                        name=agent_config["name"],
                        config=agent_config
                    )
                    await agent.initialize(self.integration_service)
                    self.agents[agent.agent_id] = agent
                    self.logger.info(f"Agent {agent.agent_id} initialized")
                except Exception as e:
                    self.logger.error(f"Error initializing agent {agent_type}: {str(e)}")

    async def _start_deployment_workers(self):
        """Start tool deployment workers"""
        worker_count = self.config.get("deployment_workers", 3)
        for i in range(worker_count):
            worker = asyncio.create_task(self._deployment_worker(f"deployment_worker_{i}"))
            self.deployment_workers.append(worker)

    async def _start_update_workers(self):
        """Start agent update workers"""
        worker_count = self.config.get("update_workers", 2)
        for i in range(worker_count):
            worker = asyncio.create_task(self._update_worker(f"update_worker_{i}"))
            self.update_workers.append(worker)

    async def _deployment_worker(self, worker_id: str):
        """Worker for handling tool deployments"""
        while self.is_running:
            try:
                deployment = await self.tool_deployment_queue.get()
                await self._process_deployment(deployment)
                self.tool_deployment_queue.task_done()
            except Exception as e:
                self.logger.error(f"Deployment worker {worker_id} error: {str(e)}")
                await asyncio.sleep(1)

    async def _update_worker(self, worker_id: str):
        """Worker for handling agent updates"""
        while self.is_running:
            try:
                update = await self.agent_update_queue.get()
                await self._process_agent_update(update)
                self.agent_update_queue.task_done()
            except Exception as e:
                self.logger.error(f"Update worker {worker_id} error: {str(e)}")
                await asyncio.sleep(1)

    async def _process_deployment(self, deployment: Dict[str, Any]):
        """Process a tool deployment"""
        try:
            tool_id = deployment["tool_id"]
            server_id = deployment.get("server_id", "tool_integration")
            version = deployment.get("version", "latest")
            
            # Get tool and server
            tool = self.tools.get(tool_id)
            server = self.mcp_servers.get(server_id)
            
            if not tool or not server:
                raise ValueError(f"Tool {tool_id} or server {server_id} not found")
            
            # Prepare deployment package
            package = await self._prepare_deployment_package(tool, version)
            
            # Deploy to MCP server
            result = await server.execute_command(
                "deploy_tool",
                {
                    "tool_id": tool_id,
                    "package": package,
                    "version": version
                }
            )
            
            # Update tool status
            tool.status = "deployed"
            tool.last_deployment = datetime.now()
            tool.deployment_server = server_id
            
            self.logger.info(f"Tool {tool_id} deployed successfully to {server_id}")
            return result
        except Exception as e:
            self.logger.error(f"Deployment failed: {str(e)}")
            raise

    async def _process_agent_update(self, update: Dict[str, Any]):
        """Process an agent update"""
        try:
            agent_id = update["agent_id"]
            server_id = update.get("server_id", "primary")
            version = update.get("version", "latest")
            
            # Get agent and server
            agent = self.agents.get(agent_id)
            server = self.mcp_servers.get(server_id)
            
            if not agent or not server:
                raise ValueError(f"Agent {agent_id} or server {server_id} not found")
            
            # Prepare update package
            package = await self._prepare_agent_update(agent, version)
            
            # Update via MCP server
            result = await server.execute_command(
                "update_agent",
                {
                    "agent_id": agent_id,
                    "package": package,
                    "version": version
                }
            )
            
            # Update agent status
            agent.status = "updated"
            agent.last_update = datetime.now()
            agent.update_server = server_id
            
            self.logger.info(f"Agent {agent_id} updated successfully via {server_id}")
            return result
        except Exception as e:
            self.logger.error(f"Agent update failed: {str(e)}")
            raise

    async def _prepare_deployment_package(self, tool: Any, version: str) -> Dict[str, Any]:
        """Prepare a tool deployment package"""
        return {
            "tool_id": tool.tool_id,
            "version": version,
            "config": tool.config,
            "dependencies": tool.dependencies,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "package_type": "tool",
                "checksum": "calculated_checksum"
            }
        }

    async def _prepare_agent_update(self, agent: BaseAgent, version: str) -> Dict[str, Any]:
        """Prepare an agent update package"""
        return {
            "agent_id": agent.agent_id,
            "version": version,
            "config": agent.config,
            "capabilities": agent.capabilities,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "package_type": "agent",
                "checksum": "calculated_checksum"
            }
        }

    async def deploy_tool(self, tool_id: str, server_id: str = "tool_integration", version: str = "latest") -> Dict[str, Any]:
        """Queue a tool deployment"""
        deployment = {
            "tool_id": tool_id,
            "server_id": server_id,
            "version": version,
            "timestamp": datetime.now().isoformat()
        }
        await self.tool_deployment_queue.put(deployment)
        return {"status": "queued", "deployment": deployment}

    async def update_agent(self, agent_id: str, server_id: str = "primary", version: str = "latest") -> Dict[str, Any]:
        """Queue an agent update"""
        update = {
            "agent_id": agent_id,
            "server_id": server_id,
            "version": version,
            "timestamp": datetime.now().isoformat()
        }
        await self.agent_update_queue.put(update)
        return {"status": "queued", "update": update}

    async def get_deployment_status(self, tool_id: str) -> Dict[str, Any]:
        """Get deployment status for a tool"""
        tool = self.tools.get(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")
        
        return {
            "tool_id": tool_id,
            "status": tool.status,
            "last_deployment": tool.last_deployment,
            "deployment_server": tool.deployment_server
        }

    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get update status for an agent"""
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        return {
            "agent_id": agent_id,
            "status": agent.status,
            "last_update": agent.last_update,
            "update_server": agent.update_server
        }

    async def _load_mcp_servers(self):
        """Load and initialize MCP servers"""
        try:
            mcp_config_path = Path("mycosoft_mas/config/mcp_servers.yaml")
            if mcp_config_path.exists():
                with open(mcp_config_path) as f:
                    mcp_config = yaml.safe_load(f)
                
                for server_id, server_config in mcp_config["servers"].items():
                    server = MCPServer(server_config)
                    await server.initialize()
                    self.mcp_servers[server_id] = server
                    self.logger.info(f"MCP server {server.name} initialized")
        except Exception as e:
            self.logger.error(f"Error loading MCP servers: {str(e)}")
            raise

    async def add_mcp_server(self, server_id: str, config: Dict[str, Any]) -> MCPServer:
        """Add a new MCP server"""
        try:
            server = MCPServer(config)
            await server.initialize()
            self.mcp_servers[server_id] = server
            self.logger.info(f"Added new MCP server {server.name}")
            return server
        except Exception as e:
            self.logger.error(f"Error adding MCP server: {str(e)}")
            raise

    async def remove_mcp_server(self, server_id: str) -> None:
        """Remove an MCP server"""
        try:
            if server_id in self.mcp_servers:
                server = self.mcp_servers[server_id]
                await server.shutdown()
                del self.mcp_servers[server_id]
                self.logger.info(f"Removed MCP server {server_id}")
        except Exception as e:
            self.logger.error(f"Error removing MCP server {server_id}: {str(e)}")
            raise

    async def update_mcp_server(self, server_id: str, new_config: Dict[str, Any]) -> None:
        """Update an MCP server's configuration"""
        try:
            if server_id in self.mcp_servers:
                server = self.mcp_servers[server_id]
                await server.shutdown()
                
                new_server = MCPServer(new_config)
                await new_server.initialize()
                self.mcp_servers[server_id] = new_server
                
                self.logger.info(f"Updated MCP server {server_id}")
        except Exception as e:
            self.logger.error(f"Error updating MCP server {server_id}: {str(e)}")
            raise

    async def execute_mcp_command(self, server_id: str, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a command on a specific MCP server"""
        try:
            if server_id not in self.mcp_servers:
                raise ValueError(f"No MCP server found with ID {server_id}")
            
            server = self.mcp_servers[server_id]
            return await server.execute_command(command, params)
        except Exception as e:
            self.logger.error(f"Error executing MCP command: {str(e)}")
            raise

    async def deploy_tool(self, tool_id: str, server_id: str = "tool_integration") -> Dict[str, Any]:
        """Deploy a tool using the MCP server"""
        try:
            if tool_id not in self.tools:
                raise ValueError(f"No tool found with ID {tool_id}")
            
            tool = self.tools[tool_id]
            return await self.execute_mcp_command(
                server_id,
                "deploy_tool",
                {
                    "tool_id": tool_id,
                    "tool_config": tool.config
                }
            )
        except Exception as e:
            self.logger.error(f"Error deploying tool {tool_id}: {str(e)}")
            raise

    async def update_agent_via_mcp(self, agent_id: str, server_id: str = "primary") -> Dict[str, Any]:
        """Update an agent using the MCP server"""
        try:
            if agent_id not in self.agents:
                raise ValueError(f"No agent found with ID {agent_id}")
            
            agent = self.agents[agent_id]
            return await self.execute_mcp_command(
                server_id,
                "update_agent",
                {
                    "agent_id": agent_id,
                    "agent_config": agent.config
                }
            )
        except Exception as e:
            self.logger.error(f"Error updating agent {agent_id} via MCP: {str(e)}")
            raise

    async def _load_dependencies(self):
        """Load and verify all dependencies"""
        try:
            # Load dependency configuration
            deps_path = Path("mycosoft_mas/config/dependencies.yaml")
            if deps_path.exists():
                with open(deps_path) as f:
                    deps_config = yaml.safe_load(f)
                
                # Verify Python package dependencies
                for pkg, version in deps_config.get("python_packages", {}).items():
                    try:
                        pkg_version = importlib.import_module(pkg).__version__
                        if not semver.match(pkg_version, version):
                            raise ValueError(f"Package {pkg} version {pkg_version} does not match required version {version}")
                    except ImportError:
                        raise ImportError(f"Required package {pkg} not found")
                
                # Store dependency relationships
                self.dependencies = deps_config.get("agent_dependencies", {})
        except Exception as e:
            self.logger.error(f"Error loading dependencies: {str(e)}")
            raise

    async def _initialize_modules(self):
        """Initialize all modules"""
        try:
            # Discover and load modules
            modules_path = Path("mycosoft_mas/modules")
            for module_info in pkgutil.iter_modules([str(modules_path)]):
                try:
                    module = importlib.import_module(f"mycosoft_mas.modules.{module_info.name}")
                    if hasattr(module, "initialize"):
                        await module.initialize(self.config)
                    self.modules[module_info.name] = module
                    self.logger.info(f"Module {module_info.name} initialized")
                except Exception as e:
                    self.logger.error(f"Error initializing module {module_info.name}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error initializing modules: {str(e)}")
            raise

    async def _initialize_tools(self):
        """Initialize all tools"""
        try:
            # Load tool configuration
            tools_path = Path("mycosoft_mas/config/tools.yaml")
            if tools_path.exists():
                with open(tools_path) as f:
                    tools_config = yaml.safe_load(f)
                
                # Initialize each tool
                for tool_name, tool_config in tools_config.items():
                    try:
                        tool_module = importlib.import_module(f"mycosoft_mas.tools.{tool_name}")
                        tool_instance = tool_module.Tool(tool_config)
                        if hasattr(tool_instance, "initialize"):
                            await tool_instance.initialize()
                        self.tools[tool_name] = tool_instance
                        self.logger.info(f"Tool {tool_name} initialized")
                    except Exception as e:
                        self.logger.error(f"Error initializing tool {tool_name}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error initializing tools: {str(e)}")
            raise

    async def _create_agent(self, config: Dict[str, Any]) -> BaseAgent:
        """Create an agent instance with all required components"""
        try:
            # Get agent class
            agent_type = config.get("type")
            agent_class = self._get_agent_class(agent_type)
            
            # Enable desktop automation by default
            if "config" not in config:
                config["config"] = {}
            config["config"]["enable_desktop_automation"] = True
            
            # Create agent instance
            agent = agent_class(
                agent_id=config["agent_id"],
                name=config["name"],
                config=config["config"]
            )
            
            # Inject dependencies
            for dep_name in self.dependencies.get(agent_type, []):
                if dep_name in self.modules:
                    setattr(agent, dep_name, self.modules[dep_name])
                elif dep_name in self.tools:
                    setattr(agent, dep_name, self.tools[dep_name])
            
            return agent
        except Exception as e:
            self.logger.error(f"Error creating agent: {str(e)}")
            raise

    def _get_agent_class(self, agent_type: str) -> Type[BaseAgent]:
        """Get the agent class for the given type"""
        try:
            # Try to import the agent module
            agent_module = importlib.import_module(f"mycosoft_mas.agents.{agent_type}")
            
            # Get the agent class (convention: class name is AgentType + "Agent")
            class_name = f"{agent_type.title().replace('_', '')}Agent"
            agent_class = getattr(agent_module, class_name)
            
            if not issubclass(agent_class, BaseAgent):
                raise TypeError(f"{class_name} is not a subclass of BaseAgent")
            
            return agent_class
        except Exception as e:
            self.logger.error(f"Error getting agent class for {agent_type}: {str(e)}")
            raise

    async def add_agent(self, agent_config: Dict[str, Any]) -> BaseAgent:
        """Add a new agent to the system"""
        try:
            # Check dependencies
            agent_type = agent_config.get("type")
            for dep in self.dependencies.get(agent_type, []):
                if dep not in self.modules and dep not in self.tools:
                    raise ValueError(f"Missing dependency {dep} for agent type {agent_type}")
            
            # Create and initialize agent
            agent = await self._create_agent(agent_config)
            await agent.initialize()
            self.agents[agent.agent_id] = agent
            
            self.logger.info(f"Added new agent {agent.name}")
            return agent
        except Exception as e:
            self.logger.error(f"Error adding agent: {str(e)}")
            raise

    async def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from the system"""
        try:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                await agent.shutdown()
                del self.agents[agent_id]
                self.logger.info(f"Removed agent {agent_id}")
        except Exception as e:
            self.logger.error(f"Error removing agent {agent_id}: {str(e)}")
            raise

    async def update_agent(self, agent_id: str, new_config: Dict[str, Any]) -> None:
        """Update an agent's configuration"""
        try:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                await agent.shutdown()
                
                # Create new agent instance with updated config
                new_agent = await self._create_agent(new_config)
                await new_agent.initialize()
                self.agents[agent_id] = new_agent
                
                self.logger.info(f"Updated agent {agent_id}")
        except Exception as e:
            self.logger.error(f"Error updating agent {agent_id}: {str(e)}")
            raise

    async def handle_message(self, message: Message) -> None:
        """Handle messages with desktop automation fallback"""
        try:
            # Try to route to appropriate agent
            target_agent = self.agents.get(message.target_agent_id)
            if target_agent:
                await target_agent.handle_message(message)
            else:
                # If no specific agent is targeted and desktop automation is available,
                # try to handle it with desktop automation
                if self.desktop_automation and message.type in [MessageType.BROWSER, MessageType.DESKTOP]:
                    self.logger.info("Routing message to global desktop automation")
                    await self.desktop_automation.handle_message(message)
                else:
                    raise ValueError(f"No agent found with ID {message.target_agent_id}")
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of all agents and desktop automation"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "agents": {},
            "desktop_automation": None
        }

        # Check desktop automation health
        if self.desktop_automation:
            desktop_health = await self.desktop_automation.health_check()
            health_status["desktop_automation"] = {
                "status": "healthy" if desktop_health else "unhealthy",
                "metrics": self.desktop_automation.get_metrics()
            }

        # Check each agent's health
        for agent_id, agent in self.agents.items():
            try:
                agent_health = await agent.health_check()
                health_status["agents"][agent_id] = {
                    "status": "healthy" if agent_health else "unhealthy",
                    "metrics": agent.get_metrics()
                }
            except Exception as e:
                health_status["agents"][agent_id] = {
                    "status": "error",
                    "error": str(e)
                }

        # Update overall status if any component is unhealthy
        if any(agent["status"] != "healthy" for agent in health_status["agents"].values()):
            health_status["status"] = "unhealthy"
        if health_status["desktop_automation"] and health_status["desktop_automation"]["status"] != "healthy":
            health_status["status"] = "unhealthy"

        return health_status

    async def shutdown(self):
        """Shutdown all agents and desktop automation"""
        try:
            # Shutdown agents
            for agent in self.agents.values():
                await agent.shutdown()
            
            # Shutdown desktop automation
            if self.desktop_automation:
                await self.desktop_automation.shutdown()
            
            self.is_running = False
            self.logger.info("Orchestrator shut down successfully")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
            raise

    async def start(self):
        """Start all agents and monitoring."""
        try:
            # Start all agents
            for agent in self.agents.values():
                await agent.start()
            
            # Start metrics collection
            await self.integration_service.metrics_collector.start()
            
            self.logger.info("Orchestrator started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting orchestrator: {str(e)}")
            raise

    async def stop(self):
        """Stop all agents and monitoring."""
        try:
            self.is_running = False
            
            # Stop all agents
            for agent in self.agents.values():
                await agent.stop()
            
            # Stop integration service
            await self.integration_service.shutdown()
            
            self.logger.info("Orchestrator stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping orchestrator: {str(e)}")
            raise

    def get_agent_status(self) -> Dict[str, Any]:
        """Get current status of all agents."""
        return {
            agent_id: {
                "name": agent.name,
                "status": agent.status,
                "metrics": agent.get_metrics()
            }
            for agent_id, agent in self.agents.items()
        }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        return self.integration_service.get_system_metrics() if self.integration_service else {}

    async def monitor_system_evolution(self):
        """Monitor system evolution and technology changes."""
        while self.is_running:
            try:
                # Check for new technologies
                new_tech = await self.technology_tracker.check_for_updates()
                if new_tech:
                    await self._handle_new_technology(new_tech)
                
                # Check for system updates
                updates = await self.system_updates.check_updates()
                if updates:
                    await self._handle_system_updates(updates)
                
                # Check for security issues
                security_issues = await self.security_monitor.check_security()
                if security_issues:
                    await self._handle_security_issues(security_issues)
                
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                self.logger.error(f"Error in evolution monitoring: {str(e)}")
                await asyncio.sleep(60)
                
    async def _handle_new_technology(self, new_tech: Dict[str, Any]):
        """Handle new technology discoveries."""
        try:
            # Notify relevant agents
            for agent_id, agent in self.agents.items():
                if "technology_monitoring" in agent.capabilities:
                    await agent.handle_message(Message.create_technology_update(
                        sender="orchestrator",
                        receiver=agent_id,
                        technology=new_tech
                    ))
            
            # Update dependencies if needed
            if new_tech.get("requires_dependency_update"):
                await self.dependency_manager.update_dependencies(new_tech["dependencies"])
            
            # Update integrations if needed
            if new_tech.get("requires_integration_update"):
                await self.integration_manager.update_integrations(new_tech["integrations"])
                
        except Exception as e:
            self.logger.error(f"Error handling new technology: {str(e)}")
            
    async def _handle_system_updates(self, updates: Dict[str, Any]):
        """Handle system updates and upgrades."""
        try:
            # Check dependencies
            dependency_status = await self.dependency_manager.check_dependencies()
            if dependency_status["status"] == "conflict":
                await self._resolve_dependency_conflicts(dependency_status["conflicts"])
            
            # Update integrations
            for integration_id, update in updates.get("integrations", {}).items():
                await self.integration_manager.update_integration(integration_id, update)
            
            # Update tasks
            for task_id, update in updates.get("tasks", {}).items():
                await self.task_manager.update_task(task_id, update)
                
        except Exception as e:
            self.logger.error(f"Error handling system updates: {str(e)}")
            
    async def _handle_security_issues(self, issues: List[Dict[str, Any]]):
        """Handle security issues and alerts."""
        try:
            for issue in issues:
                # Notify security agent
                if "security_agent" in self.agents:
                    await self.agents["security_agent"].handle_message(
                        Message.create_security_alert(
                            sender="orchestrator",
                            receiver="security_agent",
                            alert_type=issue["type"],
                            message=issue["message"],
                            severity=issue["severity"]
                        )
                    )
                
                # Update security measures
                if issue.get("requires_security_update"):
                    await self.security_service.update_security_measures(issue["updates"])
                
                # Update dependencies if needed
                if issue.get("requires_dependency_update"):
                    await self.dependency_manager.update_dependencies(issue["dependencies"])
                    
        except Exception as e:
            self.logger.error(f"Error handling security issues: {str(e)}")
            
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "agents": {
                agent_id: agent.get_status()
                for agent_id, agent in self.agents.items()
            },
            "dependencies": await self.dependency_manager.get_status(),
            "integrations": await self.integration_manager.get_status(),
            "tasks": await self.task_manager.get_status(),
            "security": await self.security_service.get_status(),
            "evolution": {
                "new_technologies": await self.technology_tracker.get_status(),
                "pending_updates": await self.system_updates.get_status(),
                "security_issues": await self.security_monitor.get_status()
            }
        } 