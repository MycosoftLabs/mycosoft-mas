"""
Visualization Service for Mycosoft MAS

This service handles real-time data visualization and metrics display.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path
import aiohttp
from fastapi import WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

class VisualizationService:
    """Service for handling real-time data visualization."""
    
    def __init__(self, config: Dict):
        """
        Initialize the visualization service.
        
        Args:
            config: Service configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.websockets: List[WebSocket] = []
        self.metrics_data = {}
        self.templates = Jinja2Templates(directory="templates")
        
        # Initialize static files
        self.static_files = StaticFiles(directory="static")
        
        # Initialize metrics storage
        self.metrics_history = {
            "system_metrics": [],
            "agent_metrics": {},
            "resource_metrics": []
        }
        
    async def initialize(self):
        """Initialize the visualization service."""
        try:
            # Create necessary directories
            Path("static").mkdir(exist_ok=True)
            Path("templates").mkdir(exist_ok=True)
            
            # Initialize WebSocket connections
            self.logger.info("Visualization service initialized")
        except Exception as e:
            self.logger.error(f"Error initializing visualization service: {str(e)}")
            raise
    
    async def update_metrics(self, metrics: Dict):
        """
        Update metrics data and broadcast to connected clients.
        
        Args:
            metrics: Dictionary containing metrics data
        """
        try:
            # Update metrics history
            timestamp = datetime.now().isoformat()
            self.metrics_data = metrics
            
            # Add to history
            self.metrics_history["system_metrics"].append({
                "timestamp": timestamp,
                "metrics": metrics.get("system", {})
            })
            
            # Update agent metrics
            for agent_id, agent_metrics in metrics.get("agents", {}).items():
                if agent_id not in self.metrics_history["agent_metrics"]:
                    self.metrics_history["agent_metrics"][agent_id] = []
                self.metrics_history["agent_metrics"][agent_id].append({
                    "timestamp": timestamp,
                    "metrics": agent_metrics
                })
            
            # Update resource metrics
            self.metrics_history["resource_metrics"].append({
                "timestamp": timestamp,
                "metrics": metrics.get("resources", {})
            })
            
            # Broadcast to connected clients
            await self.broadcast_metrics()
            
        except Exception as e:
            self.logger.error(f"Error updating metrics: {str(e)}")
    
    async def broadcast_metrics(self):
        """Broadcast current metrics to all connected WebSocket clients."""
        try:
            for websocket in self.websockets:
                try:
                    await websocket.send_json(self.metrics_data)
                except Exception as e:
                    self.logger.error(f"Error broadcasting to WebSocket: {str(e)}")
                    self.websockets.remove(websocket)
        except Exception as e:
            self.logger.error(f"Error in broadcast_metrics: {str(e)}")
    
    async def connect_websocket(self, websocket: WebSocket):
        """
        Connect a new WebSocket client.
        
        Args:
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.websockets.append(websocket)
        await websocket.send_json(self.metrics_data)
    
    async def disconnect_websocket(self, websocket: WebSocket):
        """
        Disconnect a WebSocket client.
        
        Args:
            websocket: WebSocket connection
        """
        if websocket in self.websockets:
            self.websockets.remove(websocket)
    
    def get_dashboard_html(self) -> HTMLResponse:
        """Get the dashboard HTML with embedded charts."""
        return self.templates.TemplateResponse(
            "dashboard.html",
            {
                "request": None,
                "metrics": self.metrics_data,
                "config": self.config
            }
        )
    
    def get_metrics_history(self, metric_type: str, agent_id: Optional[str] = None) -> List[Dict]:
        """
        Get historical metrics data.
        
        Args:
            metric_type: Type of metrics to retrieve
            agent_id: Optional agent ID for agent-specific metrics
            
        Returns:
            List of historical metrics data
        """
        if metric_type == "system":
            return self.metrics_history["system_metrics"]
        elif metric_type == "agent" and agent_id:
            return self.metrics_history["agent_metrics"].get(agent_id, [])
        elif metric_type == "resources":
            return self.metrics_history["resource_metrics"]
        return [] 