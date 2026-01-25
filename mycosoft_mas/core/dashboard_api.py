"""
MAS v2 Dashboard API

FastAPI routes for the real-time agent monitoring dashboard.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse

from mycosoft_mas.runtime import (
    AgentPool,
    AgentState,
    AgentStatus,
    MessageBroker,
)


logger = logging.getLogger("DashboardAPI")
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


# Global references (set during app startup)
agent_pool: Optional[AgentPool] = None
message_broker: Optional[MessageBroker] = None


def set_agent_pool(pool: AgentPool):
    global agent_pool
    agent_pool = pool


def set_message_broker(broker: MessageBroker):
    global message_broker
    message_broker = broker


@router.get("/agents")
async def get_all_agents():
    """Get all agents with their current status"""
    if not agent_pool:
        return {"agents": [], "error": "Agent pool not initialized"}
    
    agents = await agent_pool.get_all_agents()
    return {
        "agents": [a.to_dict() for a in agents],
        "total": len(agents),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/agents/{agent_id}")
async def get_agent_details(agent_id: str):
    """Get detailed information about a specific agent"""
    if not agent_pool:
        raise HTTPException(status_code=503, detail="Agent pool not initialized")
    
    agent = await agent_pool.get_agent_state(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent.to_dict()


@router.get("/agents/{agent_id}/logs")
async def get_agent_logs(agent_id: str, limit: int = 100):
    """Get recent logs for an agent"""
    # Would query MINDEX for logs
    return {
        "agent_id": agent_id,
        "logs": [],
        "limit": limit,
    }


@router.get("/stats")
async def get_pool_stats():
    """Get agent pool statistics"""
    if not agent_pool:
        return {"error": "Agent pool not initialized"}
    
    stats = await agent_pool.get_pool_stats()
    return {
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/topology")
async def get_topology():
    """Get agent topology for visualization"""
    if not agent_pool:
        return {"nodes": [], "edges": []}
    
    agents = await agent_pool.get_all_agents()
    
    # Build topology nodes
    nodes = [
        {
            "id": "orchestrator",
            "type": "orchestrator",
            "label": "MYCA Orchestrator",
            "status": "active",
        }
    ]
    
    for agent in agents:
        nodes.append({
            "id": agent.agent_id,
            "type": "agent",
            "label": agent.agent_id,
            "status": agent.status.value,
        })
    
    # Build edges (all agents connect to orchestrator)
    edges = [
        {"from": "orchestrator", "to": agent.agent_id}
        for agent in agents
    ]
    
    return {
        "nodes": nodes,
        "edges": edges,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        # Send initial state
        if agent_pool:
            agents = await agent_pool.get_all_agents()
            await websocket.send_json({
                "type": "initial_state",
                "agents": [a.to_dict() for a in agents],
            })
        
        # Keep connection alive and handle messages
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0
                )
                
                # Handle client messages
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "subscribe":
                    agent_id = data.get("agent_id")
                    # Subscribe to specific agent updates
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.get("/stream")
async def stream_updates():
    """Server-Sent Events endpoint for log streaming"""
    
    async def event_generator():
        while True:
            if agent_pool:
                agents = await agent_pool.get_all_agents()
                data = {
                    "type": "agent_update",
                    "agents": [a.to_dict() for a in agents],
                    "timestamp": datetime.utcnow().isoformat(),
                }
                yield f"data: {json.dumps(data)}\n\n"
            
            await asyncio.sleep(5)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


# Background task to broadcast updates
async def broadcast_updates():
    """Broadcast agent updates to all connected WebSocket clients"""
    while True:
        try:
            if agent_pool and manager.active_connections:
                agents = await agent_pool.get_all_agents()
                await manager.broadcast({
                    "type": "agent_update",
                    "agents": [a.to_dict() for a in agents],
                    "timestamp": datetime.utcnow().isoformat(),
                })
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
        
        await asyncio.sleep(5)
