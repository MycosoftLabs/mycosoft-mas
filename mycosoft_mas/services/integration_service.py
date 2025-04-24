"""
Integration Service for Mycosoft MAS
"""

from typing import Dict, Any, List, Optional
import logging
import asyncio
from datetime import datetime
import json
from pathlib import Path
from ..core.interfaces import AgentInterface
from ..core.knowledge_graph import KnowledgeGraph
from .websocket_server import WebSocketServer
from .metrics_collector import MetricsCollector
from .visualization_service import VisualizationService

logger = logging.getLogger(__name__)

class IntegrationService:
    """Service for handling integrations and data access."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the integration service.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(config.get("data_dir", "data"))
        self.data_dir.mkdir(exist_ok=True)
        self.connections = {}
        self.status = "initialized"
        self.metrics = {
            "requests_processed": 0,
            "errors": 0,
            "last_activity": None
        }
        
        # Initialize knowledge graph if not provided
        self.knowledge_graph = config.get("knowledge_graph") or KnowledgeGraph()
        
        # Initialize WebSocket server with knowledge graph
        self.websocket_server = WebSocketServer(
            knowledge_graph=self.knowledge_graph,
            host=config.get("websocket_host", "0.0.0.0"),
            port=config.get("websocket_port", 8765)
        )
        
        self.metrics_collector = MetricsCollector(
            websocket_server=self.websocket_server,
            interval=config.get("metrics_interval", 1.0)
        )
        self.visualization_service = VisualizationService(config)
        self.agents: Dict[str, AgentInterface] = {}
        self.running = False

    async def initialize(self):
        """Initialize the integration service."""
        self.status = "running"
        self.metrics["last_activity"] = datetime.now()
        self.running = True
        await self.websocket_server.start()
        await self.metrics_collector.start()
        await self.visualization_service.initialize()
        self.logger.info("Integration service initialized successfully")
        
    async def shutdown(self):
        """Shutdown the integration service."""
        self.status = "stopped"
        self.running = False
        await self.metrics_collector.stop()
        await self.websocket_server.stop()
        await self.visualization_service.shutdown()
        self.logger.info("Integration service shut down successfully")
        
    async def get_sales_data(self) -> Dict[str, Any]:
        """Get sales data from the data store.
        
        Returns:
            Dict containing sales data
        """
        try:
            sales_file = self.data_dir / "sales.json"
            if sales_file.exists():
                with open(sales_file, "r") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error getting sales data: {str(e)}")
            return {}
            
    async def get_customer_data(self) -> Dict[str, Any]:
        """Get customer data from the data store.
        
        Returns:
            Dict containing customer data
        """
        try:
            customer_file = self.data_dir / "customers.json"
            if customer_file.exists():
                with open(customer_file, "r") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error getting customer data: {str(e)}")
            return {}
            
    async def get_project_data(self) -> Dict[str, Any]:
        """Get project data from the data store.
        
        Returns:
            Dict containing project data
        """
        try:
            project_file = self.data_dir / "projects.json"
            if project_file.exists():
                with open(project_file, "r") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error getting project data: {str(e)}")
            return {}
            
    async def get_knowledge_data(self) -> Dict[str, Any]:
        """Get knowledge data from the data store.
        
        Returns:
            Dict containing knowledge data
        """
        try:
            knowledge_file = self.data_dir / "knowledge.json"
            if knowledge_file.exists():
                with open(knowledge_file, "r") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error getting knowledge data: {str(e)}")
            return {}
            
    async def save_sales_data(self, data: Dict[str, Any]):
        """Save sales data to the data store.
        
        Args:
            data: Sales data to save
        """
        try:
            sales_file = self.data_dir / "sales.json"
            with open(sales_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving sales data: {str(e)}")
            
    async def save_customer_data(self, data: Dict[str, Any]):
        """Save customer data to the data store.
        
        Args:
            data: Customer data to save
        """
        try:
            customer_file = self.data_dir / "customers.json"
            with open(customer_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving customer data: {str(e)}")
            
    async def save_project_data(self, data: Dict[str, Any]):
        """Save project data to the data store.
        
        Args:
            data: Project data to save
        """
        try:
            project_file = self.data_dir / "projects.json"
            with open(project_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving project data: {str(e)}")
            
    async def save_knowledge_data(self, data: Dict[str, Any]):
        """Save knowledge data to the data store.
        
        Args:
            data: Knowledge data to save
        """
        try:
            knowledge_file = self.data_dir / "knowledge.json"
            with open(knowledge_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving knowledge data: {str(e)}")
            
    async def connect_to_service(self, service_name: str, connection_params: Dict[str, Any]) -> bool:
        """Connect to an external service.
        
        Args:
            service_name: Name of the service to connect to
            connection_params: Connection parameters
            
        Returns:
            bool indicating success
        """
        try:
            # TODO: Implement actual service connections
            self.connections[service_name] = {
                "params": connection_params,
                "connected_at": datetime.now(),
                "status": "connected"
            }
            return True
        except Exception as e:
            self.logger.error(f"Error connecting to service {service_name}: {str(e)}")
            return False
            
    async def disconnect_from_service(self, service_name: str) -> bool:
        """Disconnect from an external service.
        
        Args:
            service_name: Name of the service to disconnect from
            
        Returns:
            bool indicating success
        """
        try:
            if service_name in self.connections:
                del self.connections[service_name]
            return True
        except Exception as e:
            self.logger.error(f"Error disconnecting from service {service_name}: {str(e)}")
            return False
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get the current metrics for the service.
        
        Returns:
            Dict containing the service metrics
        """
        return {
            **self.metrics,
            "status": self.status,
            "connections": len(self.connections),
            "uptime": (datetime.now() - self.metrics["last_activity"]).total_seconds() if self.metrics["last_activity"] else 0
        }

    async def register_agent(self, agent: AgentInterface):
        """Register an agent with the monitoring system."""
        try:
            self.agents[agent.agent_id] = agent
            await self.metrics_collector.update_agent_status(
                agent.agent_id,
                "active",
                {"name": agent.name, "type": agent.__class__.__name__}
            )
            self.logger.info(f"Agent {agent.agent_id} registered with monitoring system")
        except Exception as e:
            self.logger.error(f"Error registering agent {agent.agent_id}: {str(e)}")

    async def update_agent_metrics(self, agent_id: str, metrics: Dict[str, Any]):
        """Update metrics for a specific agent."""
        try:
            await self.visualization_service.update_metrics({
                "agents": {
                    agent_id: {
                        "timestamp": metrics.get("timestamp"),
                        "metrics": metrics
                    }
                }
            })
        except Exception as e:
            self.logger.error(f"Error updating metrics for agent {agent_id}: {str(e)}")

    async def broadcast_system_metrics(self):
        """Broadcast system-wide metrics to all connected clients."""
        try:
            system_metrics = await self.metrics_collector._collect_metrics()
            await self.visualization_service.update_metrics(system_metrics)
        except Exception as e:
            self.logger.error(f"Error broadcasting system metrics: {str(e)}")

    def get_agent_status(self) -> Dict[str, Any]:
        """Get current status of all registered agents."""
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
        return self.metrics_collector.last_metrics

    async def handle_websocket_connection(self, websocket):
        """Handle new WebSocket connections."""
        try:
            await self.visualization_service.connect_websocket(websocket)
            # Send initial data
            await websocket.send_json({
                "agents": self.get_agent_status(),
                "system": self.get_system_metrics()
            })
        except Exception as e:
            self.logger.error(f"Error handling WebSocket connection: {str(e)}")
            raise 