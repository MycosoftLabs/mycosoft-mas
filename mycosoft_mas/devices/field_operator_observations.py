"""Read-only field-operator observation contract for Mushroom 1 and Hyphae 1.

GET-only. Does not actuate hardware, send serial, or invent readings.
The shared board MDP identifier is evidence, never a unique deployment key.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urljoin

import httpx

SCHEMA = "mas-field-operator-observation/v1"
STATUS_PATH = "/api/status"
SENSOR_PATH = "/api/sensor"
STATUS_TIMEOUT_S = 7.0
SENSOR_TIMEOUT_S = 2.0

ISO_PREFIX_LEN = 19

FetchJson = Callable[[str, float], Awaitable[Optional[Dict[str, Any]]]]

FIELD_OPERATOR_DEPLOYMENTS: Tuple[Dict[str, Any], ...] = (
    {
        "registry_id": "mycobrain-mushroom1-jetson-123",
        "catalog_id": "mushroom-1",
        "name": "Mushroom 1",
        "role": "mushroom1",
        "host_ip": "192.168.0.123",
        "agent_port": 8787,
        "agent_url": "http://192.168.0.123:8787",
        "mdp_device_id": "mycobrain-sidea-10b41d",
        "board_type": "jetson_orin",
    },
    {
        "registry_id": "mycobrain-hyphae1-jetson-228",
        "catalog_id": "hyphae-1",
        "name": "Hyphae 1",
        "role": "hyphae1",
        "host_ip": "192.168.0.228",
        "agent_port": 8787,
        "agent_url": "http://192.168.0.228:8787",
        "mdp_device_id": "mycobrain-sidea-10b41d",
        "board_type": "jetson_orin",
    },
)

CANONICAL_MEASUREMENTS: Tuple[Tuple[str, Tuple[str, ...], str], ...] = (
    ("temperature_c", ("temperature_c_comp", "ambient_temperature_c", "temperature"), "°C"),
    ("humidity_pct", ("humidity_pct_comp", "ambient_humidity_pct", "humidity"), "%RH"),
    ("pressure_hpa", ("pressure_hpa", "pressure"), "hPa"),
    ("gas_resistance_ohm", ("gas_resistance_ohm_comp", "gas_resistance_ohm", "gas_resistance"), "Ω"),
    ("iaq", ("iaq",), "IAQ index"),
    ("eco2_ppm", ("eco2_ppm", "eco2"), "ppm"),
    ("bvoc_ppm", ("bvoc_ppm", "bvoc"), "ppm"),
)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def is_iso_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or len(value) < ISO_PREFIX_LEN:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def finite_number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def mdp_owner_count(mdp_device_id: str) -> int:
    return sum(1 for row in FIELD_OPERATOR_DEPLOYMENTS if row["mdp_device_id"] == mdp_device_id)


def mdp_is_unique(mdp_device_id: str) -> bool:
    return mdp_owner_count(mdp_device_id) == 1


def list_field_operator_catalog() -> Dict[str, Any]:
    deployments = []
    for row in FIELD_OPERATOR_DEPLOYMENTS:
        deployments.append(
            {
                "registry_id": row["registry_id"],
                "catalog_id": row["catalog_id"],
                "name": row["name"],
                "role": row["role"],
                "host_ip": row["host_ip"],
                "agent_port": row["agent_port"],
                "agent_url": row["agent_url"],
                "board_type": row["board_type"],
                "reported_mdp_device_id": row["mdp_device_id"],
                "mdp_is_unique": mdp_is_unique(str(row["mdp_device_id"])),
            }
        )
    return {
        "schema": SCHEMA,
        "count": len(deployments),
        "deployments": deployments,
        "note": "Shared reported_mdp_device_id values do not select a deployment.",
    }


def resolve_field_operator(device_id: str) -> Dict[str, Any]:
    token = (device_id or "").strip()
    if not token:
        return {"kind": "unknown", "device_id": token, "deployment": None}

    registry_hits = [row for row in FIELD_OPERATOR_DEPLOYMENTS if row["registry_id"] == token]
    if len(registry_hits) == 1:
        return {"kind": "found", "device_id": token, "deployment": dict(registry_hits[0])}

    catalog_hits = [row for row in FIELD_OPERATOR_DEPLOYMENTS if row["catalog_id"] == token]
    if len(catalog_hits) == 1:
        return {"kind": "found", "device_id": token, "deployment": dict(catalog_hits[0])}

    mdp_hits = [row for row in FIELD_OPERATOR_DEPLOYMENTS if row["mdp_device_id"] == token]
    if len(mdp_hits) > 1:
        return {
            "kind": "ambiguous_mdp",
            "device_id": token,
            "deployment": None,
            "registry_ids": [row["registry_id"] for row in mdp_hits],
        }
    if len(mdp_hits) == 1:
        return {"kind": "found", "device_id": token, "deployment": dict(mdp_hits[0])}

    return {"kind": "unknown", "device_id": token, "deployment": None}


def catalog_identity_record(deployment: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "device_id": deployment["registry_id"],
        "device_name": deployment["name"],
        "device_role": deployment["role"],
        "device_display_name": deployment["name"],
        "host": deployment["host_ip"],
        "port": deployment["agent_port"],
        "firmware_version": "unknown",
        "board_type": deployment["board_type"],
        "sensors": [],
        "capabilities": ["operator-http"],
        "location": None,
        "connection_type": "lan",
        "ingestion_source": "operator-http",
        "status": "catalog",
        "source": "field-operator-catalog",
        "extra": {
            "registry_id": deployment["registry_id"],
            "catalog_id": deployment["catalog_id"],
            "reported_mdp_device_id": deployment["mdp_device_id"],
            "mdp_is_unique": mdp_is_unique(str(deployment["mdp_device_id"])),
            "agent_url": deployment["agent_url"],
            "identity_verified": False,
        },
    }


def _slot_key(reading: Mapping[str, Any], fallback: str) -> str:
    slot = reading.get("sensor_slot") or reading.get("address") or fallback
    return str(slot)


def _extract_operator_readings(status: Optional[Mapping[str, Any]], sensor: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    collected: Dict[str, Dict[str, Any]] = {}

    def add(raw: Any) -> None:
        if not isinstance(raw, Mapping):
            return
        if raw.get("type") not in (None, "telemetry"):
            if raw.get("sensor_slot") is None and raw.get("address") is None:
                return
        key = _slot_key(raw, str(len(collected)))
        collected[key] = dict(raw)

    if isinstance(status, Mapping):
        for entry in status.get("lastLines") or []:
            if not isinstance(entry, Mapping):
                continue
            line = entry.get("line")
            if not isinstance(line, str) or not line.startswith("{"):
                continue
            try:
                parsed = json.loads(line)
            except (TypeError, ValueError):
                continue
            if isinstance(parsed, Mapping) and parsed.get("type") == "telemetry":
                add(parsed)
        add(status.get("lastSensorReading"))

    if isinstance(sensor, Mapping):
        add(sensor.get("reading"))
        slots = sensor.get("slots")
        if isinstance(slots, Mapping):
            for value in slots.values():
                add(value)

    return list(collected.values())


def _identity_verified(status: Optional[Mapping[str, Any]], reading: Mapping[str, Any]) -> bool:
    status_flag = isinstance(status, Mapping) and status.get("identityVerified") is True
    reading_flag = reading.get("identity_verified") is True
    return status_flag and reading_flag


def _measurements(reading: Mapping[str, Any]) -> List[Dict[str, Any]]:
    measurements: List[Dict[str, Any]] = []
    for name, keys, unit in CANONICAL_MEASUREMENTS:
        for key in keys:
            number = finite_number(reading.get(key))
            if number is None:
                continue
            measurements.append(
                {
                    "name": name,
                    "source_field": key,
                    "value": number,
                    "unit": unit,
                }
            )
            break
    return measurements


def normalize_operator_observation(
    deployment: Mapping[str, Any],
    *,
    status: Optional[Mapping[str, Any]],
    sensor: Optional[Mapping[str, Any]],
    received_at: str,
    status_ok: bool,
    sensor_ok: bool,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    operator_url = str(deployment["agent_url"]).rstrip("/")
    readings_out: List[Dict[str, Any]] = []
    rejected: List[Dict[str, str]] = []

    for raw in _extract_operator_readings(status, sensor):
        observed_at = raw.get("ts")
        sensor_slot = raw.get("sensor_slot")
        address = raw.get("address")
        if not isinstance(sensor_slot, str) or not sensor_slot.strip():
            rejected.append({"reason": "missing_sensor_slot"})
            continue
        if not isinstance(address, str) or not address.strip():
            rejected.append({"reason": "missing_sensor_address", "sensor_slot": sensor_slot})
            continue
        if not is_iso_timestamp(observed_at):
            rejected.append({"reason": "missing_or_invalid_observed_at", "sensor_slot": sensor_slot})
            continue
        measurements = _measurements(raw)
        if not measurements:
            rejected.append({"reason": "no_finite_canonical_measurements", "sensor_slot": sensor_slot})
            continue
        reported = raw.get("device_id") or raw.get("node_id")
        readings_out.append(
            {
                "device_id": deployment["registry_id"],
                "registry_id": deployment["registry_id"],
                "catalog_id": deployment["catalog_id"],
                "reported_device_id": reported if isinstance(reported, str) and reported.strip() else None,
                "sensor_id": sensor_slot,
                "sensor_slot": sensor_slot,
                "address": address,
                "observed_at": observed_at,
                "received_at": received_at,
                "valid": raw.get("valid") is True,
                "identity_verified": _identity_verified(status, raw),
                "measurements": measurements,
                "operator_fields": {
                    key: raw.get(key)
                    for key in (
                        "type",
                        "device_id",
                        "node_id",
                        "role",
                        "sensor_slot",
                        "address",
                        "fw_version",
                        "ts",
                        "ts_ms",
                        "temperature_c_comp",
                        "humidity_pct_comp",
                        "pressure_hpa",
                        "gas_resistance_ohm",
                        "iaq",
                        "eco2_ppm",
                        "bvoc_ppm",
                        "valid",
                    )
                    if key in raw
                },
            }
        )

    reachable = status_ok or sensor_ok
    if not reachable:
        state = "unreachable"
        message = error or "Documented operator GET endpoints timed out or failed."
    elif not readings_out:
        state = "unbound"
        message = "Operator was reachable but no reading had sensor identity, observation time, and finite values."
    else:
        state = "available"
        message = "Accepted operator readings preserve deployment identity, sensor identity, time, units, and provenance."

    serial_connected = isinstance(status, Mapping) and status.get("serialConnected") is True
    last_heartbeat = status.get("lastHeartbeat") if isinstance(status, Mapping) else None

    return {
        "schema": SCHEMA,
        "state": state,
        "message": message,
        "device_id": deployment["registry_id"],
        "registry_id": deployment["registry_id"],
        "catalog_id": deployment["catalog_id"],
        "name": deployment["name"],
        "role": deployment["role"],
        "host_ip": deployment["host_ip"],
        "agent_url": operator_url,
        "reported_mdp_device_id": deployment["mdp_device_id"],
        "mdp_is_unique": mdp_is_unique(str(deployment["mdp_device_id"])),
        "identity_verified": False,
        "serial_connected": serial_connected,
        "serial_port": status.get("serialPort") if isinstance(status, Mapping) else None,
        "last_heartbeat": last_heartbeat if is_iso_timestamp(last_heartbeat) else None,
        "received_at": received_at,
        "rejected_count": len(rejected),
        "rejected": rejected,
        "readings": readings_out,
        "provenance": {
            "source": "operator-http",
            "status_url": urljoin(operator_url + "/", STATUS_PATH.lstrip("/")),
            "sensor_url": urljoin(operator_url + "/", SENSOR_PATH.lstrip("/")),
            "status_ok": status_ok,
            "sensor_ok": sensor_ok,
        },
    }


def to_device_telemetry_payload(observation: Mapping[str, Any]) -> Dict[str, Any]:
    """Shape consumed by exact selected-device telemetry parsers.

    Intentionally omits source_device_id so a shared board MDP cannot steal
    identity from the unique deployment registry_id.
    """
    telemetry: List[Dict[str, Any]] = []
    for reading in observation.get("readings") or []:
        if not isinstance(reading, Mapping):
            continue
        row: Dict[str, Any] = {
            "device_id": observation["registry_id"],
            "registry_id": observation["registry_id"],
            "sensor_id": reading.get("sensor_id"),
            "sensor_slot": reading.get("sensor_slot"),
            "address": reading.get("address"),
            "observed_at": reading.get("observed_at"),
            "received_at": reading.get("received_at"),
            "reported_device_id": reading.get("reported_device_id"),
        }
        for measurement in reading.get("measurements") or []:
            if not isinstance(measurement, Mapping):
                continue
            name = measurement.get("name")
            if isinstance(name, str):
                row[name] = measurement.get("value")
                row[f"{name}_unit"] = measurement.get("unit")
        telemetry.append(row)

    return {
        "device_id": observation["registry_id"],
        "registry_id": observation["registry_id"],
        "catalog_id": observation["catalog_id"],
        "state": observation["state"],
        "received_at": observation["received_at"],
        "last_seen": observation.get("last_heartbeat") or observation["received_at"],
        "telemetry": telemetry,
        "field_operator": observation,
    }


async def _default_fetch_json(url: str, timeout_s: float) -> Optional[Dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.get(url, headers={"Accept": "application/json"})
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError):
        return None
    if response.status_code != 200:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


async def collect_field_operator_observation(
    deployment: Mapping[str, Any],
    *,
    fetch_json: Optional[FetchJson] = None,
    received_at: Optional[str] = None,
) -> Dict[str, Any]:
    getter = fetch_json or _default_fetch_json
    received = received_at or now_utc_iso()
    operator_url = str(deployment["agent_url"]).rstrip("/")
    status_url = f"{operator_url}{STATUS_PATH}"
    sensor_url = f"{operator_url}{SENSOR_PATH}"

    status = await getter(status_url, STATUS_TIMEOUT_S)
    sensor = await getter(sensor_url, SENSOR_TIMEOUT_S)
    status_ok = status is not None
    sensor_ok = sensor is not None
    error = None
    if not status_ok and not sensor_ok:
        error = f"GET {STATUS_PATH} and {SENSOR_PATH} failed or timed out at {operator_url}"
    return normalize_operator_observation(
        deployment,
        status=status,
        sensor=sensor,
        received_at=received,
        status_ok=status_ok,
        sensor_ok=sensor_ok,
        error=error,
    )


async def collect_field_operator_observations(
    *,
    device_id: Optional[str] = None,
    fetch_json: Optional[FetchJson] = None,
    received_at: Optional[str] = None,
) -> Dict[str, Any]:
    received = received_at or now_utc_iso()
    if device_id:
        resolved = resolve_field_operator(device_id)
        if resolved["kind"] == "ambiguous_mdp":
            return {
                "schema": SCHEMA,
                "state": "unbound",
                "message": "Shared board MDP identifier does not select a unique field deployment.",
                "device_id": device_id,
                "registry_ids": resolved.get("registry_ids"),
                "received_at": received,
                "observations": [],
            }
        if resolved["kind"] != "found" or not resolved["deployment"]:
            return {
                "schema": SCHEMA,
                "state": "unbound",
                "message": "Unknown field-operator identity.",
                "device_id": device_id,
                "received_at": received,
                "observations": [],
            }
        targets: Sequence[Mapping[str, Any]] = (resolved["deployment"],)
    else:
        targets = FIELD_OPERATOR_DEPLOYMENTS

    observations = [
        await collect_field_operator_observation(
            deployment,
            fetch_json=fetch_json,
            received_at=received,
        )
        for deployment in targets
    ]
    available = [row for row in observations if row["state"] == "available"]
    if available:
        state = "available"
        message = "One or more field operators returned provenance-bearing readings."
    elif any(row["state"] == "unreachable" for row in observations):
        state = "unreachable" if all(row["state"] == "unreachable" for row in observations) else "unbound"
        message = "At least one configured operator was unreachable; no readings were fabricated."
    else:
        state = "unbound"
        message = "No accepted field-operator reading."

    return {
        "schema": SCHEMA,
        "state": state,
        "message": message,
        "received_at": received,
        "observations": observations,
    }
