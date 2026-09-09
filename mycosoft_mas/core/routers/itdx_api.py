"""ITDX Task 8 + Earth Sim situation assessment — live MAS bindings.

POST /api/itdx/task8                  seven-role COA review
GET  /api/itdx/task8                  same, default Fort Stewart demo slice
POST /api/itdx/situation-assessment   per-channel scores for the globe
GET  /api/itdx/health

schema_version:
  itdx-task8/v1
  itdx.situation_assessment/v1

Assessment is in-process (no HTTP to 127.0.0.1:8001 / self). Missing
channel → NOT_SUPPLIED. NLM stub / model_loaded=false → UNQUALIFIED
with p=null. Stub confidence 0.85 is never a Fusarium p.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from mycosoft_mas.agents.itdx_task8_agent import (
    ITDXTask8Agent,
    SCHEMA_VERSION,
    SITUATION_SCHEMA_VERSION,
    mapped_role_probes,
)
from mycosoft_mas.core.routers.itdx_public_sources import gather_public_osint
from mycosoft_mas.nlm.inference.service import (
    NLM_STUB_CONFIDENCE,
    is_usable_nlm_confidence,
    nlm_text_is_stub,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/itdx", tags=["itdx"])

CHANNEL_KEYS = (
    "physics",
    "biology",
    "chemistry",
    "economics",
    "weather",
    "topology",
    "biometry",
    "equipment_weapons_assets",
    "officer_capability",
    "persona",
    "information",
    "decision_authority",
    "traffic",
    "pathways",
    "navigation",
)

# Wall clock for situation-assessment. Must return before Fusarium 8s abort.
ASSESSMENT_WALL_S = 5.6
PROBE_S = 1.2

MAS_PUBLIC_URL = os.getenv("MAS_API_URL", "http://192.168.0.188:8001").rstrip("/")
MINDEX_PUBLIC_URL = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")


class MapSliceRequest(BaseModel):
    schema_version: Optional[str] = None
    ao: Dict[str, Any] = Field(default_factory=dict)
    slice: Optional[Dict[str, Any]] = None
    clock: Optional[str] = None
    assets: List[Dict[str, Any]] = Field(default_factory=list)
    origin: str = "SYNTHETIC_EXERCISE"
    execution: str = "ADVISORY_ONLY"
    goal: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    units: Optional[List[Dict[str, Any]]] = None


def _normalize_map_slice(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Accept website `slice` or kit `ao`; empty body → Fort Stewart demo."""
    ao = payload.get("ao") if isinstance(payload.get("ao"), dict) else {}
    slice_ = payload.get("slice") if isinstance(payload.get("slice"), dict) else {}
    if not ao and slice_:
        ao = dict(slice_)
        if "place" not in ao and ao.get("name"):
            ao["place"] = ao.get("name")
        payload["ao"] = ao
    if not payload.get("assets") and payload.get("units"):
        payload["assets"] = payload["units"]
    if not ao and not payload.get("assets"):
        return fort_stewart_demo_slice()
    return payload


def fort_stewart_demo_slice() -> Dict[str, Any]:
    return {
        "schema_version": SITUATION_SCHEMA_VERSION,
        "origin": "SYNTHETIC_EXERCISE",
        "execution": "ADVISORY_ONLY",
        "clock": "2026-09-09T17:00:00Z",
        "ao": {
            "name": "Fort Stewart",
            "place": "Liberty County, Georgia",
            "bbox": [-81.70, 31.80, -81.45, 32.05],
            "center": {"lat": 31.8697, "lon": -81.6072},
        },
        "assets": [
            {
                "id": "3id-hq-synthetic",
                "type": "friendly_unit",
                "lat": 31.88,
                "lon": -81.61,
                "label": "3ID HQ (synthetic exercise marker)",
            },
            {
                "id": "collection-node-a",
                "type": "sensor",
                "lat": 31.90,
                "lon": -81.58,
                "label": "Collection node A (synthetic)",
            },
        ],
        "goal": "Review Fort Stewart AO evidence and preserve the record. Advisory only.",
    }


def _channel(
    *,
    status: str,
    agent_id: Optional[str] = None,
    p: Optional[float] = None,
    uncertainty: Optional[float] = None,
    error: Optional[str] = None,
    note: str = "",
    live: Optional[Dict[str, Any]] = None,
    source_name: Optional[str] = None,
    source_url: Optional[str] = None,
    retrieved_at: Optional[str] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    reason: Optional[str] = None,
    capability_class: Optional[str] = None,
    sample_count: Optional[int] = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "status": status,
        "agent_id": agent_id,
        "p": p,
        "uncertainty": uncertainty,
        "error": error,
        "note": note,
        "live": live or {},
        "sources": sources or [],
    }
    if source_name is not None:
        row["source_name"] = source_name
    if source_url is not None:
        row["source_url"] = source_url
    if retrieved_at is not None:
        row["retrieved_at"] = retrieved_at
    if reason is not None:
        row["reason"] = reason
    if capability_class is not None:
        row["capability_class"] = capability_class
    if sample_count is not None:
        row["sample_count"] = sample_count
    return row


