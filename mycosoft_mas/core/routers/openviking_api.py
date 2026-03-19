"""
OpenViking API - REST endpoints for managing OpenViking device connections.

Provides endpoints to register/unregister edge devices running OpenViking,
trigger manual sync, query device memory, and push content to devices.

Created: March 19, 2026
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.core.routers.api_keys import require_api_key_scoped

router = APIRouter(prefix="/api/openviking", tags=["OpenViking - Edge Memory"])

# Auth dependencies — scoped by operation type
_read_auth = require_api_key_scoped("openviking:read")
_write_auth = require_api_key_scoped("openviking:write")
_admin_auth = require_api_key_scoped("openviking:admin")


# ── Request/Response Models ────────────────────────────────────────────


class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    openviking_url: str = Field(
        ..., description="OpenViking server URL (e.g., http://192.168.0.123:1933)"
    )
    device_name: Optional[str] = Field(None, description="Human-readable device name")
    tags: Optional[List[str]] = Field(None, description="Tags for sync filtering")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Extra metadata")


class DeviceResponse(BaseModel):
    device_id: str
    device_name: str
    openviking_url: str
    status: str
    last_sync: Optional[str] = None
    sync_count: int = 0
    tags: List[str] = []


class QueryRequest(BaseModel):
    query: str = Field(..., description="Semantic search query")
    tier: str = Field("L1", description="Context tier: L0 (abstract), L1 (overview), L2 (full)")
    top_k: int = Field(10, ge=1, le=100, description="Max results")
    target_uri: Optional[str] = Field(None, description="Restrict to a viking:// path")


class PushRequest(BaseModel):
    content: str = Field(..., description="Content to push to the device")
    viking_path: str = Field(
        "viking://resources/mas-agent-context/",
        description="Target path on the device's viking:// filesystem",
    )
    reason: Optional[str] = Field(None, description="Reason for the push (triggers L0/L1 generation)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Extra metadata")


class SyncResponse(BaseModel):
    device_id: str
    synced_items: int = 0
    pushed_items: int = 0
    errors: int = 0
    timestamp: str


class SyncServiceStatus(BaseModel):
    running: bool
    sync_interval: int
    history_count: int
    last_sync: Optional[str] = None


# ── Endpoints ──────────────────────────────────────────────────────────


@router.post("/devices/register", response_model=DeviceResponse)
async def register_device(request: DeviceRegisterRequest, _auth: dict = _admin_auth) -> DeviceResponse:
    """Register an edge device's OpenViking instance.

    Connects to the device's OpenViking server, verifies reachability,
    and sets up the standard viking:// directory structure.
    """
    from mycosoft_mas.memory.openviking_bridge import get_openviking_bridge

    bridge = await get_openviking_bridge()
    try:
        conn = await bridge.register_device(
            device_id=request.device_id,
            openviking_url=request.openviking_url,
            device_name=request.device_name,
            tags=request.tags,
            metadata=request.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return DeviceResponse(
        device_id=conn.device_id,
        device_name=conn.device_name,
        openviking_url=conn.openviking_url,
        status=conn.status.value,
        last_sync=conn.last_sync.isoformat() if conn.last_sync else None,
        sync_count=conn.sync_count,
        tags=conn.tags,
    )


@router.delete("/devices/{device_id}")
async def unregister_device(device_id: str, _auth: dict = _admin_auth) -> Dict[str, Any]:
    """Unregister a device and close its OpenViking connection."""
    from mycosoft_mas.memory.openviking_bridge import get_openviking_bridge

    bridge = await get_openviking_bridge()
    removed = await bridge.unregister_device(device_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    return {"status": "unregistered", "device_id": device_id}


@router.get("/devices", response_model=List[DeviceResponse])
async def list_devices(_auth: dict = _read_auth) -> List[DeviceResponse]:
    """List all registered OpenViking devices."""
    from mycosoft_mas.memory.openviking_bridge import get_openviking_bridge

    bridge = await get_openviking_bridge()
    devices = bridge.list_devices()
    return [
        DeviceResponse(
            device_id=d.device_id,
            device_name=d.device_name,
            openviking_url=d.openviking_url,
            status=d.status.value,
            last_sync=d.last_sync.isoformat() if d.last_sync else None,
            sync_count=d.sync_count,
            tags=d.tags,
        )
        for d in devices
    ]


@router.post("/sync/{device_id}", response_model=SyncResponse)
async def sync_device(device_id: str, _auth: dict = _write_auth) -> SyncResponse:
    """Trigger a manual bidirectional sync for a specific device."""
    from mycosoft_mas.memory.openviking_bridge import get_openviking_bridge

    bridge = await get_openviking_bridge()
    if not bridge.get_device(device_id):
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    result = await bridge.sync_device(device_id)
    pull = result.get("pull", {})
    push = result.get("push", {})
    return SyncResponse(
        device_id=device_id,
        synced_items=pull.get("synced_items", 0),
        pushed_items=push.get("pushed_items", 0),
        errors=pull.get("errors", 0) + push.get("errors", 0),
        timestamp=result.get("timestamp", datetime.now(timezone.utc).isoformat()),
    )


@router.post("/sync/all")
async def sync_all_devices(_auth: dict = _write_auth) -> List[Dict[str, Any]]:
    """Trigger a manual sync for all registered devices."""
    from mycosoft_mas.memory.openviking_bridge import get_openviking_bridge

    bridge = await get_openviking_bridge()
    return await bridge.sync_all_devices()


@router.post("/query/{device_id}")
async def query_device_memory(
    device_id: str,
    request: QueryRequest,
    _auth: dict = _read_auth,
) -> Dict[str, Any]:
    """Query a device's OpenViking memory with tiered context loading.

    Tier controls how much context is returned:
    - L0: ~100 token abstract (fastest, cheapest)
    - L1: ~2k token overview (balanced)
    - L2: Full content (most detail)
    """
    from mycosoft_mas.memory.openviking_bridge import get_openviking_bridge

    bridge = await get_openviking_bridge()
    if not bridge.get_device(device_id):
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    results = await bridge.query_device_memory(
        device_id=device_id,
        query=request.query,
        tier=request.tier,
        top_k=request.top_k,
        target_uri=request.target_uri,
    )
    if results is None:
        raise HTTPException(status_code=502, detail="Device query failed")

    return {
        "device_id": device_id,
        "query": request.query,
        "tier": request.tier,
        "result_count": len(results),
        "results": results,
    }


@router.post("/push/{device_id}")
async def push_to_device(
    device_id: str,
    request: PushRequest,
    _auth: dict = _write_auth,
) -> Dict[str, Any]:
    """Push content to a device's OpenViking filesystem.

    If `reason` is provided, content is ingested via OpenViking's pipeline
    (generates L0/L1 summaries). Otherwise, written directly.
    """
    from mycosoft_mas.memory.openviking_bridge import get_openviking_bridge

    bridge = await get_openviking_bridge()
    if not bridge.get_device(device_id):
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    if request.reason:
        uri = await bridge.push_resource_to_device(
            device_id=device_id,
            content=request.content,
            reason=request.reason,
            target=request.viking_path,
            metadata=request.metadata,
        )
        return {
            "status": "ingested" if uri else "failed",
            "device_id": device_id,
            "uri": uri,
        }
    else:
        success = await bridge.push_to_device(
            device_id=device_id,
            content=request.content,
            viking_path=request.viking_path,
            metadata=request.metadata,
        )
        return {
            "status": "pushed" if success else "failed",
            "device_id": device_id,
            "viking_path": request.viking_path,
        }


@router.get("/health")
async def openviking_health() -> Dict[str, Any]:
    """Health check for the OpenViking bridge and all device connections."""
    from mycosoft_mas.memory.openviking_bridge import get_openviking_bridge

    bridge = await get_openviking_bridge()
    return await bridge.health_check()


@router.get("/sync/status", response_model=SyncServiceStatus)
async def sync_status(_auth: dict = _read_auth) -> SyncServiceStatus:
    """Get the status of the background sync service."""
    from mycosoft_mas.memory.openviking_sync import get_openviking_sync

    sync = await get_openviking_sync()
    status = sync.get_status()
    return SyncServiceStatus(**status)


@router.post("/sync/start")
async def start_sync_service(_auth: dict = _admin_auth) -> Dict[str, str]:
    """Start the periodic background sync service."""
    from mycosoft_mas.memory.openviking_sync import get_openviking_sync

    sync = await get_openviking_sync()
    if sync.is_running:
        return {"status": "already_running"}
    await sync.start()
    return {"status": "started"}


@router.post("/sync/stop")
async def stop_sync_service(_auth: dict = _admin_auth) -> Dict[str, str]:
    """Stop the periodic background sync service."""
    from mycosoft_mas.memory.openviking_sync import get_openviking_sync

    sync = await get_openviking_sync()
    if not sync.is_running:
        return {"status": "not_running"}
    await sync.stop()
    return {"status": "stopped"}


@router.get("/sync/history")
async def sync_history(limit: int = 10, _auth: dict = _read_auth) -> List[Dict[str, Any]]:
    """Get recent sync cycle history."""
    from mycosoft_mas.memory.openviking_sync import get_openviking_sync

    sync = await get_openviking_sync()
    return sync.get_history(limit=limit)


@router.post("/devices/{device_id}/browse")
async def browse_device_filesystem(
    device_id: str,
    uri: str = "viking://",
    _auth: dict = _read_auth,
) -> Dict[str, Any]:
    """Browse a device's OpenViking filesystem (ls)."""
    from mycosoft_mas.memory.openviking_bridge import get_openviking_bridge

    bridge = await get_openviking_bridge()
    client = bridge._clients.get(device_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    entries = await client.ls(uri)
    if entries is None:
        raise HTTPException(status_code=502, detail="Device filesystem browse failed")

    return {
        "device_id": device_id,
        "uri": uri,
        "entries": entries,
    }


@router.post("/devices/{device_id}/read")
async def read_device_content(
    device_id: str,
    uri: str,
    tier: str = "L1",
    _auth: dict = _read_auth,
) -> Dict[str, Any]:
    """Read content from a device's OpenViking filesystem with tier selection."""
    from mycosoft_mas.memory.openviking_bridge import get_openviking_bridge

    bridge = await get_openviking_bridge()
    client = bridge._clients.get(device_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    content = await client.read(uri, tier=tier)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Content not found: {uri}")

    return {
        "device_id": device_id,
        "uri": uri,
        "tier": tier,
        "content": content,
    }
