"""
Infrastructure Operations API Routes
Provides REST endpoints for Proxmox, UniFi, NAS, GPU, and UART operations
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging

from mycosoft_mas.services.infrastructure_ops import InfrastructureOpsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["infrastructure"])

# Initialize service
infra_ops = InfrastructureOpsService()


# ============================================================================
# Request Models
# ============================================================================

class SnapshotRequest(BaseModel):
    """Request to create VM snapshot"""
    node: str = Field(..., description="Proxmox node name")
    vmid: int = Field(..., description="VM ID")
    snapshot_name: str = Field(..., description="Snapshot name")
    confirm: bool = Field(False, description="Confirm execution (dry-run if false)")


class RollbackRequest(BaseModel):
    """Request to rollback VM to snapshot"""
    node: str = Field(..., description="Proxmox node name")
    vmid: int = Field(..., description="VM ID")
    snapshot_name: str = Field(..., description="Snapshot name to rollback to")
    confirm: bool = Field(False, description="Confirm execution (dry-run if false)")


class CommandRequest(BaseModel):
    """Generic command request"""
    command: str = Field(..., description="Command to execute")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Command parameters")
    confirm: bool = Field(False, description="Confirm execution")


# ============================================================================
# Status Endpoints
# ============================================================================

@router.get("/status")
async def get_status():
    """Get overall infrastructure status"""
    try:
        status = await infra_ops.get_status()
        return status
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Proxmox Endpoints
# ============================================================================

@router.post("/proxmox/inventory")
async def proxmox_inventory():
    """Get Proxmox inventory (nodes, VMs, containers, storage)"""
    try:
        inventory = await infra_ops.proxmox_inventory()
        return inventory
    except Exception as e:
        logger.error(f"Proxmox inventory failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proxmox/snapshot")
async def proxmox_snapshot(request: SnapshotRequest):
    """
    Create VM snapshot with confirmation gate
    
    Set confirm=true to execute, otherwise returns dry-run result.
    """
    try:
        result = await infra_ops.proxmox_snapshot(
            node=request.node,
            vmid=request.vmid,
            snapshot_name=request.snapshot_name,
            confirm=request.confirm
        )
        return result
    except Exception as e:
        logger.error(f"Proxmox snapshot failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proxmox/rollback")
async def proxmox_rollback(request: RollbackRequest):
    """
    Rollback VM to snapshot with confirmation gate
    
    Set confirm=true to execute, otherwise returns dry-run result.
    WARNING: This operation will revert VM state!
    """
    try:
        result = await infra_ops.proxmox_rollback(
            node=request.node,
            vmid=request.vmid,
            snapshot_name=request.snapshot_name,
            confirm=request.confirm
        )
        return result
    except Exception as e:
        logger.error(f"Proxmox rollback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# UniFi Endpoints
# ============================================================================

@router.post("/unifi/topology")
async def unifi_topology():
    """Get UniFi network topology (devices, clients, networks, WLANs)"""
    try:
        topology = await infra_ops.unifi_topology()
        return topology
    except Exception as e:
        logger.error(f"UniFi topology failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unifi/client/{mac}")
async def unifi_client_info(mac: str):
    """Get detailed information about a specific client"""
    try:
        client_info = await infra_ops.unifi_client_info(mac)
        return client_info
    except Exception as e:
        logger.error(f"UniFi client info failed: {e}")
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# GPU Endpoints
# ============================================================================

@router.post("/gpu/run_test")
async def gpu_run_test():
    """Run GPU validation test"""
    try:
        result = await infra_ops.gpu_run_test()
        return result
    except Exception as e:
        logger.error(f"GPU test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# UART Endpoints
# ============================================================================

@router.get("/uart/tail")
async def uart_tail(lines: int = Query(100, description="Number of lines to return")):
    """Get recent UART log entries from MycoBrain"""
    try:
        result = await infra_ops.uart_tail(lines)
        return result
    except Exception as e:
        logger.error(f"UART tail failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NAS Endpoints
# ============================================================================

@router.get("/nas/status")
async def nas_status():
    """Check NAS mount status and disk usage"""
    try:
        status = await infra_ops.nas_status()
        return status
    except Exception as e:
        logger.error(f"NAS status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Generic Command Endpoint
# ============================================================================

@router.post("/command")
async def execute_command(request: CommandRequest):
    """
    Execute infrastructure command
    
    Supported commands:
    - proxmox.inventory
    - proxmox.snapshot
    - proxmox.rollback
    - unifi.topology
    - gpu.run_test
    - uart.tail
    - nas.status
    """
    try:
        command = request.command
        params = request.params or {}
        
        if command == "proxmox.inventory":
            return await infra_ops.proxmox_inventory()
        
        elif command == "proxmox.snapshot":
            return await infra_ops.proxmox_snapshot(
                node=params.get("node"),
                vmid=params.get("vmid"),
                snapshot_name=params.get("snapshot_name"),
                confirm=request.confirm
            )
        
        elif command == "proxmox.rollback":
            return await infra_ops.proxmox_rollback(
                node=params.get("node"),
                vmid=params.get("vmid"),
                snapshot_name=params.get("snapshot_name"),
                confirm=request.confirm
            )
        
        elif command == "unifi.topology":
            return await infra_ops.unifi_topology()
        
        elif command == "gpu.run_test":
            return await infra_ops.gpu_run_test()
        
        elif command == "uart.tail":
            lines = params.get("lines", 100)
            return await infra_ops.uart_tail(lines)
        
        elif command == "nas.status":
            return await infra_ops.nas_status()
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown command: {command}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Speech Interface Endpoint
# ============================================================================

@router.post("/speak")
async def speak(request: Dict[str, Any]):
    """
    Speech interface endpoint
    
    Placeholder for n8n integration
    """
    text = request.get("text", "")
    
    return {
        "status": "not_implemented",
        "message": "Speech interface requires n8n workflow deployment",
        "text": text,
        "next_steps": [
            "Deploy n8n workflow from infra/myca-online/out/n8n/",
            "Configure TTS/STT services",
            "Enable voice profiles in docker-compose"
        ]
    }