def _channel_from_osint(block: Dict[str, Any], *, agent_id: Optional[str] = None) -> Dict[str, Any]:
    """Map a public-OSINT block onto the situation channel contract. Never invents p."""
    if not isinstance(block, dict):
        return _channel(status="NOT_SUPPLIED", note="OSINT block missing.", reason="empty", agent_id=agent_id)
    sources = block.get("sources") if isinstance(block.get("sources"), list) else []
    primary = sources[0] if sources else {}
    return _channel(
        status=str(block.get("status") or "NOT_SUPPLIED"),
        agent_id=agent_id or block.get("agent_id"),
        p=None if block.get("status") != "SCORED" else block.get("p"),
        error=block.get("error"),
        note=str(block.get("note") or ""),
        live=block.get("live") if isinstance(block.get("live"), dict) else {},
        source_name=block.get("source_name") or primary.get("source_name"),
        source_url=block.get("source_url") or primary.get("source_url"),
        retrieved_at=block.get("retrieved_at") or primary.get("retrieved_at"),
        sources=sources,
        reason=block.get("reason"),
        capability_class=block.get("capability_class"),
        sample_count=block.get("sample_count"),
    )


def _nlm_channel_from_predict(
    probe: Dict[str, Any], *, agent_id: str, domain: str
) -> Dict[str, Any]:
    data = probe.get("data") if isinstance(probe.get("data"), dict) else {}
    text = str(data.get("text") or "")
    confidence = data.get("confidence")
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    if not probe.get("ok"):
        return _channel(
            status="UNQUALIFIED" if probe.get("status_code") else "NOT_SUPPLIED",
            agent_id=agent_id,
            error=str(data.get("error") or data.get("detail") or f"HTTP {probe.get('status_code')}"),
            note=f"NLM {domain} predict failed. No invented score.",
            live={"http": probe.get("status_code")},
        )
    if nlm_text_is_stub(text) or not is_usable_nlm_confidence(confidence, text, metadata):
        ignored = confidence if confidence is not None else data.get("confidence")
        return _channel(
            status="UNQUALIFIED",
            agent_id=agent_id,
            p=None,
            note=(
                "NLM predict is a stub or unused placeholder confidence. "
                f"Service confidence {ignored!r} is not P(event) and is not used as p."
            ),
            live={
                "model": data.get("model"),
                "query_type": data.get("query_type"),
                "nlm_service_confidence_ignored": ignored,
                "stub_confidence_rejected": ignored == NLM_STUB_CONFIDENCE
                or (
                    isinstance(ignored, (int, float))
                    and abs(float(ignored) - NLM_STUB_CONFIDENCE) < 1e-9
                ),
                "excerpt": text[:240],
            },
        )
    return _channel(
        status="SCORED",
        agent_id=agent_id,
        p=float(confidence),
        note=f"NLM service confidence for {domain}. Not P(truth).",
        live={"model": data.get("model")},
    )


def _empty_channels(*, note: str, error: Optional[str] = None) -> Dict[str, Any]:
    return {
        key: _channel(status="NOT_SUPPLIED", note=note, error=error) for key in CHANNEL_KEYS
    }


def _fusion_block() -> Dict[str, Any]:
    return {
        "p_truth": _channel(
            status="NOT_SUPPLIED",
            note="P(truth) needs its own labeled observation process. NLM class-p is not that.",
        ),
        "p_deception": _channel(
            status="NOT_SUPPLIED",
            note="P(deception) is a distinct target. Graph edges are not source truthfulness.",
        ),
        "data_quality": _channel(
            status="NOT_SUPPLIED",
            note="Good vs bad data requires an adjudicated quality model. Not supplied.",
        ),
    }


async def _nlm_predict_inprocess(text: str, query_type: str = "ecology") -> Dict[str, Any]:
    """In-process predict only if the model is already ready. Never auto-load a stub."""
    from mycosoft_mas.nlm.inference.service import PredictionRequest, QueryType, get_nlm_service

    service = get_nlm_service()
    if not service.is_ready:
        return {
            "ok": False,
            "status_code": 0,
            "data": {
                "error": "model_not_ready",
                "text": "",
                "confidence": None,
                "metadata": {"stub": True, "confidence_usable": False},
            },
        }
    try:
        qt = QueryType(query_type)
    except ValueError:
        qt = QueryType.ECOLOGY
    result = await service.predict(
        PredictionRequest(text=text, query_type=qt, max_tokens=64, temperature=0.0)
    )
    return {"ok": True, "status_code": 200, "data": result.to_dict()}


async def _nlm_status_inprocess() -> Dict[str, Any]:
    from mycosoft_mas.nlm.config import get_nlm_config
    from mycosoft_mas.nlm.inference.service import get_nlm_service, is_usable_nlm_confidence

    service = get_nlm_service()
    config = get_nlm_config()
    status = service.get_status()
    predict: Dict[str, Any] = {
        "ok": False,
        "data": {"error": "model_not_ready", "confidence": None, "metadata": {"stub": True}},
    }
    if service.is_ready:
        predict = await _nlm_predict_inprocess(
            "Fort Stewart Fusarium ecology. Advisory only. Do not invent a probability.",
            "ecology",
        )
    data = predict.get("data") if isinstance(predict.get("data"), dict) else {}
    usable = bool(
        predict.get("ok")
        and is_usable_nlm_confidence(
            data.get("confidence"),
            str(data.get("text") or ""),
            data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
        )
    )
    return {
        "model_loaded": bool(service.is_ready),
        "status": status.get("status") or ("ready" if service.is_ready else "not_loaded"),
        "model_name": getattr(config, "model_name", "nlm"),
        "model_version": getattr(config, "model_version", "0.0.0"),
        "uptime_seconds": status.get("uptime_seconds", 0),
        "qualification": "BOUND" if usable else "UNQUALIFIED",
        "stub_confidence_rejected": True,
        "predict": predict,
        "note": (
            "BOUND/SCORED only after a usable non-stub predict. "
            "model_loaded=true alone is not Fusarium p. Stub 0.85 is rejected."
        ),
    }


