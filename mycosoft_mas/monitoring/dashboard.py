from fastapi import FastAPI, Request, Depends, HTTPException, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import APIKeyHeader
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import asyncio
import aiohttp
from typing import Dict, Any, List
import json
from pathlib import Path
import secrets
import datetime
import logging
from mycosoft_mas.core.agent_manager import AgentManager
from mycosoft_mas.core.knowledge_graph import KnowledgeGraph
from mycosoft_mas.core.metrics_collector import MetricsCollector
from mycosoft_mas.core.task_manager import TaskManager
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mycosoft MAS Dashboard", root_path="/dashboard")

# Get the absolute paths
current_dir = Path(__file__).parent.resolve()
static_dir = current_dir / "static"
templates_dir = current_dir / "templates"

# Create directories if they don't exist
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

# Mount static files with the correct base path
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))
templates.env.globals["url_for"] = lambda name, path: f"/dashboard/static/{path}"

# Configuration
OXIGRAPH_URL = "http://localhost:7878"
PROMETHEUS_URL = "http://localhost:9090"

# Initialize MAS components
agent_manager = AgentManager()
knowledge_graph = KnowledgeGraph()
metrics_collector = MetricsCollector()
task_manager = TaskManager()

# API Key security
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")
api_keys = {}

# WebSocket connections
websocket_connections = set()

async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    if api_key not in [key["key"] for key in api_keys.values()]:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.on_event("startup")
async def startup_event():
    """Initialize MAS components on startup"""
    try:
        await agent_manager.initialize()
        await knowledge_graph.initialize()
        await metrics_collector.initialize()
        await task_manager.initialize()
        logger.info("MAS components initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MAS components: {str(e)}")
        raise

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_connections.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        websocket_connections.remove(websocket)

async def broadcast_update(data: Dict[str, Any]):
    """Broadcast updates to all connected WebSocket clients"""
    for connection in websocket_connections:
        try:
            await connection.send_json(data)
        except Exception as e:
            logger.error(f"Error broadcasting update: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def dashboard_root(request: Request):
    """Render the main dashboard."""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "base_url": "/dashboard"}
    )

@app.get("/api-keys", response_class=HTMLResponse)
async def api_keys_page(request: Request):
    """Render the API keys management page."""
    return templates.TemplateResponse(
        "api_keys.html",
        {"request": request}
    )

@app.get("/api/api-keys")
async def get_api_keys():
    """Get all API keys."""
    return list(api_keys.values())

@app.post("/api/api-keys")
async def create_api_key(data: Dict[str, Any]):
    """Create a new API key."""
    key_id = secrets.token_urlsafe(16)
    api_key = secrets.token_urlsafe(32)
    api_keys[key_id] = {
        "id": key_id,
        "name": data["name"],
        "key": api_key,
        "created": datetime.datetime.now().isoformat(),
        "last_used": None
    }
    return api_keys[key_id]

@app.delete("/api/api-keys/{key_id}")
async def delete_api_key(key_id: str):
    """Delete an API key."""
    if key_id in api_keys:
        del api_keys[key_id]
        return {"status": "success"}
    return {"status": "error", "message": "Key not found"}

@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics."""
    return generate_latest()

@app.get("/api/agents")
async def get_agents():
    """Get agent status and metrics."""
    try:
        agents = await agent_manager.get_agent_status()
        return {"agents": agents}
    except Exception as e:
        logger.error(f"Error fetching agent data: {str(e)}")
        return {"error": "Unable to fetch agent data"}

@app.post("/api/agents/{agent_id}/restart")
async def restart_agent(agent_id: str):
    """Restart a specific agent."""
    try:
        await agent_manager.restart_agent(agent_id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error restarting agent: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/api/agents/{agent_id}/logs")
async def get_agent_logs(agent_id: str):
    """Get logs for a specific agent."""
    try:
        logs = await agent_manager.get_agent_logs(agent_id)
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error fetching agent logs: {str(e)}")
        return {"error": "Unable to fetch agent logs"}

@app.get("/api/knowledge-graph")
async def get_knowledge_graph():
    """Get knowledge graph data."""
    try:
        graph_data = await knowledge_graph.get_graph_data()
        return graph_data
    except Exception as e:
        logger.error(f"Error fetching knowledge graph data: {str(e)}")
        return {"error": "Unable to fetch knowledge graph data"}

@app.get("/api/tasks")
async def get_tasks():
    """Get all tasks."""
    try:
        tasks = await task_manager.get_tasks()
        return {"tasks": tasks}
    except Exception as e:
        logger.error(f"Error fetching tasks: {str(e)}")
        return {"error": "Unable to fetch tasks"}

@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a specific task."""
    try:
        await task_manager.cancel_task(task_id)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error canceling task: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/api/tasks/{task_id}")
async def get_task_details(task_id: str):
    """Get details for a specific task."""
    try:
        task = await task_manager.get_task_details(task_id)
        return task
    except Exception as e:
        logger.error(f"Error fetching task details: {str(e)}")
        return {"error": "Unable to fetch task details"}

@app.get("/api/metrics")
async def get_metrics():
    """Get system metrics."""
    try:
        metrics = metrics_collector.get_metrics()
        return {
            "metrics": {
                "agent_count": metrics["agent_count"],
                "total_agents": len(agent_manager.agents),
                "active_tasks": len([t for t in task_manager.tasks.values() if t["status"] == "running"]),
                "completed_tasks": metrics["task_count"],
                "knowledge_nodes": len(knowledge_graph.graph.nodes),
                "knowledge_relations": len(knowledge_graph.graph.edges),
                "system_health": 100 if metrics["error_count"] == 0 else 90,
                "uptime": f"{int((time.time() - metrics['last_update']) / 3600)}h {int((time.time() - metrics['last_update']) % 3600 / 60)}m",
                "performance_data": {
                    "labels": [datetime.now().strftime("%H:%M:%S")],
                    "cpu": [metrics.get("cpu_usage", 0)],
                    "memory": [metrics.get("memory_usage", 0)]
                },
                "system_metrics": {
                    "tasks": metrics["task_count"],
                    "errors": metrics["error_count"],
                    "api_calls": metrics.get("api_calls", 0)
                }
            }
        }
    except Exception as e:
        logger.error(f"Error fetching metrics data: {str(e)}")
        return {"error": "Unable to fetch metrics data"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        return {
            "status": "ok",
            "agents": [{
                "name": agent.__class__.__name__,
                "status": agent.status.value if hasattr(agent.status, 'value') else str(agent.status)
            } for agent in agent_manager.agents],
            "services": {
                "message_broker": agent_manager.message_broker.status,
                "communication_service": agent_manager.communication_service.status,
                "error_logging_service": agent_manager.error_logging_service.status
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "error", "message": str(e)} 