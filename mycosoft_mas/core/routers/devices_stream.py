"""
Device Telemetry Stream Router - February 12, 2026

Real-time streaming of device telemetry data using Redis pub/sub.
Provides WebSocket connections for dashboards monitoring:
- MycoBrain sensor data (temperature, humidity, BME688/690, etc.)
- Lab equipment telemetry
- Environmental sensors
- Device health and diagnostics

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

router = APIRouter(prefix="/ws/devices", tags=["Device Stream"])


class DeviceStreamManager:
    """Manages WebSocket connections for device telemetry streaming."""
    
    def __init__(self):
        # Map device_id -> set of connected websockets
        self.device_connections: Dict[str, Set[WebSocket]] = {}
        # All connections for broadcast
        self.all_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._subscription_active = False
    
    async def connect(self, websocket: WebSocket, device_id: str):
        """Connect a new client for a specific device."""
        await websocket.accept()
        async with self._lock:
            if device_id not in self.device_connections:
                self.device_connections[device_id] = set()
            self.device_connections[device_id].add(websocket)
            self.all_connections.add(websocket)
        
        logger.info(f"Device stream: Client connected to {device_id}. Total for device: {len(self.device_connections[device_id])}")
        
        # Start Redis subscription if this is the first client
        if not self._subscription_active:
            asyncio.create_task(self._subscribe_to_redis())
    
    async def disconnect(self, websocket: WebSocket, device_id: str):
        """Disconnect a client."""
        async with self._lock:
            if device_id in self.device_connections:
                self.device_connections[device_id].discard(websocket)
                if not self.device_connections[device_id]:
                    del self.device_connections[device_id]
            self.all_connections.discard(websocket)
        
        logger.info(f"Device stream: Client disconnected from {device_id}. Total: {len(self.all_connections)}")
    
    async def broadcast_to_device(self, device_id: str, message: Dict[str, Any]):
        """Broadcast message to all clients watching a specific device."""
        async with self._lock:
            connections = self.device_connections.get(device_id, set()).copy()
        
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
                    self.device_connections.get(device_id, set()).discard(ws)
                    self.all_connections.discard(ws)
    
    async def _subscribe_to_redis(self):
        """Subscribe to Redis devices:telemetry channel."""
        if self._subscription_active:
            return
        
        self._subscription_active = True
        
        try:
            client = await get_client()
            
            async def handle_message(message: PubSubMessage):
                """Handle incoming device telemetry from Redis."""
                # Extract device_id from message data
                device_id = message.data.get("device_id")
                if device_id:
                    await self.broadcast_to_device(device_id, {
                        "type": "telemetry",
                        "timestamp": message.timestamp,
                        "source": message.source,
                        "device_id": device_id,
                        "data": message.data.get("telemetry", {}),
                    })
            
            # Subscribe to devices telemetry channel
            await client.subscribe(
                Channel.DEVICES_TELEMETRY.value,
                handle_message,
            )
            
            logger.info("Subscribed to Redis devices:telemetry channel")
            
            # Keep subscription alive while clients are connected
            while True:
                async with self._lock:
                    if not self.all_connections:
                        break
                await asyncio.sleep(5)
            
            # Unsubscribe when no clients remain
            await client.unsubscribe(Channel.DEVICES_TELEMETRY.value, handle_message)
            logger.info("Unsubscribed from Redis devices:telemetry channel")
        
        except Exception as e:
            logger.error(f"Redis subscription error: {e}")
        
        finally:
            self._subscription_active = False


manager = DeviceStreamManager()


@router.websocket("/{device_id}")
async def device_telemetry_stream(
    websocket: WebSocket,
    device_id: str,
):
    """
    WebSocket endpoint for live device telemetry streaming.
    
    Subscribes to Redis 'devices:telemetry' channel and streams
    telemetry data for the specified device.
    
    URL params:
    - device_id: Device identifier (e.g., "mushroom1", "sporebase")
    
    Messages sent to client:
    {
        "type": "telemetry",
        "timestamp": "ISO timestamp",
        "source": "device:id",
        "device_id": "...",
        "data": {
            "temperature": 22.5,
            "humidity": 65.2,
            "pressure": 1013.25,
            ...
        }
    }
    
    Messages from client:
    - {"type": "ping"}: Keep-alive
    """
    await manager.connect(websocket, device_id)
    
    try:
        # Send connection acknowledgment
        await websocket.send_json({
            "type": "connected",
            "message": f"Device stream connected to {device_id}",
            "device_id": device_id,
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
                        "device_id": device_id,
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
        await manager.disconnect(websocket, device_id)


@router.get("/status")
async def get_devices_stream_status():
    """Get status of device stream WebSocket connections."""
    return {
        "active_connections": len(manager.all_connections),
        "devices_monitored": list(manager.device_connections.keys()),
        "subscription_active": manager._subscription_active,
        "channel": Channel.DEVICES_TELEMETRY.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
