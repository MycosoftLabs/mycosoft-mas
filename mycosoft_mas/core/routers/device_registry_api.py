"""
Device Registry API Router

Central registry for MycoBrain devices across the network.
Devices register via heartbeat and are tracked with TTL expiration.

Created: February 10, 2026
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel, Field

from mycosoft_mas.deep_agents.domain_hooks import schedule_domain_task

logger = logging.getLogger("DeviceRegistry")


def _mycobrain_service_forward_headers() -> Dict[str, str]:
    """Optional API key when the MycoBrain HTTP service requires X-API-Key (e.g. Jetson gateway)."""
    key = os.getenv("MYCOBRAIN_SERVICE_FORWARD_API_KEY") or os.getenv("MYCOBRAIN_API_KEY")
    if key:
        return {"X-API-Key": key}
    return {}


async def _resolve_mycobrain_mdp_http_id(
    registry_device_id: str,
    device: Dict[str, Any],
    base_url: str,
    client: httpx.AsyncClient,
) -> str:
    """
    Registry device_id may be a gateway-only heartbeat (mycobrain-service-*) while the
    MycoBrain HTTP API paths use mycobrain-<PORT> for serial MDP devices. Resolve the path id.
    """
    extra = device.get("extra") or {}
    explicit = extra.get("mdp_device_id") or extra.get("primary_serial_device_id")
    if explicit:
        return str(explicit)

    board = (device.get("board_type") or "").lower()
    is_service_gateway = board == "service" or registry_device_id.startswith("mycobrain-service-")
    if not is_service_gateway:
        return registry_device_id

    snap = extra.get("mdp_device_ids_on_host")
    if isinstance(snap, list) and len(snap) == 1:
        return str(snap[0])

    h = _mycobrain_service_forward_headers()
    try:
        r = await client.get(f"{base_url}/devices", headers=h)
        if r.status_code != 200:
            logger.warning(
                "GET /devices returned %s for gateway %s",
                r.status_code,
                registry_device_id,
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Gateway {registry_device_id} could not list serial devices (HTTP {r.status_code}). "
                    "Connect an ESP32 on this host or select the mycobrain-<PORT> registry entry."
                ),
            )
        data = r.json()
        devs = data.get("devices") or []
        if not devs:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Gateway {registry_device_id} has no serial MDP device connected. "
                    "Plug in the MycoBrain or wait for auto-connect; use the mycobrain-<PORT> row for commands."
                ),
            )
        if len(devs) == 1:
            return devs[0].get("device_id") or registry_device_id
        for d in devs:
            did = (d.get("device_id") or "").lower()
            if any(
                x in did
                for x in ("com", "ttyusb", "ttyacm", "cu.usb", "wchusb", "serial")
            ):
                return d.get("device_id") or registry_device_id
        return devs[0].get("device_id") or registry_device_id
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("MDP path resolve failed for %s: %s", registry_device_id, e)
        raise HTTPException(
            status_code=503,
            detail=f"Could not resolve MDP device on gateway {registry_device_id}: {e}",
        ) from e


router = APIRouter(prefix="/api/devices", tags=["device-registry"])

# In-memory device registry (Redis can be added later for persistence)
_device_registry: Dict[str, Dict[str, Any]] = {}
_device_last_seen: Dict[str, datetime] = {}

# Orchestrator integration (optional)
_orchestrator = None


def _get_orchestrator():
    """Get the orchestrator instance if available."""
    global _orchestrator
    if _orchestrator is None:
        try:
            from mycosoft_mas.core.orchestrator import get_orchestrator

            _orchestrator = get_orchestrator()
            logger.info("Device registry connected to orchestrator")
        except ImportError:
            logger.debug("Orchestrator not available for device registration")
        except Exception as e:
            logger.warning(f"Orchestrator initialization failed: {e}")
    return _orchestrator


def _register_device_with_orchestrator(device_id: str, device: Dict[str, Any]):
    """Register device as a service with the orchestrator for health monitoring."""
    orchestrator = _get_orchestrator()
    if not orchestrator:
        return

    try:
        from mycosoft_mas.core.orchestrator import ServiceConfig

        host = device.get("host", "")
        port = device.get("port", 8003)

        # Build health URL
        if host.startswith("http://") or host.startswith("https://"):
            health_url = f"{host.rstrip('/')}/health"
        elif device.get("connection_type") == "cloudflare":
            health_url = f"https://{host}/health"
        else:
            health_url = f"http://{host}:{port}/health"

        config = ServiceConfig(
            id=f"mycobrain-{device_id}",
            name=device.get("device_name", f"MycoBrain {device_id}"),
            health_url=health_url,
            host=host if not host.startswith("http") else None,
            port=port if not host.startswith("http") else None,
            health_check_interval=30,
            failure_threshold=3,
            is_critical=False,
        )

        orchestrator.register_service(config)
        logger.info(f"Device {device_id} registered with orchestrator")

    except Exception as e:
        logger.warning(f"Failed to register device {device_id} with orchestrator: {e}")


# Configuration
DEVICE_TTL_SECONDS = int(os.getenv("DEVICE_TTL_SECONDS", "120"))  # 2 minutes default
DEVICE_STALE_SECONDS = int(os.getenv("DEVICE_STALE_SECONDS", "60"))  # 1 minute stale threshold


class DeviceHeartbeat(BaseModel):
    """Schema for device heartbeat/registration (serial, LoRa, Bluetooth, WiFi gateways)."""

    device_id: str = Field(..., description="Unique device identifier")
    device_name: str = Field(default="MycoBrain", description="Human-friendly device name")
    device_role: str = Field(
        default="standalone",
        description=(
            "Device role: mushroom1, sporebase, hyphae1, myconode, psathyrella, alarm, gateway, "
            "mycodrone (generic airframe), agaric_mini, agaric_standard, agaric_heavy, standalone"
        ),
    )
    device_display_name: Optional[str] = Field(
        default=None, description="UI display name (e.g. 'Mushroom 1', 'SporeBase Alpha')"
    )
    host: str = Field(..., description="Reachable IP or URL (gateway/server reachable from MAS)")
    port: int = Field(default=8003, description="MycoBrain service or gateway port")
    firmware_version: str = Field(default="unknown")
    board_type: str = Field(
        default="esp32s3", description="Board type: esp32s3, esp32, service, etc."
    )
    sensors: List[str] = Field(default_factory=list, description="Connected sensors")
    capabilities: List[str] = Field(default_factory=list, description="Device capabilities")
    location: Optional[str] = Field(default=None, description="Physical location")
    connection_type: str = Field(default="lan", description="lan, tailscale, cloudflare")
    ingestion_source: str = Field(
        default="serial", description="serial, lora, bluetooth, wifi, gateway"
    )
    extra: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


def _soc_pg_for_inventory() -> bool:
    return bool(os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL"))


def _host_to_ipv4(host: str) -> Optional[str]:
    h = (host or "").strip()
    if not h:
        return None
    if h.startswith("http://") or h.startswith("https://"):
        parsed = urlparse(h)
        return parsed.hostname
    return h.split(":")[0].strip() or None


async def _persist_heartbeat_to_device_inventory(hb: DeviceHeartbeat) -> None:
    """Mirror heartbeats into soc_ops.device_inventory for SOC /security network."""
    if not _soc_pg_for_inventory():
        return
    ip = _host_to_ipv4(hb.host)
    if not ip:
        return
    mac = None
    extra = hb.extra or {}
    if isinstance(extra.get("mac"), str) and extra.get("mac").strip():
        mac = extra["mac"].strip().lower()
    try:
        from mycosoft_mas.soc import repository as soc_repo

        caps: Dict[str, Any] = {
            "device_role": hb.device_role,
            "ingestion_source": hb.ingestion_source,
            "connection_type": hb.connection_type,
            "capabilities": hb.capabilities,
            "sensors": hb.sensors,
        }
        dump = hb.model_dump() if hasattr(hb, "model_dump") else hb.dict()
        await soc_repo.upsert_device_inventory(
            mac=mac,
            ip=ip,
            hostname=hb.device_name,
            board_type=hb.board_type,
            device_id=hb.device_id,
            source="heartbeat",
            classified_as=hb.device_role,
            status="online",
            capabilities=caps,
            raw={"heartbeat": dump},
        )
    except Exception as e:
        logger.warning("device_inventory upsert from heartbeat failed: %s", e)


class DeviceInfo(BaseModel):
    """Full device information returned by registry."""

    device_id: str
    device_name: str
    device_role: str = "standalone"
    device_display_name: Optional[str] = None
    host: str
    port: int
    firmware_version: str
    board_type: str
    sensors: List[str]
    capabilities: List[str]
    location: Optional[str]
    connection_type: str
    ingestion_source: str = "serial"
    status: str  # online, stale, offline
    last_seen: str
    registered_at: str
    extra: Dict[str, Any] = Field(default_factory=dict)


class DeviceCommand(BaseModel):
    """Command to send to a remote device."""

    command: str = Field(..., description="Command to send (CLI format)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Optional parameters")
    timeout: float = Field(default=5.0, description="Command timeout in seconds")


def _get_device_status(device_id: str) -> str:
    """Determine device status based on last seen time."""
    if device_id not in _device_last_seen:
        return "offline"

    last_seen = _device_last_seen[device_id]
    now = datetime.now(timezone.utc)
    elapsed = (now - last_seen).total_seconds()

    if elapsed > DEVICE_TTL_SECONDS:
        return "offline"
    elif elapsed > DEVICE_STALE_SECONDS:
        return "stale"
    else:
        return "online"


def get_device_registry_snapshot() -> Dict[str, Any]:
    """
    Thread-safe snapshot of device registry for Merkle world root.
    Returns JSON-serializable dict: devices, last_seen_iso, timestamp.
    """
    _cleanup_expired_devices()
    devices = {}
    for device_id, device in list(_device_registry.items()):
        status = _get_device_status(device_id)
        devices[device_id] = {**device, "status": status}
    last_seen_iso = {k: v.isoformat() for k, v in _device_last_seen.items()}
    return {
        "devices": devices,
        "last_seen_iso": last_seen_iso,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _cleanup_expired_devices():
    """Remove devices that haven't sent heartbeat within TTL."""
    now = datetime.now(timezone.utc)
    expired = []

    for device_id, last_seen in list(_device_last_seen.items()):
        if (now - last_seen).total_seconds() > DEVICE_TTL_SECONDS:
            expired.append(device_id)

    for device_id in expired:
        if device_id in _device_registry:
            logger.info(f"Device expired: {device_id}")
            del _device_registry[device_id]
        if device_id in _device_last_seen:
            del _device_last_seen[device_id]

    return expired


