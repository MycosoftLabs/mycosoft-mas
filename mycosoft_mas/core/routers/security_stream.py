"""
Security WebSocket Stream Router - February 12, 2026

Real-time streaming of security events, incidents, and alerts using Redis pub/sub.
Provides WebSocket connections for SOC dashboards monitoring:
- Security incidents (created, updated, escalated, resolved)
- IDS/IPS alerts from Suricata
- Agent activity (playbooks, threat detection)
- System health events

Replaces polling-based SSE with true push-based WebSocket streaming.

NO MOCK DATA - Real Redis integration with VM 192.168.0.189:6379
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/security", tags=["Security Stream"])


class SecurityEventType(str, Enum):
    """Types of security events that can be streamed."""
    INCIDENT = "incident"
    ALERT = "alert"
    IDS = "ids"
    PLAYBOOK = "playbook"
    AGENT_ACTIVITY = "agent_activity"
    SYSTEM = "system"
    THREAT = "threat"
    SCAN = "scan"


class SeverityLevel(str, Enum):
    """Severity levels for security events."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityStreamManager:
    """Manages WebSocket connections for security event streaming."""
    
    def __init__(self):
        # All connected clients
        self.connections: Set[WebSocket] = set()
        # Client-specific filters (websocket -> filter config)
        self.client_filters: Dict[WebSocket, Dict[str, Any]] = {}
        # Event queue for recent events (ring buffer)
        self._event_queue: List[Dict[str, Any]] = []
        self._max_queue_size = 100
        self._lock = asyncio.Lock()
        self._redis_subscription_active = False
    
    async def connect(
        self,
        websocket: WebSocket,
        severities: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None,
    ):
        """Connect a new security dashboard client."""
        await websocket.accept()
        async with self._lock:
            self.connections.add(websocket)
            self.client_filters[websocket] = {
                "severities": severities,
                "event_types": event_types,
            }
        
        logger.info(f"Security stream: Client connected. Total: {len(self.connections)}")
        
        # Start Redis subscription if this is the first client
        if not self._redis_subscription_active:
            asyncio.create_task(self._subscribe_to_redis())
    
    async def disconnect(self, websocket: WebSocket):
        """Disconnect a client."""
        async with self._lock:
            self.connections.discard(websocket)
            self.client_filters.pop(websocket, None)
        
        logger.info(f"Security stream: Client disconnected. Total: {len(self.connections)}")
    
    def _should_send_to_client(
        self,
        websocket: WebSocket,
        event_type: str,
        severity: str,
    ) -> bool:
        """Check if an event should be sent to a specific client based on filters."""
        filters = self.client_filters.get(websocket, {})
        
        # Check severity filter
        severities = filters.get("severities")
        if severities and severity not in severities:
            return False
        
        # Check event type filter
        event_types = filters.get("event_types")
        if event_types and event_type not in event_types:
            return False
        
        return True
    
    async def broadcast(self, event: Dict[str, Any]):
        """Broadcast a security event to all connected clients."""
        # Add to event queue
        async with self._lock:
            self._event_queue.append(event)
            if len(self._event_queue) > self._max_queue_size:
                self._event_queue.pop(0)
            connections = self.connections.copy()
        
        event_type = event.get("event_type", "unknown")
        severity = event.get("severity", "info")
        
        logger.debug(f"Broadcasting security event: {event_type} ({severity})")
        
        disconnected = []
        for websocket in connections:
            if not self._should_send_to_client(websocket, event_type, severity):
                continue
            
            try:
                await websocket.send_json(event)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    self.connections.discard(ws)
                    self.client_filters.pop(ws, None)
    
    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent events from the queue."""
        return self._event_queue[-limit:][::-1]  # Most recent first
    
    async def _subscribe_to_redis(self):
        """Subscribe to Redis security channels."""
        if self._redis_subscription_active:
            return
        
        self._redis_subscription_active = True
        
        try:
            # Import here to avoid circular dependencies
            from mycosoft_mas.realtime.redis_pubsub import (
                get_client,
                PubSubMessage,
            )
            
            client = await get_client()
            
            async def handle_security_event(message: PubSubMessage):
                """Handle incoming security events from Redis."""
                event = {
                    "event_type": message.data.get("type", "security"),
                    "timestamp": message.timestamp,
                    "source": message.source,
                    "severity": message.data.get("severity", "info"),
                    "title": message.data.get("title", "Security Event"),
                    "message": message.data.get("message", ""),
                    "data": message.data,
                }
                await self.broadcast(event)
            
            # Subscribe to security channels
            security_channels = [
                "security:incidents",
                "security:alerts",
                "security:ids",
                "security:threats",
            ]
            
            for channel in security_channels:
                try:
                    await client.subscribe(channel, handle_security_event)
                    logger.info(f"Subscribed to Redis channel: {channel}")
                except Exception as e:
                    logger.warning(f"Failed to subscribe to {channel}: {e}")
            
            # Keep subscription alive while clients are connected
            while True:
                async with self._lock:
                    if not self.connections:
                        break
                await asyncio.sleep(5)
            
            # Unsubscribe when no clients remain
            for channel in security_channels:
                try:
                    await client.unsubscribe(channel, handle_security_event)
                except Exception:
                    pass
            
            logger.info("Unsubscribed from Redis security channels")
        
        except ImportError:
            logger.warning("Redis pubsub not available - using internal broadcast only")
            # Keep running for internal broadcasts even without Redis
            while True:
                async with self._lock:
                    if not self.connections:
                        break
                await asyncio.sleep(5)
        
        except Exception as e:
            logger.error(f"Redis subscription error: {e}")
        
        finally:
            self._redis_subscription_active = False


# Global manager instance
manager = SecurityStreamManager()


# ═══════════════════════════════════════════════════════════════
# API FOR INTERNAL BROADCASTING
# ═══════════════════════════════════════════════════════════════

async def broadcast_security_event(
    event_type: str,
    title: str,
    message: str,
    severity: str = "info",
    data: Optional[Dict[str, Any]] = None,
):
    """
    Broadcast a security event to all connected WebSocket clients.
    
    Call this from anywhere in MAS to push events to the security dashboard.
    
    Args:
        event_type: Type of event (incident, alert, ids, playbook, agent_activity, system, threat, scan)
        title: Short title for the event
        message: Detailed message
        severity: Severity level (info, low, medium, high, critical)
        data: Additional event data
    """
    event = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "mas",
        "severity": severity,
        "title": title,
        "message": message,
        "data": data or {},
    }
    await manager.broadcast(event)


async def broadcast_incident(
    incident_id: str,
    title: str,
    action: str,
    severity: str = "medium",
    status: str = "open",
):
    """Broadcast an incident event."""
    await broadcast_security_event(
        event_type=SecurityEventType.INCIDENT.value,
        title=f"Incident {action}: {title}",
        message=f"Incident {incident_id} has been {action}. Status: {status}",
        severity=severity,
        data={
            "incident_id": incident_id,
            "action": action,
            "status": status,
        },
    )


async def broadcast_ids_alert(
    signature: str,
    signature_id: int,
    severity: str,
    src_ip: str,
    dest_ip: str,
    category: str = "Unknown",
):
    """Broadcast an IDS alert."""
    await broadcast_security_event(
        event_type=SecurityEventType.IDS.value,
        title=f"IDS Alert: {signature}",
        message=f"Source: {src_ip} -> Dest: {dest_ip}",
        severity=severity,
        data={
            "signature": signature,
            "signature_id": signature_id,
            "src_ip": src_ip,
            "dest_ip": dest_ip,
            "category": category,
        },
    )


async def broadcast_agent_activity(
    agent_id: str,
    agent_name: str,
    action: str,
    details: str = "",
):
    """Broadcast agent activity."""
    await broadcast_security_event(
        event_type=SecurityEventType.AGENT_ACTIVITY.value,
        title=f"Agent: {agent_name}",
        message=f"{action}: {details}" if details else action,
        severity="info",
        data={
            "agent_id": agent_id,
            "agent_name": agent_name,
            "action": action,
        },
    )


# ═══════════════════════════════════════════════════════════════
# WEBSOCKET ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.websocket("/stream")
async def security_event_stream(
    websocket: WebSocket,
    severities: Optional[str] = Query(None, description="Comma-separated severity filter"),
    types: Optional[str] = Query(None, description="Comma-separated event type filter"),
):
    """
    WebSocket endpoint for live security event streaming.
    
    Streams real-time security events including:
    - Incidents (created, updated, escalated, resolved)
    - IDS/IPS alerts
    - Agent activity
    - System health events
    - Threat detections
    
    Query params:
    - severities: Comma-separated list (e.g., "high,critical")
    - types: Comma-separated list (e.g., "incident,ids,threat")
    
    Messages sent to client:
    {
        "event_type": "incident|alert|ids|...",
        "timestamp": "ISO timestamp",
        "source": "mas",
        "severity": "info|low|medium|high|critical",
        "title": "Event title",
        "message": "Event details",
        "data": {...}
    }
    
    Messages from client:
    - {"type": "ping"}: Keep-alive
    - {"type": "subscribe", "severities": [...], "types": [...]}: Update filters
    """
    # Parse filter params
    severity_list = severities.split(",") if severities else None
    type_list = types.split(",") if types else None
    
    await manager.connect(websocket, severities=severity_list, event_types=type_list)
    
    try:
        # Send connection acknowledgment
        await websocket.send_json({
            "type": "connected",
            "message": "Security stream connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "filters": {
                "severities": severity_list,
                "event_types": type_list,
            },
            "subscribers": len(manager.connections),
        })
        
        # Send recent events
        recent_events = manager.get_recent_events(10)
        for event in recent_events:
            event_type = event.get("event_type", "unknown")
            severity = event.get("severity", "info")
            if manager._should_send_to_client(websocket, event_type, severity):
                await websocket.send_json(event)
        
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
                
                # Handle filter subscription update
                elif data.get("type") == "subscribe":
                    new_severities = data.get("severities")
                    new_types = data.get("types")
                    async with manager._lock:
                        manager.client_filters[websocket] = {
                            "severities": new_severities,
                            "event_types": new_types,
                        }
                    await websocket.send_json({
                        "type": "subscribed",
                        "filters": {
                            "severities": new_severities,
                            "event_types": new_types,
                        },
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


@router.get("/status")
async def get_security_stream_status():
    """Get status of security stream WebSocket connections."""
    return {
        "active_connections": len(manager.connections),
        "redis_subscription_active": manager._redis_subscription_active,
        "recent_events_count": len(manager._event_queue),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/test")
async def test_broadcast():
    """Test endpoint to trigger a security event broadcast."""
    await broadcast_security_event(
        event_type="system",
        title="Test Event",
        message="This is a test security event broadcast",
        severity="info",
        data={"test": True},
    )
    return {"status": "broadcast_sent", "timestamp": datetime.now(timezone.utc).isoformat()}
