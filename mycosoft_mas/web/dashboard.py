"""
Mycosoft MAS - Web Dashboard Server

This module provides a web interface for monitoring and managing the MAS.
"""

from typing import Dict, Any, Optional
import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from mycosoft_mas.monitoring.dashboard import MonitoringDashboard
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

logger = logging.getLogger(__name__)

class DashboardServer:
    """Web dashboard server for the MAS."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.app = FastAPI(title="Mycosoft MAS Dashboard")
        self.server = None
        self.is_running = False
        
        # Get base directory
        self.base_dir = Path(__file__).parent
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=config.get('cors_origins', ['*']),
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*']
        )
        
        # Setup routes
        self._setup_routes()
        
        # Initialize monitoring dashboard
        self.monitoring_dashboard = MonitoringDashboard()
        
        # Mount static files
        self.app.mount("/static", StaticFiles(directory=str(self.base_dir / "static")), name="static")
        
        # Setup templates
        self.templates = Jinja2Templates(directory=str(self.base_dir / "templates"))
        
    def _setup_routes(self) -> None:
        """Setup API routes."""
        
        @self.app.get("/")
        async def get_dashboard(request: Request):
            """Serve the main dashboard page."""
            return self.templates.TemplateResponse(
                "dashboard.html",
                {"request": request, "metrics": self.monitoring_dashboard.get_metrics()}
            )
            
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": self.config.get('version', '0.1.0')
            }
            
        @self.app.get("/metrics")
        async def get_metrics():
            try:
                metrics = self.monitoring_dashboard.get_metrics()
                return {"metrics": metrics}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/agents")
        async def get_agents():
            try:
                agents = self.monitoring_dashboard.get_agents()
                return {"agents": agents}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/clusters")
        async def get_clusters():
            try:
                clusters = self.monitoring_dashboard.get_clusters()
                return {"clusters": clusters}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/services")
        async def get_services():
            try:
                services = self.monitoring_dashboard.get_services()
                return {"services": services}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.websocket("/ws/metrics")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time metrics updates."""
            await websocket.accept()
            try:
                while True:
                    metrics = self.monitoring_dashboard.get_metrics()
                    await websocket.send_json(metrics)
                    await asyncio.sleep(1)  # Update every second
            except Exception as e:
                logger.error(f"Error in websocket: {str(e)}")
            finally:
                await websocket.close()
            
    async def start(self) -> None:
        """Start the dashboard server."""
        try:
            if self.is_running:
                logger.warning("Dashboard server already running")
                return
                
            host = self.config.get('dashboard_host', '0.0.0.0')
            port = self.config.get('dashboard_port', 8000)
            
            config = uvicorn.Config(
                self.app,
                host=host,
                port=port,
                log_level="info"
            )
            self.server = uvicorn.Server(config)
            
            # Start server in background
            await self.server.serve()
            self.is_running = True
            logger.info(f"Dashboard server started on {host}:{port}")
            
        except Exception as e:
            logger.error(f"Error starting dashboard server: {str(e)}")
            raise
            
    async def stop(self) -> None:
        """Stop the dashboard server."""
        try:
            if not self.is_running:
                logger.warning("Dashboard server not running")
                return
                
            if self.server:
                self.server.should_exit = True
                await self.server.shutdown()
                
            self.is_running = False
            logger.info("Dashboard server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping dashboard server: {str(e)}")
            raise
            
    def is_running(self) -> bool:
        """Check if the dashboard server is running."""
        return self.is_running 