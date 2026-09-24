"""
NLM Ingest + Agent + Security API — September 23, 2026

Wires MAS device registry + MycoBrain/MDP into NLM ingest surfaces.
Real data only; empty states when no device/sensor samples.
Does not touch website nginx / Sandbox 187.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nlm", tags=["nlm-ingest"])


class RootedFrameRequest(BaseModel):
    device_id: str = Field(..., min_length=1)
    sensor_id: Optional[str] = None
    protocol: Optional[Dict[str, Any]] = None
    payload: Dict[str, Any] = Field(..., description="Real sample/NMF payload — never empty")
    source: str = "nlm_ingest"


class AgentTaskRequest(BaseModel):
    task_type: str
    payload: Optional[Dict[str, Any]] = None
    requested_by: Optional[str] = None


@router.get("/ingest/live")
async def ingest_live(
    include_offline: bool = False,
    fetch_telemetry: bool = True,
) -> Dict[str, Any]:
    """Live devices + sensors from registry/MycoBrain, or honest empty state."""
    from mycosoft_mas.nlm.device_ingest import build_live_ingest

    return await build_live_ingest(
        include_offline=include_offline,
        fetch_telemetry=fetch_telemetry,
    )


@router.get("/ingest/devices")
async def ingest_device_protocol_map() -> Dict[str, Any]:
    """Network/protocol mapping (device_id, sensor_id, MDP metadata)."""
    from mycosoft_mas.nlm.device_ingest import build_device_protocol_map

    return await build_device_protocol_map()


@router.post("/ingest/frame")
async def ingest_rooted_frame(body: RootedFrameRequest) -> Dict[str, Any]:
    """Persist RootedNatureFrame to NAS + Merkle/ECDSA attestation."""
    from mycosoft_mas.nlm.rooted_frames import write_rooted_frame_async
    from mycosoft_mas.nlm.training_store import persist_grounding

    if not body.payload:
        raise HTTPException(status_code=400, detail="payload required — no empty/mock frames")
    try:
        written = await write_rooted_frame_async(
            device_id=body.device_id,
            sensor_id=body.sensor_id,
            protocol=body.protocol,
            payload=body.payload,
            source=body.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    grounding = await persist_grounding(
        {
            "type": "rooted_nature_frame",
            "frame_id": written.get("frame_id"),
            "device_id": body.device_id,
            "sensor_id": body.sensor_id,
            "sha256": written.get("sha256"),
            "merkle_root": written.get("merkle_root"),
            "storage_ref": written.get("storage_ref"),
        }
    )
    return {
        "status": "stored",
        "frame": written,
        "grounding": grounding.get("grounding"),
        "model_kind": "nature_learning_model",
    }


@router.get("/ingest/timeline")
async def ingest_timeline(
    limit: int = 50,
    device_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Rooted frame timeline (NAS index). Empty when none."""
    from mycosoft_mas.nlm.rooted_frames import list_timeline

    return list_timeline(limit=limit, device_id=device_id)


@router.get("/ingest/timeline/{frame_id}")
async def ingest_timeline_frame(frame_id: str) -> Dict[str, Any]:
    from mycosoft_mas.nlm.rooted_frames import get_frame

    row = get_frame(frame_id)
    if not row:
        raise HTTPException(status_code=404, detail="frame not found")
    return row


@router.get("/agents/tasks")
async def agents_list_tasks(limit: int = 50) -> Dict[str, Any]:
    from mycosoft_mas.nlm.agent_runtime import list_tasks

    return list_tasks(limit=limit)


@router.post("/agents/tasks")
async def agents_submit_task(body: AgentTaskRequest) -> Dict[str, Any]:
    from mycosoft_mas.nlm.agent_runtime import submit_task

    try:
        return await submit_task(
            task_type=body.task_type,
            payload=body.payload,
            requested_by=body.requested_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/agents/tasks/{task_id}")
async def agents_get_task(task_id: str) -> Dict[str, Any]:
    from mycosoft_mas.nlm.agent_runtime import get_task

    row = get_task(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return {"status": "ok", "task": row, "model_kind": "nature_learning_model"}


@router.get("/security/status")
async def security_status() -> Dict[str, Any]:
    from mycosoft_mas.nlm.security_hooks import scan_nlm_security

    return scan_nlm_security()


@router.post("/security/scan")
async def security_scan(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
) -> Dict[str, Any]:
    from mycosoft_mas.nlm.security_hooks import scan_nlm_security
    from mycosoft_mas.nlm.training_store import changelog

    result = scan_nlm_security()
    changelog(
        entity_type="security_scan",
        entity_id=result.get("timestamp") or "scan",
        action="scan",
        detail={
            "status": result.get("status"),
            "finding_count": result.get("finding_count"),
            "requested_by": x_user_id,
        },
    )
    return result
