"""
MAS Topology Stream Router - February 12, 2026

Real-time streaming of agent status and topology visualization using Redis pub/sub.
Provides WebSocket connections for dashboards monitoring the Multi-Agent System
topology, agent health, task execution, and system status.

NO MOCK DATA - Real Redis integration with VM 192.168.0.189:6379
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mycosoft_mas.realtime.redis_pubsub import (
    get_client,
    Channel,
    PubSubMessage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Topology Stream"])


class TopologyStreamManager:
    """Manages WebSocket connections for MAS topology visualization."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._subscription_active = False
    
    async def connect(self, websocket: WebSocket):
        """Connect a new client."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        
        logger.info(f"Topology stream: Client connected. Total: {len(self.active_connections)}")
        
        # Start Redis subscription if this is the first client
        if not self._subscription_active:
            asyncio.create_task(self._subscribe_to_redis())
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect a client."""
        async with self._lock:
            self.active_connections.discard(websocket)
        
        logger.info(f"Topology stream: Client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        async with self._lock:
            connections = self.active_connections.copy()
        
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    self.active_connections.discard(ws)
    
    async def _subscribe_to_redis(self):
        """Subscribe to Redis agents:status channel."""
        if self._subscription_active:
            return
        
        self._subscription_active = True
        
        try:
            client = await get_client()
            
            async def handle_message(message: PubSubMessage):
                """Handle incoming agent status from Redis."""
                await self.broadcast({
                    "type": "agent_status",
                    "timestamp": message.timestamp,
                    "source": message.source,
                    "data": message.data,
                })
            
            # Subscribe to agents status channel
            await client.subscribe(
                Channel.AGENTS_STATUS.value,
                handle_message,
            )
            
            logger.info("Subscribed to Redis agents:status channel")
            
            # Keep subscription alive while clients are connected
            while True:
                async with self._lock:
                    if not self.active_connections:
                        break
                await asyncio.sleep(5)
            
            # Unsubscribe when no clients remain
            await client.unsubscribe(Channel.AGENTS_STATUS.value, handle_message)
            logger.info("Unsubscribed from Redis agents:status channel")
        
        except Exception as e:
            logger.error(f"Redis subscription error: {e}")
        
        finally:
            self._subscription_active = False


manager = TopologyStreamManager()


@router.websocket("/topology")
async def topology_stream(websocket: WebSocket):
    """
    WebSocket endpoint for MAS topology visualization.
    
    Subscribes to Redis 'agents:status' channel and streams:
    - Agent health updates
    - Task completion events
    - Error notifications
    - Agent state changes
    
    Messages sent to client:
    {
        "type": "agent_status",
        "timestamp": "ISO timestamp",
        "source": "agent:id",
        "data": {
            "agent_id": "...",
            "status": "healthy|degraded|error",
            "details": {...}
        }
    }
    
    Messages from client:
    - {"type": "ping"}: Keep-alive
    - {"type": "request_snapshot"}: Request full topology snapshot
    """
    await manager.connect(websocket)
    
    try:
        # Send connection acknowledgment
        await websocket.send_json({
            "type": "connected",
            "message": "Topology stream connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        # Keep connection alive and handle client messages
        while True:
            try:
                data = await websocket.receive_json()
                
                # Handle ping
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                
                # Handle snapshot request
                elif data.get("type") == "request_snapshot":
                    # TODO: Query current agent status from registry
                    await websocket.send_json({
                        "type": "snapshot",
                        "message": "Snapshot not yet implemented",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                break
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        await manager.disconnect(websocket)


@router.get("/topology/status")
async def get_topology_stream_status():
    """Get status of topology stream WebSocket connections."""
    return {
        "active_connections": len(manager.active_connections),
        "subscription_active": manager._subscription_active,
        "channel": Channel.AGENTS_STATUS.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
