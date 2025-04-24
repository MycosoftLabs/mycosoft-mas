"""
Mycosoft MAS Main Application

This module serves as the main entry point for the Mycosoft Multi-Agent System (MAS).
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app, generate_latest
import time
from datetime import datetime
import yaml
import argparse
from prometheus_fastapi_instrumentator import Instrumentator

from mycosoft_mas.agents.messaging.message_broker import MessageBroker
from mycosoft_mas.agents.messaging.communication_service import CommunicationService
from mycosoft_mas.agents.messaging.error_logging_service import ErrorLoggingService
from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.mycology_bio_agent import MycologyBioAgent
from mycosoft_mas.agents.financial.financial_agent import FinancialAgent
from mycosoft_mas.agents.corporate.corporate_operations_agent import CorporateOperationsAgent
from mycosoft_mas.agents.marketing_agent import MarketingAgent
from mycosoft_mas.agents.project_manager_agent import ProjectManagerAgent
from mycosoft_mas.agents.myco_dao_agent import MycoDAOAgent
from mycosoft_mas.agents.ip_tokenization_agent import IPTokenizationAgent
from mycosoft_mas.agents.dashboard_agent import DashboardAgent
from mycosoft_mas.agents.opportunity_scout import OpportunityScout
from mycosoft_mas.orchestrator import Orchestrator
from mycosoft_mas.agents.base_agent import AgentStatus
from mycosoft_mas.services.integration_service import IntegrationService
from mycosoft_mas.core.knowledge_graph import KnowledgeGraph
from mycosoft_mas.monitoring.dashboard import app as dashboard_app
from .security import get_current_user
from .routers import agents, tasks, dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mycosoft_mas.log')
    ]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])
ERROR_COUNT = Counter('http_errors_total', 'Total HTTP errors', ['method', 'endpoint', 'error_type'])
AGENT_STATUS = Gauge('agent_status', 'Agent status', ['agent_name'])
SERVICE_STATUS = Gauge('service_status', 'Service status', ['service_name'])

class MycosoftMAS:
    """Main application class for the Mycosoft MAS."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Mycosoft MAS.
        
        Args:
            config: Configuration dictionary for the MAS
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create data directory
        self.data_dir = Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logs directory
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize services
        self.message_broker = MessageBroker(config.get("messaging", {}))
        self.communication_service = CommunicationService(config.get("communication", {}))
        self.error_logging_service = ErrorLoggingService(config.get("error_logging", {}))
        
        # Initialize agents
        self.agents: List[BaseAgent] = []
        
        # Create FastAPI app
        self.app = FastAPI(
            title="Mycosoft MAS",
            description="Mycosoft Multi-Agent System API",
            version="1.0.0"
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Mount Prometheus metrics endpoint
        self.metrics_app = make_asgi_app()
        self.app.mount("/metrics", self.metrics_app)
        
        # Mount dashboard at /dashboard with prefix
        dashboard_app.root_path = "/dashboard"
        self.app.mount("/dashboard", dashboard_app)
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""
        # Include routers
        self.app.include_router(agents)
        self.app.include_router(tasks)
        self.app.include_router(dashboard)

        @self.app.get("/")
        async def root():
            """Root endpoint."""
            start_time = time.time()
            REQUEST_COUNT.labels(method='GET', endpoint='/', status='200').inc()
            try:
                return {"status": "ok", "message": "Mycosoft MAS is running"}
            finally:
                REQUEST_LATENCY.labels(method='GET', endpoint='/').observe(time.time() - start_time)
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            start_time = time.time()
            REQUEST_COUNT.labels(method='GET', endpoint='/health', status='200').inc()
            try:
                health_data = {
                    "status": "ok",
                    "agents": [{
                        "name": agent.__class__.__name__,
                        "status": agent.status.value if hasattr(agent.status, 'value') else str(agent.status)
                    } for agent in self.agents],
                    "services": {
                        "message_broker": self.message_broker.status,
                        "communication_service": self.communication_service.status,
                        "error_logging_service": self.error_logging_service.status
                    }
                }
                
                # Update Prometheus metrics
                for agent in self.agents:
                    agent_status = agent.status.value if hasattr(agent.status, 'value') else str(agent.status)
                    AGENT_STATUS.labels(agent_name=agent.__class__.__name__).set(
                        1 if agent_status == AgentStatus.ACTIVE.value else 0
                    )
                
                SERVICE_STATUS.labels(service_name='message_broker').set(
                    1 if self.message_broker.status == 'running' else 0
                )
                SERVICE_STATUS.labels(service_name='communication_service').set(
                    1 if self.communication_service.status == 'running' else 0
                )
                SERVICE_STATUS.labels(service_name='error_logging_service').set(
                    1 if self.error_logging_service.status == 'running' else 0
                )
                
                return health_data
            except Exception as e:
                REQUEST_COUNT.labels(method='GET', endpoint='/health', status='500').inc()
                ERROR_COUNT.labels(method='GET', endpoint='/health', error_type=str(type(e).__name__)).inc()
                self.logger.error(f"Health check failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
            finally:
                REQUEST_LATENCY.labels(method='GET', endpoint='/health').observe(time.time() - start_time)
        
        @self.app.get("/metrics")
        async def metrics():
            """Metrics endpoint."""
            return generate_latest()
    
    async def initialize(self) -> None:
        """Initialize the MAS."""
        try:
            self.logger.info("Initializing Mycosoft MAS")
            
            # Start services
            await self.message_broker.start()
            await self.communication_service.start()
            await self.error_logging_service.start()
            
            # Initialize agents
            mycology_config = self.config.get("mycology", {})
            financial_config = self.config.get("financial", {})
            corporate_config = self.config.get("corporate", {})
            marketing_config = self.config.get("marketing", {})
            project_config = self.config.get("project", {})
            mycodao_config = self.config.get("mycodao", {})
            ip_config = self.config.get("ip", {})
            dashboard_config = self.config.get("dashboard", {})
            opportunity_scout_config = self.config.get("opportunity_scout", {})
            
            # Create knowledge graph
            self.knowledge_graph = KnowledgeGraph()
            
            # Create integration service
            self.integration_service = IntegrationService(
                config={
                    "websocket_host": "0.0.0.0",
                    "websocket_port": 8765,
                    "metrics_interval": 1.0,
                    "knowledge_graph": self.knowledge_graph
                }
            )
            
            self.agents = [
                MycologyBioAgent(
                    agent_id=mycology_config["agent_id"],
                    name=mycology_config["name"],
                    config=mycology_config
                ),
                FinancialAgent(
                    agent_id=financial_config["agent_id"],
                    name=financial_config["name"],
                    config=financial_config
                ),
                CorporateOperationsAgent(
                    agent_id=corporate_config["agent_id"],
                    name=corporate_config["name"],
                    config=corporate_config
                ),
                MarketingAgent(
                    agent_id=marketing_config["agent_id"],
                    name=marketing_config["name"],
                    config=marketing_config
                ),
                ProjectManagerAgent(
                    agent_id=project_config["agent_id"],
                    name=project_config["name"],
                    config=project_config
                ),
                MycoDAOAgent(
                    agent_id=mycodao_config["agent_id"],
                    name=mycodao_config["name"],
                    config=mycodao_config
                ),
                IPTokenizationAgent(
                    agent_id=ip_config["agent_id"],
                    name=ip_config["name"],
                    config=ip_config
                ),
                DashboardAgent(
                    agent_id=dashboard_config["agent_id"],
                    name=dashboard_config["name"],
                    config=dashboard_config
                ),
                OpportunityScout(
                    agent_id=opportunity_scout_config["agent_id"],
                    name=opportunity_scout_config["name"],
                    config=opportunity_scout_config
                )
            ]
            
            # Start agents
            for agent in self.agents:
                try:
                    await agent.initialize(self.integration_service)
                    self.logger.info(f"Agent {agent.__class__.__name__} initialized")
                except Exception as e:
                    self.logger.error(f"Failed to initialize agent {agent.__class__.__name__}: {str(e)}")
                    await self.error_logging_service.log_error(
                        "agent_initialization_error",
                        {
                            "agent": agent.__class__.__name__,
                            "error": str(e)
                        }
                    )
            
            self.logger.info("Mycosoft MAS initialization complete")
        except Exception as e:
            self.logger.error(f"Failed to initialize Mycosoft MAS: {str(e)}")
            await self.error_logging_service.log_error(
                "mas_initialization_error",
                {"error": str(e)}
            )
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the MAS."""
        try:
            self.logger.info("Shutting down Mycosoft MAS")
            
            # Stop agents
            for agent in self.agents:
                try:
                    await agent.shutdown()
                    self.logger.info(f"Agent {agent.__class__.__name__} shut down")
                except Exception as e:
                    self.logger.error(f"Failed to shut down agent {agent.__class__.__name__}: {str(e)}")
                    await self.error_logging_service.log_error(
                        "agent_shutdown_error",
                        {
                            "agent": agent.__class__.__name__,
                            "error": str(e)
                        }
                    )
            
            # Stop services
            await self.message_broker.stop()
            await self.communication_service.stop()
            await self.error_logging_service.stop()
            
            self.logger.info("Mycosoft MAS shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to shut down Mycosoft MAS: {str(e)}")
            await self.error_logging_service.log_error(
                "mas_shutdown_error",
                {
                    "error": str(e)
                }
            )
            raise

def load_config():
    """Load configuration from file."""
    with open("config/config.yaml", "r") as f:
        return yaml.safe_load(f)

# Create MAS instance and expose app
config = load_config()
mas = MycosoftMAS(config)
app = mas.app

@app.on_event("startup")
async def startup_event():
    """Initialize MAS on startup."""
    await mas.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown MAS gracefully."""
    await mas.shutdown()

async def main():
    """Main entry point."""
    config = load_config()
    mas = MycosoftMAS(config)
    await mas.initialize()
    return mas

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 