async def _earth2_status_inprocess() -> Dict[str, Any]:
    from mycosoft_mas.core.routers.earth2_api import get_status

    return await get_status()


async def _physics_remote() -> Dict[str, Any]:
    """Probe PhysicsNeMo on its own URL — never loop back into MAS :8001."""
    import httpx

    base = os.getenv("PHYSICSNEMO_API_URL", "").strip().rstrip("/")
    if not base:
        return {"ok": False, "error": "PHYSICSNEMO_API_URL unset", "available": False}
    try:
        async with httpx.AsyncClient(timeout=PROBE_S) as client:
            response = await client.get(f"{base}/health")
            body: Any
            try:
                body = response.json()
            except Exception:
                body = {"raw": response.text[:200]}
            return {
                "ok": response.is_success,
                "status_code": response.status_code,
                "available": response.is_success,
                "data": body,
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "available": False}


async def _myca_health_inprocess() -> Dict[str, Any]:
    from mycosoft_mas.consciousness import get_consciousness

    consciousness = get_consciousness()
    return {
        "status": "healthy" if consciousness.is_conscious else "dormant",
        "state": consciousness.state.value,
        "is_conscious": bool(consciousness.is_conscious),
        "note": "Dormant is honest. Consciousness is not a Task 8 seven-role consult.",
    }


async def _avani_evaluate_inprocess(place: str, clock: Optional[str], origin: Any) -> Dict[str, Any]:
    from mycosoft_mas.avani.governor.governor import Proposal, RiskTier
    from mycosoft_mas.core.routers.avani_router import get_governor

    gov = get_governor()
    decision = await gov.evaluate_proposal(
        Proposal(
            source_agent="itdx-situation-assessment",
            action_type="observe",
            description=(
                f"Situation assessment for {place}. Advisory only. "
                "No actuator. Synthetic exercise envelope."
            ),
            risk_tier=RiskTier.LOW,
            ecological_impact=0.0,
            reversibility=1.0,
            metadata={"origin": origin, "clock": clock},
        )
    )
    return decision.to_dict()


def _devices_inprocess() -> Dict[str, Any]:
    from mycosoft_mas.core.routers.device_registry_api import get_device_registry_snapshot

    snap = get_device_registry_snapshot()
    devices = snap.get("devices") if isinstance(snap.get("devices"), dict) else {}
    rows = list(devices.values()) if isinstance(devices, dict) else []
    return {"ok": True, "device_count": len(rows), "devices": rows, "snapshot": snap}


