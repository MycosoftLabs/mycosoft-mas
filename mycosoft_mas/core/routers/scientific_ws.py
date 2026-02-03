"""
Scientific WebSocket Server
Unified real-time communication for all scientific operations
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set, Optional, Any
import asyncio
import json
import logging
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

router = APIRouter()


class EventType(str, Enum):
    """Supported WebSocket event types"""
    SIMULATION_PROGRESS = "simulation.progress"
    EXPERIMENT_STEP = "experiment.step"
    FCI_SIGNAL = "fci.signal"
    DEVICE_STATUS = "device.status"
    TELEMETRY_UPDATE = "telemetry.update"
    MYCELIUM_STATE = "mycelium.state"
    SAFETY_ALERT = "safety.alert"
    HYPOTHESIS_UPDATE = "hypothesis.update"
    MYCOBRAIN_RESULT = "mycobrain.result"
    LAB_INSTRUMENT = "lab.instrument"


class ScientificWSManager:
    """Manages WebSocket connections and event subscriptions"""
    
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.subscriptions: Dict[WebSocket, Set[str]] = {}
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
            self.subscriptions[websocket] = set()
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.active_connections.discard(websocket)
            if websocket in self.subscriptions:
                for event_type in self.subscriptions[websocket]:
                    if event_type in self.connections:
                        self.connections[event_type].discard(websocket)
                del self.subscriptions[websocket]
        logger.info(f"WebSocket disconnected. Remaining: {len(self.active_connections)}")
    
    async def subscribe(self, websocket: WebSocket, event_type: str) -> None:
        async with self._lock:
            if event_type not in self.connections:
                self.connections[event_type] = set()
            self.connections[event_type].add(websocket)
            if websocket in self.subscriptions:
                self.subscriptions[websocket].add(event_type)
        await websocket.send_json({
            "type": "subscribed",
            "payload": {"eventType": event_type},
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def unsubscribe(self, websocket: WebSocket, event_type: str) -> None:
        async with self._lock:
            if event_type in self.connections:
                self.connections[event_type].discard(websocket)
            if websocket in self.subscriptions:
                self.subscriptions[websocket].discard(event_type)
    
    async def broadcast(self, event_type: str, data: Any, session_id: Optional[str] = None) -> None:
        message = {
            "type": event_type,
            "payload": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if session_id:
            message["sessionId"] = session_id
        
        async with self._lock:
            subscribers = self.connections.get(event_type, set()).copy()
        
        disconnected = []
        for websocket in subscribers:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send: {e}")
                disconnected.append(websocket)
        
        for ws in disconnected:
            await self.disconnect(ws)
    
    def get_subscriber_count(self, event_type: str) -> int:
        return len(self.connections.get(event_type, set()))
    
    def get_total_connections(self) -> int:
        return len(self.active_connections)


ws_manager = ScientificWSManager()


@router.websocket("/ws/scientific")
async def scientific_websocket(websocket: WebSocket):
    await ws_manager.connect(websocket)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "payload": {
                "message": "Connected to MYCA Scientific WebSocket",
                "availableEvents": [e.value for e in EventType]
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            try:
                data = await websocket.receive_json()
                msg_type = data.get("type")
                payload = data.get("payload", {})
                
                if msg_type == "subscribe":
                    event_type = payload.get("eventType")
                    if event_type:
                        await ws_manager.subscribe(websocket, event_type)
                elif msg_type == "unsubscribe":
                    event_type = payload.get("eventType")
                    if event_type:
                        await ws_manager.unsubscribe(websocket, event_type)
                elif msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": "Invalid JSON format"},
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await ws_manager.disconnect(websocket)


@router.get("/ws/scientific/status")
async def websocket_status():
    return {
        "status": "online",
        "totalConnections": ws_manager.get_total_connections(),
        "subscriptions": {
            event_type.value: ws_manager.get_subscriber_count(event_type.value)
            for event_type in EventType
        }
    }


# Broadcast helper functions
async def broadcast_simulation_progress(simulation_id: str, progress: int, eta: str, status: str):
    await ws_manager.broadcast(EventType.SIMULATION_PROGRESS.value, {
        "id": simulation_id, "progress": progress, "eta": eta, "status": status
    })

async def broadcast_experiment_step(experiment_id: str, step: int, total_steps: int, status: str, message: str = None):
    await ws_manager.broadcast(EventType.EXPERIMENT_STEP.value, {
        "id": experiment_id, "step": step, "totalSteps": total_steps, "status": status, "message": message
    })

async def broadcast_fci_signal(session_id: str, channels: list, sample_rate: int):
    await ws_manager.broadcast(EventType.FCI_SIGNAL.value, {
        "sessionId": session_id, "channels": channels, "sampleRate": sample_rate
    }, session_id=session_id)

async def broadcast_device_status(device_id: str, status: str):
    await ws_manager.broadcast(EventType.DEVICE_STATUS.value, {
        "deviceId": device_id, "status": status, "lastSeen": int(datetime.utcnow().timestamp())
    })

async def broadcast_telemetry(device_id: str, readings: dict):
    await ws_manager.broadcast(EventType.TELEMETRY_UPDATE.value, {
        "deviceId": device_id, "readings": readings, "timestamp": datetime.utcnow().isoformat()
    })

async def broadcast_safety_alert(alert_type: str, message: str, severity: str):
    await ws_manager.broadcast(EventType.SAFETY_ALERT.value, {
        "type": alert_type, "message": message, "severity": severity,
        "timestamp": int(datetime.utcnow().timestamp() * 1000)
    })

async def broadcast_mycobrain_result(job_id: str, status: str, result: Any = None):
    await ws_manager.broadcast(EventType.MYCOBRAIN_RESULT.value, {
        "jobId": job_id, "status": status, "result": result
    })
