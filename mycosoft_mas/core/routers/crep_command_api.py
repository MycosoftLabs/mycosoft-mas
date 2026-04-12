"""
CREP Command API — Mar 13, 2026

REST endpoint for autonomous MYCA and other callers to execute
CREP map commands via the CrepCommandBus. Returns frontend_command
for website consumption.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.crep import get_crep_command_bus
from mycosoft_mas.integrations.zeetachec_client import MaritimeSensorNetworkClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crep", tags=["crep"])
sensor_network_client = MaritimeSensorNetworkClient()


# ============================================================================
# Request/Response Models
# ============================================================================


class CrepCommandRequest(BaseModel):
    """Request to execute a CREP tool command."""

    tool: str = Field(..., description="CREP tool name: crep_fly_to, crep_show_layer, etc.")
    args: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    confirmed: bool = Field(False, description="User confirmed (required for clearFilters)")


class CrepCommandResponse(BaseModel):
    """Response from CREP command execution."""

    success: bool = Field(..., description="Whether command executed successfully")
    frontend_command: Optional[Dict[str, Any]] = Field(
        None, description="Command for website to execute"
    )
    speak: Optional[str] = Field(None, description="Text for MYCA to speak")
    requires_confirmation: bool = Field(False, description="Command needs user confirmation")
    error: Optional[str] = Field(None, description="Error message if failed")


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/command", response_model=CrepCommandResponse)
async def execute_crep_command(request: CrepCommandRequest):
    """
    Execute a CREP map command via the CrepCommandBus.

    For autonomous MYCA and tool callers. Returns frontend_command
    that the website CREP dashboard can consume.
    """
    bus = get_crep_command_bus()
    result = bus.execute(
        tool_name=request.tool,
        args=request.args,
        confirmed=request.confirmed,
    )
    if not result.get("success"):
        if result.get("requires_confirmation"):
            return CrepCommandResponse(
                success=False,
                requires_confirmation=True,
                error=result.get("message", "Command requires confirmation"),
            )
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "CREP command failed"),
        )
    return CrepCommandResponse(
        success=True,
        frontend_command=result.get("frontend_command"),
        speak=result.get("speak"),
    )


@router.get("/tools")
async def list_crep_tools():
    """List available CREP tools for autonomous MYCA."""
    tools = [
        {
            "name": "crep_fly_to",
            "args": ["center", "zoom?", "duration?"],
            "description": "Fly map to [lon, lat]",
        },
        {
            "name": "crep_geocode_and_fly_to",
            "args": ["query", "zoom?", "duration?"],
            "description": "Geocode and fly",
        },
        {
            "name": "crep_set_layer_visibility",
            "args": ["layer", "visible"],
            "description": "Show or hide layer",
        },
        {"name": "crep_toggle_layer", "args": ["layer"], "description": "Toggle layer visibility"},
        {
            "name": "crep_apply_filter",
            "args": ["filter_type", "filter_value"],
            "description": "Apply filter",
        },
        {
            "name": "crep_clear_filters",
            "args": [],
            "description": "Clear all filters (requires confirmation)",
        },
        {
            "name": "crep_get_view_context",
            "args": [],
            "description": "Get current viewport context",
        },
        {
            "name": "crep_get_entity_details",
            "args": ["entity"],
            "description": "Get entity details",
        },
        {
            "name": "crep_set_time_cursor",
            "args": ["time"],
            "description": "Set timeline cursor (ISO8601)",
        },
        {"name": "crep_timeline_search", "args": ["query"], "description": "Search timeline"},
        {"name": "crep_set_zoom", "args": ["zoom", "duration?"], "description": "Set zoom level"},
        {
            "name": "crep_zoom_by",
            "args": ["delta", "duration?"],
            "description": "Zoom in/out by delta",
        },
        {
            "name": "crep_pan_by",
            "args": ["offset", "duration?"],
            "description": "Pan map by [dx, dy]",
        },
    ]
    return {"tools": tools}


# ============================================================================
# CREP MARITIME SENSOR COMMANDS — TAC-O
# ============================================================================


@router.post("/command/sensor/deploy")
async def deploy_sensor(command: dict):
    """Deploy a maritime sensor at specified depth/location."""
    sensor_id = command.get("sensor_id")
    if not sensor_id:
        raise HTTPException(status_code=400, detail="sensor_id_required")
    result = await sensor_network_client.send_command(
        sensor_id=sensor_id,
        command="deploy",
        params={"depth_m": command.get("depth_m"), "location": command.get("location")},
    )
    return {"command": "deploy", **result}


@router.post("/command/sensor/reconfigure")
async def reconfigure_sensor(command: dict):
    """Reconfigure a maritime sensor's operating parameters."""
    sensor_id = command.get("sensor_id")
    if not sensor_id:
        raise HTTPException(status_code=400, detail="sensor_id_required")
    result = await sensor_network_client.reconfigure_sensor(
        sensor_id=sensor_id,
        config=command.get("config", {}),
    )
    return {"command": "reconfigure", **result}


@router.post("/command/sensor/interrogate")
async def interrogate_sensor(command: dict):
    """Interrogate a maritime sensor for current status and data."""
    sensor_id = command.get("sensor_id")
    if not sensor_id:
        raise HTTPException(status_code=400, detail="sensor_id_required")
    result = await sensor_network_client.send_command(
        sensor_id=sensor_id,
        command="interrogate",
        params=command.get("params", {}),
    )
    return {"command": "interrogate", **result}
