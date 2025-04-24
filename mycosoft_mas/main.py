"""
Mycosoft MAS - Main Application Module

This module contains the main application class for the Multi-Agent System.
"""

from typing import Dict, Any, List, Optional
import logging
import asyncio
from pathlib import Path
import redis
from prometheus_client import start_http_server, Counter, Gauge, Histogram

from .orchestrator import Orchestrator
from .agents.base_agent import BaseAgent
from .agents.cluster_manager import ClusterManager
from .services.evolution_monitor import EvolutionMonitor
from .services.security_monitor import SecurityMonitor
from .services.technology_tracker import TechnologyTracker
from .services.system_updates import SystemUpdates
from .integrations.integration_manager import IntegrationManager
from .dependencies.dependency_manager import DependencyManager
from .tasks.task_manager import TaskManager
from .monitoring.metrics import MetricsCollector
from .web.dashboard import DashboardServer

logger = logging.getLogger(__name__)

class MASApplication:
    """Main application class for the Multi-Agent System."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the MAS application."""
        self.config = config
        self.redis_client = redis.Redis(
            host=config.get('redis_host', 'localhost'),
            port=config.get('redis_port', 6379),
            db=config.get('redis_db', 0)
        )
        
        # Core components
        self.orchestrator = Orchestrator(config)
        self.cluster_manager = ClusterManager(config)
        self.integration_manager = IntegrationManager()
        self.dependency_manager = DependencyManager()
        self.task_manager = TaskManager()
        
        # Monitoring services
        self.evolution_monitor = EvolutionMonitor()
        self.security_monitor = SecurityMonitor()
        self.technology_tracker = TechnologyTracker()
        self.system_updates = SystemUpdates()
        
        # Metrics and monitoring
        self.metrics_collector = MetricsCollector()
        self.prometheus_port = config.get('prometheus_port', 8000)
        
        # Web interface
        self.dashboard = DashboardServer(config)
        
        # Agent registry
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_clusters: Dict[str, List[str]] = {}
        
    async def start(self) -> None:
        """Start the MAS application."""
        try:
            # Start Prometheus metrics server
            start_http_server(self.prometheus_port)
            
            # Initialize Redis connection
            self.redis_client.ping()
            
            # Start core components
            await self.orchestrator.start()
            await self.cluster_manager.start()
            await self.integration_manager.start()
            await self.dependency_manager.start()
            await self.task_manager.start()
            
            # Start monitoring services
            await asyncio.gather(
                self.evolution_monitor.check_for_updates(),
                self.security_monitor.check_security(),
                self.technology_tracker.check_for_updates(),
                self.system_updates.check_for_updates()
            )
            
            # Start web dashboard
            await self.dashboard.start()
            
            # Initialize health checks
            await self._initialize_health_checks()
            
            logger.info("MAS application started successfully")
            
        except Exception as e:
            logger.error(f"Error starting MAS application: {str(e)}")
            raise
            
    async def stop(self) -> None:
        """Stop the MAS application."""
        try:
            # Stop all agents
            for agent in self.agents.values():
                await agent.stop()
                
            # Stop core components
            await self.orchestrator.stop()
            await self.cluster_manager.stop()
            await self.integration_manager.stop()
            await self.dependency_manager.stop()
            await self.task_manager.stop()
            
            # Stop web dashboard
            await self.dashboard.stop()
            
            # Close Redis connection
            self.redis_client.close()
            
            logger.info("MAS application stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping MAS application: {str(e)}")
            raise
            
    async def register_agent(self, agent: BaseAgent, cluster_id: Optional[str] = None) -> bool:
        """Register a new agent with the system."""
        try:
            if agent.agent_id in self.agents:
                logger.warning(f"Agent {agent.agent_id} already registered")
                return False
                
            # Register with orchestrator
            if not await self.orchestrator.register_agent(agent):
                return False
                
            # Add to agent registry
            self.agents[agent.agent_id] = agent
            
            # Assign to cluster if specified
            if cluster_id:
                if cluster_id not in self.agent_clusters:
                    self.agent_clusters[cluster_id] = []
                self.agent_clusters[cluster_id].append(agent.agent_id)
                await self.cluster_manager.add_agent_to_cluster(agent, cluster_id)
                
            # Update metrics
            self.metrics_collector.record_agent_registration(agent.agent_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error registering agent: {str(e)}")
            return False
            
    async def _initialize_health_checks(self) -> None:
        """Initialize health check endpoints."""
        # Service health checks
        self.metrics_collector.record_service_health('orchestrator', True)
        self.metrics_collector.record_service_health('cluster_manager', True)
        self.metrics_collector.record_service_health('integration_manager', True)
        self.metrics_collector.record_service_health('dependency_manager', True)
        self.metrics_collector.record_service_health('task_manager', True)
        
        # Resource health checks
        self.metrics_collector.record_resource_health('redis', True)
        self.metrics_collector.record_resource_health('prometheus', True)
        self.metrics_collector.record_resource_health('dashboard', True)
        
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the MAS application."""
        return {
            'agents': {
                'total_count': len(self.agents),
                'clusters': self.agent_clusters,
                'status': {agent_id: agent.get_status() for agent_id, agent in self.agents.items()}
            },
            'services': {
                'orchestrator': self.orchestrator.get_status(),
                'cluster_manager': self.cluster_manager.get_status(),
                'integration_manager': self.integration_manager.get_status(),
                'dependency_manager': self.dependency_manager.get_status(),
                'task_manager': self.task_manager.get_status()
            },
            'monitoring': {
                'evolution': self.evolution_monitor.get_status(),
                'security': self.security_monitor.get_status(),
                'technology': self.technology_tracker.get_status(),
                'system': self.system_updates.get_status()
            },
            'metrics': self.metrics_collector.get_status(),
            'resources': {
                'redis': self.redis_client.ping(),
                'prometheus': True,
                'dashboard': self.dashboard.is_running()
            }
        } 