def _upsert_device_heartbeat(heartbeat: DeviceHeartbeat) -> Dict[str, Any]:
    """
    Upsert a device record from a heartbeat payload.
    Shared implementation for /heartbeat (canonical) and /register (alias).
    """
    now = datetime.now(timezone.utc)
    device_id = heartbeat.device_id

    is_new = device_id not in _device_registry

    if is_new:
        _device_registry[device_id] = {"registered_at": now.isoformat()}
        logger.info(
            f"New device registered: {device_id} ({heartbeat.device_name}) from {heartbeat.host}:{heartbeat.port}"
        )

    _device_registry[device_id].update(
        {
            "device_id": device_id,
            "device_name": heartbeat.device_name,
            "device_role": heartbeat.device_role,
            "device_display_name": heartbeat.device_display_name,
            "host": heartbeat.host,
            "port": heartbeat.port,
            "firmware_version": heartbeat.firmware_version,
            "board_type": heartbeat.board_type,
            "sensors": heartbeat.sensors,
            "capabilities": heartbeat.capabilities,
            "location": heartbeat.location,
            "connection_type": heartbeat.connection_type,
            "ingestion_source": heartbeat.ingestion_source,
            "extra": heartbeat.extra,
            "last_seen": now.isoformat(),
        }
    )

    _device_last_seen[device_id] = now

    if is_new:
        _register_device_with_orchestrator(device_id, _device_registry[device_id])
        schedule_domain_task(
            domain="device",
            task=f"New device registered: {heartbeat.device_name} ({device_id})",
            context={
                "device_id": device_id,
                "device_name": heartbeat.device_name,
                "device_role": heartbeat.device_role,
                "connection_type": heartbeat.connection_type,
                "ingestion_source": heartbeat.ingestion_source,
            },
        )

    _cleanup_expired_devices()

    return {
        "status": "registered" if is_new else "updated",
        "device_id": device_id,
        "timestamp": now.isoformat(),
    }


