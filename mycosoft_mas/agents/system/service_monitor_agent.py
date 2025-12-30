"""
Service Monitor Agent for MYCA
Monitors and maintains all system integrations and services.
"""

import asyncio
import logging
import requests
import subprocess
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class ServiceMonitorAgent(BaseAgent):
    """
    Agent that monitors and maintains all system services and integrations.
    
    Responsibilities:
    - Monitor service health
    - Auto-restart failed services
    - Report service status to MYCA
    - Maintain service availability
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """Initialize the Service Monitor Agent."""
        super().__init__(agent_id, name, config)
        
        # Service configurations
        self.services: Dict[str, Dict[str, Any]] = {
            "mycobrain": {
                "name": "MycoBrain Service",
                "port": 8765,
                "health_url": "http://localhost:8765/health",
                "command": ["python", "-m", "uvicorn", "mycobrain_service:app", "--host", "0.0.0.0", "--port", "8765"],
                "working_dir": None,  # Will be set dynamically
                "process_name": "uvicorn",
                "max_restarts": 10,
                "restart_delay": 5
            },
            # Add more services here as needed
        }
        
        # Monitoring state
        self.service_status: Dict[str, Dict[str, Any]] = {}
        self.restart_counts: Dict[str, int] = {}
        self.last_check: Dict[str, datetime] = {}
        
        # Monitoring interval
        self.check_interval = config.get("check_interval", 30)  # seconds
        self.monitoring_active = False
    
    async def initialize(self) -> bool:
        """Initialize the agent."""
        try:
            # Set working directories
            mas_root = Path(__file__).parent.parent.parent.parent.parent
            website_root = mas_root.parent / "WEBSITE" / "website"
            
            if "mycobrain" in self.services:
                self.services["mycobrain"]["working_dir"] = str(website_root / "services" / "mycobrain")
            
            # Initialize service status
            for service_id in self.services.keys():
                self.service_status[service_id] = {
                    "status": "unknown",
                    "last_check": None,
                    "uptime": None,
                    "restarts": 0,
                    "error": None
                }
                self.restart_counts[service_id] = 0
            
            self.status = AgentStatus.RUNNING
            logger.info(f"{self.name} initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.name}: {e}")
            self.status = AgentStatus.ERROR
            return False
    
    async def start(self) -> bool:
        """Start the agent."""
        try:
            self.monitoring_active = True
            asyncio.create_task(self._monitoring_loop())
            logger.info(f"{self.name} started")
            return True
        except Exception as e:
            logger.error(f"Failed to start {self.name}: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the agent."""
        self.monitoring_active = False
        logger.info(f"{self.name} stopped")
        return True
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_all_services()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_all_services(self):
        """Check all services."""
        for service_id, service_config in self.services.items():
            try:
                await self._check_service(service_id, service_config)
            except Exception as e:
                logger.error(f"Error checking service {service_id}: {e}")
                self.service_status[service_id]["status"] = "error"
                self.service_status[service_id]["error"] = str(e)
    
    async def _check_service(self, service_id: str, config: Dict[str, Any]):
        """Check a single service."""
        now = datetime.now()
        self.last_check[service_id] = now
        self.service_status[service_id]["last_check"] = now.isoformat()
        
        # Check if service is responding
        is_healthy = await self._check_service_health(service_id, config)
        
        if is_healthy:
            self.service_status[service_id]["status"] = "online"
            self.service_status[service_id]["error"] = None
            
            # Check uptime
            uptime = await self._get_service_uptime(service_id, config)
            self.service_status[service_id]["uptime"] = uptime
            
        else:
            self.service_status[service_id]["status"] = "offline"
            logger.warning(f"Service {service_id} is offline, attempting restart...")
            
            # Attempt to restart
            restart_success = await self._restart_service(service_id, config)
            
            if restart_success:
                self.restart_counts[service_id] += 1
                self.service_status[service_id]["restarts"] = self.restart_counts[service_id]
                logger.info(f"Service {service_id} restarted successfully")
            else:
                self.service_status[service_id]["error"] = "Failed to restart"
                logger.error(f"Failed to restart service {service_id}")
    
    async def _check_service_health(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Check if a service is healthy."""
        # Check health endpoint
        health_url = config.get("health_url")
        if health_url:
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200:
                    return True
            except Exception:
                pass
        
        # Check if process is running
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if process_name in proc.info['name'] or \
                       (proc.info['cmdline'] and any(process_name in str(cmd) for cmd in proc.info['cmdline'])):
                        # Check if it's listening on the expected port
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return True
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        return False
    
    async def _get_service_uptime(self, service_id: str, config: Dict[str, Any]) -> Optional[float]:
        """Get service uptime in seconds."""
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    if process_name in proc.info['name']:
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return time.time() - proc.info['create_time']
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return time.time() - proc.info['create_time']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return None
    
    async def _restart_service(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Restart a service."""
        # Check restart limits
        max_restarts = config.get("max_restarts", 10)
        if self.restart_counts[service_id] >= max_restarts:
            logger.error(f"Service {service_id} exceeded max restarts ({max_restarts})")
            return False
        
        try:
            # Kill existing process
            process_name = config.get("process_name")
            if process_name:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if process_name in proc.info['name']:
                            port = config.get("port")
                            if port:
                                try:
                                    connections = proc.connections()
                                    if any(conn.laddr.port == port for conn in connections):
                                        proc.terminate()
                                        proc.wait(timeout=5)
                                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.TimeoutExpired):
                                    try:
                                        proc.kill()
                                    except:
                                        pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            # Wait before restart
            restart_delay = config.get("restart_delay", 5)
            await asyncio.sleep(restart_delay)
            
            # Start service
            command = config.get("command", [])
            working_dir = config.get("working_dir")
            
            if command:
                subprocess.Popen(
                    command,
                    cwd=working_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                
                # Wait a moment for service to start
                await asyncio.sleep(3)
                
                # Check if it started successfully
                return await self._check_service_health(service_id, config)
            
            return False
            
        except Exception as e:
            logger.error(f"Error restarting service {service_id}: {e}")
            return False
    
    async def get_service_status(self, service_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of service(s)."""
        if service_id:
            return self.service_status.get(service_id, {})
        return self.service_status
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming messages."""
        msg_type = message.get("type")
        
        if msg_type == "get_status":
            service_id = message.get("service_id")
            status = await self.get_service_status(service_id)
            return {"status": "success", "data": status}
        
        elif msg_type == "restart_service":
            service_id = message.get("service_id")
            if service_id in self.services:
                success = await self._restart_service(service_id, self.services[service_id])
                return {"status": "success" if success else "error", "service_id": service_id}
            return {"status": "error", "message": f"Service {service_id} not found"}
        
        return {"status": "error", "message": "Unknown message type"}


# Fix missing import
import time
import sys







"""
Service Monitor Agent for MYCA
Monitors and maintains all system integrations and services.
"""

import asyncio
import logging
import requests
import subprocess
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class ServiceMonitorAgent(BaseAgent):
    """
    Agent that monitors and maintains all system services and integrations.
    
    Responsibilities:
    - Monitor service health
    - Auto-restart failed services
    - Report service status to MYCA
    - Maintain service availability
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """Initialize the Service Monitor Agent."""
        super().__init__(agent_id, name, config)
        
        # Service configurations
        self.services: Dict[str, Dict[str, Any]] = {
            "mycobrain": {
                "name": "MycoBrain Service",
                "port": 8765,
                "health_url": "http://localhost:8765/health",
                "command": ["python", "-m", "uvicorn", "mycobrain_service:app", "--host", "0.0.0.0", "--port", "8765"],
                "working_dir": None,  # Will be set dynamically
                "process_name": "uvicorn",
                "max_restarts": 10,
                "restart_delay": 5
            },
            # Add more services here as needed
        }
        
        # Monitoring state
        self.service_status: Dict[str, Dict[str, Any]] = {}
        self.restart_counts: Dict[str, int] = {}
        self.last_check: Dict[str, datetime] = {}
        
        # Monitoring interval
        self.check_interval = config.get("check_interval", 30)  # seconds
        self.monitoring_active = False
    
    async def initialize(self) -> bool:
        """Initialize the agent."""
        try:
            # Set working directories
            mas_root = Path(__file__).parent.parent.parent.parent.parent
            website_root = mas_root.parent / "WEBSITE" / "website"
            
            if "mycobrain" in self.services:
                self.services["mycobrain"]["working_dir"] = str(website_root / "services" / "mycobrain")
            
            # Initialize service status
            for service_id in self.services.keys():
                self.service_status[service_id] = {
                    "status": "unknown",
                    "last_check": None,
                    "uptime": None,
                    "restarts": 0,
                    "error": None
                }
                self.restart_counts[service_id] = 0
            
            self.status = AgentStatus.RUNNING
            logger.info(f"{self.name} initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.name}: {e}")
            self.status = AgentStatus.ERROR
            return False
    
    async def start(self) -> bool:
        """Start the agent."""
        try:
            self.monitoring_active = True
            asyncio.create_task(self._monitoring_loop())
            logger.info(f"{self.name} started")
            return True
        except Exception as e:
            logger.error(f"Failed to start {self.name}: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the agent."""
        self.monitoring_active = False
        logger.info(f"{self.name} stopped")
        return True
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_all_services()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_all_services(self):
        """Check all services."""
        for service_id, service_config in self.services.items():
            try:
                await self._check_service(service_id, service_config)
            except Exception as e:
                logger.error(f"Error checking service {service_id}: {e}")
                self.service_status[service_id]["status"] = "error"
                self.service_status[service_id]["error"] = str(e)
    
    async def _check_service(self, service_id: str, config: Dict[str, Any]):
        """Check a single service."""
        now = datetime.now()
        self.last_check[service_id] = now
        self.service_status[service_id]["last_check"] = now.isoformat()
        
        # Check if service is responding
        is_healthy = await self._check_service_health(service_id, config)
        
        if is_healthy:
            self.service_status[service_id]["status"] = "online"
            self.service_status[service_id]["error"] = None
            
            # Check uptime
            uptime = await self._get_service_uptime(service_id, config)
            self.service_status[service_id]["uptime"] = uptime
            
        else:
            self.service_status[service_id]["status"] = "offline"
            logger.warning(f"Service {service_id} is offline, attempting restart...")
            
            # Attempt to restart
            restart_success = await self._restart_service(service_id, config)
            
            if restart_success:
                self.restart_counts[service_id] += 1
                self.service_status[service_id]["restarts"] = self.restart_counts[service_id]
                logger.info(f"Service {service_id} restarted successfully")
            else:
                self.service_status[service_id]["error"] = "Failed to restart"
                logger.error(f"Failed to restart service {service_id}")
    
    async def _check_service_health(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Check if a service is healthy."""
        # Check health endpoint
        health_url = config.get("health_url")
        if health_url:
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200:
                    return True
            except Exception:
                pass
        
        # Check if process is running
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if process_name in proc.info['name'] or \
                       (proc.info['cmdline'] and any(process_name in str(cmd) for cmd in proc.info['cmdline'])):
                        # Check if it's listening on the expected port
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return True
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        return False
    
    async def _get_service_uptime(self, service_id: str, config: Dict[str, Any]) -> Optional[float]:
        """Get service uptime in seconds."""
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    if process_name in proc.info['name']:
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return time.time() - proc.info['create_time']
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return time.time() - proc.info['create_time']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return None
    
    async def _restart_service(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Restart a service."""
        # Check restart limits
        max_restarts = config.get("max_restarts", 10)
        if self.restart_counts[service_id] >= max_restarts:
            logger.error(f"Service {service_id} exceeded max restarts ({max_restarts})")
            return False
        
        try:
            # Kill existing process
            process_name = config.get("process_name")
            if process_name:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if process_name in proc.info['name']:
                            port = config.get("port")
                            if port:
                                try:
                                    connections = proc.connections()
                                    if any(conn.laddr.port == port for conn in connections):
                                        proc.terminate()
                                        proc.wait(timeout=5)
                                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.TimeoutExpired):
                                    try:
                                        proc.kill()
                                    except:
                                        pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            # Wait before restart
            restart_delay = config.get("restart_delay", 5)
            await asyncio.sleep(restart_delay)
            
            # Start service
            command = config.get("command", [])
            working_dir = config.get("working_dir")
            
            if command:
                subprocess.Popen(
                    command,
                    cwd=working_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                
                # Wait a moment for service to start
                await asyncio.sleep(3)
                
                # Check if it started successfully
                return await self._check_service_health(service_id, config)
            
            return False
            
        except Exception as e:
            logger.error(f"Error restarting service {service_id}: {e}")
            return False
    
    async def get_service_status(self, service_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of service(s)."""
        if service_id:
            return self.service_status.get(service_id, {})
        return self.service_status
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming messages."""
        msg_type = message.get("type")
        
        if msg_type == "get_status":
            service_id = message.get("service_id")
            status = await self.get_service_status(service_id)
            return {"status": "success", "data": status}
        
        elif msg_type == "restart_service":
            service_id = message.get("service_id")
            if service_id in self.services:
                success = await self._restart_service(service_id, self.services[service_id])
                return {"status": "success" if success else "error", "service_id": service_id}
            return {"status": "error", "message": f"Service {service_id} not found"}
        
        return {"status": "error", "message": "Unknown message type"}


# Fix missing import
import time
import sys








"""
Service Monitor Agent for MYCA
Monitors and maintains all system integrations and services.
"""

import asyncio
import logging
import requests
import subprocess
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class ServiceMonitorAgent(BaseAgent):
    """
    Agent that monitors and maintains all system services and integrations.
    
    Responsibilities:
    - Monitor service health
    - Auto-restart failed services
    - Report service status to MYCA
    - Maintain service availability
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """Initialize the Service Monitor Agent."""
        super().__init__(agent_id, name, config)
        
        # Service configurations
        self.services: Dict[str, Dict[str, Any]] = {
            "mycobrain": {
                "name": "MycoBrain Service",
                "port": 8765,
                "health_url": "http://localhost:8765/health",
                "command": ["python", "-m", "uvicorn", "mycobrain_service:app", "--host", "0.0.0.0", "--port", "8765"],
                "working_dir": None,  # Will be set dynamically
                "process_name": "uvicorn",
                "max_restarts": 10,
                "restart_delay": 5
            },
            # Add more services here as needed
        }
        
        # Monitoring state
        self.service_status: Dict[str, Dict[str, Any]] = {}
        self.restart_counts: Dict[str, int] = {}
        self.last_check: Dict[str, datetime] = {}
        
        # Monitoring interval
        self.check_interval = config.get("check_interval", 30)  # seconds
        self.monitoring_active = False
    
    async def initialize(self) -> bool:
        """Initialize the agent."""
        try:
            # Set working directories
            mas_root = Path(__file__).parent.parent.parent.parent.parent
            website_root = mas_root.parent / "WEBSITE" / "website"
            
            if "mycobrain" in self.services:
                self.services["mycobrain"]["working_dir"] = str(website_root / "services" / "mycobrain")
            
            # Initialize service status
            for service_id in self.services.keys():
                self.service_status[service_id] = {
                    "status": "unknown",
                    "last_check": None,
                    "uptime": None,
                    "restarts": 0,
                    "error": None
                }
                self.restart_counts[service_id] = 0
            
            self.status = AgentStatus.RUNNING
            logger.info(f"{self.name} initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.name}: {e}")
            self.status = AgentStatus.ERROR
            return False
    
    async def start(self) -> bool:
        """Start the agent."""
        try:
            self.monitoring_active = True
            asyncio.create_task(self._monitoring_loop())
            logger.info(f"{self.name} started")
            return True
        except Exception as e:
            logger.error(f"Failed to start {self.name}: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the agent."""
        self.monitoring_active = False
        logger.info(f"{self.name} stopped")
        return True
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_all_services()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_all_services(self):
        """Check all services."""
        for service_id, service_config in self.services.items():
            try:
                await self._check_service(service_id, service_config)
            except Exception as e:
                logger.error(f"Error checking service {service_id}: {e}")
                self.service_status[service_id]["status"] = "error"
                self.service_status[service_id]["error"] = str(e)
    
    async def _check_service(self, service_id: str, config: Dict[str, Any]):
        """Check a single service."""
        now = datetime.now()
        self.last_check[service_id] = now
        self.service_status[service_id]["last_check"] = now.isoformat()
        
        # Check if service is responding
        is_healthy = await self._check_service_health(service_id, config)
        
        if is_healthy:
            self.service_status[service_id]["status"] = "online"
            self.service_status[service_id]["error"] = None
            
            # Check uptime
            uptime = await self._get_service_uptime(service_id, config)
            self.service_status[service_id]["uptime"] = uptime
            
        else:
            self.service_status[service_id]["status"] = "offline"
            logger.warning(f"Service {service_id} is offline, attempting restart...")
            
            # Attempt to restart
            restart_success = await self._restart_service(service_id, config)
            
            if restart_success:
                self.restart_counts[service_id] += 1
                self.service_status[service_id]["restarts"] = self.restart_counts[service_id]
                logger.info(f"Service {service_id} restarted successfully")
            else:
                self.service_status[service_id]["error"] = "Failed to restart"
                logger.error(f"Failed to restart service {service_id}")
    
    async def _check_service_health(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Check if a service is healthy."""
        # Check health endpoint
        health_url = config.get("health_url")
        if health_url:
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200:
                    return True
            except Exception:
                pass
        
        # Check if process is running
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if process_name in proc.info['name'] or \
                       (proc.info['cmdline'] and any(process_name in str(cmd) for cmd in proc.info['cmdline'])):
                        # Check if it's listening on the expected port
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return True
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        return False
    
    async def _get_service_uptime(self, service_id: str, config: Dict[str, Any]) -> Optional[float]:
        """Get service uptime in seconds."""
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    if process_name in proc.info['name']:
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return time.time() - proc.info['create_time']
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return time.time() - proc.info['create_time']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return None
    
    async def _restart_service(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Restart a service."""
        # Check restart limits
        max_restarts = config.get("max_restarts", 10)
        if self.restart_counts[service_id] >= max_restarts:
            logger.error(f"Service {service_id} exceeded max restarts ({max_restarts})")
            return False
        
        try:
            # Kill existing process
            process_name = config.get("process_name")
            if process_name:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if process_name in proc.info['name']:
                            port = config.get("port")
                            if port:
                                try:
                                    connections = proc.connections()
                                    if any(conn.laddr.port == port for conn in connections):
                                        proc.terminate()
                                        proc.wait(timeout=5)
                                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.TimeoutExpired):
                                    try:
                                        proc.kill()
                                    except:
                                        pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            # Wait before restart
            restart_delay = config.get("restart_delay", 5)
            await asyncio.sleep(restart_delay)
            
            # Start service
            command = config.get("command", [])
            working_dir = config.get("working_dir")
            
            if command:
                subprocess.Popen(
                    command,
                    cwd=working_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                
                # Wait a moment for service to start
                await asyncio.sleep(3)
                
                # Check if it started successfully
                return await self._check_service_health(service_id, config)
            
            return False
            
        except Exception as e:
            logger.error(f"Error restarting service {service_id}: {e}")
            return False
    
    async def get_service_status(self, service_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of service(s)."""
        if service_id:
            return self.service_status.get(service_id, {})
        return self.service_status
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming messages."""
        msg_type = message.get("type")
        
        if msg_type == "get_status":
            service_id = message.get("service_id")
            status = await self.get_service_status(service_id)
            return {"status": "success", "data": status}
        
        elif msg_type == "restart_service":
            service_id = message.get("service_id")
            if service_id in self.services:
                success = await self._restart_service(service_id, self.services[service_id])
                return {"status": "success" if success else "error", "service_id": service_id}
            return {"status": "error", "message": f"Service {service_id} not found"}
        
        return {"status": "error", "message": "Unknown message type"}


# Fix missing import
import time
import sys







"""
Service Monitor Agent for MYCA
Monitors and maintains all system integrations and services.
"""

import asyncio
import logging
import requests
import subprocess
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class ServiceMonitorAgent(BaseAgent):
    """
    Agent that monitors and maintains all system services and integrations.
    
    Responsibilities:
    - Monitor service health
    - Auto-restart failed services
    - Report service status to MYCA
    - Maintain service availability
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """Initialize the Service Monitor Agent."""
        super().__init__(agent_id, name, config)
        
        # Service configurations
        self.services: Dict[str, Dict[str, Any]] = {
            "mycobrain": {
                "name": "MycoBrain Service",
                "port": 8765,
                "health_url": "http://localhost:8765/health",
                "command": ["python", "-m", "uvicorn", "mycobrain_service:app", "--host", "0.0.0.0", "--port", "8765"],
                "working_dir": None,  # Will be set dynamically
                "process_name": "uvicorn",
                "max_restarts": 10,
                "restart_delay": 5
            },
            # Add more services here as needed
        }
        
        # Monitoring state
        self.service_status: Dict[str, Dict[str, Any]] = {}
        self.restart_counts: Dict[str, int] = {}
        self.last_check: Dict[str, datetime] = {}
        
        # Monitoring interval
        self.check_interval = config.get("check_interval", 30)  # seconds
        self.monitoring_active = False
    
    async def initialize(self) -> bool:
        """Initialize the agent."""
        try:
            # Set working directories
            mas_root = Path(__file__).parent.parent.parent.parent.parent
            website_root = mas_root.parent / "WEBSITE" / "website"
            
            if "mycobrain" in self.services:
                self.services["mycobrain"]["working_dir"] = str(website_root / "services" / "mycobrain")
            
            # Initialize service status
            for service_id in self.services.keys():
                self.service_status[service_id] = {
                    "status": "unknown",
                    "last_check": None,
                    "uptime": None,
                    "restarts": 0,
                    "error": None
                }
                self.restart_counts[service_id] = 0
            
            self.status = AgentStatus.RUNNING
            logger.info(f"{self.name} initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.name}: {e}")
            self.status = AgentStatus.ERROR
            return False
    
    async def start(self) -> bool:
        """Start the agent."""
        try:
            self.monitoring_active = True
            asyncio.create_task(self._monitoring_loop())
            logger.info(f"{self.name} started")
            return True
        except Exception as e:
            logger.error(f"Failed to start {self.name}: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the agent."""
        self.monitoring_active = False
        logger.info(f"{self.name} stopped")
        return True
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_all_services()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_all_services(self):
        """Check all services."""
        for service_id, service_config in self.services.items():
            try:
                await self._check_service(service_id, service_config)
            except Exception as e:
                logger.error(f"Error checking service {service_id}: {e}")
                self.service_status[service_id]["status"] = "error"
                self.service_status[service_id]["error"] = str(e)
    
    async def _check_service(self, service_id: str, config: Dict[str, Any]):
        """Check a single service."""
        now = datetime.now()
        self.last_check[service_id] = now
        self.service_status[service_id]["last_check"] = now.isoformat()
        
        # Check if service is responding
        is_healthy = await self._check_service_health(service_id, config)
        
        if is_healthy:
            self.service_status[service_id]["status"] = "online"
            self.service_status[service_id]["error"] = None
            
            # Check uptime
            uptime = await self._get_service_uptime(service_id, config)
            self.service_status[service_id]["uptime"] = uptime
            
        else:
            self.service_status[service_id]["status"] = "offline"
            logger.warning(f"Service {service_id} is offline, attempting restart...")
            
            # Attempt to restart
            restart_success = await self._restart_service(service_id, config)
            
            if restart_success:
                self.restart_counts[service_id] += 1
                self.service_status[service_id]["restarts"] = self.restart_counts[service_id]
                logger.info(f"Service {service_id} restarted successfully")
            else:
                self.service_status[service_id]["error"] = "Failed to restart"
                logger.error(f"Failed to restart service {service_id}")
    
    async def _check_service_health(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Check if a service is healthy."""
        # Check health endpoint
        health_url = config.get("health_url")
        if health_url:
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200:
                    return True
            except Exception:
                pass
        
        # Check if process is running
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if process_name in proc.info['name'] or \
                       (proc.info['cmdline'] and any(process_name in str(cmd) for cmd in proc.info['cmdline'])):
                        # Check if it's listening on the expected port
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return True
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        return False
    
    async def _get_service_uptime(self, service_id: str, config: Dict[str, Any]) -> Optional[float]:
        """Get service uptime in seconds."""
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    if process_name in proc.info['name']:
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return time.time() - proc.info['create_time']
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return time.time() - proc.info['create_time']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return None
    
    async def _restart_service(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Restart a service."""
        # Check restart limits
        max_restarts = config.get("max_restarts", 10)
        if self.restart_counts[service_id] >= max_restarts:
            logger.error(f"Service {service_id} exceeded max restarts ({max_restarts})")
            return False
        
        try:
            # Kill existing process
            process_name = config.get("process_name")
            if process_name:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if process_name in proc.info['name']:
                            port = config.get("port")
                            if port:
                                try:
                                    connections = proc.connections()
                                    if any(conn.laddr.port == port for conn in connections):
                                        proc.terminate()
                                        proc.wait(timeout=5)
                                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.TimeoutExpired):
                                    try:
                                        proc.kill()
                                    except:
                                        pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            # Wait before restart
            restart_delay = config.get("restart_delay", 5)
            await asyncio.sleep(restart_delay)
            
            # Start service
            command = config.get("command", [])
            working_dir = config.get("working_dir")
            
            if command:
                subprocess.Popen(
                    command,
                    cwd=working_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                
                # Wait a moment for service to start
                await asyncio.sleep(3)
                
                # Check if it started successfully
                return await self._check_service_health(service_id, config)
            
            return False
            
        except Exception as e:
            logger.error(f"Error restarting service {service_id}: {e}")
            return False
    
    async def get_service_status(self, service_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of service(s)."""
        if service_id:
            return self.service_status.get(service_id, {})
        return self.service_status
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming messages."""
        msg_type = message.get("type")
        
        if msg_type == "get_status":
            service_id = message.get("service_id")
            status = await self.get_service_status(service_id)
            return {"status": "success", "data": status}
        
        elif msg_type == "restart_service":
            service_id = message.get("service_id")
            if service_id in self.services:
                success = await self._restart_service(service_id, self.services[service_id])
                return {"status": "success" if success else "error", "service_id": service_id}
            return {"status": "error", "message": f"Service {service_id} not found"}
        
        return {"status": "error", "message": "Unknown message type"}


# Fix missing import
import time
import sys











"""
Service Monitor Agent for MYCA
Monitors and maintains all system integrations and services.
"""

import asyncio
import logging
import requests
import subprocess
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class ServiceMonitorAgent(BaseAgent):
    """
    Agent that monitors and maintains all system services and integrations.
    
    Responsibilities:
    - Monitor service health
    - Auto-restart failed services
    - Report service status to MYCA
    - Maintain service availability
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """Initialize the Service Monitor Agent."""
        super().__init__(agent_id, name, config)
        
        # Service configurations
        self.services: Dict[str, Dict[str, Any]] = {
            "mycobrain": {
                "name": "MycoBrain Service",
                "port": 8765,
                "health_url": "http://localhost:8765/health",
                "command": ["python", "-m", "uvicorn", "mycobrain_service:app", "--host", "0.0.0.0", "--port", "8765"],
                "working_dir": None,  # Will be set dynamically
                "process_name": "uvicorn",
                "max_restarts": 10,
                "restart_delay": 5
            },
            # Add more services here as needed
        }
        
        # Monitoring state
        self.service_status: Dict[str, Dict[str, Any]] = {}
        self.restart_counts: Dict[str, int] = {}
        self.last_check: Dict[str, datetime] = {}
        
        # Monitoring interval
        self.check_interval = config.get("check_interval", 30)  # seconds
        self.monitoring_active = False
    
    async def initialize(self) -> bool:
        """Initialize the agent."""
        try:
            # Set working directories
            mas_root = Path(__file__).parent.parent.parent.parent.parent
            website_root = mas_root.parent / "WEBSITE" / "website"
            
            if "mycobrain" in self.services:
                self.services["mycobrain"]["working_dir"] = str(website_root / "services" / "mycobrain")
            
            # Initialize service status
            for service_id in self.services.keys():
                self.service_status[service_id] = {
                    "status": "unknown",
                    "last_check": None,
                    "uptime": None,
                    "restarts": 0,
                    "error": None
                }
                self.restart_counts[service_id] = 0
            
            self.status = AgentStatus.RUNNING
            logger.info(f"{self.name} initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.name}: {e}")
            self.status = AgentStatus.ERROR
            return False
    
    async def start(self) -> bool:
        """Start the agent."""
        try:
            self.monitoring_active = True
            asyncio.create_task(self._monitoring_loop())
            logger.info(f"{self.name} started")
            return True
        except Exception as e:
            logger.error(f"Failed to start {self.name}: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the agent."""
        self.monitoring_active = False
        logger.info(f"{self.name} stopped")
        return True
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_all_services()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_all_services(self):
        """Check all services."""
        for service_id, service_config in self.services.items():
            try:
                await self._check_service(service_id, service_config)
            except Exception as e:
                logger.error(f"Error checking service {service_id}: {e}")
                self.service_status[service_id]["status"] = "error"
                self.service_status[service_id]["error"] = str(e)
    
    async def _check_service(self, service_id: str, config: Dict[str, Any]):
        """Check a single service."""
        now = datetime.now()
        self.last_check[service_id] = now
        self.service_status[service_id]["last_check"] = now.isoformat()
        
        # Check if service is responding
        is_healthy = await self._check_service_health(service_id, config)
        
        if is_healthy:
            self.service_status[service_id]["status"] = "online"
            self.service_status[service_id]["error"] = None
            
            # Check uptime
            uptime = await self._get_service_uptime(service_id, config)
            self.service_status[service_id]["uptime"] = uptime
            
        else:
            self.service_status[service_id]["status"] = "offline"
            logger.warning(f"Service {service_id} is offline, attempting restart...")
            
            # Attempt to restart
            restart_success = await self._restart_service(service_id, config)
            
            if restart_success:
                self.restart_counts[service_id] += 1
                self.service_status[service_id]["restarts"] = self.restart_counts[service_id]
                logger.info(f"Service {service_id} restarted successfully")
            else:
                self.service_status[service_id]["error"] = "Failed to restart"
                logger.error(f"Failed to restart service {service_id}")
    
    async def _check_service_health(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Check if a service is healthy."""
        # Check health endpoint
        health_url = config.get("health_url")
        if health_url:
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200:
                    return True
            except Exception:
                pass
        
        # Check if process is running
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if process_name in proc.info['name'] or \
                       (proc.info['cmdline'] and any(process_name in str(cmd) for cmd in proc.info['cmdline'])):
                        # Check if it's listening on the expected port
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return True
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        return False
    
    async def _get_service_uptime(self, service_id: str, config: Dict[str, Any]) -> Optional[float]:
        """Get service uptime in seconds."""
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    if process_name in proc.info['name']:
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return time.time() - proc.info['create_time']
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return time.time() - proc.info['create_time']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return None
    
    async def _restart_service(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Restart a service."""
        # Check restart limits
        max_restarts = config.get("max_restarts", 10)
        if self.restart_counts[service_id] >= max_restarts:
            logger.error(f"Service {service_id} exceeded max restarts ({max_restarts})")
            return False
        
        try:
            # Kill existing process
            process_name = config.get("process_name")
            if process_name:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if process_name in proc.info['name']:
                            port = config.get("port")
                            if port:
                                try:
                                    connections = proc.connections()
                                    if any(conn.laddr.port == port for conn in connections):
                                        proc.terminate()
                                        proc.wait(timeout=5)
                                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.TimeoutExpired):
                                    try:
                                        proc.kill()
                                    except:
                                        pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            # Wait before restart
            restart_delay = config.get("restart_delay", 5)
            await asyncio.sleep(restart_delay)
            
            # Start service
            command = config.get("command", [])
            working_dir = config.get("working_dir")
            
            if command:
                subprocess.Popen(
                    command,
                    cwd=working_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                
                # Wait a moment for service to start
                await asyncio.sleep(3)
                
                # Check if it started successfully
                return await self._check_service_health(service_id, config)
            
            return False
            
        except Exception as e:
            logger.error(f"Error restarting service {service_id}: {e}")
            return False
    
    async def get_service_status(self, service_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of service(s)."""
        if service_id:
            return self.service_status.get(service_id, {})
        return self.service_status
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming messages."""
        msg_type = message.get("type")
        
        if msg_type == "get_status":
            service_id = message.get("service_id")
            status = await self.get_service_status(service_id)
            return {"status": "success", "data": status}
        
        elif msg_type == "restart_service":
            service_id = message.get("service_id")
            if service_id in self.services:
                success = await self._restart_service(service_id, self.services[service_id])
                return {"status": "success" if success else "error", "service_id": service_id}
            return {"status": "error", "message": f"Service {service_id} not found"}
        
        return {"status": "error", "message": "Unknown message type"}


# Fix missing import
import time
import sys







"""
Service Monitor Agent for MYCA
Monitors and maintains all system integrations and services.
"""

import asyncio
import logging
import requests
import subprocess
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class ServiceMonitorAgent(BaseAgent):
    """
    Agent that monitors and maintains all system services and integrations.
    
    Responsibilities:
    - Monitor service health
    - Auto-restart failed services
    - Report service status to MYCA
    - Maintain service availability
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """Initialize the Service Monitor Agent."""
        super().__init__(agent_id, name, config)
        
        # Service configurations
        self.services: Dict[str, Dict[str, Any]] = {
            "mycobrain": {
                "name": "MycoBrain Service",
                "port": 8765,
                "health_url": "http://localhost:8765/health",
                "command": ["python", "-m", "uvicorn", "mycobrain_service:app", "--host", "0.0.0.0", "--port", "8765"],
                "working_dir": None,  # Will be set dynamically
                "process_name": "uvicorn",
                "max_restarts": 10,
                "restart_delay": 5
            },
            # Add more services here as needed
        }
        
        # Monitoring state
        self.service_status: Dict[str, Dict[str, Any]] = {}
        self.restart_counts: Dict[str, int] = {}
        self.last_check: Dict[str, datetime] = {}
        
        # Monitoring interval
        self.check_interval = config.get("check_interval", 30)  # seconds
        self.monitoring_active = False
    
    async def initialize(self) -> bool:
        """Initialize the agent."""
        try:
            # Set working directories
            mas_root = Path(__file__).parent.parent.parent.parent.parent
            website_root = mas_root.parent / "WEBSITE" / "website"
            
            if "mycobrain" in self.services:
                self.services["mycobrain"]["working_dir"] = str(website_root / "services" / "mycobrain")
            
            # Initialize service status
            for service_id in self.services.keys():
                self.service_status[service_id] = {
                    "status": "unknown",
                    "last_check": None,
                    "uptime": None,
                    "restarts": 0,
                    "error": None
                }
                self.restart_counts[service_id] = 0
            
            self.status = AgentStatus.RUNNING
            logger.info(f"{self.name} initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.name}: {e}")
            self.status = AgentStatus.ERROR
            return False
    
    async def start(self) -> bool:
        """Start the agent."""
        try:
            self.monitoring_active = True
            asyncio.create_task(self._monitoring_loop())
            logger.info(f"{self.name} started")
            return True
        except Exception as e:
            logger.error(f"Failed to start {self.name}: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the agent."""
        self.monitoring_active = False
        logger.info(f"{self.name} stopped")
        return True
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_all_services()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_all_services(self):
        """Check all services."""
        for service_id, service_config in self.services.items():
            try:
                await self._check_service(service_id, service_config)
            except Exception as e:
                logger.error(f"Error checking service {service_id}: {e}")
                self.service_status[service_id]["status"] = "error"
                self.service_status[service_id]["error"] = str(e)
    
    async def _check_service(self, service_id: str, config: Dict[str, Any]):
        """Check a single service."""
        now = datetime.now()
        self.last_check[service_id] = now
        self.service_status[service_id]["last_check"] = now.isoformat()
        
        # Check if service is responding
        is_healthy = await self._check_service_health(service_id, config)
        
        if is_healthy:
            self.service_status[service_id]["status"] = "online"
            self.service_status[service_id]["error"] = None
            
            # Check uptime
            uptime = await self._get_service_uptime(service_id, config)
            self.service_status[service_id]["uptime"] = uptime
            
        else:
            self.service_status[service_id]["status"] = "offline"
            logger.warning(f"Service {service_id} is offline, attempting restart...")
            
            # Attempt to restart
            restart_success = await self._restart_service(service_id, config)
            
            if restart_success:
                self.restart_counts[service_id] += 1
                self.service_status[service_id]["restarts"] = self.restart_counts[service_id]
                logger.info(f"Service {service_id} restarted successfully")
            else:
                self.service_status[service_id]["error"] = "Failed to restart"
                logger.error(f"Failed to restart service {service_id}")
    
    async def _check_service_health(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Check if a service is healthy."""
        # Check health endpoint
        health_url = config.get("health_url")
        if health_url:
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200:
                    return True
            except Exception:
                pass
        
        # Check if process is running
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if process_name in proc.info['name'] or \
                       (proc.info['cmdline'] and any(process_name in str(cmd) for cmd in proc.info['cmdline'])):
                        # Check if it's listening on the expected port
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return True
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        return False
    
    async def _get_service_uptime(self, service_id: str, config: Dict[str, Any]) -> Optional[float]:
        """Get service uptime in seconds."""
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    if process_name in proc.info['name']:
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return time.time() - proc.info['create_time']
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return time.time() - proc.info['create_time']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return None
    
    async def _restart_service(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Restart a service."""
        # Check restart limits
        max_restarts = config.get("max_restarts", 10)
        if self.restart_counts[service_id] >= max_restarts:
            logger.error(f"Service {service_id} exceeded max restarts ({max_restarts})")
            return False
        
        try:
            # Kill existing process
            process_name = config.get("process_name")
            if process_name:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if process_name in proc.info['name']:
                            port = config.get("port")
                            if port:
                                try:
                                    connections = proc.connections()
                                    if any(conn.laddr.port == port for conn in connections):
                                        proc.terminate()
                                        proc.wait(timeout=5)
                                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.TimeoutExpired):
                                    try:
                                        proc.kill()
                                    except:
                                        pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            # Wait before restart
            restart_delay = config.get("restart_delay", 5)
            await asyncio.sleep(restart_delay)
            
            # Start service
            command = config.get("command", [])
            working_dir = config.get("working_dir")
            
            if command:
                subprocess.Popen(
                    command,
                    cwd=working_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                
                # Wait a moment for service to start
                await asyncio.sleep(3)
                
                # Check if it started successfully
                return await self._check_service_health(service_id, config)
            
            return False
            
        except Exception as e:
            logger.error(f"Error restarting service {service_id}: {e}")
            return False
    
    async def get_service_status(self, service_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of service(s)."""
        if service_id:
            return self.service_status.get(service_id, {})
        return self.service_status
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming messages."""
        msg_type = message.get("type")
        
        if msg_type == "get_status":
            service_id = message.get("service_id")
            status = await self.get_service_status(service_id)
            return {"status": "success", "data": status}
        
        elif msg_type == "restart_service":
            service_id = message.get("service_id")
            if service_id in self.services:
                success = await self._restart_service(service_id, self.services[service_id])
                return {"status": "success" if success else "error", "service_id": service_id}
            return {"status": "error", "message": f"Service {service_id} not found"}
        
        return {"status": "error", "message": "Unknown message type"}


# Fix missing import
import time
import sys








"""
Service Monitor Agent for MYCA
Monitors and maintains all system integrations and services.
"""

import asyncio
import logging
import requests
import subprocess
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class ServiceMonitorAgent(BaseAgent):
    """
    Agent that monitors and maintains all system services and integrations.
    
    Responsibilities:
    - Monitor service health
    - Auto-restart failed services
    - Report service status to MYCA
    - Maintain service availability
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """Initialize the Service Monitor Agent."""
        super().__init__(agent_id, name, config)
        
        # Service configurations
        self.services: Dict[str, Dict[str, Any]] = {
            "mycobrain": {
                "name": "MycoBrain Service",
                "port": 8765,
                "health_url": "http://localhost:8765/health",
                "command": ["python", "-m", "uvicorn", "mycobrain_service:app", "--host", "0.0.0.0", "--port", "8765"],
                "working_dir": None,  # Will be set dynamically
                "process_name": "uvicorn",
                "max_restarts": 10,
                "restart_delay": 5
            },
            # Add more services here as needed
        }
        
        # Monitoring state
        self.service_status: Dict[str, Dict[str, Any]] = {}
        self.restart_counts: Dict[str, int] = {}
        self.last_check: Dict[str, datetime] = {}
        
        # Monitoring interval
        self.check_interval = config.get("check_interval", 30)  # seconds
        self.monitoring_active = False
    
    async def initialize(self) -> bool:
        """Initialize the agent."""
        try:
            # Set working directories
            mas_root = Path(__file__).parent.parent.parent.parent.parent
            website_root = mas_root.parent / "WEBSITE" / "website"
            
            if "mycobrain" in self.services:
                self.services["mycobrain"]["working_dir"] = str(website_root / "services" / "mycobrain")
            
            # Initialize service status
            for service_id in self.services.keys():
                self.service_status[service_id] = {
                    "status": "unknown",
                    "last_check": None,
                    "uptime": None,
                    "restarts": 0,
                    "error": None
                }
                self.restart_counts[service_id] = 0
            
            self.status = AgentStatus.RUNNING
            logger.info(f"{self.name} initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.name}: {e}")
            self.status = AgentStatus.ERROR
            return False
    
    async def start(self) -> bool:
        """Start the agent."""
        try:
            self.monitoring_active = True
            asyncio.create_task(self._monitoring_loop())
            logger.info(f"{self.name} started")
            return True
        except Exception as e:
            logger.error(f"Failed to start {self.name}: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the agent."""
        self.monitoring_active = False
        logger.info(f"{self.name} stopped")
        return True
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_all_services()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_all_services(self):
        """Check all services."""
        for service_id, service_config in self.services.items():
            try:
                await self._check_service(service_id, service_config)
            except Exception as e:
                logger.error(f"Error checking service {service_id}: {e}")
                self.service_status[service_id]["status"] = "error"
                self.service_status[service_id]["error"] = str(e)
    
    async def _check_service(self, service_id: str, config: Dict[str, Any]):
        """Check a single service."""
        now = datetime.now()
        self.last_check[service_id] = now
        self.service_status[service_id]["last_check"] = now.isoformat()
        
        # Check if service is responding
        is_healthy = await self._check_service_health(service_id, config)
        
        if is_healthy:
            self.service_status[service_id]["status"] = "online"
            self.service_status[service_id]["error"] = None
            
            # Check uptime
            uptime = await self._get_service_uptime(service_id, config)
            self.service_status[service_id]["uptime"] = uptime
            
        else:
            self.service_status[service_id]["status"] = "offline"
            logger.warning(f"Service {service_id} is offline, attempting restart...")
            
            # Attempt to restart
            restart_success = await self._restart_service(service_id, config)
            
            if restart_success:
                self.restart_counts[service_id] += 1
                self.service_status[service_id]["restarts"] = self.restart_counts[service_id]
                logger.info(f"Service {service_id} restarted successfully")
            else:
                self.service_status[service_id]["error"] = "Failed to restart"
                logger.error(f"Failed to restart service {service_id}")
    
    async def _check_service_health(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Check if a service is healthy."""
        # Check health endpoint
        health_url = config.get("health_url")
        if health_url:
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200:
                    return True
            except Exception:
                pass
        
        # Check if process is running
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if process_name in proc.info['name'] or \
                       (proc.info['cmdline'] and any(process_name in str(cmd) for cmd in proc.info['cmdline'])):
                        # Check if it's listening on the expected port
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return True
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        return False
    
    async def _get_service_uptime(self, service_id: str, config: Dict[str, Any]) -> Optional[float]:
        """Get service uptime in seconds."""
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    if process_name in proc.info['name']:
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return time.time() - proc.info['create_time']
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return time.time() - proc.info['create_time']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return None
    
    async def _restart_service(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Restart a service."""
        # Check restart limits
        max_restarts = config.get("max_restarts", 10)
        if self.restart_counts[service_id] >= max_restarts:
            logger.error(f"Service {service_id} exceeded max restarts ({max_restarts})")
            return False
        
        try:
            # Kill existing process
            process_name = config.get("process_name")
            if process_name:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if process_name in proc.info['name']:
                            port = config.get("port")
                            if port:
                                try:
                                    connections = proc.connections()
                                    if any(conn.laddr.port == port for conn in connections):
                                        proc.terminate()
                                        proc.wait(timeout=5)
                                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.TimeoutExpired):
                                    try:
                                        proc.kill()
                                    except:
                                        pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            # Wait before restart
            restart_delay = config.get("restart_delay", 5)
            await asyncio.sleep(restart_delay)
            
            # Start service
            command = config.get("command", [])
            working_dir = config.get("working_dir")
            
            if command:
                subprocess.Popen(
                    command,
                    cwd=working_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                
                # Wait a moment for service to start
                await asyncio.sleep(3)
                
                # Check if it started successfully
                return await self._check_service_health(service_id, config)
            
            return False
            
        except Exception as e:
            logger.error(f"Error restarting service {service_id}: {e}")
            return False
    
    async def get_service_status(self, service_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of service(s)."""
        if service_id:
            return self.service_status.get(service_id, {})
        return self.service_status
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming messages."""
        msg_type = message.get("type")
        
        if msg_type == "get_status":
            service_id = message.get("service_id")
            status = await self.get_service_status(service_id)
            return {"status": "success", "data": status}
        
        elif msg_type == "restart_service":
            service_id = message.get("service_id")
            if service_id in self.services:
                success = await self._restart_service(service_id, self.services[service_id])
                return {"status": "success" if success else "error", "service_id": service_id}
            return {"status": "error", "message": f"Service {service_id} not found"}
        
        return {"status": "error", "message": "Unknown message type"}


# Fix missing import
import time
import sys







"""
Service Monitor Agent for MYCA
Monitors and maintains all system integrations and services.
"""

import asyncio
import logging
import requests
import subprocess
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class ServiceMonitorAgent(BaseAgent):
    """
    Agent that monitors and maintains all system services and integrations.
    
    Responsibilities:
    - Monitor service health
    - Auto-restart failed services
    - Report service status to MYCA
    - Maintain service availability
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """Initialize the Service Monitor Agent."""
        super().__init__(agent_id, name, config)
        
        # Service configurations
        self.services: Dict[str, Dict[str, Any]] = {
            "mycobrain": {
                "name": "MycoBrain Service",
                "port": 8765,
                "health_url": "http://localhost:8765/health",
                "command": ["python", "-m", "uvicorn", "mycobrain_service:app", "--host", "0.0.0.0", "--port", "8765"],
                "working_dir": None,  # Will be set dynamically
                "process_name": "uvicorn",
                "max_restarts": 10,
                "restart_delay": 5
            },
            # Add more services here as needed
        }
        
        # Monitoring state
        self.service_status: Dict[str, Dict[str, Any]] = {}
        self.restart_counts: Dict[str, int] = {}
        self.last_check: Dict[str, datetime] = {}
        
        # Monitoring interval
        self.check_interval = config.get("check_interval", 30)  # seconds
        self.monitoring_active = False
    
    async def initialize(self) -> bool:
        """Initialize the agent."""
        try:
            # Set working directories
            mas_root = Path(__file__).parent.parent.parent.parent.parent
            website_root = mas_root.parent / "WEBSITE" / "website"
            
            if "mycobrain" in self.services:
                self.services["mycobrain"]["working_dir"] = str(website_root / "services" / "mycobrain")
            
            # Initialize service status
            for service_id in self.services.keys():
                self.service_status[service_id] = {
                    "status": "unknown",
                    "last_check": None,
                    "uptime": None,
                    "restarts": 0,
                    "error": None
                }
                self.restart_counts[service_id] = 0
            
            self.status = AgentStatus.RUNNING
            logger.info(f"{self.name} initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.name}: {e}")
            self.status = AgentStatus.ERROR
            return False
    
    async def start(self) -> bool:
        """Start the agent."""
        try:
            self.monitoring_active = True
            asyncio.create_task(self._monitoring_loop())
            logger.info(f"{self.name} started")
            return True
        except Exception as e:
            logger.error(f"Failed to start {self.name}: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the agent."""
        self.monitoring_active = False
        logger.info(f"{self.name} stopped")
        return True
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._check_all_services()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_all_services(self):
        """Check all services."""
        for service_id, service_config in self.services.items():
            try:
                await self._check_service(service_id, service_config)
            except Exception as e:
                logger.error(f"Error checking service {service_id}: {e}")
                self.service_status[service_id]["status"] = "error"
                self.service_status[service_id]["error"] = str(e)
    
    async def _check_service(self, service_id: str, config: Dict[str, Any]):
        """Check a single service."""
        now = datetime.now()
        self.last_check[service_id] = now
        self.service_status[service_id]["last_check"] = now.isoformat()
        
        # Check if service is responding
        is_healthy = await self._check_service_health(service_id, config)
        
        if is_healthy:
            self.service_status[service_id]["status"] = "online"
            self.service_status[service_id]["error"] = None
            
            # Check uptime
            uptime = await self._get_service_uptime(service_id, config)
            self.service_status[service_id]["uptime"] = uptime
            
        else:
            self.service_status[service_id]["status"] = "offline"
            logger.warning(f"Service {service_id} is offline, attempting restart...")
            
            # Attempt to restart
            restart_success = await self._restart_service(service_id, config)
            
            if restart_success:
                self.restart_counts[service_id] += 1
                self.service_status[service_id]["restarts"] = self.restart_counts[service_id]
                logger.info(f"Service {service_id} restarted successfully")
            else:
                self.service_status[service_id]["error"] = "Failed to restart"
                logger.error(f"Failed to restart service {service_id}")
    
    async def _check_service_health(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Check if a service is healthy."""
        # Check health endpoint
        health_url = config.get("health_url")
        if health_url:
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200:
                    return True
            except Exception:
                pass
        
        # Check if process is running
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if process_name in proc.info['name'] or \
                       (proc.info['cmdline'] and any(process_name in str(cmd) for cmd in proc.info['cmdline'])):
                        # Check if it's listening on the expected port
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return True
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        return False
    
    async def _get_service_uptime(self, service_id: str, config: Dict[str, Any]) -> Optional[float]:
        """Get service uptime in seconds."""
        process_name = config.get("process_name")
        if process_name:
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    if process_name in proc.info['name']:
                        port = config.get("port")
                        if port:
                            try:
                                connections = proc.connections()
                                if any(conn.laddr.port == port for conn in connections):
                                    return time.time() - proc.info['create_time']
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        else:
                            return time.time() - proc.info['create_time']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return None
    
    async def _restart_service(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Restart a service."""
        # Check restart limits
        max_restarts = config.get("max_restarts", 10)
        if self.restart_counts[service_id] >= max_restarts:
            logger.error(f"Service {service_id} exceeded max restarts ({max_restarts})")
            return False
        
        try:
            # Kill existing process
            process_name = config.get("process_name")
            if process_name:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if process_name in proc.info['name']:
                            port = config.get("port")
                            if port:
                                try:
                                    connections = proc.connections()
                                    if any(conn.laddr.port == port for conn in connections):
                                        proc.terminate()
                                        proc.wait(timeout=5)
                                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.TimeoutExpired):
                                    try:
                                        proc.kill()
                                    except:
                                        pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            # Wait before restart
            restart_delay = config.get("restart_delay", 5)
            await asyncio.sleep(restart_delay)
            
            # Start service
            command = config.get("command", [])
            working_dir = config.get("working_dir")
            
            if command:
                subprocess.Popen(
                    command,
                    cwd=working_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                
                # Wait a moment for service to start
                await asyncio.sleep(3)
                
                # Check if it started successfully
                return await self._check_service_health(service_id, config)
            
            return False
            
        except Exception as e:
            logger.error(f"Error restarting service {service_id}: {e}")
            return False
    
    async def get_service_status(self, service_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of service(s)."""
        if service_id:
            return self.service_status.get(service_id, {})
        return self.service_status
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming messages."""
        msg_type = message.get("type")
        
        if msg_type == "get_status":
            service_id = message.get("service_id")
            status = await self.get_service_status(service_id)
            return {"status": "success", "data": status}
        
        elif msg_type == "restart_service":
            service_id = message.get("service_id")
            if service_id in self.services:
                success = await self._restart_service(service_id, self.services[service_id])
                return {"status": "success" if success else "error", "service_id": service_id}
            return {"status": "error", "message": f"Service {service_id} not found"}
        
        return {"status": "error", "message": "Unknown message type"}


# Fix missing import
import time
import sys











