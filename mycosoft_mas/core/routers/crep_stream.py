"""
CREP/OEI Dashboard Stream Router - February 12, 2026

Real-time streaming of CREP (Comprehensive Real-time Earth Processor)
and OEI (Object Event Indexing) data using Redis pub/sub.
Provides WebSocket connections for dashboards monitoring:
- Aviation tracking (aircraft positions)
- Maritime tracking (vessel positions)
- Satellite tracking
- Weather updates

NO MOCK DATA - Real Redis integration with VM 192.168.0.189:6379
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from mycosoft_mas.realtime.redis_pubsub import (
    get_client,
    Channel,
    PubSubMessage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crep", tags=["CREP Stream"])


class CREPStreamManager:
    """Manages WebSocket connections for CREP/OEI dashboard streaming."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._subscription_active = False
    
    async def connect(self, websocket: WebSocket):
        """Connect a new client."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        
        logger.info(f"CREP stream: Client connected. Total: {len(self.active_connections)}")
        
        # Start Redis subscription if this is the first client
        if not self._subscription_active:
            asyncio.create_task(self._subscribe_to_redis())
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect a client."""
        async with self._lock:
            self.active_connections.discard(websocket)
        
        logger.info(f"CREP stream: Client disconnected. Total: {len(self.active_connections)}")
    
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
        """Subscribe to Redis crep:live channel."""
        if self._subscription_active:
            return
        
        self._subscription_active = True
        
        try:
            client = await get_client()
            
            async def handle_message(message: PubSubMessage):
                """Handle incoming CREP data from Redis."""
                await self.broadcast({
                    "type": "crep_update",
                    "timestamp": message.timestamp,
                    "source": message.source,
                    "data": message.data,
                })
            
            # Subscribe to CREP live channel
            await client.subscribe(
                Channel.CREP_LIVE.value,
                handle_message,
            )
            
            logger.info("Subscribed to Redis crep:live channel")
            
            # Keep subscription alive while clients are connected
            while True:
                async with self._lock:
                    if not self.active_connections:
                        break
                await asyncio.sleep(5)
            
            # Unsubscribe when no clients remain
            await client.unsubscribe(Channel.CREP_LIVE.value, handle_message)
            logger.info("Unsubscribed from Redis crep:live channel")
        
        except Exception as e:
            logger.error(f"Redis subscription error: {e}")
        
        finally:
            self._subscription_active = False


manager = CREPStreamManager()


@router.websocket("/stream")
async def crep_live_stream(
    websocket: WebSocket,
    category: Optional[str] = Query(default=None, description="Filter by category: aircraft, vessel, satellite, weather"),
):
    """
    WebSocket endpoint for live CREP/OEI dashboard data.
    
    Subscribes to Redis 'crep:live' channel and streams:
    - Aircraft positions (ADS-B data)
    - Vessel positions (AIS data)
    - Satellite tracking
    - Weather updates
    
    Query params:
    - category: Optional filter for specific CREP category
    
    Messages sent to client:
    {
        "type": "crep_update",
        "timestamp": "ISO timestamp",
        "source": "crep:category",
        "data": {
            "category": "aircraft|vessel|satellite|weather",
            "data": {...}
        }
    }
    
    Messages from client:
    - {"type": "ping"}: Keep-alive
    - {"type": "set_filter", "category": "..."}: Set category filter
    """
    await manager.connect(websocket)
    
    # Store filter for this connection (if provided)
    category_filter = category
    
    try:
        # Send connection acknowledgment
        await websocket.send_json({
            "type": "connected",
            "message": "CREP stream connected",
            "filter": category_filter,
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
                
                # Handle filter update
                elif data.get("type") == "set_filter":
                    category_filter = data.get("category")
                    await websocket.send_json({
                        "type": "filter_updated",
                        "category": category_filter,
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


@router.get("/stream/status")
async def get_crep_stream_status():
    """Get status of CREP stream WebSocket connections."""
    return {
        "active_connections": len(manager.active_connections),
        "subscription_active": manager._subscription_active,
        "channel": Channel.CREP_LIVE.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
