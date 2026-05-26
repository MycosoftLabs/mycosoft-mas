"""NatureOS Petri profile routes for BlueSight integration."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import BaseModel, Field

from mycosoft_mas.bluesight.service import get_bluesight_service
from mycosoft_mas.schemas.bluesight import BlueSightSensorPacket, PetriTruthState

router = APIRouter(prefix="/api/natureos/petri", tags=["natureos", "petri", "bluesight"])

_truth_state_by_run: Dict[str, PetriTruthState] = {}


class UpsertTruthStateRequest(BaseModel):
    tick: int = 0
    colonies: List[Dict[str, Any]] = Field(default_factory=list)
    spores: List[Dict[str, Any]] = Field(default_factory=list)
    tips: List[Dict[str, Any]] = Field(default_factory=list)
    segments: List[Dict[str, Any]] = Field(default_factory=list)
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    chemical_fields_summary: Dict[str, float] = Field(default_factory=dict)
    events_since_last_frame: List[Dict[str, Any]] = Field(default_factory=list)


class ObserveFrameRequest(BaseModel):
    frame_id: str
    width: int
    height: int
    source: str = "screen_capture"
    frame_ref: Optional[str] = None
    provider: str = "truth_bootstrap"
    dish: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post("/runs/{run_id}/state")
async def upsert_truth_state(run_id: str, payload: UpsertTruthStateRequest) -> Dict[str, Any]:
    state = PetriTruthState(run_id=run_id, **payload.dict())
    _truth_state_by_run[run_id] = state
    return {"status": "ok", "run_id": run_id, "tick": state.tick}


@router.get("/runs/{run_id}/state/latest")
async def latest_truth_state(run_id: str) -> Dict[str, Any]:
    state = _truth_state_by_run.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run state not found")
    return {"status": "ok", "state": state.dict()}


@router.post("/runs/{run_id}/frame")
async def observe_frame(run_id: str, payload: ObserveFrameRequest) -> Dict[str, Any]:
    state = _truth_state_by_run.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run state not found")
    service = get_bluesight_service()
    packet = BlueSightSensorPacket(
        profile="petri",
        run_id=run_id,
        frame_id=payload.frame_id,
        source=payload.source,  # type: ignore[arg-type]
        width=payload.width,
        height=payload.height,
        frame_ref=payload.frame_ref,
        truth_state=state.dict(),
        payload={
            "dish": payload.dish,
            "summary": {
                "colony_count": len(state.colonies),
                "spore_count": len(state.spores),
                "active_tip_count": len(state.tips),
                "branch_node_count": len(state.nodes),
            },
        },
        metadata=payload.metadata,
    )
    observation = await service.observe(packet, provider_name=payload.provider)
    return {"status": "ok", "observation": observation.dict()}


@router.get("/runs/{run_id}/frame/latest")
async def latest_frame(run_id: str) -> Dict[str, Any]:
    service = get_bluesight_service()
    observation = await service.latest(run_id=run_id)
    if observation is None:
        raise HTTPException(status_code=404, detail="No frame observed for run")
    return {
        "status": "ok",
        "frame": {
            "run_id": run_id,
            "frame_id": observation.frame_id,
            "timestamp": observation.timestamp,
            "source": observation.source,
            "width": observation.metadata.get("width"),
            "height": observation.metadata.get("height"),
            "frame_ref": observation.metadata.get("frame_ref"),
        },
    }


@router.websocket("/runs/{run_id}/bluesight/stream")
async def run_bluesight_stream(websocket: WebSocket, run_id: str):
    await websocket.accept()
    service = get_bluesight_service()
    last_frame_id: Optional[str] = None
    try:
        while True:
            observation = await service.next_for_stream(run_id, last_frame_id=last_frame_id)
            if observation is not None:
                await websocket.send_json({"type": "petri_observation", "observation": observation.dict()})
                last_frame_id = observation.frame_id
            await asyncio.sleep(0.5)
    except Exception:
        await websocket.close()


@router.get("/profiles/earth-globe/health")
async def earth_globe_profile_health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "profile": "earth_globe",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Earth/GLOBE BlueSight profile adapter is available.",
    }