@router.post("/heartbeat")
async def heartbeat_device(heartbeat: DeviceHeartbeat):
    """
    Canonical heartbeat endpoint for device registration and keepalive.

    Devices should call this endpoint every 30 seconds to maintain registration.
    Devices not seen within TTL (2 minutes) are marked offline.
    Use POST /api/devices/register as a legacy alias; both behave identically.
    """
    result = _upsert_device_heartbeat(heartbeat)
    await _persist_heartbeat_to_device_inventory(heartbeat)
    return result


@router.post("/register")
async def register_device(heartbeat: DeviceHeartbeat):
    """
    Legacy alias for /heartbeat. Use POST /api/devices/heartbeat as canonical.
    """
    result = _upsert_device_heartbeat(heartbeat)
    await _persist_heartbeat_to_device_inventory(heartbeat)
    return result


async def _list_devices_impl(
    status: Optional[str] = None,
    include_offline: bool = False,
):
    """Shared implementation for list devices (used by both / and empty path)."""
    _cleanup_expired_devices()
    devices_out = []
    for device_id, device in _device_registry.items():
        device_status = _get_device_status(device_id)
        if status and device_status != status:
            continue
        if not include_offline and device_status == "offline":
            continue
        devices_out.append({**device, "status": device_status})
    return {
        "devices": devices_out,
        "count": len(devices_out),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("")
@router.get("/")
async def list_devices(
    status: Optional[str] = Query(None, description="Filter by status: online, stale, offline"),
    include_offline: bool = Query(False, description="Include offline devices"),
):
    """
    List all registered devices (serial, LoRa, Bluetooth, WiFi gateways).
    Returns devices with their current status based on last heartbeat.
    """
    return await _list_devices_impl(status=status, include_offline=include_offline)


@router.get("/inventory")
async def list_device_inventory(
    limit: int = Query(500, ge=1, le=5000, description="Max rows from soc_ops.device_inventory"),
):
    """
    LAN / SOC device inventory (Postgres). Used by security network monitor.
    In-memory MycoBrain registry remains on GET /api/devices/; this is the reconciled inventory.
    """
    if not _soc_pg_for_inventory():
        return {
            "items": [],
            "count": 0,
            "source": "postgres_not_configured",
            "hint": "Set MINDEX_DATABASE_URL and apply migration 030_soc_security_platform_may03_2026.sql",
        }
    try:
        from mycosoft_mas.soc import repository as soc_repo

        items = await soc_repo.list_device_inventory(limit=limit)
        return {"items": items, "count": len(items), "source": "postgres"}
    except Exception as e:
        logger.exception("list_device_inventory failed: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/crep")
async def list_devices_crep(
    include_offline: bool = Query(False, description="Include offline devices"),
):
    """
    List devices as CREP UnifiedEntity format for unified entity aggregation.
    Devices without lat/lng use [0, 0]; CREP layers can override with known positions.
    """
    _cleanup_expired_devices()
    entities = []
    import time as _time

    for device_id, device in _device_registry.items():
        status = _get_device_status(device_id)
        if not include_offline and status == "offline":
            continue
        loc = device.get("location") or device.get("extra", {}).get("location")
        coords: list[float] = [0.0, 0.0]
        if isinstance(loc, str) and "," in loc:
            try:
                parts = loc.split(",")
                coords = [float(parts[0].strip()), float(parts[1].strip())]
            except (ValueError, IndexError):
                pass
        elif isinstance(loc, (list, tuple)) and len(loc) >= 2:
            try:
                coords = [float(loc[0]), float(loc[1])]
            except (ValueError, TypeError):
                pass
        now_iso = datetime.now(timezone.utc).isoformat()
        entities.append(
            {
                "id": device_id,
                "type": "device",
                "geometry": {"type": "Point", "coordinates": coords},
                "state": {
                    "classification": device.get("device_role", "standalone"),
                    "energy": 1.0 if status == "online" else 0.5 if status == "stale" else 0.0,
                },
                "time": {"observed_at": now_iso, "valid_from": now_iso},
                "confidence": 0.9 if status == "online" else 0.6,
                "source": "mas-device-registry",
                "properties": {
                    "device_name": device.get("device_name"),
                    "device_role": device.get("device_role"),
                    "status": status,
                    "host": device.get("host"),
                    "port": device.get("port"),
                    "board_type": device.get("board_type"),
                    "ingestion_source": device.get("ingestion_source", "serial"),
                },
                "s2_cell": "0",
            }
        )
    return {
        "entities": entities,
        "server_time_ms": int(_time.time() * 1000),
    }


@router.get("/unified-network")
async def list_unified_network_devices(
    include_offline_mycobrain: bool = Query(
        False,
        description="Include MycoBrain rows past heartbeat TTL (offline)",
    ),
    include_meshtastic: bool = Query(
        True,
        description="Include MINDEX meshtastic.nodes (MQTT/LAN-ingested mesh radios)",
    ),
    include_observers: bool = Query(
        True,
        description="Include MINDEX meshtastic.observers",
    ),
    mesh_node_limit: int = Query(2000, ge=1, le=2000),
):
    """
    Single merge of in-memory MycoBrain heartbeats with MINDEX Meshtastic inventory.

    New Meshtastic nodes appear in MINDEX automatically when the MQTT bridge ingests
    traffic; MycoBrain devices appear when they heartbeat to POST /api/devices/heartbeat.
    MYCA and dashboards should poll this instead of stitching /api/devices + /api/meshtastic/nodes.
    """
    mb = await _list_devices_impl(status=None, include_offline=include_offline_mycobrain)
    mycobrain_devices: List[Dict[str, Any]] = mb.get("devices") or []

    mesh_payload: Dict[str, Any] = {"items": [], "error": None}
    obs_payload: Dict[str, Any] = {"items": [], "error": None}

    try:
        from mycosoft_mas.core.routers.meshtastic_api import _mindex_get
    except Exception as e:
        logger.warning("unified-network: meshtastic client import failed: %s", e)
        err = f"import:{e}"
        mesh_payload["error"] = err
        obs_payload["error"] = err
        _mindex_get = None  # type: ignore[assignment]

    if _mindex_get is not None:
        if include_meshtastic:
            try:
                mesh_payload = await _mindex_get(
                    "/nodes", {"limit": mesh_node_limit, "offset": 0}
                )
            except HTTPException as e:
                mesh_payload = {"items": [], "error": str(e.detail), "limit": mesh_node_limit}
            except Exception as e:
                logger.warning("unified-network: meshtastic /nodes failed: %s", e)
                mesh_payload = {"items": [], "error": str(e), "limit": mesh_node_limit}
        if include_observers:
            try:
                obs_payload = await _mindex_get("/observers")
            except HTTPException as e:
                obs_payload = {"items": [], "error": str(e.detail)}
            except Exception as e:
                logger.warning("unified-network: meshtastic /observers failed: %s", e)
                obs_payload = {"items": [], "error": str(e)}

    mesh_items = mesh_payload.get("items") if isinstance(mesh_payload, dict) else []
    if not isinstance(mesh_items, list):
        mesh_items = []

    obs_items = obs_payload.get("items") if isinstance(obs_payload, dict) else []
    if not isinstance(obs_items, list):
        obs_items = []

    unified: List[Dict[str, Any]] = []
    for d in mycobrain_devices:
        did = str(d.get("device_id") or "")
        unified.append(
            {
                "network_source": "mycobrain",
                "unified_id": f"mycobrain:{did}",
                "device": d,
            }
        )
    for row in mesh_items:
        nid = str(row.get("node_id") or "")
        unified.append(
            {
                "network_source": "meshtastic_node",
                "unified_id": f"meshtastic:{nid}",
                "meshtastic_node": row,
            }
        )
    for row in obs_items:
        oid = str(row.get("observer_id") or row.get("node_id") or "")
        unified.append(
            {
                "network_source": "meshtastic_observer",
                "unified_id": f"meshtastic_observer:{oid}",
                "meshtastic_observer": row,
            }
        )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "mycobrain": len(mycobrain_devices),
            "meshtastic_nodes": len(mesh_items),
            "meshtastic_observers": len(obs_items),
            "unified_total": len(unified),
        },
        "mycobrain": mb,
        "meshtastic_nodes": mesh_payload,
        "meshtastic_observers": obs_payload,
        "unified": unified,
    }


