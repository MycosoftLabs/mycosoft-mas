"""FUSARIUM API Router.

No mock/synthetic responses. All operational data is sourced from MINDEX and upstream services.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from mycosoft_mas.agents.clusters.taco import (
    AnomalyInvestigatorAgent,
    DataCuratorAgent,
    OceanPredictorAgent,
    PolicyComplianceAgent,
    SignalClassifierAgent,
)
from mycosoft_mas.integrations.zeetachec_client import MaritimeSensorNetworkClient

logger = logging.getLogger(__name__)
router = APIRouter()

MINDEX_API_URL = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000/api/mindex").rstrip("/")
MINDEX_INTERNAL_TOKEN = os.environ.get("MINDEX_INTERNAL_TOKEN", "").strip()
MINDEX_API_KEY = os.environ.get("MINDEX_API_KEY", "").strip()
sensor_network_client = MaritimeSensorNetworkClient()
TACO_AGENTS = {
    "signal_classifier": SignalClassifierAgent(config={}),
    "anomaly_investigator": AnomalyInvestigatorAgent(config={}),
    "ocean_predictor": OceanPredictorAgent(config={}),
    "policy_compliance": PolicyComplianceAgent(config={}),
    "data_curator": DataCuratorAgent(config={}),
}


class SpeciesQueryParams(BaseModel):
    min_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    max_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    min_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    max_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    species_name: Optional[str] = None
    pathogenic_only: bool = False
    limit: int = Field(default=100, ge=1, le=1000)


class DispersalRequest(BaseModel):
    origin_lat: float = Field(ge=-90, le=90)
    origin_lon: float = Field(ge=-180, le=180)
    species: Optional[str] = None
    forecast_hours: int = Field(default=72, ge=1, le=168)
    wind_factor: float = Field(default=1.0, ge=0.1, le=5.0)


async def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=25.0) as client:
        headers = (
            {"X-Internal-Token": MINDEX_INTERNAL_TOKEN}
            if MINDEX_INTERNAL_TOKEN
            else {"X-API-Key": MINDEX_API_KEY} if MINDEX_API_KEY else None
        )
        response = await client.get(f"{MINDEX_API_URL}{path}", params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {"items": data}


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "fusarium",
        "timestamp": datetime.utcnow().isoformat(),
        "upstream": MINDEX_API_URL,
    }


@router.get("/species", response_model=List[Dict[str, Any]])
async def get_fungal_species(
    min_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    max_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    min_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    max_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    species_name: Optional[str] = None,
    pathogenic_only: bool = False,
    limit: int = Query(default=100, ge=1, le=1000),
):
    try:
        params: Dict[str, Any] = {"limit": limit}
        if species_name:
            params["name"] = species_name
        if pathogenic_only:
            params["pathogenic"] = "true"
        if min_lat is not None:
            params["min_lat"] = min_lat
        if max_lat is not None:
            params["max_lat"] = max_lat
        if min_lon is not None:
            params["min_lon"] = min_lon
        if max_lon is not None:
            params["max_lon"] = max_lon

        data = await _get("/species/fungi", params)
        if "species" in data and isinstance(data["species"], list):
            return data["species"]
        if "items" in data and isinstance(data["items"], list):
            return data["items"]
        return []
    except httpx.HTTPError as exc:
        logger.error("Species query failed: %s", exc)
        raise HTTPException(status_code=502, detail="mindex_species_query_failed") from exc


@router.post("/dispersal")
async def calculate_spore_dispersal(request: DispersalRequest):
    payload = {
        "origin_lat": request.origin_lat,
        "origin_lon": request.origin_lon,
        "species": request.species,
        "forecast_hours": request.forecast_hours,
        "wind_factor": request.wind_factor,
    }
    # Uses tactical assessment endpoint as current upstream model surface.
    async with httpx.AsyncClient(timeout=25.0) as client:
        headers = (
            {"X-Internal-Token": MINDEX_INTERNAL_TOKEN}
            if MINDEX_INTERNAL_TOKEN
            else {"X-API-Key": MINDEX_API_KEY} if MINDEX_API_KEY else None
        )
        response = await client.post(f"{MINDEX_API_URL}/nlm/assess/tactical", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


@router.get("/dispersal")
async def get_current_dispersal(
    min_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    max_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    min_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    max_lon: Optional[float] = Query(default=None, ge=-180, le=180),
):
    # Returns ocean environment + assessments; client can render active zones from real observations.
    ocean = await _get("/maritime/ocean-environments", {"limit": 200})
    assessments = await _get("/taco/assessments", {"limit": 200, "offset": 0})
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "bounds": {"min_lat": min_lat, "max_lat": max_lat, "min_lon": min_lon, "max_lon": max_lon},
        "ocean_environments": ocean.get("environments", []),
        "assessments": assessments.get("assessments", []),
    }


@router.get("/risk-zones")
async def get_risk_zones(
    crop: Optional[str] = None,
    threat_level: Optional[str] = None,
):
    assessments = await _get("/taco/assessments", {"limit": 200, "offset": 0})
    result = []
    for item in assessments.get("assessments", []):
        urgency = float(item.get("urgency", 0.0))
        if threat_level == "low" and urgency > 0.33:
            continue
        if threat_level == "medium" and not (0.33 < urgency <= 0.66):
            continue
        if threat_level == "high" and urgency <= 0.66:
            continue
        if crop and crop.lower() not in str(item).lower():
            continue
        result.append(item)
    return result


@router.get("/threats")
async def get_active_threats(
    severity: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    assessments = await _get("/taco/assessments", {"limit": max(limit, 200), "offset": 0})
    threats: List[Dict[str, Any]] = []
    for item in assessments.get("assessments", []):
        urgency = float(item.get("urgency", 0.0))
        threat_severity = "critical" if urgency >= 0.85 else "high" if urgency >= 0.66 else "medium" if urgency >= 0.33 else "low"
        domain_category = item.get("assessment_type", "marine")
        if severity and severity != threat_severity:
            continue
        if category and category != domain_category:
            continue
        threats.append(
            {
                "id": str(item.get("assessment_id") or item.get("id") or datetime.utcnow().timestamp()),
                "title": item.get("classification", {}).get("label", "Tactical Assessment"),
                "description": item.get("recommendation", {}).get("summary", "Assessment available"),
                "severity": threat_severity,
                "category": domain_category,
                "source": "mindex/taco",
                "timestamp": item.get("created_at") or item.get("observed_at") or datetime.utcnow().isoformat(),
                "metadata": item,
            }
        )
        if len(threats) >= limit:
            break
    return threats


@router.post("/threats/report")
async def report_threat(threat: Dict[str, Any]):
    # Persist externally once incident write endpoint is available.
    return {
        "status": "received",
        "threat": threat,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/maritime/threat-panel")
async def maritime_threat_panel():
    return await get_active_threats(category="hydrosphere", limit=100)


@router.get("/maritime/sensor-network")
async def maritime_sensor_network():
    return await _get("/taco/sensor-status")


@router.get("/maritime/contacts")
async def maritime_contacts(limit: int = Query(default=100, ge=1, le=500)):
    observations = await _get("/taco/observations", {"limit": limit, "offset": 0})
    contacts = []
    for item in observations.get("observations", []):
        classification = item.get("nlm_classification") or {}
        contacts.append(
            {
                "observation_id": item.get("observation_id"),
                "sensor_id": item.get("sensor_id"),
                "sensor_type": item.get("sensor_type"),
                "classification": classification.get("classification") or classification.get("label"),
                "confidence": item.get("confidence"),
                "anomaly_score": item.get("anomaly_score"),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "depth_m": item.get("depth_m"),
                "timestamp": item.get("observed_at"),
                "avani_review": item.get("avani_review"),
            }
        )
    return {"contacts": contacts, "total": len(contacts)}


@router.get("/maritime/environment")
async def maritime_environment(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_nm: float = Query(default=25.0, ge=1.0, le=500.0),
):
    params: Dict[str, Any] = {"limit": 50}
    if lat is not None and lon is not None:
        params.update({"lat": lat, "lon": lon, "radius_nm": radius_nm})
    environments = await _get("/maritime/ocean-environments", params)
    return {"environment": environments.get("environments", []), "total": len(environments.get("environments", []))}


@router.post("/maritime/assess")
async def maritime_assessment(payload: Dict[str, Any]):
    async with httpx.AsyncClient(timeout=25.0) as client:
        headers = (
            {"X-Internal-Token": MINDEX_INTERNAL_TOKEN}
            if MINDEX_INTERNAL_TOKEN
            else {"X-API-Key": MINDEX_API_KEY} if MINDEX_API_KEY else None
        )
        response = await client.post(f"{MINDEX_API_URL}/nlm/assess/tactical", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


@router.get("/maritime/threat-history")
async def maritime_threat_history(limit: int = Query(default=100, ge=1, le=500)):
    return await _get("/taco/assessments", {"limit": limit, "offset": 0})


@router.get("/maritime/fusion-status")
async def maritime_fusion_status():
    sensors = await sensor_network_client.get_sensor_status()
    assessments = await _get("/taco/assessments", {"limit": 200, "offset": 0})
    observations = await _get("/taco/observations", {"limit": 200, "offset": 0})
    return {
        "sources": {
            "maritime_sensor_network": {"online_sensors": len(sensors), "status": "online" if sensors else "degraded"},
            "mindex_observations": {"count": observations.get("total", 0)},
            "taco_assessments": {"count": assessments.get("total", 0)},
        },
        "processing_lag": "live",
        "data_quality_metrics": {
            "observation_count": observations.get("total", 0),
            "assessment_count": assessments.get("total", 0),
        },
    }


@router.get("/maritime/correlation-graph")
async def maritime_correlation_graph(limit: int = Query(default=100, ge=1, le=500)):
    events = await _get("/fusarium/correlation-events", {"limit": limit})
    nodes = {}
    edges = []
    for event in events.get("events", []):
        entity_id = str(event.get("entity_id"))
        nodes[entity_id] = {"id": entity_id, "type": "entity"}
        for domain in event.get("domains", []):
            domain_id = f"domain:{domain}"
            nodes[domain_id] = {"id": domain_id, "type": "domain", "label": domain}
            edges.append({"source": entity_id, "target": domain_id, "confidence": event.get("confidence", 0.0)})
    return {"nodes": list(nodes.values()), "edges": edges, "total_events": events.get("total", 0)}


@router.get("/maritime/provenance/{observation_id}")
async def maritime_provenance(observation_id: str):
    observation = await _get(f"/taco/observations/{observation_id}")
    related = await _get("/taco/assessments", {"limit": 100, "offset": 0})
    matching = [
        item
        for item in related.get("assessments", [])
        if observation_id in [str(value) for value in item.get("observation_ids", [])]
    ]
    return {
        "observation": observation.get("observation"),
        "related_assessments": matching,
        "merkle_hash": (observation.get("observation") or {}).get("merkle_hash"),
    }


@router.get("/maritime/decision-aid")
async def maritime_decision_aid(limit: int = Query(default=25, ge=1, le=100)):
    assessments = await _get("/taco/assessments", {"limit": limit, "offset": 0})
    recommendations = []
    for item in assessments.get("assessments", []):
        recommendation = item.get("recommendation")
        if recommendation:
            recommendations.append(recommendation)
    return {
        "recommendations": recommendations,
        "total": len(recommendations),
        "source": "mindex/taco_assessments",
    }


@router.get("/maritime/agents/status")
async def maritime_agents_status():
    agents = []
    for key, agent in TACO_AGENTS.items():
        status = agent.get_status()
        status["agent_key"] = key
        agents.append(status)
    return {"agents": agents, "total": len(agents)}


@router.post("/maritime/command/sensor/{action}")
async def maritime_sensor_command(action: str, payload: Dict[str, Any]):
    sensor_id = payload.get("sensor_id")
    if not sensor_id:
        raise HTTPException(status_code=400, detail="sensor_id_required")
    result = await sensor_network_client.send_command(sensor_id=sensor_id, command=action, params=payload)
    return {"action": action, **result}


@router.post("/maritime/voice-command")
async def maritime_voice_command(command: Dict[str, Any]):
    from mycosoft_mas.core.routers.voice_command_api import taco_voice_command

    return await taco_voice_command(command)


@router.websocket("/maritime/stream")
async def maritime_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.send_json({"type": "connected", "timestamp": datetime.utcnow().isoformat()})
        while True:
            packet = await websocket.receive_json()
            if packet.get("type") == "ping":
                snapshot = {
                    "type": "sensor_status",
                    "timestamp": datetime.utcnow().isoformat(),
                        "data": await sensor_network_client.get_sensor_status(),
                }
                await websocket.send_json(snapshot)
            else:
                await websocket.send_json(
                    {
                        "type": "agent_action",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": packet,
                    }
                )
    except WebSocketDisconnect:
        logger.info("FUSARIUM maritime stream disconnected")
