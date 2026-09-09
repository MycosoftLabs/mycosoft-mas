"""FUSARIUM API Router.

No mock/synthetic responses. All operational data is sourced from MINDEX and upstream services.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
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
from mycosoft_mas.integrations.maritime_sensor_client import MaritimeSensorNetworkClient

logger = logging.getLogger(__name__)
router = APIRouter()

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


@dataclass
class MindexFetch:
    ok: bool
    status: int
    data: Dict[str, Any]
    reason: str
    path: str


def _mindex_api_base() -> str:
    """``MINDEX_API_URL`` is origin-only on 188; Fusarium paths live under ``/api/mindex``."""
    raw = (os.environ.get("MINDEX_API_URL") or "http://192.168.0.189:8000").rstrip("/")
    if raw.endswith("/api/mindex"):
        return raw
    return f"{raw}/api/mindex"


def _mindex_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {"Accept": "application/json"}
    secret = (os.environ.get("MINDEX_INTERNAL_SECRET") or "").strip()
    token = ""
    if secret:
        from mycosoft_mas.integrations.mqtt_mycobrain_bridge import _mindex_hmac_token

        svc = (os.environ.get("MINDEX_INTERNAL_SERVICE_NAME") or "mas-orchestrator").strip()
        token = _mindex_hmac_token(svc, secret)
    if not token:
        token = (
            os.environ.get("MINDEX_INTERNAL_TOKEN")
            or os.environ.get("MINDEX_INTERNAL_TOKENS", "").split(",")[0]
            or ""
        ).strip()
    if token:
        headers["X-Internal-Token"] = token
    api_key = (os.environ.get("MINDEX_API_KEY") or "").strip()
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _empty_mindex_payload() -> Dict[str, Any]:
    return {
        "items": [],
        "data": [],
        "species": [],
        "assessments": [],
        "environments": [],
        "events": [],
        "observations": [],
        "total": 0,
    }


def _public_list(key: str, items: List[Dict[str, Any]], fetch: MindexFetch) -> Dict[str, Any]:
    qualification = "QUALIFIED" if fetch.ok and items else "UNQUALIFIED"
    reason = fetch.reason if not fetch.ok else ("ok" if items else "empty")
    return {
        key: items,
        "items": items,
        "qualification": qualification,
        "source": "mindex",
        "source_path": fetch.path,
        "source_status": fetch.status,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def _get(path: str, params: Optional[Dict[str, Any]] = None) -> MindexFetch:
    url = f"{_mindex_api_base()}{path}"
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.get(url, params=params, headers=_mindex_headers())
            if response.status_code >= 400:
                logger.warning("MINDEX GET %s failed status=%s", path, response.status_code)
                return MindexFetch(False, response.status_code, _empty_mindex_payload(), "upstream_error", path)
            raw = response.json()
            data = raw if isinstance(raw, dict) else {"items": raw if isinstance(raw, list) else []}
            return MindexFetch(True, response.status_code, data, "ok", path)
    except httpx.TimeoutException as exc:
        logger.warning("MINDEX GET %s timeout: %s", path, exc)
        return MindexFetch(False, 504, _empty_mindex_payload(), "upstream_timeout", path)
    except Exception as exc:
        logger.warning("MINDEX GET %s unavailable: %s", path, exc)
        return MindexFetch(False, 502, _empty_mindex_payload(), "upstream_unavailable", path)


async def _post_json(path: str, payload: Dict[str, Any]) -> MindexFetch:
    url = f"{_mindex_api_base()}{path}"
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(url, json=payload, headers=_mindex_headers())
            if response.status_code >= 400:
                logger.warning("MINDEX POST %s failed status=%s", path, response.status_code)
                return MindexFetch(False, response.status_code, {}, "upstream_error", path)
            raw = response.json()
            data = raw if isinstance(raw, dict) else {"items": raw if isinstance(raw, list) else []}
            return MindexFetch(True, response.status_code, data, "ok", path)
    except httpx.TimeoutException as exc:
        logger.warning("MINDEX POST %s timeout: %s", path, exc)
        return MindexFetch(False, 504, {}, "upstream_timeout", path)
    except Exception as exc:
        logger.warning("MINDEX POST %s unavailable: %s", path, exc)
        return MindexFetch(False, 502, {}, "upstream_unavailable", path)


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "fusarium",
        "timestamp": datetime.utcnow().isoformat(),
        "upstream": _mindex_api_base(),
    }


@router.get("/species")
async def get_fungal_species(
    min_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    max_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    min_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    max_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    species_name: Optional[str] = None,
    pathogenic_only: bool = False,
    limit: int = Query(default=100, ge=1, le=1000),
):
    params: Dict[str, Any] = {
        "limit": limit,
        "q": species_name or "Fusarium",
        "kingdom": "Fungi",
    }
    if pathogenic_only:
        params["lineage_contains"] = "Fusarium"
    if min_lat is not None:
        params["min_lat"] = min_lat
    if max_lat is not None:
        params["max_lat"] = max_lat
    if min_lon is not None:
        params["min_lon"] = min_lon
    if max_lon is not None:
        params["max_lon"] = max_lon

    fetch = await _get("/taxa", params)
    rows: List[Dict[str, Any]] = []
    if isinstance(fetch.data.get("data"), list):
        rows = [item for item in fetch.data["data"] if isinstance(item, dict)]
    elif isinstance(fetch.data.get("items"), list):
        rows = [item for item in fetch.data["items"] if isinstance(item, dict)]
    elif isinstance(fetch.data.get("species"), list):
        rows = [item for item in fetch.data["species"] if isinstance(item, dict)]
    return _public_list("species", rows, fetch)


@router.post("/dispersal")
async def calculate_spore_dispersal(request: DispersalRequest):
    payload = {
        "origin_lat": request.origin_lat,
        "origin_lon": request.origin_lon,
        "species": request.species,
        "forecast_hours": request.forecast_hours,
        "wind_factor": request.wind_factor,
    }
    fetch = await _post_json("/nlm/assess/tactical", payload)
    if not fetch.ok:
        return {
            "qualification": "UNQUALIFIED",
            "source": "mindex",
            "source_path": fetch.path,
            "source_status": fetch.status,
            "reason": fetch.reason,
            "items": [],
            "timestamp": datetime.utcnow().isoformat(),
        }
    return fetch.data


@router.get("/dispersal")
async def get_current_dispersal(
    min_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    max_lat: Optional[float] = Query(default=None, ge=-90, le=90),
    min_lon: Optional[float] = Query(default=None, ge=-180, le=180),
    max_lon: Optional[float] = Query(default=None, ge=-180, le=180),
):
    ocean = await _get("/maritime/ocean-environments", {"limit": 200})
    assessments = await _get("/taco/assessments", {"limit": 200, "offset": 0})
    environments = ocean.data.get("environments", []) if isinstance(ocean.data.get("environments"), list) else []
    assessment_rows = assessments.data.get("assessments", []) if isinstance(assessments.data.get("assessments"), list) else []
    ok = ocean.ok and assessments.ok
    has_rows = bool(environments or assessment_rows)
    failed = assessments if not assessments.ok else ocean
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "bounds": {"min_lat": min_lat, "max_lat": max_lat, "min_lon": min_lon, "max_lon": max_lon},
        "ocean_environments": environments,
        "assessments": assessment_rows,
        "items": assessment_rows,
        "qualification": "QUALIFIED" if ok and has_rows else "UNQUALIFIED",
        "source": "mindex",
        "source_path": failed.path,
        "source_status": failed.status if not ok else 200,
        "reason": failed.reason if not ok else ("ok" if has_rows else "empty"),
    }


@router.get("/risk-zones")
async def get_risk_zones(
    crop: Optional[str] = None,
    threat_level: Optional[str] = None,
):
    fetch = await _get("/taco/assessments", {"limit": 200, "offset": 0})
    result: List[Dict[str, Any]] = []
    for item in fetch.data.get("assessments", []):
        if not isinstance(item, dict):
            continue
        urgency = float(item.get("urgency", 0.0) or 0.0)
        if threat_level == "low" and urgency > 0.33:
            continue
        if threat_level == "medium" and not (0.33 < urgency <= 0.66):
            continue
        if threat_level == "high" and urgency <= 0.66:
            continue
        if crop and crop.lower() not in str(item).lower():
            continue
        result.append(item)
    return _public_list("risk_zones", result, fetch)


@router.get("/threats")
async def get_active_threats(
    severity: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    fetch = await _get("/taco/assessments", {"limit": max(limit, 200), "offset": 0})
    threats: List[Dict[str, Any]] = []
    for item in fetch.data.get("assessments", []):
        if not isinstance(item, dict):
            continue
        urgency = float(item.get("urgency", 0.0) or 0.0)
        threat_severity = "critical" if urgency >= 0.85 else "high" if urgency >= 0.66 else "medium" if urgency >= 0.33 else "low"
        domain_category = item.get("assessment_type", "marine")
        if severity and severity != threat_severity:
            continue
        if category and category != domain_category:
            continue
        classification = item.get("classification") if isinstance(item.get("classification"), dict) else {}
        recommendation = item.get("recommendation") if isinstance(item.get("recommendation"), dict) else {}
        threats.append(
            {
                "id": str(item.get("assessment_id") or item.get("id") or datetime.utcnow().timestamp()),
                "title": classification.get("label", "Tactical Assessment"),
                "description": recommendation.get("summary", "Assessment available"),
                "severity": threat_severity,
                "category": domain_category,
                "source": "mindex/taco",
                "timestamp": item.get("created_at") or item.get("observed_at") or datetime.utcnow().isoformat(),
                "metadata": item,
            }
        )
        if len(threats) >= limit:
            break
    return _public_list("threats", threats, fetch)


@router.post("/threats/report")
async def report_threat(threat: Dict[str, Any]):
    """Persist FUSARIUM / tactical threat reports as SOC incidents when Postgres is configured."""
    out: Dict[str, Any] = {
        "status": "received",
        "threat": threat,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL"):
        try:
            from mycosoft_mas.soc import repository as soc_repo

            title = str(threat.get("title") or threat.get("label") or "FUSARIUM threat report")[:500]
            desc = str(threat.get("description") or threat.get("summary") or "")[:8000]
            sev = str(threat.get("severity") or "medium").lower()
            if sev not in ("info", "low", "medium", "high", "critical"):
                sev = "medium"
            row = await soc_repo.create_incident(
                title=title,
                description=desc,
                severity=sev,
                status="open",
                source="fusarium",
                kind=str(threat.get("category") or "anomaly"),
                source_ip=threat.get("source_ip"),
                host=threat.get("host"),
                details={"fusarium": threat},
                tags=["fusarium"],
                timeline=[{"event": "report_received", "at": datetime.utcnow().isoformat()}],
            )
            out["incident_id"] = row.get("id")
            out["status"] = "persisted"
        except Exception as exc:
            logger.exception("FUSARIUM threat incident persist failed: %s", exc)
            out["persist_error"] = str(exc)
    return out


@router.get("/maritime/threat-panel")
async def maritime_threat_panel():
    return await get_active_threats(category="hydrosphere", limit=100)


@router.get("/maritime/sensor-network")
async def maritime_sensor_network():
    fetch = await _get("/taco/sensor-status")
    return fetch.data


@router.get("/maritime/contacts")
async def maritime_contacts(limit: int = Query(default=100, ge=1, le=500)):
    observations = await _get("/taco/observations", {"limit": limit, "offset": 0})
    contacts = []
    for item in observations.data.get("observations", []):
        if not isinstance(item, dict):
            continue
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
    rows = environments.data.get("environments", []) if isinstance(environments.data.get("environments"), list) else []
    return {"environment": rows, "total": len(rows)}


@router.post("/maritime/assess")
async def maritime_assessment(payload: Dict[str, Any]):
    fetch = await _post_json("/nlm/assess/tactical", payload)
    if not fetch.ok:
        return {
            "qualification": "UNQUALIFIED",
            "source": "mindex",
            "source_path": fetch.path,
            "source_status": fetch.status,
            "reason": fetch.reason,
            "items": [],
            "timestamp": datetime.utcnow().isoformat(),
        }
    return fetch.data


@router.get("/maritime/threat-history")
async def maritime_threat_history(limit: int = Query(default=100, ge=1, le=500)):
    fetch = await _get("/taco/assessments", {"limit": limit, "offset": 0})
    return fetch.data


@router.get("/maritime/fusion-status")
async def maritime_fusion_status():
    sensors = await sensor_network_client.get_sensor_status()
    assessments = await _get("/taco/assessments", {"limit": 200, "offset": 0})
    observations = await _get("/taco/observations", {"limit": 200, "offset": 0})
    return {
        "sources": {
            "maritime_sensor_network": {"online_sensors": len(sensors), "status": "online" if sensors else "degraded"},
            "mindex_observations": {"count": observations.data.get("total", 0)},
            "taco_assessments": {"count": assessments.data.get("total", 0)},
        },
        "processing_lag": "live",
        "data_quality_metrics": {
            "observation_count": observations.data.get("total", 0),
            "assessment_count": assessments.data.get("total", 0),
        },
    }


@router.get("/maritime/correlation-graph")
async def maritime_correlation_graph(limit: int = Query(default=100, ge=1, le=500)):
    events = await _get("/fusarium/correlation-events", {"limit": limit})
    nodes = {}
    edges = []
    for event in events.data.get("events", []):
        if not isinstance(event, dict):
            continue
        entity_id = str(event.get("entity_id"))
        nodes[entity_id] = {"id": entity_id, "type": "entity"}
        for domain in event.get("domains", []):
            domain_id = f"domain:{domain}"
            nodes[domain_id] = {"id": domain_id, "type": "domain", "label": domain}
            edges.append({"source": entity_id, "target": domain_id, "confidence": event.get("confidence", 0.0)})
    return {"nodes": list(nodes.values()), "edges": edges, "total_events": events.data.get("total", 0)}


@router.get("/maritime/provenance/{observation_id}")
async def maritime_provenance(observation_id: str):
    observation = await _get(f"/taco/observations/{observation_id}")
    related = await _get("/taco/assessments", {"limit": 100, "offset": 0})
    matching = [
        item
        for item in related.data.get("assessments", [])
        if isinstance(item, dict) and observation_id in [str(value) for value in item.get("observation_ids", [])]
    ]
    return {
        "observation": observation.data.get("observation"),
        "related_assessments": matching,
        "merkle_hash": (observation.data.get("observation") or {}).get("merkle_hash"),
    }


@router.get("/maritime/decision-aid")
async def maritime_decision_aid(limit: int = Query(default=25, ge=1, le=100)):
    assessments = await _get("/taco/assessments", {"limit": limit, "offset": 0})
    recommendations = []
    for item in assessments.data.get("assessments", []):
        if not isinstance(item, dict):
            continue
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
