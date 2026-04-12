"""
FUSARIUM Platform API Router
April 2026
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from mycosoft_mas.fusarium.auth.defense_auth import (
    DefenseIdentity,
    enforce_classification,
    require_defense_identity,
)
from mycosoft_mas.fusarium.fusion.fusion_engine import FusionEngine
from mycosoft_mas.fusarium.nlm_bridge import NLMBridge

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/platform", tags=["fusarium-platform"])

MINDEX_BASE_URL = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000/api/mindex").rstrip("/")
MINDEX_INTERNAL_TOKEN = os.environ.get("MINDEX_INTERNAL_TOKEN", "").strip()
MINDEX_API_KEY = os.environ.get("MINDEX_API_KEY", "").strip()

# Runtime mission contexts (created from real operator requests)
MISSION_STORE: Dict[str, Dict[str, Any]] = {}


class MissionCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    aor: Dict[str, float] = Field(..., description="lat, lon, radius_nm")
    classification: str = Field(..., pattern="^(UNCLASSIFIED|CUI|SECRET|TS_SCI)$")
    objectives: List[str] = Field(default_factory=list)


class IntelligenceProductModel(BaseModel):
    product_id: UUID = Field(default_factory=uuid4)
    title: str
    body: str
    classification: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    sources: List[str]
    merkle_root: str
    stix_bundle: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AlertCreate(BaseModel):
    title: str
    description: str
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    domain: str
    location: Optional[Dict[str, float]] = None


class TimelineEvent(BaseModel):
    event_id: UUID
    timestamp: datetime
    domain: str
    type: str
    description: str
    confidence: float
    correlated_observations: List[str] = Field(default_factory=list)


async def _fetch_json(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{MINDEX_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        headers = (
            {"X-Internal-Token": MINDEX_INTERNAL_TOKEN}
            if MINDEX_INTERNAL_TOKEN
            else {"X-API-Key": MINDEX_API_KEY} if MINDEX_API_KEY else None
        )
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {"items": data}


@router.post("/mission")
async def create_mission(
    mission: MissionCreate,
    identity: DefenseIdentity = Depends(require_defense_identity),
):
    enforce_classification(identity, mission.classification)
    mission_id = str(uuid4())
    payload = {
        "mission_id": mission_id,
        "name": mission.name,
        "aor": mission.aor,
        "classification": mission.classification,
        "objectives": mission.objectives,
        "created_by": identity.subject,
        "created_at": datetime.utcnow().isoformat(),
    }
    MISSION_STORE[mission_id] = payload
    return {"status": "created", "mission": payload}


@router.get("/cop")
async def get_common_operating_picture(
    mission_id: Optional[str] = Query(default=None),
    domain: Optional[str] = Query(default=None),
    identity: DefenseIdentity = Depends(require_defense_identity),
):
    if mission_id:
        mission = MISSION_STORE.get(mission_id)
        if not mission:
            raise HTTPException(status_code=404, detail="mission_not_found")
        enforce_classification(identity, mission.get("classification", "CUI"))

    fusion_engine = FusionEngine()
    maritime_obs = await _fetch_json("/taco/observations", params={"limit": 200, "offset": 0})
    maritime_assessments = await _fetch_json("/taco/assessments", params={"limit": 200, "offset": 0})
    ocean = await _fetch_json("/maritime/ocean-environments", params={"limit": 200})

    observations = maritime_obs.get("observations", [])
    assessments = maritime_assessments.get("assessments", [])
    environments = ocean.get("environments", [])

    domain_assessments = [
        {
            "domain": item.get("domain", "hydrosphere"),
            "confidence": item.get("confidence", 0.0),
            "entities": item.get("observation_ids", []),
        }
        for item in assessments
    ]

    entities = fusion_engine.resolve_entities(domain_assessments)
    threat_score = fusion_engine.score_threat(domain_assessments)
    correlations = fusion_engine.correlate(domain_assessments)

    return {
        "mission_id": mission_id,
        "domain_filter": domain,
        "classification": identity.clearance,
        "observation_count": len(observations),
        "assessment_count": len(assessments),
        "environment_count": len(environments),
        "entities": entities,
        "threat_score": threat_score,
        "correlations": correlations,
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.post("/intel-product")
async def generate_intel_product(
    request: Dict[str, Any],
    identity: DefenseIdentity = Depends(require_defense_identity),
):
    requested_classification = (request.get("classification") or "CUI").upper()
    enforce_classification(identity, requested_classification)

    title = request.get("title", "FUSARIUM Intelligence Product")
    body = request.get("body", "")
    confidence = float(request.get("confidence", 0.5))
    sources = [str(x) for x in request.get("sources", [])]

    model = IntelligenceProductModel(
        title=title,
        body=body,
        classification=requested_classification,
        confidence=max(0.0, min(confidence, 1.0)),
        sources=sources,
        merkle_root=request.get("merkle_root", ""),
        stix_bundle=request.get("stix_bundle"),
    )
    return model.model_dump()


@router.get("/dashboard-state")
async def get_dashboard_state(
    mission_id: str,
    identity: DefenseIdentity = Depends(require_defense_identity),
):
    mission = MISSION_STORE.get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="mission_not_found")
    enforce_classification(identity, mission.get("classification", "CUI"))

    cop = await get_common_operating_picture(mission_id=mission_id, identity=identity)
    return {
        "mission": mission,
        "cop": cop,
        "active_alerts": [],
        "compliance_status": {
            "nist_800_171": "tracked",
            "cac_piv_required": True,
            "classification_enforced": True,
        },
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.post("/alert")
async def create_alert(
    alert: AlertCreate,
    identity: DefenseIdentity = Depends(require_defense_identity),
):
    enforce_classification(identity, "CUI")
    return {
        "status": "created",
        "alert_id": str(uuid4()),
        "title": alert.title,
        "description": alert.description,
        "severity": alert.severity,
        "domain": alert.domain,
        "created_by": identity.subject,
        "created_at": datetime.utcnow().isoformat(),
    }


@router.get("/timeline")
async def get_timeline(
    mission_id: str,
    start: datetime = Query(...),
    end: datetime = Query(...),
    identity: DefenseIdentity = Depends(require_defense_identity),
):
    mission = MISSION_STORE.get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="mission_not_found")
    enforce_classification(identity, mission.get("classification", "CUI"))

    records = await _fetch_json("/taco/assessments", params={"limit": 200, "offset": 0})
    events: List[TimelineEvent] = []
    for item in records.get("assessments", []):
        ts_raw = item.get("created_at") or item.get("observed_at")
        try:
            timestamp = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00")) if ts_raw else datetime.utcnow()
        except Exception:
            timestamp = datetime.utcnow()
        if timestamp < start or timestamp > end:
            continue
        events.append(
            TimelineEvent(
                event_id=uuid4(),
                timestamp=timestamp,
                domain=item.get("assessment_type", "hydrosphere"),
                type="assessment",
                description=item.get("recommendation", {}).get("summary", "Assessment generated"),
                confidence=float(item.get("urgency", 0.0)),
                correlated_observations=[str(x) for x in item.get("observation_ids", [])],
            )
        )

    return {
        "events": [event.model_dump() for event in events],
        "total": len(events),
        "time_range": {"start": start.isoformat(), "end": end.isoformat()},
    }


@router.websocket("/stream")
async def platform_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            packet = await websocket.receive_json()
            await websocket.send_json(
                {
                    "type": "fusarium_update",
                    "received_at": datetime.utcnow().isoformat(),
                    "packet": packet,
                }
            )
    except WebSocketDisconnect:
        logger.info("FUSARIUM platform stream disconnected")
    except Exception as exc:
        logger.error("FUSARIUM platform stream error: %s", exc)
        await websocket.close()