@router.get("/{device_id}")
async def get_device(device_id: str):
    """Get information about a specific device."""
    _cleanup_expired_devices()

    if device_id not in _device_registry:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    device = _device_registry[device_id]
    device_status = _get_device_status(device_id)

    return {
        **device,
        "status": device_status,
    }


class FCISummaryPayload(BaseModel):
    """FCI summary from Mycorrhizae/FCI stream — stored under device extra for unified device_id."""

    summary: Dict[str, Any] = Field(default_factory=dict, description="FCI summary data")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp")
    source: str = Field(default="fci", description="Source: fci, mycorrhizae, etc.")


@router.post("/{device_id}/fci-summary")
async def upsert_fci_summary(device_id: str, payload: FCISummaryPayload = Body(...)):
    """
    Store FCI summary for a device (bridge from Mycorrhizae/FCI).
    Data is stored in device extra under fci_summary for unified device_id.
    Device need not exist; will be created as placeholder if missing.
    """
    _cleanup_expired_devices()
    now = datetime.now(timezone.utc)
    ts = payload.timestamp or now.isoformat()
    if device_id not in _device_registry:
        _device_registry[device_id] = {
            "device_id": device_id,
            "device_name": "FCI-Placeholder",
            "device_role": "mushroom1",
            "registered_at": now.isoformat(),
            "last_seen": now.isoformat(),
        }
        _device_last_seen[device_id] = now
    device = _device_registry[device_id]
    if "extra" not in device:
        device["extra"] = {}
    device["extra"]["fci_summary"] = {
        "summary": payload.summary,
        "timestamp": ts,
        "source": payload.source,
    }
    device["last_seen"] = now.isoformat()
    _device_last_seen[device_id] = now
    logger.info("FCI summary stored for device %s", device_id)
    return {"status": "ok", "device_id": device_id, "timestamp": now.isoformat()}


