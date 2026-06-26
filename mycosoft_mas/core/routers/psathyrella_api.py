"""Psathyrella buoy backend API surface for control, telemetry, and comms."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

import httpx
import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from mycosoft_mas.core.routers import device_registry_api
from mycosoft_mas.devices.psathyrella.autonomy import (
    PsathyrellaAutonomyController,
    SignalFollowMode,
    WaypointRecord,
)
from mycosoft_mas.devices.psathyrella.command_handler import (
    handle_legacy_operator_command,
    handle_mdp_command,
)
from mycosoft_mas.devices.psathyrella.comms_bridge import get_psathyrella_comms_bridge
from mycosoft_mas.devices.psathyrella.constants import PSATHYRELLA_DEVICE_ID
from mycosoft_mas.devices.psathyrella.telemetry_builder import build_buoy_telemetry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/psathyrella", tags=["psathyrella"])

REDIS_URL = os.getenv("REDIS_URL", "redis://192.168.0.189:6379/0")
WAYPOINT_KEY_PREFIX = "psathyrella:waypoints:"

_redis_client: Optional[redis.Redis] = None
_comms_bridge = get_psathyrella_comms_bridge()
_autonomy_controller = PsathyrellaAutonomyController()


class VisionSource(str, Enum):
    CAMERA = "camera"
    LIDAR = "lidar"
    RADAR = "radar"
    WIFI = "wifi"


class ThrusterVectorCommand(BaseModel):
    vx: float = Field(default=0.0, ge=-1.0, le=1.0)
    vy: float = Field(default=0.0, ge=-1.0, le=1.0)
    yaw: float = Field(default=0.0, ge=-1.0, le=1.0)
    spin: float = Field(default=0.0, ge=-1.0, le=1.0)


class ThrusterPwmCommand(BaseModel):
    motor_front_left: int = Field(..., ge=1100, le=1900)
    motor_front_right: int = Field(..., ge=1100, le=1900)
    motor_rear_left: int = Field(..., ge=1100, le=1900)
    motor_rear_right: int = Field(..., ge=1100, le=1900)


class PropulsionRequest(BaseModel):
    vector: Optional[ThrusterVectorCommand] = None
    motors: Optional[ThrusterPwmCommand] = None
    use_mycorrhizae: bool = True
    timeout_s: float = Field(default=6.0, ge=1.0, le=30.0)
    dry_run: bool = False

    @model_validator(mode="after")
    def validate_mode(self) -> "PropulsionRequest":
        if bool(self.vector) == bool(self.motors):
            raise ValueError("provide exactly one of vector or motors")
        return self


class WaypointMutationRequest(BaseModel):
    action: Literal["list", "replace", "append", "upsert", "delete", "clear"] = "list"
    waypoints: List[WaypointRecord] = Field(default_factory=list)
    waypoint_id: Optional[str] = None


class CameraPointRequest(BaseModel):
    bearing_deg: float = Field(..., ge=0.0, le=360.0)
    pitch_deg: float = Field(default=0.0, ge=-90.0, le=90.0)
    hold_seconds: int = Field(default=0, ge=0, le=3600)
    use_mycorrhizae: bool = True


class CommsUpdateRequest(BaseModel):
    action: Literal["set_mode", "ingest_radio", "ingest_acoustic", "flush_store_forward", "set_backhaul"] = "set_mode"
    radio_mode: str = "auto"
    bridge_enabled: Optional[bool] = None
    frame: Dict[str, Any] = Field(default_factory=dict)
    acoustic_payload: Dict[str, Any] = Field(default_factory=dict)
    classify_acoustic: bool = True
    backhaul_available: Optional[bool] = None
    flush_limit: int = Field(default=50, ge=1, le=500)


class SignalFollowRequest(BaseModel):
    mode: SignalFollowMode


class PsathyrellaMdpCommand(BaseModel):
    target: str = Field(..., description="side_a or side_b")
    cmd: str
    params: Dict[str, Any] = Field(default_factory=dict)


class PsathyrellaLegacyCommand(BaseModel):
    command: str


def _mindex_prefix() -> str:
    base = (os.getenv("MINDEX_API_URL") or "http://192.168.0.189:8000").rstrip("/")
    if base.endswith("/api/mindex"):
        return base
    return f"{base}/api/mindex"


def _mindex_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {"Accept": "application/json"}
    api_key = (os.getenv("MINDEX_API_KEY") or "").strip()
    if api_key:
        headers["X-API-Key"] = api_key
    internal = (
        os.getenv("MINDEX_INTERNAL_TOKEN")
        or os.getenv("MINDEX_INTERNAL_TOKENS", "").split(",")[0]
    ).strip()
    if internal:
        headers["X-Internal-Token"] = internal
    return headers


async def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
    return _redis_client


def _waypoint_key(device_id: str) -> str:
    return f"{WAYPOINT_KEY_PREFIX}{device_id}"


async def _load_waypoints(device_id: str) -> List[WaypointRecord]:
    client = await _get_redis()
    payload = await client.get(_waypoint_key(device_id))
    if not payload:
        return []
    try:
        data = json.loads(payload)
        return [WaypointRecord(**entry) for entry in data]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse waypoint cache for %s: %s", device_id, exc)
        return []


async def _save_waypoints(device_id: str, waypoints: List[WaypointRecord]) -> None:
    client = await _get_redis()
    serialised = [item.model_dump() for item in waypoints]
    await client.set(_waypoint_key(device_id), json.dumps(serialised, separators=(",", ":")))


async def _classify_acoustic(payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{_mindex_prefix()}/nlm/classify/acoustic"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            url,
            headers={**_mindex_headers(), "Content-Type": "application/json"},
            json=payload,
        )
    if response.status_code != 200:
        return {
            "status": "pending",
            "reason": "nlm_unavailable",
            "http_status": response.status_code,
            "detail": response.text[:300],
        }
    data = response.json()
    data["status"] = data.get("status", "ok")
    return data


async def _persist_taco_observation(
    device_id: str,
    acoustic_payload: Dict[str, Any],
    classification: Dict[str, Any],
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    location = acoustic_payload.get("gps") or {}
    body: Dict[str, Any] = {
        "sensor_id": f"{device_id}:hydrophone",
        "sensor_type": "hydrophone",
        "latitude": location.get("lat"),
        "longitude": location.get("lon"),
        "depth_m": acoustic_payload.get("depth_m"),
        "raw_data": acoustic_payload,
        "classification": classification if classification.get("status") == "ok" else None,
        "confidence": classification.get("confidence"),
        "observed_at": now,
    }
    url = f"{_mindex_prefix()}/taco/observations"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            url,
            headers={**_mindex_headers(), "Content-Type": "application/json"},
            json=body,
        )
    if response.status_code >= 400:
        return {
            "status": "pending",
            "reason": "taco_observation_rejected",
            "http_status": response.status_code,
            "detail": response.text[:300],
        }
    return {"status": "ok", "result": response.json()}


def _extract_status_fields(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    payload = telemetry.get("payload") if isinstance(telemetry.get("payload"), dict) else telemetry
    sensor_status = payload.get("sensor_status") or payload.get("sensors") or {}
    return {
        "gps": payload.get("gps") or payload.get("position") or {},
        "power": payload.get("power") or {
            "battery_v": payload.get("battery_v"),
            "solar_mv": payload.get("solar_mv"),
            "usb_power": payload.get("usb_power"),
        },
        "solar": payload.get("solar") or {"intake_mv": payload.get("solar_mv")},
        "thrusters": payload.get("thrusters") or {},
        "comms_links": payload.get("comms") or payload.get("links") or {},
        "sensor_health": sensor_status,
    }


def _vision_url_for(device_id: str, source: VisionSource) -> Optional[str]:
    env_key = f"PSATHYRELLA_{source.value.upper()}_STREAM_URL"
    configured = (os.getenv(env_key) or "").strip()
    if configured:
        return configured
    device = device_registry_api._device_registry.get(device_id)  # noqa: SLF001
    extra = device.get("extra") if isinstance(device, dict) else {}
    if isinstance(extra, dict):
        vision_urls = extra.get("vision_urls")
        if isinstance(vision_urls, dict):
            candidate = vision_urls.get(source.value)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    if source == VisionSource.RADAR:
        return "/api/natureos/bluesight/observations/stream"
    return None


@router.get("/telemetry")
async def get_default_telemetry() -> Dict[str, Any]:
    """Fused BuoyTelemetry envelope for the default Psathyrella device (GCS contract)."""
    envelope = await build_buoy_telemetry(PSATHYRELLA_DEVICE_ID)
    return {"status": "ok", **envelope}


@router.get("/{device_id}/telemetry")
async def get_buoy_telemetry(device_id: str) -> Dict[str, Any]:
    """Fused BuoyTelemetry envelope matching lib/psathyrella/contract.ts."""
    envelope = await build_buoy_telemetry(device_id)
    return {"status": "ok", **envelope}


@router.post("/{device_id}/command")
async def psathyrella_mdp_command(device_id: str, request: Request) -> Dict[str, Any]:
    """
    Psathyrella command bus: legacy operator strings or MDP {target, cmd, params}.
    Matches POST /api/devices/psathyrella-buoy-com4/command from the GCS.
    """
    try:
        body = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="invalid_json") from exc

    if isinstance(body, dict) and isinstance(body.get("command"), str) and not body.get("target"):
        try:
            result = await handle_legacy_operator_command(device_id, body["command"])
            return {"ok": True, "result": result}
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    target = body.get("target") if isinstance(body, dict) else None
    cmd = body.get("cmd") if isinstance(body, dict) else None
    if not target or not cmd:
        raise HTTPException(status_code=400, detail="missing_target_or_cmd")

    try:
        result = await handle_mdp_command(
            device_id,
            target=str(target),
            cmd=str(cmd),
            params=body.get("params") if isinstance(body.get("params"), dict) else {},
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("Psathyrella command failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{device_id}/status")
async def get_psathyrella_status(device_id: str) -> Dict[str, Any]:
    telemetry = await device_registry_api.get_device_telemetry(device_id=device_id)
    status_fields = _extract_status_fields(telemetry if isinstance(telemetry, dict) else {})
    return {
        "status": "ok",
        "device_id": device_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "telemetry_source": "device-registry-proxy",
        **status_fields,
        "raw_telemetry": telemetry,
    }


@router.get("/health")
async def psathyrella_health() -> Dict[str, Any]:
    return {"status": "ok", "service": "psathyrella-api"}


@router.post("/{device_id}/propulsion")
async def command_propulsion(device_id: str, request: PropulsionRequest) -> Dict[str, Any]:
    if request.vector is not None:
        command = device_registry_api.DeviceCommand(
            command="psa_thruster_vector_set",
            params=request.vector.model_dump(),
            timeout=request.timeout_s,
        )
        mode = "vector"
    else:
        command = device_registry_api.DeviceCommand(
            command="psa_thruster_pwm_set",
            params=request.motors.model_dump() if request.motors else {},
            timeout=request.timeout_s,
        )
        mode = "motors"

    if request.dry_run:
        return {
            "status": "dry_run",
            "device_id": device_id,
            "mode": mode,
            "command": command.model_dump(),
        }

    response = await device_registry_api.send_device_command(
        device_id=device_id,
        cmd=command,
        use_mycorrhizae=request.use_mycorrhizae,
    )
    return {"status": "ok", "device_id": device_id, "mode": mode, "response": response}


@router.post("/{device_id}/waypoints")
async def mutate_waypoints(device_id: str, request: WaypointMutationRequest) -> Dict[str, Any]:
    current = await _load_waypoints(device_id)

    if request.action == "replace":
        current = list(request.waypoints)
    elif request.action == "append":
        current.extend(request.waypoints)
    elif request.action == "upsert":
        indexed = {item.waypoint_id: item for item in current}
        for waypoint in request.waypoints:
            indexed[waypoint.waypoint_id] = waypoint
        current = list(indexed.values())
    elif request.action == "delete":
        if not request.waypoint_id:
            raise HTTPException(status_code=400, detail="waypoint_id_required_for_delete")
        current = [item for item in current if item.waypoint_id != request.waypoint_id]
    elif request.action == "clear":
        current = []

    await _save_waypoints(device_id, current)
    _autonomy_controller.replace_waypoints(current)

    return {
        "status": "ok",
        "device_id": device_id,
        "action": request.action,
        "count": len(current),
        "waypoints": [item.model_dump() for item in current],
        "autonomy_state": _autonomy_controller.state.model_dump(),
    }


@router.post("/{device_id}/point-camera")
async def point_camera(device_id: str, request: CameraPointRequest) -> Dict[str, Any]:
    _autonomy_controller.point_camera(
        bearing_deg=request.bearing_deg,
        pitch_deg=request.pitch_deg,
        hold_seconds=request.hold_seconds,
    )
    command = device_registry_api.DeviceCommand(
        command="psa_camera_point",
        params=request.model_dump(exclude={"use_mycorrhizae"}),
        timeout=6.0,
    )
    response = await device_registry_api.send_device_command(
        device_id=device_id,
        cmd=command,
        use_mycorrhizae=request.use_mycorrhizae,
    )
    return {
        "status": "ok",
        "device_id": device_id,
        "autonomy_state": _autonomy_controller.state.model_dump(),
        "response": response,
    }


@router.get("/{device_id}/comms")
async def get_comms_state(device_id: str) -> Dict[str, Any]:
    return {"status": "ok", **_comms_bridge.get_state(device_id)}


@router.post("/{device_id}/comms")
async def update_comms(device_id: str, request: CommsUpdateRequest) -> Dict[str, Any]:
    if request.action == "set_mode":
        state = _comms_bridge.update_mode(
            device_id=device_id,
            radio_mode=request.radio_mode,
            bridge_enabled=request.bridge_enabled,
        )
        return {"status": "ok", "action": request.action, "state": state}

    if request.action == "ingest_radio":
        acoustic = _comms_bridge.translate_radio_to_acoustic(device_id, request.frame)
        queued = _comms_bridge.enqueue_for_backhaul(device_id, "radio_to_acoustic", acoustic)
        await _comms_bridge.publish_acoustic_event(
            device_id,
            {
                "event": "radio_ingest",
                "frame_id": queued.frame_id,
                "payload": acoustic,
                "timestamp": queued.received_at,
            },
        )
        return {"status": "ok", "action": request.action, "frame_id": queued.frame_id, "acoustic_payload": acoustic}

    if request.action == "ingest_acoustic":
        translation = _comms_bridge.translate_acoustic_to_radio(request.acoustic_payload)
        queued = _comms_bridge.enqueue_for_backhaul(device_id, "acoustic_to_radio", translation)
        classification: Dict[str, Any] = {"status": "pending", "reason": "classification_not_requested"}
        if request.classify_acoustic:
            classification = await _classify_acoustic(request.acoustic_payload)
        persist = await _persist_taco_observation(device_id, request.acoustic_payload, classification)
        await _comms_bridge.publish_acoustic_event(
            device_id,
            {
                "event": "acoustic_ingest",
                "frame_id": queued.frame_id,
                "translation": translation,
                "classification": classification,
                "observation_ingest": persist,
                "timestamp": queued.received_at,
            },
        )
        return {
            "status": "ok",
            "action": request.action,
            "frame_id": queued.frame_id,
            "translation": translation,
            "classification": classification,
            "observation_ingest": persist,
        }

    if request.action == "flush_store_forward":
        drained = _comms_bridge.flush_store_forward(device_id, limit=request.flush_limit)
        return {"status": "ok", "action": request.action, "frames": drained, "count": len(drained)}

    if request.action == "set_backhaul":
        if request.backhaul_available is None:
            raise HTTPException(status_code=400, detail="backhaul_available_required")
        if request.backhaul_available:
            drained = _comms_bridge.flush_store_forward(device_id, limit=request.flush_limit)
            return {"status": "ok", "action": request.action, "backhaul_available": True, "flushed": len(drained)}
        return {"status": "ok", "action": request.action, "backhaul_available": False}

    raise HTTPException(status_code=400, detail=f"unsupported_action:{request.action}")


@router.get("/{device_id}/acoustic/stream")
async def acoustic_stream(device_id: str, request: Request) -> StreamingResponse:
    queue = _comms_bridge.register_acoustic_stream(device_id)

    async def event_generator() -> Any:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: acoustic\ndata: {json.dumps(event, default=str)}\n\n"
                except asyncio.TimeoutError:
                    keepalive = {
                        "device_id": device_id,
                        "status": "alive",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    yield f"event: keepalive\ndata: {json.dumps(keepalive)}\n\n"
        finally:
            _comms_bridge.unregister_acoustic_stream(device_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{device_id}/vision/{source}")
async def get_vision_metadata(device_id: str, source: VisionSource) -> Dict[str, Any]:
    stream_url = _vision_url_for(device_id, source)
    if not stream_url:
        return {
            "status": "pending",
            "device_id": device_id,
            "source": source.value,
            "stream_url": None,
            "detail": f"Set PSATHYRELLA_{source.value.upper()}_STREAM_URL or publish via device extra.vision_urls",
        }
    return {
        "status": "ok",
        "device_id": device_id,
        "source": source.value,
        "stream_url": stream_url,
        "protocol": "http" if stream_url.startswith("http") else "internal",
    }


@router.get("/{device_id}/autonomy")
async def get_autonomy_state(device_id: str) -> Dict[str, Any]:
    telemetry = await device_registry_api.get_device_telemetry(device_id=device_id)
    guidance = _autonomy_controller.compute_guidance(latest_position=(telemetry or {}).get("gps"))
    return {"status": "ok", "device_id": device_id, "autonomy": guidance}


@router.post("/{device_id}/autonomy/signal-follow")
async def set_signal_follow_mode(device_id: str, request: SignalFollowRequest) -> Dict[str, Any]:
    state = _autonomy_controller.set_mode(
        mode=_autonomy_controller.state.mode,
        signal_follow_mode=request.mode,
    )
    return {"status": "ok", "device_id": device_id, "autonomy_state": state.model_dump()}
