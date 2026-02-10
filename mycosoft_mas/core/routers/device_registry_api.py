"""
Device Registry API Router

Central registry for MycoBrain devices across the network.
Devices register via heartbeat and are tracked with TTL expiration.

Created: February 10, 2026
"""

import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
import httpx

logger = logging.getLogger("DeviceRegistry")

router = APIRouter(prefix="/api/devices", tags=["device-registry"])

# In-memory device registry (Redis can be added later for persistence)
_device_registry: Dict[str, Dict[str, Any]] = {}
_device_last_seen: Dict[str, datetime] = {}

# Orchestrator integration (optional)
_orchestrator = None

def _get_orchestrator():
    """Get the orchestrator instance if available."""
    global _orchestrator
    if _orchestrator is None:
        try:
            from mycosoft_mas.core.orchestrator import get_orchestrator, ServiceConfig
            _orchestrator = get_orchestrator()
            logger.info("Device registry connected to orchestrator")
        except ImportError:
            logger.debug("Orchestrator not available for device registration")
        except Exception as e:
            logger.warning(f"Orchestrator initialization failed: {e}")
    return _orchestrator


def _register_device_with_orchestrator(device_id: str, device: Dict[str, Any]):
    """Register device as a service with the orchestrator for health monitoring."""
    orchestrator = _get_orchestrator()
    if not orchestrator:
        return
    
    try:
        from mycosoft_mas.core.orchestrator import ServiceConfig
        
        host = device.get("host", "")
        port = device.get("port", 8003)
        
        # Build health URL
        if host.startswith("http://") or host.startswith("https://"):
            health_url = f"{host.rstrip('/')}/health"
        elif device.get("connection_type") == "cloudflare":
            health_url = f"https://{host}/health"
        else:
            health_url = f"http://{host}:{port}/health"
        
        config = ServiceConfig(
            id=f"mycobrain-{device_id}",
            name=device.get("device_name", f"MycoBrain {device_id}"),
            health_url=health_url,
            host=host if not host.startswith("http") else None,
            port=port if not host.startswith("http") else None,
            health_check_interval=30,
            failure_threshold=3,
            is_critical=False,
        )
        
        orchestrator.register_service(config)
        logger.info(f"Device {device_id} registered with orchestrator")
        
    except Exception as e:
        logger.warning(f"Failed to register device {device_id} with orchestrator: {e}")

# Configuration
DEVICE_TTL_SECONDS = int(os.getenv("DEVICE_TTL_SECONDS", "120"))  # 2 minutes default
DEVICE_STALE_SECONDS = int(os.getenv("DEVICE_STALE_SECONDS", "60"))  # 1 minute stale threshold


class DeviceHeartbeat(BaseModel):
    """Schema for device heartbeat/registration (serial, LoRa, Bluetooth, WiFi gateways)."""
    device_id: str = Field(..., description="Unique device identifier")
    device_name: str = Field(default="MycoBrain", description="Human-friendly device name")
    device_role: str = Field(default="standalone", description="Device role: mushroom1, sporebase, hyphae1, alarm, gateway, mycodrone, standalone")
    device_display_name: Optional[str] = Field(default=None, description="UI display name (e.g. 'Mushroom 1', 'SporeBase Alpha')")
    host: str = Field(..., description="Reachable IP or URL (gateway/server reachable from MAS)")
    port: int = Field(default=8003, description="MycoBrain service or gateway port")
    firmware_version: str = Field(default="unknown")
    board_type: str = Field(default="esp32s3", description="Board type: esp32s3, esp32, service, etc.")
    sensors: List[str] = Field(default_factory=list, description="Connected sensors")
    capabilities: List[str] = Field(default_factory=list, description="Device capabilities")
    location: Optional[str] = Field(default=None, description="Physical location")
    connection_type: str = Field(default="lan", description="lan, tailscale, cloudflare")
    ingestion_source: str = Field(default="serial", description="serial, lora, bluetooth, wifi, gateway")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DeviceInfo(BaseModel):
    """Full device information returned by registry."""
    device_id: str
    device_name: str
    device_role: str = "standalone"
    device_display_name: Optional[str] = None
    host: str
    port: int
    firmware_version: str
    board_type: str
    sensors: List[str]
    capabilities: List[str]
    location: Optional[str]
    connection_type: str
    ingestion_source: str = "serial"
    status: str  # online, stale, offline
    last_seen: str
    registered_at: str
    extra: Dict[str, Any] = Field(default_factory=dict)


