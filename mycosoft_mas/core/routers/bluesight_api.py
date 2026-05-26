"""BlueSight platform-level API routes."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import BaseModel, Field

from mycosoft_mas.bluesight.service import get_bluesight_service
from mycosoft_mas.bluesight.topology import default_topology
from mycosoft_mas.schemas.bluesight import BlueSightSensorPacket, ProfileName
from mycosoft_mas.simulation.petri_persistence import load_recent_bluesight_events

router = APIRouter(prefix="/api/natureos/bluesight", tags=["bluesight"])


class ObserveRequest(BaseModel):
    profile: ProfileName
    run_id: str
    frame_id: str
    source: str
    width: Optional[int] = None
    height: Optional[int] = None
    frame_ref: Optional[str] = None
    provider: str = "truth_bootstrap"
    truth_state: Optional[Dict[str, Any]] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EarthObserveRequest(BaseModel):
    run_id: str
    frame_id: str
    source: str = "camera"
    width: Optional[int] = None
    height: Optional[int] = None
    geo_bounds: Optional[Dict[str, float]] = None
    scene_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeviceObserveRequest(BaseModel):
    run_id: str
    frame_id: str
    source: str = "camera"
    width: Optional[int] = None
    height: Optional[int] = None
    device_id: Optional[str] = None
    calibration_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.get("/health")
async def bluesight_health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "bluesight",
        "timestamp": datetime.utcnow().isoformat(),
        "profiles_supported": ["petri", "earth_globe", "device_scene"],
        "sources_supported": ["camera", "lidar", "radar", "wifi_sense", "screen_capture", "microscope"],
    }


@router.get("/topology")
async def bluesight_topology() -> Dict[str, Any]:
    topology = default_topology()
    return {
        "status": "ok",
        "lanes": {
            key: {
                "lane": value.lane,
                "providers": value.providers,
                "sensor_sources": value.sensor_sources,
                "notes": value.notes,
            }
            for key, value in topology.items()
        },
    }


@router.post("/observe")
async def observe(request: ObserveRequest) -> Dict[str, Any]:
    service = get_bluesight_service()
    packet = BlueSightSensorPacket(
        profile=request.profile,
        run_id=request.run_id,
        frame_id=request.frame_id,
        source=request.source,  # type: ignore[arg-type]
        width=request.width,
        height=request.height,
        frame_ref=request.frame_ref,
        truth_state=request.truth_state,
        payload=request.payload,
        metadata=request.metadata,
    )
    observation = await service.observe(packet, provider_name=request.provider)
    return {"status": "ok", "observation": observation.dict()}


@router.post("/profiles/earth-globe/observe")
async def observe_earth_globe(request: EarthObserveRequest) -> Dict[str, Any]:
    service = get_bluesight_service()
    packet = BlueSightSensorPacket(
        profile="earth_globe",
        run_id=request.run_id,
        frame_id=request.frame_id,
        source=request.source,  # type: ignore[arg-type]
        width=request.width,
        height=request.height,
        payload={"geo_bounds": request.geo_bounds, "scene_type": request.scene_type},
        metadata=request.metadata,
    )
    observation = await service.observe(packet, provider_name="truth_bootstrap")
    return {"status": "ok", "observation": observation.dict()}


@router.post("/profiles/device-scene/observe")
async def observe_device_scene(request: DeviceObserveRequest) -> Dict[str, Any]:
    service = get_bluesight_service()
    packet = BlueSightSensorPacket(
        profile="device_scene",
        run_id=request.run_id,
        frame_id=request.frame_id,
        source=request.source,  # type: ignore[arg-type]
        width=request.width,
        height=request.height,
        payload={"device_id": request.device_id, "calibration_id": request.calibration_id},
        metadata=request.metadata,
    )
    observation = await service.observe(packet, provider_name="truth_bootstrap")
    return {"status": "ok", "observation": observation.dict()}


@router.get("/observations/latest")
async def latest_observation(profile: Optional[str] = None, run_id: Optional[str] = None) -> Dict[str, Any]:
    service = get_bluesight_service()
    observation = await service.latest(profile=profile, run_id=run_id)
    if observation is None:
        raise HTTPException(status_code=404, detail="No observation available")
    return {"status": "ok", "observation": observation.dict()}


@router.get("/observations/recent")
async def recent_observations(limit: int = 20) -> Dict[str, Any]:
    return {"status": "ok", "rows": load_recent_bluesight_events(limit=min(200, max(1, limit)))}


@router.websocket("/observations/stream")
async def stream_observations(websocket: WebSocket, profile: str = "petri"):
    await websocket.accept()
    service = get_bluesight_service()
    last_frame_id: Optional[str] = None
    try:
        while True:
            observation = await service.next_for_stream(profile, last_frame_id=last_frame_id)
            if observation is not None:
                await websocket.send_json({"type": "observation", "observation": observation.dict()})
                last_frame_id = observation.frame_id
            await asyncio.sleep(0.5)
    except Exception:
        await websocket.close()

