"""
Mycosoft MAS Startup Script

This script handles the procedural startup of the MAS and its components,
ensuring all services are properly initialized and checked before starting the dashboard.
"""

import asyncio
import logging
import sys
import time
import requests
from pathlib import Path
import docker
import yaml
from typing import Dict, Any, List

from mycosoft_mas.core.myca_main import MycosoftMAS
from mycosoft_mas.core.metrics_collector import MetricsCollector
from mycosoft_mas.core.agent_manager import AgentManager
from mycosoft_mas.core.knowledge_graph import KnowledgeGraph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/startup.log')
    ]
)
logger = logging.getLogger(__name__)

class StartupManager:
    """Manages the startup sequence of the MAS and its components."""
    
    def __init__(self):
        """Initialize the startup manager."""
        self.config = self._load_config()
        self.docker_client = docker.from_env()
        self.mas = None
        self.metrics_collector = None
        self.agent_manager = None
        self.knowledge_graph = None
        self.services = {
            "redis": {"port": 6379, "container": None},
            "prometheus": {"port": 9090, "container": None},
            "grafana": {"port": 3000, "container": None}
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml."""
        config_path = Path("config.yaml")
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
        
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    async def start_services(self) -> bool:
        """Start required services (Redis, Prometheus, Grafana)."""
        try:
            logger.info("Starting required services...")
            
            # Start Redis
            redis_container = self.docker_client.containers.run(
                "redis",
                detach=True,
                ports={'6379/tcp': 6379},
                name="mycosoft_redis"
            )
            self.services["redis"]["container"] = redis_container
            
            # Start Prometheus
            prometheus_container = self.docker_client.containers.run(
                "prom/prometheus",
                detach=True,
                ports={'9090/tcp': 9090},
                volumes={'./prometheus.yml': {'bind': '/etc/prometheus/prometheus.yml', 'mode': 'ro'}},
                name="mycosoft_prometheus"
            )
            self.services["prometheus"]["container"] = prometheus_container
            
            # Start Grafana
            grafana_container = self.docker_client.containers.run(
                "grafana/grafana",
                detach=True,
                ports={'3000/tcp': 3000},
                name="mycosoft_grafana"
            )
            self.services["grafana"]["container"] = grafana_container
            
            # Wait for services to be ready
            await self._wait_for_services()
            
            logger.info("All services started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start services: {str(e)}")
            return False
    
    async def _wait_for_services(self):
        """Wait for services to be ready."""
        for service, info in self.services.items():
            port = info["port"]
            max_retries = 30
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    response = requests.get(f"http://localhost:{port}")
                    if response.status_code == 200:
                        logger.info(f"{service.capitalize()} is ready")
                        break
                except requests.exceptions.ConnectionError:
                    retry_count += 1
                    await asyncio.sleep(1)
            
            if retry_count == max_retries:
                raise TimeoutError(f"Timeout waiting for {service} to start")
    
    async def initialize_mas(self) -> bool:
        """Initialize the MAS and its components."""
        try:
            logger.info("Initializing MAS components...")
            
            # Initialize MAS
            self.mas = MycosoftMAS(self.config)
            await self.mas.initialize()
            
            # Initialize metrics collector
            self.metrics_collector = MetricsCollector()
            await self.metrics_collector.initialize()
            
            # Initialize agent manager
            self.agent_manager = AgentManager()
            await self.agent_manager.initialize()
            
            # Initialize knowledge graph
            self.knowledge_graph = KnowledgeGraph()
            
            logger.info("MAS components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MAS: {str(e)}")
            return False
    
    async def check_system_health(self) -> bool:
        """Check the health of all system components."""
        try:
            logger.info("Checking system health...")
            
            # Check MAS health
            response = requests.get("http://localhost:8000/health")
            if response.status_code != 200:
                raise Exception("MAS health check failed")
            
            # Check metrics collector
            response = requests.get("http://localhost:8000/metrics")
            if response.status_code != 200:
                raise Exception("Metrics collector health check failed")
            
            # Check agent manager
            if not self.agent_manager.agents:
                raise Exception("No agents registered in agent manager")
            
            # Check knowledge graph
            if not self.knowledge_graph.nodes:
                raise Exception("Knowledge graph is empty")
            
            logger.info("System health check passed")
            return True
            
        except Exception as e:
            logger.error(f"System health check failed: {str(e)}")
            return False
    
    async def start_dashboard(self) -> bool:
        """Start the dashboard after all checks pass."""
        try:
            logger.info("Starting dashboard...")
            
            # Start dashboard
            dashboard_process = await asyncio.create_subprocess_exec(
                "python", "-m", "uvicorn", "mycosoft_mas.monitoring.dashboard:app",
                "--host", "0.0.0.0", "--port", "8000"
            )
            
            # Wait for dashboard to start
            await asyncio.sleep(5)
            
            # Check dashboard health
            response = requests.get("http://localhost:8000/dashboard/health")
            if response.status_code != 200:
                raise Exception("Dashboard health check failed")
            
            logger.info("Dashboard started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start dashboard: {str(e)}")
            return False
    
    async def shutdown(self):
        """Shutdown all components."""
        try:
            logger.info("Shutting down system...")
            
            # Stop dashboard
            if hasattr(self, 'dashboard_process'):
                self.dashboard_process.terminate()
            
            # Stop MAS
            if self.mas:
                await self.mas.shutdown()
            
            # Stop services
            for service in self.services.values():
                if service["container"]:
                    service["container"].stop()
                    service["container"].remove()
            
            logger.info("System shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")

async def main():
    """Main entry point for the startup script."""
    startup_manager = StartupManager()
    
    try:
        # Start required services
        if not await startup_manager.start_services():
            logger.error("Failed to start services")
            sys.exit(1)
        
        # Initialize MAS
        if not await startup_manager.initialize_mas():
            logger.error("Failed to initialize MAS")
            sys.exit(1)
        
        # Check system health
        if not await startup_manager.check_system_health():
            logger.error("System health check failed")
            sys.exit(1)
        
        # Start dashboard
        if not await startup_manager.start_dashboard():
            logger.error("Failed to start dashboard")
            sys.exit(1)
        
        logger.info("MAS and dashboard started successfully")
        
        # Keep the script running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        await startup_manager.shutdown()
    except Exception as e:
        logger.error(f"Error in startup process: {str(e)}")
        await startup_manager.shutdown()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 