class DeviceCommand(BaseModel):
    """Command to send to a remote device."""
    command: str = Field(..., description="Command to send (CLI format)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Optional parameters")
    timeout: float = Field(default=5.0, description="Command timeout in seconds")


def _get_device_status(device_id: str) -> str:
    """Determine device status based on last seen time."""
    if device_id not in _device_last_seen:
        return "offline"
    
    last_seen = _device_last_seen[device_id]
    now = datetime.now(timezone.utc)
    elapsed = (now - last_seen).total_seconds()
    
    if elapsed > DEVICE_TTL_SECONDS:
        return "offline"
    elif elapsed > DEVICE_STALE_SECONDS:
        return "stale"
    else:
        return "online"


def _cleanup_expired_devices():
    """Remove devices that haven't sent heartbeat within TTL."""
    now = datetime.now(timezone.utc)
    expired = []
    
    for device_id, last_seen in list(_device_last_seen.items()):
        if (now - last_seen).total_seconds() > DEVICE_TTL_SECONDS:
            expired.append(device_id)
    
    for device_id in expired:
        if device_id in _device_registry:
            logger.info(f"Device expired: {device_id}")
            del _device_registry[device_id]
        if device_id in _device_last_seen:
            del _device_last_seen[device_id]
    
    return expired


@router.post("/register")
async def register_device(heartbeat: DeviceHeartbeat):
    """
    Register or update a device via heartbeat.
    
    Devices should call this endpoint every 30 seconds to maintain registration.
    Devices not seen within TTL (2 minutes) are marked offline.
    """
    now = datetime.now(timezone.utc)
    device_id = heartbeat.device_id
    
    # Check if this is a new registration
    is_new = device_id not in _device_registry
    
    # Update or create device entry
    if is_new:
        _device_registry[device_id] = {
            "registered_at": now.isoformat(),
        }
        logger.info(f"New device registered: {device_id} ({heartbeat.device_name}) from {heartbeat.host}:{heartbeat.port}")
    
    # Update device info (supports serial + LoRa/BT/WiFi ingestion + device role/identity)
    _device_registry[device_id].update({
        "device_id": device_id,
        "device_name": heartbeat.device_name,
        "device_role": heartbeat.device_role,
        "device_display_name": heartbeat.device_display_name,
        "host": heartbeat.host,
        "port": heartbeat.port,
        "firmware_version": heartbeat.firmware_version,
        "board_type": heartbeat.board_type,
        "sensors": heartbeat.sensors,
        "capabilities": heartbeat.capabilities,
        "location": heartbeat.location,
        "connection_type": heartbeat.connection_type,
        "ingestion_source": heartbeat.ingestion_source,
        "extra": heartbeat.extra,
        "last_seen": now.isoformat(),
    })
    
    _device_last_seen[device_id] = now
    
    # Register with orchestrator for health monitoring (new devices only)
    if is_new:
        _register_device_with_orchestrator(device_id, _device_registry[device_id])
    
    # Cleanup expired devices occasionally
    _cleanup_expired_devices()
    
    return {
        "status": "registered" if is_new else "updated",
        "device_id": device_id,
        "timestamp": now.isoformat(),
    }


