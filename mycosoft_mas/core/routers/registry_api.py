"""
Registry API - February 4, 2026

FastAPI router exposing system registry endpoints for:
- Systems: List and manage registered systems
- APIs: Query the API catalog
- Agents: Track AI agents
- Services: Monitor services
- Devices: MycoBrain device management
- Code Files: Source code index
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from mycosoft_mas.registry.system_registry import (
    get_registry, SystemRegistry, SystemInfo, APIInfo, AgentInfo,
    ServiceInfo, DeviceInfo, CodeFileInfo, SystemType, ServiceType, DeviceType
)
from mycosoft_mas.registry.api_indexer import get_api_indexer, index_all_apis
from mycosoft_mas.registry.code_indexer import get_code_indexer, index_all_code
from mycosoft_mas.registry.device_registry import get_device_registry, initialize_devices

logger = logging.getLogger("RegistryAPI")

router = APIRouter(prefix="/api/registry", tags=["registry"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SystemRegistration(BaseModel):
    """Request to register a system."""
    name: str
    type: str
    url: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentRegistration(BaseModel):
    """Request to register an agent."""
    name: str
    type: str
    description: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    version: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class ServiceRegistration(BaseModel):
    """Request to register a service."""
    name: str
    type: str
    description: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    health_endpoint: Optional[str] = None


class DeviceRegistration(BaseModel):
    """Request to register a device."""
    device_id: str
    name: str
    type: str
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class IndexResult(BaseModel):
    """Result of an indexing operation."""
    status: str
    indexed_at: str
    details: Dict[str, Any]


# ============================================================================
# Systems Endpoints
# ============================================================================

@router.get("/systems")
async def list_systems(status: Optional[str] = Query(None)):
    """List all registered systems."""
    registry = get_registry()
    systems = await registry.list_systems(status)
    return {
        "systems": [s.dict() for s in systems],
        "count": len(systems)
    }


@router.get("/systems/{name}")
async def get_system(name: str):
    """Get a specific system by name."""
    registry = get_registry()
    system = await registry.get_system(name)
    if not system:
        raise HTTPException(status_code=404, detail=f"System not found: {name}")
    return system.dict()


@router.post("/systems")
async def register_system(request: SystemRegistration):
    """Register or update a system."""
    registry = get_registry()
    
    system = SystemInfo(
        name=request.name,
        type=SystemType(request.type),
        url=request.url,
        description=request.description,
        metadata=request.metadata
    )
    
    result = await registry.register_system(system)
    return result.dict()


# ============================================================================
# APIs Endpoints
# ============================================================================

@router.get("/apis")
async def list_apis(
    system: Optional[str] = Query(None, description="Filter by system name"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    include_deprecated: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """List registered API endpoints."""
    registry = get_registry()
    apis = await registry.list_apis(system, tag, include_deprecated)
    
    # Paginate
    total = len(apis)
    apis = apis[offset:offset + limit]
    
    return {
        "apis": [a.dict() for a in apis],
        "count": len(apis),
        "total": total,
        "has_more": total > offset + limit
    }


@router.get("/apis/count")
async def get_api_count():
    """Get total count of registered APIs."""
    registry = get_registry()
    count = await registry.get_api_count()
    return {"count": count}


@router.post("/apis/index")
async def trigger_api_indexing(background_tasks: BackgroundTasks):
    """Trigger API indexing for all systems."""
    background_tasks.add_task(index_all_apis)
    return {
        "status": "indexing_started",
        "message": "API indexing started in background"
    }


@router.post("/apis/index/sync")
async def sync_index_apis() -> IndexResult:
    """Synchronously index all APIs (blocking)."""
    result = await index_all_apis()
    return IndexResult(
        status="completed",
        indexed_at=result["indexed_at"],
        details=result
    )


# ============================================================================
# Agents Endpoints
# ============================================================================

@router.get("/agents")
async def list_agents(type: Optional[str] = Query(None)):
    """List all registered agents."""
    registry = get_registry()
    agents = await registry.list_agents(type)
    return {
        "agents": [a.dict() for a in agents],
        "count": len(agents)
    }


@router.post("/agents")
async def register_agent(request: AgentRegistration):
    """Register or update an agent."""
    registry = get_registry()
    
    agent = AgentInfo(
        name=request.name,
        type=request.type,
        description=request.description,
        capabilities=request.capabilities,
        version=request.version,
        config=request.config
    )
    
    result = await registry.register_agent(agent)
    return result.dict()


# ============================================================================
# Services Endpoints
# ============================================================================

@router.get("/services")
async def list_services(type: Optional[str] = Query(None)):
    """List all registered services."""
    registry = get_registry()
    
    # Get services via direct query
    await registry.initialize()
    async with registry._pool.acquire() as conn:
        if type:
            rows = await conn.fetch("""
                SELECT id, name, type, description, host, port, status,
                       health_endpoint, last_health_check, metadata
                FROM registry.services WHERE type = $1
                ORDER BY name
            """, type)
        else:
            rows = await conn.fetch("""
                SELECT id, name, type, description, host, port, status,
                       health_endpoint, last_health_check, metadata
                FROM registry.services ORDER BY name
            """)
    
    import json
    services = [
        {
            "id": str(row["id"]),
            "name": row["name"],
            "type": row["type"],
            "description": row["description"],
            "host": row["host"],
            "port": row["port"],
            "status": row["status"],
            "health_endpoint": row["health_endpoint"],
            "last_health_check": row["last_health_check"].isoformat() if row["last_health_check"] else None,
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
        }
        for row in rows
    ]
    
    return {
        "services": services,
        "count": len(services)
    }


@router.post("/services")
async def register_service(request: ServiceRegistration):
    """Register or update a service."""
    registry = get_registry()
    
    service = ServiceInfo(
        name=request.name,
        type=ServiceType(request.type),
        description=request.description,
        host=request.host,
        port=request.port,
        health_endpoint=request.health_endpoint
    )
    
    result = await registry.register_service(service)
    return result.dict()


@router.post("/services/{name}/health")
async def update_service_health(name: str, status: str):
    """Update service health status."""
    registry = get_registry()
    await registry.update_service_health(name, status)
    return {"status": "updated", "service": name, "health": status}


# ============================================================================
# Devices Endpoints
# ============================================================================

@router.get("/devices")
async def list_devices(type: Optional[str] = Query(None)):
    """List all registered devices."""
    registry = get_registry()
    devices = await registry.list_devices(type)
    return {
        "devices": [d.dict() for d in devices],
        "count": len(devices)
    }


@router.get("/devices/health")
async def get_devices_health():
    """Get health summary for all devices."""
    device_registry = get_device_registry()
    return await device_registry.get_device_health()


@router.get("/devices/firmware")
async def get_firmware_report():
    """Get firmware version report."""
    device_registry = get_device_registry()
    return await device_registry.get_firmware_report()


@router.post("/devices")
async def register_device(request: DeviceRegistration):
    """Register or update a device."""
    registry = get_registry()
    
    device = DeviceInfo(
        device_id=request.device_id,
        name=request.name,
        type=DeviceType(request.type),
        firmware_version=request.firmware_version,
        hardware_version=request.hardware_version,
        config=request.config
    )
    
    result = await registry.register_device(device)
    return result.dict()


@router.post("/devices/initialize")
async def init_known_devices():
    """Initialize all known devices."""
    result = await initialize_devices()
    return result


@router.post("/devices/{device_id}/status")
async def update_device_status(
    device_id: str,
    status: str,
    telemetry: Optional[Dict[str, Any]] = None
):
    """Update device status and telemetry."""
    device_registry = get_device_registry()
    device = await device_registry.update_device_status(device_id, status, telemetry)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    return device.dict()


# ============================================================================
# Code Files Endpoints
# ============================================================================

@router.get("/code/stats")
async def get_code_stats():
    """Get code file statistics by repository."""
    registry = get_registry()
    return await registry.get_code_stats()


@router.post("/code/index")
async def trigger_code_indexing(background_tasks: BackgroundTasks):
    """Trigger code file indexing for all repositories."""
    background_tasks.add_task(index_all_code)
    return {
        "status": "indexing_started",
        "message": "Code indexing started in background"
    }


@router.post("/code/index/sync")
async def sync_index_code() -> IndexResult:
    """Synchronously index all code (blocking)."""
    result = await index_all_code()
    return IndexResult(
        status="completed",
        indexed_at=result["indexed_at"],
        details=result
    )


# ============================================================================
# Statistics and Health
# ============================================================================

@router.get("/stats")
async def get_registry_stats():
    """Get overall registry statistics."""
    registry = get_registry()
    return await registry.get_registry_stats()


@router.get("/health")
async def registry_health():
    """Registry service health check."""
    registry = get_registry()
    
    try:
        await registry.initialize()
        stats = await registry.get_registry_stats()
        
        return {
            "status": "healthy",
            "service": "system-registry",
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "system-registry",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