def _skip_startup_on() -> bool:
    return os.getenv("MAS_SKIP_BACKGROUND_STARTUP", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


async def _run_situation_assessment_inner(map_slice: Dict[str, Any]) -> Dict[str, Any]:
    ao = map_slice.get("ao") if isinstance(map_slice.get("ao"), dict) else {}
    clock = map_slice.get("clock")
    place = ao.get("name") or ao.get("place") or "unspecified AO"

    nlm_data: Dict[str, Any] = {}
    earth2_data: Dict[str, Any] = {}
    physics: Dict[str, Any] = {}
    myca_data: Dict[str, Any] = {}
    avani_data: Dict[str, Any] = {}
    devices: Dict[str, Any] = {}

    async def _safe(
        name: str, coro, default: Dict[str, Any], timeout: float = PROBE_S
    ) -> Dict[str, Any]:
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except Exception as exc:
            logger.warning("situation-assessment %s probe failed: %s", name, exc)
            out = dict(default)
            out["error"] = str(exc)
            return out

    nlm_data, earth2_data, physics, myca_data, avani_data, devices, osint = await asyncio.gather(
        _safe("nlm", _nlm_status_inprocess(), {"model_loaded": False, "qualification": "UNQUALIFIED"}),
        _safe("earth2", _earth2_status_inprocess(), {"available": False}),
        _safe("physics", _physics_remote(), {"ok": False, "available": False}),
        _safe("myca", _myca_health_inprocess(), {"status": "dormant", "is_conscious": False}),
        _safe(
            "avani",
            _avani_evaluate_inprocess(place, clock, map_slice.get("origin")),
            {},
        ),
        asyncio.to_thread(lambda: _devices_inprocess()),
        _safe("osint", gather_public_osint(ao), {}, timeout=4.4),
    )

    model_loaded = bool(nlm_data.get("model_loaded"))
    nlm_predict = nlm_data.get("predict") if isinstance(nlm_data.get("predict"), dict) else {}
    nlm_ecology = _nlm_channel_from_predict(nlm_predict, agent_id="nlm", domain="ecology")
    nlm_qualified = nlm_ecology.get("status") == "SCORED" and nlm_ecology.get("p") is not None
    nlm_data["qualification"] = "BOUND" if nlm_qualified else "UNQUALIFIED"

    channels: Dict[str, Any] = {}
    nlm_unqual = _channel(
        status="UNQUALIFIED",
        agent_id="nlm",
        p=None,
        reason="nlm_predict_unusable" if model_loaded else "nlm_not_ready",
        note=(
            "NLM channel not scored. BOUND/SCORED requires a usable non-stub predict. "
            "model_loaded alone is not Fusarium p. Stub 0.85 is rejected."
        ),
        live={
            k: nlm_data.get(k)
            for k in ("model_loaded", "status", "uptime_seconds", "qualification")
        },
    )
    if physics.get("ok"):
        channels["physics"] = _channel(
            status="SUPPLIED",
            agent_id="physicsnemo",
            p=None,
            note=(
                "PhysicsNeMo health reached. Not a labeled physics p. "
                "NLM ecology predict is not reused as physics p."
            ),
            live={"physicsnemo": physics, "nlm": nlm_data.get("qualification")},
            source_name="PhysicsNeMo",
            reason="service_health_only",
        )
    else:
        channels["physics"] = dict(nlm_unqual)
        channels["physics"]["live"] = {
            **channels["physics"]["live"],
            "physicsnemo": physics,
        }
        channels["physics"]["reason"] = str(physics.get("error") or "physicsnemo_unset_or_down")
        channels["physics"]["note"] = (
            "PhysicsNeMo not reached from MAS (PHYSICSNEMO_API_URL unset or down). "
            "No labeled NLM physics checkpoint. No invented p."
        )
    channels["biology"] = dict(nlm_unqual)
    channels["biology"]["agent_id"] = "mycology_bio"
    channels["chemistry"] = dict(nlm_unqual)
    channels["chemistry"]["note"] = (
        "No labeled NLM chemistry checkpoint. PubChem may later mark SUPPLIED "
        "(identity only). Ecology predict is not a chemistry p."
    )

    channels["economics"] = _channel(
        status="NOT_SUPPLIED",
        agent_id="financial",
        note=(
            "FinancialAgent requires Stripe credentials and has no labeled "
            "AO economics model. No invented 0.73."
        ),
    )

    retrieved_at = osint.get("retrieved_at")
    open_meteo = osint.get("open_meteo") if isinstance(osint.get("open_meteo"), dict) else {}
    nws = osint.get("nws") if isinstance(osint.get("nws"), dict) else {}
    air_quality = osint.get("air_quality") if isinstance(osint.get("air_quality"), dict) else {}
    if open_meteo.get("ok") and open_meteo.get("current"):
        channels["weather"] = _channel(
            status="SUPPLIED",
            agent_id="open-meteo",
            p=None,
            note=(
                "Public Open-Meteo current at 31.8697,-81.6072. "
                "Not a calibrated weather p. Earth-2 is not required."
            ),
            live={
                "open_meteo": open_meteo,
                "nws": nws,
                "air_quality": air_quality,
                "earth2": earth2_data,
            },
            source_name="Open-Meteo",
            source_url=str(open_meteo.get("citation") or "https://api.open-meteo.com/v1/forecast"),
            retrieved_at=retrieved_at,
            sources=[
                {
                    "source_name": "Open-Meteo",
                    "source_url": open_meteo.get("citation"),
                    "retrieved_at": retrieved_at,
                    "sample_count": 1,
                }
            ]
            + (
                [
                    {
                        "source_name": "NWS api.weather.gov",
                        "source_url": nws.get("citation"),
                        "retrieved_at": nws.get("retrieved_at") or retrieved_at,
                    }
                ]
                if nws.get("ok")
                else []
            ),
            sample_count=1,
        )
    elif nws.get("ok"):
        channels["weather"] = _channel(
            status="SUPPLIED",
            agent_id="nws",
            p=None,
            note="NWS points/forecast for the public Fort Stewart point. Earth-2 not required.",
            live={"nws": nws, "earth2": earth2_data},
            source_name="NWS",
            source_url=str(nws.get("citation") or ""),
            retrieved_at=nws.get("retrieved_at") or retrieved_at,
            sources=[{"source_name": "NWS", "source_url": nws.get("citation"), "retrieved_at": retrieved_at}],
        )
    else:
        channels["weather"] = _channel(
            status="NOT_SUPPLIED",
            agent_id="earth2",
            error=str(
                open_meteo.get("error")
                or nws.get("error")
                or earth2_data.get("error")
                or "public weather and Earth-2 unavailable"
            ),
            note="Open-Meteo, NWS, and Earth-2 did not return current values. Weather p not invented.",
            live={"open_meteo": open_meteo, "nws": nws, "earth2": earth2_data},
            reason="empty",
        )

    mindex = osint.get("mindex") if isinstance(osint.get("mindex"), dict) else {}
    gbif = osint.get("gbif") if isinstance(osint.get("gbif"), dict) else {}
    inat = osint.get("inaturalist") if isinstance(osint.get("inaturalist"), dict) else {}
    gbif_species = osint.get("gbif_species") if isinstance(osint.get("gbif_species"), dict) else {}
    if (
        mindex.get("has_taxa")
        or mindex.get("has_observations")
        or gbif.get("ok")
        or inat.get("ok")
        or gbif_species.get("ok")
    ):
        channels["biology"] = _channel(
            status="SUPPLIED",
            agent_id="mindex",
            p=None,
            note="MINDEX and/or public GBIF/iNaturalist/species-match rows. Not a Fusarium biology p.",
            live={"mindex": mindex, "gbif": gbif, "inaturalist": inat, "gbif_species": gbif_species},
            source_name="GBIF" if gbif.get("ok") else ("iNaturalist" if inat.get("ok") else "MINDEX"),
            source_url=str(
                (gbif.get("citation") if gbif.get("ok") else None)
                or (inat.get("citation") if inat.get("ok") else None)
                or MINDEX_PUBLIC_URL
            ),
            retrieved_at=retrieved_at,
            sources=[
                row
                for row in (
                    {
                        "source_name": "GBIF Occurrence API",
                        "source_url": gbif.get("citation"),
                        "retrieved_at": retrieved_at,
                        "sample_count": gbif.get("count"),
                    }
                    if gbif.get("ok")
                    else None,
                    {
                        "source_name": "iNaturalist Observations API",
                        "source_url": inat.get("citation"),
                        "retrieved_at": retrieved_at,
                        "sample_count": inat.get("total"),
                    }
                    if inat.get("ok")
                    else None,
                )
                if row
            ],
            sample_count=int(gbif.get("count") or inat.get("total") or 0),
        )
    pubchem = osint.get("pubchem") if isinstance(osint.get("pubchem"), dict) else {}
    if mindex.get("has_compounds"):
        channels["chemistry"] = _channel(
            status="SUPPLIED",
            agent_id="mindex",
            p=None,
            note="MINDEX compound rows for Fungi. Not a calibrated chemistry p.",
            live={"compounds": mindex.get("compounds")},
            source_name="MINDEX",
            source_url=MINDEX_PUBLIC_URL,
            retrieved_at=retrieved_at,
            sources=[{"source_name": "MINDEX compounds", "source_url": MINDEX_PUBLIC_URL, "retrieved_at": retrieved_at}],
        )
    elif pubchem.get("ok"):
        channels["chemistry"] = _channel(
            status="SUPPLIED",
            agent_id="pubchem",
            p=None,
            note="Public PubChem fusaric acid record. Not an NLM chemistry p.",
            live={"pubchem": pubchem},
            source_name="PubChem",
            source_url=str(pubchem.get("citation") or ""),
            retrieved_at=pubchem.get("retrieved_at") or retrieved_at,
            sources=[{"source_name": "PubChem", "source_url": pubchem.get("citation"), "retrieved_at": retrieved_at}],
            sample_count=len(pubchem.get("properties") or []),
        )

    osm = osint.get("osm_military") if isinstance(osint.get("osm_military"), dict) else {}
    directions = osint.get("google_directions") if isinstance(osint.get("google_directions"), dict) else {}
    traffic = osint.get("google_traffic") if isinstance(osint.get("google_traffic"), dict) else {}
    road_limits = osint.get("road_limits") if isinstance(osint.get("road_limits"), dict) else {}
    if osm.get("ok") or directions.get("ok") or traffic.get("ok") or road_limits.get("ok"):
        channels["topology"] = _channel(
            status="SUPPLIED",
            agent_id="public-osint",
            p=None,
            note=(
                "Public OSM military landuse and/or Google public-road pathways, "
                "live traffic duration, and civilian road limits. Not a topology p."
            ),
            live={
                "osm_military": osm,
                "google_directions": directions,
                "google_traffic": traffic,
                "road_limits": road_limits,
                "google_key_present": osint.get("google_key_present"),
            },
        )
    else:
        channels["topology"] = _channel(
            status="NOT_SUPPLIED",
            agent_id="topology-stream",
            error=str(
                directions.get("error")
                or traffic.get("error")
                or osm.get("error")
                or road_limits.get("error")
                or "no public topology rows"
            ),
            note=(
                "OSM / Google Directions / traffic / road-limit probes did not return rows. "
                "No invented topology p."
            ),
            live={
                "google_key_present": osint.get("google_key_present"),
                "google_directions": directions,
                "google_traffic": traffic,
            },
        )
    channels["biometry"] = _channel(
        status="NOT_SUPPLIED",
        agent_id="mycology_bio",
        note="No labeled biometry / officer-physiology model for this slice.",
    )

    device_rows = devices.get("devices") if isinstance(devices, dict) else []
    if not isinstance(device_rows, list):
        device_rows = []
    public_base = osint.get("public_base") if isinstance(osint.get("public_base"), dict) else {}
    if public_base.get("ok"):
        mycobrain = osint.get("mycobrain") if isinstance(osint.get("mycobrain"), dict) else {}
        channels["equipment_weapons_assets"] = _channel(
            status="SUPPLIED",
            agent_id="public-base",
            p=None,
            note=(
                "Public Fort Stewart / Hunter AAF names (Nominatim / HIFLD Open / Places / Wikipedia). "
                f"{len(device_rows)} device-registry rows are inventory only. "
                "Weapons/armor/TM stay NOT_SUPPLIED. capability_class=public_road for OSM limits. "
                "Exercise tracks live=false. Official injects stay NOT_SUPPLIED."
            ),
            live={
                "public_base": public_base,
                "road_limits": osint.get("road_limits"),
                "mycobrain": mycobrain,
                "opensky": osint.get("opensky"),
                "device_count": devices.get("device_count", len(device_rows)),
                "exercise_synthetic": True,
                "live": False,
            },
            source_name="OpenStreetMap Nominatim",
            source_url="https://nominatim.openstreetmap.org/search",
            retrieved_at=retrieved_at,
            capability_class="public_road",
            sources=[
                {
                    "source_name": "OpenStreetMap Nominatim",
                    "source_url": "https://nominatim.openstreetmap.org/search",
                    "retrieved_at": retrieved_at,
                }
            ],
        )
    else:
        channels["equipment_weapons_assets"] = _channel(
            status="NOT_SUPPLIED",
            agent_id="device-registry",
            note=(
                f"{len(device_rows)} device-registry rows visible. That is inventory, "
                "not P(equipment) or a weapons score. Public base lookup empty. "
                "Weapons remain NOT_SUPPLIED."
            ),
            live={"device_count": devices.get("device_count", len(device_rows))},
        )

    channels["officer_capability"] = _channel(
        status="NOT_SUPPLIED",
        note="No labeled officer-capability model. Official 1–5 rubric is NOT_SUPPLIED.",
    )

    channels["persona"] = _channel(
        status="NOT_SUPPLIED",
        agent_id="myca",
        note=(
            f"MYCA health state={myca_data.get('state') or myca_data.get('status')}. "
            "Consciousness flag is not a persona probability. Voice /voice/brain "
            "is not the seven-role consult."
        ),
        live=myca_data,
    )

    citations = [
        row.get("citation")
        for row in (
            open_meteo,
            gbif,
            inat,
            osm,
            directions,
            traffic,
            road_limits,
            osint.get("nominatim") if isinstance(osint.get("nominatim"), dict) else {},
            osint.get("hifld") if isinstance(osint.get("hifld"), dict) else {},
            osint.get("google_places") if isinstance(osint.get("google_places"), dict) else {},
        )
        if isinstance(row, dict) and row.get("citation") and row.get("ok")
    ]
    wikipedia = osint.get("wikipedia") if isinstance(osint.get("wikipedia"), dict) else {}
    if wikipedia.get("ok"):
        citations.append(wikipedia.get("citation"))
    if citations or wikipedia.get("ok"):
        channels["information"] = _channel(
            status="SUPPLIED",
            agent_id="public-osint",
            p=None,
            note=(
                "Citations of public APIs + Wikipedia Fort Stewart / Hunter AAF. "
                "Not P(report is true). Official injects stay NOT_SUPPLIED."
            ),
            live={
                "citations": citations,
                "wikipedia": wikipedia,
                "usgs": osint.get("usgs") if isinstance(osint.get("usgs"), dict) else {},
                "google_key_present": osint.get("google_key_present"),
                "official_injects": "NOT_SUPPLIED",
            },
            source_name="Wikipedia REST",
            source_url="https://en.wikipedia.org/api/rest_v1/page/summary/Fort_Stewart",
            retrieved_at=wikipedia.get("retrieved_at") or retrieved_at,
            sources=[
                {
                    "source_name": "Wikipedia",
                    "source_url": p.get("citation"),
                    "retrieved_at": p.get("retrieved_at") or retrieved_at,
                }
                for p in (wikipedia.get("pages") or [])
                if isinstance(p, dict)
            ],
        )
    else:
        channels["information"] = _channel(
            status="NOT_SUPPLIED",
            agent_id="search",
            note="Information-collection completeness is not a calibrated P(report is true).",
            reason="empty",
        )

    directions = osint.get("google_directions") if isinstance(osint.get("google_directions"), dict) else {}
    traffic = osint.get("google_traffic") if isinstance(osint.get("google_traffic"), dict) else {}
    google_missing_reason = (
        "google_maps_key_missing"
        if not osint.get("google_key_present")
        else (traffic.get("google_status") or directions.get("google_status") or "google_maps_api_denied")
    )
    if traffic.get("ok"):
        channels["traffic"] = _channel(
            status="SUPPLIED",
            agent_id="google-maps",
            p=None,
            note="Google Distance Matrix duration_in_traffic on a public civilian road. Not a COP track.",
            live=traffic,
            source_name="Google Maps Distance Matrix",
            source_url="https://developers.google.com/maps/documentation/distance-matrix",
            retrieved_at=retrieved_at,
            sources=[
                {
                    "source_name": "Google Maps Distance Matrix",
                    "source_url": traffic.get("citation"),
                    "retrieved_at": retrieved_at,
                }
            ],
            capability_class="public_road",
            sample_count=1,
        )
    else:
        channels["traffic"] = _channel(
            status="NOT_SUPPLIED",
            agent_id="google-maps",
            error=str(traffic.get("error") or "no live traffic"),
            note=(
                "Google live traffic not available. Set GOOGLE_MAPS_API_KEY "
                "(Directions + Distance Matrix enabled). Map Tiles key is not sufficient."
            ),
            live={"google_key_present": osint.get("google_key_present"), "google_key_env_name": osint.get("google_key_env_name")},
            reason=google_missing_reason,
            capability_class="public_road",
        )
    if directions.get("ok"):
        channels["pathways"] = _channel(
            status="SUPPLIED",
            agent_id="google-maps",
            p=None,
            note="Google Directions public driving paths Fort Stewart → Hunter AAF / Hinesville. Civilian roads only.",
            live=directions,
            source_name="Google Maps Directions",
            source_url="https://developers.google.com/maps/documentation/directions",
            retrieved_at=directions.get("retrieved_at") or retrieved_at,
            sources=[
                {
                    "source_name": "Google Maps Directions",
                    "source_url": directions.get("citation"),
                    "retrieved_at": directions.get("retrieved_at") or retrieved_at,
                }
            ],
            capability_class="public_road",
            sample_count=len(directions.get("routes") or []),
        )
    else:
        channels["pathways"] = _channel(
            status="NOT_SUPPLIED",
            agent_id="google-maps",
            error=str(directions.get("error") or "no public pathway"),
            note="Google Directions empty or key missing. Pathways not invented.",
            live={"google_key_present": osint.get("google_key_present")},
            reason=google_missing_reason,
            capability_class="public_road",
        )
    if directions.get("ok") or traffic.get("ok"):
        channels["navigation"] = _channel(
            status="SUPPLIED",
            agent_id="google-maps",
            p=None,
            note="Public-road ETAs from Directions/Distance Matrix. Cited Google. Not a classified movement table.",
            live={"directions": directions, "traffic": traffic},
            source_name="Google Maps Directions" if directions.get("ok") else "Google Maps Distance Matrix",
            source_url=(
                "https://developers.google.com/maps/documentation/directions"
                if directions.get("ok")
                else "https://developers.google.com/maps/documentation/distance-matrix"
            ),
            retrieved_at=directions.get("retrieved_at") or traffic.get("retrieved_at") or retrieved_at,
            sources=[
                {
                    "source_name": "Google Maps",
                    "source_url": directions.get("citation") or traffic.get("citation"),
                    "retrieved_at": retrieved_at,
                }
            ],
            capability_class="public_road",
        )
    else:
        channels["navigation"] = _channel(
            status="NOT_SUPPLIED",
            agent_id="google-maps",
            error=str(directions.get("error") or traffic.get("error") or "no public ETA"),
            note="Google navigation ETAs not available without a Directions-capable key.",
            live={"google_key_present": osint.get("google_key_present")},
            reason=google_missing_reason,
            capability_class="public_road",
        )

    if avani_data and "approved" in avani_data:
        channels["decision_authority"] = _channel(
            status="UNQUALIFIED",
            agent_id="avani-governor",
            p=None,
            note=(
                "AVANI gate only (approved/denied). Not command authority and not P(success)."
            ),
            live={
                "approved": avani_data.get("approved"),
                "reason": avani_data.get("reason"),
                "in_process": True,
            },
        )
    else:
        channels["decision_authority"] = _channel(
            status="NOT_SUPPLIED",
            agent_id="avani-governor",
            error=str(avani_data.get("error") or avani_data.get("detail") or "evaluate failed"),
            live={"in_process": True},
        )

    return {
        "schema_version": SITUATION_SCHEMA_VERSION,
        "agent_id": "itdx-situation-assessment",
        "role": "situation_assessment",
        "source": "mas",
        "origin": map_slice.get("origin") or "SYNTHETIC_EXERCISE",
        "execution": "ADVISORY_ONLY",
        "synthetic": True,
        "live_cop": False,
        "in_process": True,
        "self_http": False,
        "clock": clock,
        "map_slice": map_slice,
        "ao": ao,
        "assets_submitted": len(map_slice.get("assets") or map_slice.get("units") or []),
        "mas_url": MAS_PUBLIC_URL,
        "mindex_url": MINDEX_PUBLIC_URL,
        "nlm": {
            "model_loaded": model_loaded,
            "health": nlm_data,
            "qualification": "BOUND" if nlm_qualified else "UNQUALIFIED",
            "stub_confidence_rejected": True,
            "ecology_predict_status": nlm_ecology.get("status"),
            "ecology_p": nlm_ecology.get("p"),
        },
        "earth2": earth2_data,
        "public_osint": {
            "google_key_present": osint.get("google_key_present"),
            "google_key_env_name": osint.get("google_key_env_name"),
            "official_injects": "NOT_SUPPLIED",
            "fouo": False,
            "cui": False,
            "refused": osint.get("refused") or [],
        },
        "sources": [
            src
            for key in CHANNEL_KEYS
            for src in (channels.get(key) or {}).get("sources") or []
        ],
        "geojson": osint.get("geojson")
        if isinstance(osint.get("geojson"), dict)
        else {"type": "FeatureCollection", "features": []},
        "myca": myca_data,
        "brain": {
            "used_as_task8": False,
            "note": "/voice/brain is not the seven-role consult.",
        },
        "channels": channels,
        "fusion": _fusion_block(),
        "channel_order": list(CHANNEL_KEYS),
    }


async def run_situation_assessment(map_slice: Dict[str, Any]) -> Dict[str, Any]:
    """In-process assessment. Never HTTP-loops to this worker."""
    try:
        return await asyncio.wait_for(
            _run_situation_assessment_inner(map_slice), timeout=ASSESSMENT_WALL_S
        )
    except asyncio.TimeoutError:
        ao = map_slice.get("ao") if isinstance(map_slice.get("ao"), dict) else {}
        return {
            "schema_version": SITUATION_SCHEMA_VERSION,
            "agent_id": "itdx-situation-assessment",
            "role": "situation_assessment",
            "source": "mas",
            "origin": map_slice.get("origin") or "SYNTHETIC_EXERCISE",
            "execution": "ADVISORY_ONLY",
            "synthetic": True,
            "live_cop": False,
            "in_process": True,
            "self_http": False,
            "timed_out": True,
            "clock": map_slice.get("clock"),
            "map_slice": map_slice,
            "ao": ao,
            "assets_submitted": len(map_slice.get("assets") or map_slice.get("units") or []),
            "nlm": {
                "model_loaded": False,
                "qualification": "UNQUALIFIED",
                "stub_confidence_rejected": True,
            },
            "myca": {"status": "unknown", "note": "assessment wall time exceeded"},
            "brain": {"used_as_task8": False},
            "channels": _empty_channels(
                note="Assessment wall time exceeded. Partial NOT_SUPPLIED. No invented p.",
                error=f"timeout>{ASSESSMENT_WALL_S}s",
            ),
            "fusion": _fusion_block(),
            "channel_order": list(CHANNEL_KEYS),
        }


def _task8_agent() -> ITDXTask8Agent:
    return ITDXTask8Agent()


@router.get("/health")
async def itdx_health() -> Dict[str, Any]:
    probes = mapped_role_probes()
    return {
        "status": "healthy",
        "service": "itdx",
        "schema_task8": SCHEMA_VERSION,
        "schema_situation_assessment": SITUATION_SCHEMA_VERSION,
        "mas_url": MAS_PUBLIC_URL,
        "mindex_url": MINDEX_PUBLIC_URL,
        "self_http_assessment": False,
        "skip_background_startup": _skip_startup_on(),
        "skip_startup_reason": (
            "MAS_SKIP_BACKGROUND_STARTUP is on so collectors do not wedge the API. "
            "health.agents stays []. Seven mapped roles are listed here, not invented as running."
            if _skip_startup_on()
            else None
        ),
        "myca_consult": (
            "Task 8 calls existing v2 agents in-process. "
            "GET /api/myca/health dormant is allowed and is not a persona p. "
            "/voice/brain is not the seven-role consult."
        ),
        "mapped_roles": probes,
        "roles": [
            "State summarizer",
            "COA proposer",
            "Alternative planner",
            "Skeptical critic",
            "Evidence verifier",
            "AVANI guardian",
            "Human handoff",
        ],
    }


@router.get("/task8")
async def get_task8() -> Dict[str, Any]:
    agent = _task8_agent()
    result = await agent.run_task8(fort_stewart_demo_slice())
    result["path"] = "/api/itdx/task8"
    result["demo_slice"] = "fort_stewart"
    return result


@router.post("/task8")
async def post_task8(body: MapSliceRequest) -> Dict[str, Any]:
    payload = _normalize_map_slice(body.model_dump())
    agent = _task8_agent()
    result = await agent.run_task8(payload)
    result["path"] = "/api/itdx/task8"
    return result


@router.get("/situation-assessment")
async def get_situation_assessment() -> Dict[str, Any]:
    return await run_situation_assessment(fort_stewart_demo_slice())


@router.post("/situation-assessment")
async def post_situation_assessment(body: MapSliceRequest) -> Dict[str, Any]:
    return await run_situation_assessment(_normalize_map_slice(body.model_dump()))


@router.get("/authority")
@router.post("/authority")
async def task8_authority_alias(body: Optional[MapSliceRequest] = None) -> Dict[str, Any]:
    """Website consumer alias — same payload as Task 8."""
    payload = _normalize_map_slice(body.model_dump() if body else {})
    result = await _task8_agent().run_task8(payload)
    result["path"] = "/api/itdx/authority"
    return result


avani_task8_router = APIRouter(prefix="/api/avani", tags=["itdx"])
myca_task8_router = APIRouter(prefix="/api/myca", tags=["itdx"])


@avani_task8_router.get("/task8")
@avani_task8_router.post("/task8")
async def avani_task8_alias(body: Optional[MapSliceRequest] = None) -> Dict[str, Any]:
    payload = _normalize_map_slice(body.model_dump() if body else {})
    result = await _task8_agent().run_task8(payload)
    result["path"] = "/api/avani/task8"
    return result


@myca_task8_router.get("/task8")
@myca_task8_router.post("/task8")
async def myca_task8_alias(body: Optional[MapSliceRequest] = None) -> Dict[str, Any]:
    payload = _normalize_map_slice(body.model_dump() if body else {})
    result = await _task8_agent().run_task8(payload)
    result["path"] = "/api/myca/task8"
    result["myca_consciousness_used"] = False
    result["note"] = (
        "This alias is the seven-role Task 8 consult via existing agents. "
        "It is not /api/myca/health and not /voice/brain."
    )
    return result