async def _list_devices_impl(
    status: Optional[str] = None,
    include_offline: bool = False,
):
    """Shared implementation for list devices (used by both / and empty path)."""
    _cleanup_expired_devices()
    devices_out = []
    for device_id, device in _device_registry.items():
        device_status = _get_device_status(device_id)
        if status and device_status != status:
            continue
        if not include_offline and device_status == "offline":
            continue
        devices_out.append({**device, "status": device_status})
    return {
        "devices": devices_out,
        "count": len(devices_out),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("")
@router.get("/")
async def list_devices(
    status: Optional[str] = Query(None, description="Filter by status: online, stale, offline"),
    include_offline: bool = Query(False, description="Include offline devices"),
):
    """
    List all registered devices (serial, LoRa, Bluetooth, WiFi gateways).
    Returns devices with their current status based on last heartbeat.
    """
    return await _list_devices_impl(status=status, include_offline=include_offline)


@router.get("/{device_id}")
async def get_device(device_id: str):
    """Get information about a specific device."""
    _cleanup_expired_devices()
    
    if device_id not in _device_registry:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    
    device = _device_registry[device_id]
    device_status = _get_device_status(device_id)
    
    return {
        **device,
        "status": device_status,
    }


@router.delete("/{device_id}")
async def unregister_device(device_id: str):
    """Unregister a device."""
    if device_id not in _device_registry:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    
    del _device_registry[device_id]
    if device_id in _device_last_seen:
        del _device_last_seen[device_id]
    
    logger.info(f"Device unregistered: {device_id}")
    
    return {
        "status": "unregistered",
        "device_id": device_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/{device_id}/command")
async def send_device_command(device_id: str, cmd: DeviceCommand):
    """
    Forward a command to a remote device.
    
    The command is proxied to the device's MycoBrain service.
    """
    _cleanup_expired_devices()
    
    if device_id not in _device_registry:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    
    device = _device_registry[device_id]
    device_status = _get_device_status(device_id)
    
    if device_status == "offline":
        raise HTTPException(status_code=503, detail=f"Device {device_id} is offline")
    
    # Build target URL
    host = device["host"]
    port = device["port"]
    
    # Determine protocol (https for cloudflare, http for tailscale/lan)
    if host.startswith("http://") or host.startswith("https://"):
        base_url = host.rstrip("/")
    elif device.get("connection_type") == "cloudflare":
        base_url = f"https://{host}"
    else:
        base_url = f"http://{host}:{port}"
    
    # Forward command to device
    try:
        async with httpx.AsyncClient(timeout=cmd.timeout) as client:
            response = await client.post(
                f"{base_url}/devices/{device_id}/command",
                json={
                    "command": {
                        "cmd": cmd.command,
                        **cmd.params,
                    }
                },
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Device returned error: {response.text}"
                )
            
            return {
                "status": "ok",
                "device_id": device_id,
                "command": cmd.command,
                "response": response.json(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Command timeout for device {device_id}")
    except httpx.ConnectError as e:
        # Update device status
        logger.warning(f"Device {device_id} unreachable: {e}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to device {device_id}: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {e}")


@router.get("/{device_id}/telemetry")
async def get_device_telemetry(device_id: str):
    """
    Get telemetry from a remote device.
    
    Proxies the telemetry request to the device's MycoBrain service.
    """
    _cleanup_expired_devices()
    
    if device_id not in _device_registry:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    
    device = _device_registry[device_id]
    device_status = _get_device_status(device_id)
    
    if device_status == "offline":
        raise HTTPException(status_code=503, detail=f"Device {device_id} is offline")
    
    # Build target URL
    host = device["host"]
    port = device["port"]
    
    if host.startswith("http://") or host.startswith("https://"):
        base_url = host.rstrip("/")
    elif device.get("connection_type") == "cloudflare":
        base_url = f"https://{host}"
    else:
        base_url = f"http://{host}:{port}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/devices/{device_id}/telemetry")
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Device returned error: {response.text}"
                )
            
            return response.json()
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Telemetry timeout for device {device_id}")
    except httpx.ConnectError as e:
        raise HTTPException(status_code=503, detail=f"Cannot connect to device {device_id}: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Telemetry failed: {e}")


@router.get("/health")
async def registry_health():
    """Health check for the device registry."""
    _cleanup_expired_devices()
    
    online = sum(1 for d in _device_registry if _get_device_status(d) == "online")
    stale = sum(1 for d in _device_registry if _get_device_status(d) == "stale")
    
    return {
        "status": "ok",
        "total_devices": len(_device_registry),
        "online_devices": online,
        "stale_devices": stale,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