@router.delete("/{device_id}")
async def unregister_device(device_id: str):
    """Unregister a device."""
    if device_id not in _device_registry:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    del _device_registry[device_id]
    if device_id in _device_last_seen:
        del _device_last_seen[device_id]

    logger.info(f"Device unregistered: {device_id}")

    return {
        "status": "unregistered",
        "device_id": device_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _device_base_url(device: Dict[str, Any]) -> str:
    """Resolve HTTP base URL for a registered device (legacy :8003 or agent :8787)."""
    extra = device.get("extra") or {}
    agent_url = extra.get("agent_url")
    if isinstance(agent_url, str) and agent_url.strip():
        return agent_url.rstrip("/")

    host = device.get("host", "")
    port = int(device.get("port") or 8003)

    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    if device.get("connection_type") == "cloudflare":
        return f"https://{host}"
    return f"http://{host}:{port}"


def _is_agent_api(device: Dict[str, Any]) -> bool:
    extra = device.get("extra") or {}
    if extra.get("api_kind") == "agent":
        return True
    if isinstance(extra.get("agent_url"), str) and ":8787" in extra["agent_url"]:
        return True
    return int(device.get("port") or 8003) == 8787


async def _fetch_agent_telemetry(client: httpx.AsyncClient, base_url: str) -> Dict[str, Any]:
    """Fetch telemetry from unified agent (:8787) — canonical or legacy /api paths."""
    for path in ("/telemetry/latest", "/api/sensor", "/api/status"):
        try:
            r = await client.get(f"{base_url}{path}")
            if r.status_code != 200:
                continue
            body = r.json()
            if path == "/api/status":
                reading = body.get("lastSensorReading")
                if reading:
                    return {"source": path, "reading": reading, "status": body}
                continue
            if path == "/api/sensor":
                reading = body.get("reading")
                if reading:
                    return {"source": path, "reading": reading}
                continue
            return body
        except Exception:
            continue
    raise HTTPException(status_code=503, detail="Agent telemetry endpoints unreachable")


async def _post_agent_command(
    client: httpx.AsyncClient,
    base_url: str,
    cmd: "DeviceCommand",
    path_id: str,
) -> Dict[str, Any]:
    """POST command to agent API (8787) or legacy MycoBrain service (8003)."""
    operator_cmd = (cmd.command or "").strip()
    if operator_cmd.startswith("beep "):
        operator_cmd = "bump"
    elif operator_cmd in ("led rgb 0 0 0", "led pattern off"):
        operator_cmd = "led off"

    # Jetson field agents (recovery-operator) expose plain-text /api/cmd only.
    try:
        r = await client.post(
            f"{base_url}/api/cmd",
            json={"cmd": operator_cmd},
        )
        if r.status_code == 200:
            body = r.json()
            if isinstance(body, dict) and body.get("ok") is False:
                raise HTTPException(
                    status_code=502,
                    detail=f"Agent rejected command: {body.get('error', body)}",
                )
            return body
    except HTTPException:
        raise
    except Exception:
        pass

    payload = {"command": {"cmd": cmd.command, **cmd.params}}
    mdp_payload = {
        "target": "side_a",
        "cmd": cmd.command,
        "params": cmd.params or {},
        "ack_requested": True,
        "timeout_ms": int((cmd.timeout or 5) * 1000),
    }
    for path, body in (
        ("/command", mdp_payload),
        (f"/devices/{path_id}/command", payload),
        ("/api/command", payload),
    ):
        try:
            r = await client.post(f"{base_url}{path}", json=body)
            if r.status_code == 200:
                result = r.json()
                if isinstance(result, dict) and result.get("ok") is False:
                    continue
                return result
        except Exception:
            continue
    raise HTTPException(status_code=503, detail="Agent command endpoints unreachable")


@router.post("/{device_id}/command")
async def send_device_command(
    device_id: str,
    cmd: DeviceCommand,
    use_mycorrhizae: bool = Query(
        True, description="Also publish command via Mycorrhizae for gateways"
    ),
):
    """
    Forward a command to a remote device.

    Proxies to the device's MycoBrain service. When use_mycorrhizae is true,
    also publishes to device.{device_id}.command via Mycorrhizae so gateways
    can forward to serial/LoRa devices.
    """
    _cleanup_expired_devices()

    if device_id not in _device_registry:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    device = _device_registry[device_id]
    device_status = _get_device_status(device_id)

    if device_status == "offline":
        raise HTTPException(status_code=503, detail=f"Device {device_id} is offline")

    # Publish to Mycorrhizae so gateways can forward (optional, non-blocking)
    if use_mycorrhizae:
        try:
            from mycosoft_mas.integrations.mycorrhizae_client import MycorrhizaeClient

            client = MycorrhizaeClient()
            command_payload = {"cmd": cmd.command, **cmd.params}
            published = await client.send_device_command(device_id, command_payload)
            if published:
                logger.info("Command published to Mycorrhizae device.%s.command", device_id)
        except Exception as e:
            logger.debug("Mycorrhizae publish skipped: %s", e)

    # Build target URL for direct device call
    base_url = _device_base_url(device)
    is_agent = _is_agent_api(device)

    h_forward = _mycobrain_service_forward_headers()

    # Forward command to device
    try:
        async with httpx.AsyncClient(timeout=cmd.timeout) as client:
            if is_agent:
                path_id = str(
                    (device.get("extra") or {}).get("mdp_device_id") or device_id
                )
                result = await _post_agent_command(client, base_url, cmd, path_id)
                schedule_domain_task(
                    domain="device",
                    task=f"Device command executed: {cmd.command} on {device_id}",
                    context={
                        "device_id": device_id,
                        "command": cmd.command,
                        "params": cmd.params,
                        "connection_type": device.get("connection_type"),
                        "mdp_path_id": path_id,
                        "api_kind": "agent",
                    },
                )
                return {
                    "status": "ok",
                    "device_id": device_id,
                    "mdp_path_id": path_id,
                    "command": cmd.command,
                    "response": result,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            path_id = await _resolve_mycobrain_mdp_http_id(device_id, device, base_url, client)
            response = await client.post(
                f"{base_url}/devices/{path_id}/command",
                json={
                    "command": {
                        "cmd": cmd.command,
                        **cmd.params,
                    }
                },
                headers=h_forward,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Device returned error: {response.text}",
                )

            schedule_domain_task(
                domain="device",
                task=f"Device command executed: {cmd.command} on {device_id}",
                context={
                    "device_id": device_id,
                    "command": cmd.command,
                    "params": cmd.params,
                    "connection_type": device.get("connection_type"),
                    "mdp_path_id": path_id,
                },
            )

            return {
                "status": "ok",
                "device_id": device_id,
                "mdp_path_id": path_id,
                "command": cmd.command,
                "response": response.json(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Command timeout for device {device_id}")
    except httpx.ConnectError as e:
        # Update device status
        logger.warning(f"Device {device_id} unreachable: {e}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to device {device_id}: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {e}")


@router.get("/{device_id}/telemetry")
async def get_device_telemetry(device_id: str):
    """
    Get telemetry from a remote device.

    Proxies the telemetry request to the device's MycoBrain service.
    """
    _cleanup_expired_devices()

    if device_id not in _device_registry:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")

    device = _device_registry[device_id]
    device_status = _get_device_status(device_id)

    if device_status == "offline":
        raise HTTPException(status_code=503, detail=f"Device {device_id} is offline")

    # Build target URL
    base_url = _device_base_url(device)
    is_agent = _is_agent_api(device)

    h_forward = _mycobrain_service_forward_headers()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if is_agent:
                body = await _fetch_agent_telemetry(client, base_url)
                path_id = str(
                    (device.get("extra") or {}).get("mdp_device_id") or device_id
                )
                if isinstance(body, dict):
                    body["mdp_path_id"] = path_id
                return body

            path_id = await _resolve_mycobrain_mdp_http_id(device_id, device, base_url, client)
            response = await client.get(
                f"{base_url}/devices/{path_id}/telemetry",
                headers=h_forward,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Device returned error: {response.text}",
                )

            body = response.json()
            if isinstance(body, dict):
                body["mdp_path_id"] = path_id
            return body

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Telemetry timeout for device {device_id}")
    except httpx.ConnectError as e:
        raise HTTPException(status_code=503, detail=f"Cannot connect to device {device_id}: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Telemetry failed: {e}")


@router.get("/health")
async def registry_health():
    """Health check for the device registry."""
    _cleanup_expired_devices()

    online = sum(1 for d in _device_registry if _get_device_status(d) == "online")
    stale = sum(1 for d in _device_registry if _get_device_status(d) == "stale")

    return {
        "status": "ok",
        "total_devices": len(_device_registry),
        "online_devices": online,
        "stale_devices": stale,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
