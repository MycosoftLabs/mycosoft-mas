"""
GPU Node Router - API endpoints for managing mycosoft-gpu01 compute node.

Provides HTTP API for:
- GPU status monitoring
- Container deployment
- Service management
- Health checks
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging

from mycosoft_mas.integrations.gpu_node_client import (
    GPUNodeClient,
    check_gpu_node,
    deploy_gpu_service,
    deploy_personaplex_split,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/gpu-node", tags=["gpu-node"])


# Request/Response models
class DeployContainerRequest(BaseModel):
    name: str
    image: str
    port: int
    gpu: bool = True
    env_vars: Optional[Dict[str, str]] = None
    volumes: Optional[Dict[str, str]] = None


class DeployServiceRequest(BaseModel):
    service_name: str  # moshi-voice, earth2-inference, personaplex-bridge


class DeployPersonaPlexSplitRequest(BaseModel):
    inference_host: str
    inference_port: int = 8998
    mas_orchestrator_url: str = "http://192.168.0.188:8001"


class GPUStatusResponse(BaseModel):
    name: str
    memory_used_mb: int
    memory_total_mb: int
    utilization_percent: int
    temperature_c: int


class ContainerResponse(BaseModel):
    name: str
    image: str
    status: str
    ports: str


# Endpoints
@router.get("/health")
async def health():
    """Check if GPU node router is healthy."""
    return {"status": "healthy", "service": "gpu-node-router"}


@router.get("/status")
async def get_status():
    """Get full GPU node status including GPU, memory, and containers."""
    try:
        status = await check_gpu_node()
        return status
    except Exception as e:
        logger.error(f"Failed to get GPU node status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reachable")
async def check_reachable():
    """Quick check if GPU node is reachable via SSH."""
    client = GPUNodeClient()
    reachable = await client.is_reachable()
    return {"reachable": reachable, "host": client.IP}


@router.get("/gpu")
async def get_gpu_status():
    """Get GPU-specific status (memory, utilization, temperature)."""
    client = GPUNodeClient()
    
    if not await client.is_reachable():
        raise HTTPException(status_code=503, detail="GPU node not reachable")
    
    gpu = await client.get_gpu_status()
    if not gpu:
        raise HTTPException(status_code=500, detail="Failed to get GPU status")
    
    return {
        "name": gpu.name,
        "memory_used_mb": gpu.memory_used_mb,
        "memory_total_mb": gpu.memory_total_mb,
        "memory_free_mb": gpu.memory_total_mb - gpu.memory_used_mb,
        "utilization_percent": gpu.utilization_percent,
        "temperature_c": gpu.temperature_c
    }


@router.get("/containers")
async def list_containers():
    """List all containers on GPU node."""
    client = GPUNodeClient()
    
    if not await client.is_reachable():
        raise HTTPException(status_code=503, detail="GPU node not reachable")
    
    containers = await client.list_containers()
    return {
        "count": len(containers),
        "containers": [
            {
                "name": c.name,
                "image": c.image,
                "status": c.status,
                "ports": c.ports
            }
            for c in containers
        ]
    }


@router.get("/containers/{name}/logs")
async def get_container_logs(name: str, tail: int = 100):
    """Get logs from a specific container."""
    client = GPUNodeClient()
    
    if not await client.is_reachable():
        raise HTTPException(status_code=503, detail="GPU node not reachable")
    
    logs = await client.get_container_logs(name, tail)
    return {"container": name, "logs": logs}


@router.get("/containers/{name}/running")
async def check_container_running(name: str):
    """Check if a specific container is running."""
    client = GPUNodeClient()
    
    if not await client.is_reachable():
        raise HTTPException(status_code=503, detail="GPU node not reachable")
    
    running = await client.is_container_running(name)
    return {"container": name, "running": running}


@router.post("/deploy/container")
async def deploy_container(request: DeployContainerRequest):
    """Deploy a custom container to GPU node."""
    client = GPUNodeClient()
    
    if not await client.is_reachable():
        raise HTTPException(status_code=503, detail="GPU node not reachable")
    
    success = await client.deploy_container(
        name=request.name,
        image=request.image,
        port=request.port,
        gpu=request.gpu,
        env_vars=request.env_vars,
        volumes=request.volumes
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Container deployment failed")
    
    return {
        "success": True,
        "container": request.name,
        "port": request.port,
        "endpoint": f"http://{client.IP}:{request.port}"
    }


@router.post("/deploy/service")
async def deploy_known_service(request: DeployServiceRequest):
    """Deploy a known GPU service (moshi-voice, earth2-inference, personaplex-bridge)."""
    result = await deploy_gpu_service(request.service_name)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Deployment failed"))
    
    # Get service port
    client = GPUNodeClient()
    service_config = client.SERVICES.get(request.service_name, {})
    port = service_config.get("port", "unknown")
    
    return {
        "success": True,
        "service": request.service_name,
        "endpoint": f"http://{client.IP}:{port}",
        "health": result.get("health")
    }


@router.post("/deploy/personaplex-split")
async def deploy_personaplex_split_architecture(request: DeployPersonaPlexSplitRequest):
    """Deploy split PersonaPlex: bridge on gpu01, inference on remote host.

    Use when RTX 5090 machine serves heavy Moshi inference and gpu01
    handles interface/logic bridge at port 8999.
    """
    result = await deploy_personaplex_split(
        inference_host=request.inference_host,
        inference_port=request.inference_port,
        mas_orchestrator_url=request.mas_orchestrator_url,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Split deployment failed"))
    return result


@router.delete("/containers/{name}")
async def stop_container(name: str):
    """Stop and remove a container."""
    client = GPUNodeClient()
    
    if not await client.is_reachable():
        raise HTTPException(status_code=503, detail="GPU node not reachable")
    
    success = await client.stop_container(name)
    return {"success": success, "container": name, "action": "stopped"}


@router.get("/services")
async def list_known_services():
    """List known GPU services that can be deployed."""
    client = GPUNodeClient()
    return {
        "services": [
            {
                "name": name,
                "image": config["image"],
                "port": config["port"],
                "gpu_required": config["gpu"]
            }
            for name, config in client.SERVICES.items()
        ]
    }


@router.get("/services/{service_name}/health")
async def get_service_health(service_name: str):
    """Check health of a deployed GPU service."""
    client = GPUNodeClient()
    
    if service_name not in client.SERVICES:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service_name}")
    
    if not await client.is_reachable():
        raise HTTPException(status_code=503, detail="GPU node not reachable")
    
    health = await client.get_service_health(service_name)
    return {"service": service_name, **health}
