"""Maritime Sensor Network Integration Client — TAC-O Maritime Integration."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)


def _normalize_base(url: str, suffix: str = "") -> str:
    value = (url or "").rstrip("/")
    if suffix and not value.endswith(suffix):
        value = f"{value}{suffix}"
    return value


class MaritimeSensorNetworkClient:
    """Integration client for contractor-agnostic maritime sensor networks."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.mycobrain_url = _normalize_base(
            self.config.get("mycobrain_url") or os.environ.get("MYCOBRAIN_URL") or "http://localhost:8003"
        )
        self.mindex_url = _normalize_base(
            self.config.get("mindex_url") or os.environ.get("MINDEX_API_URL") or "http://192.168.0.189:8000",
            "/api/mindex",
        )
        self.timeout_s = float(self.config.get("timeout_s", 20.0))
        self.internal_token = self.config.get("internal_token") or os.environ.get("MINDEX_INTERNAL_TOKEN")
        self.api_key = self.config.get("api_key") or os.environ.get("MINDEX_API_KEY")

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.internal_token:
            headers["X-Internal-Token"] = self.internal_token
        elif self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _build_message(self, sensor_id: str, data_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        message = {
            "message_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sensor_id": sensor_id,
            "data_type": data_type,
            "payload": payload,
        }
        message["merkle_hash"] = hashlib.sha256(
            json.dumps(message, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        return message

    async def _get_json(self, url: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {"items": data}

    async def _post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {"items": data}

    async def subscribe_sensor_feed(self, sensor_ids: Optional[List[str]] = None):
        """Return the latest persisted observations for the requested sensors."""
        data = await self._get_json(f"{self.mindex_url}/taco/observations?limit=200&offset=0")
        observations = data.get("observations", [])
        if sensor_ids:
            observations = [item for item in observations if item.get("sensor_id") in sensor_ids]
        logger.info("Loaded %s maritime sensor observations", len(observations))
        return {"status": "subscribed", "sensor_ids": sensor_ids or [], "observations": observations}

    async def reconfigure_sensor(self, sensor_id: str, config: Dict[str, Any]):
        """Send configuration update to a maritime sensor via bridge."""
        return await self.send_command(sensor_id=sensor_id, command="reconfigure", params=config)

    async def get_sensor_status(self) -> List[Dict[str, Any]]:
        """Query current maritime sensor network health and merge edge status."""
        mindex_status = await self._get_json(f"{self.mindex_url}/taco/sensor-status")
        sensors = mindex_status.get("sensors", [])
        try:
            mycobrain_devices = await self._get_json(f"{self.mycobrain_url}/devices")
            device_items = mycobrain_devices if isinstance(mycobrain_devices, list) else mycobrain_devices.get("devices", [])
            by_device = {str(item.get("device_id") or item.get("id")): item for item in device_items}
            for sensor in sensors:
                matched = by_device.get(str(sensor.get("sensor_id")))
                if matched:
                    sensor["edge_status"] = matched.get("status")
                    sensor["edge_capabilities"] = matched.get("capabilities", [])
        except Exception as exc:  # noqa: BLE001
            logger.warning("MycoBrain device merge unavailable: %s", exc)
        return sensors

    async def get_buoy_network_topology(self) -> Dict[str, Any]:
        """Derive current relay topology from sensor inventory."""
        sensors = await self.get_sensor_status()
        buoys = [sensor for sensor in sensors if "buoy" in str(sensor.get("sensor_type", "")).lower()]
        fuzes = [sensor for sensor in sensors if "fuze" in str(sensor.get("sensor_type", "")).lower()]
        links = []
        for fuze in fuzes:
            if buoys:
                links.append(
                    {
                        "from_sensor": fuze.get("sensor_id"),
                        "to_buoy": buoys[0].get("sensor_id"),
                        "link_type": "surface_relay",
                    }
                )
        return {"buoys": buoys, "links": links, "topology_status": "online" if sensors else "degraded"}

    async def ingest_observation(self, sensor_id: str, sensor_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        message = self._build_message(sensor_id=sensor_id, data_type=payload.get("data_type", "sensor_observation"), payload=payload)
        observed_at = payload.get("timestamp") or message["timestamp"]
        request_body = {
            "sensor_id": sensor_id,
            "sensor_type": sensor_type,
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "depth_m": payload.get("depth_m"),
            "raw_data": payload.get("raw_data", payload),
            "processed_fingerprint": payload.get("processed_fingerprint"),
            "classification": payload.get("classification"),
            "anomaly_score": payload.get("anomaly_score"),
            "confidence": payload.get("confidence"),
            "avani_review": payload.get("avani_review"),
            "observed_at": observed_at,
            "merkle_hash": message["merkle_hash"],
        }
        return await self._post_json(f"{self.mindex_url}/taco/observations", request_body)

    async def create_assessment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._post_json(f"{self.mindex_url}/taco/assessments", payload)

    async def send_command(self, sensor_id: str, command: str, params: Optional[Dict] = None):
        """Send a command to a specific maritime sensor via the available bridge.

        If no device command bridge is available, return an explicit unavailable state.
        """
        envelope = self._build_message(sensor_id=sensor_id, data_type="command", payload={"command": command, "params": params or {}})
        logger.info("Sending maritime sensor command '%s' to sensor %s", command, sensor_id)
        try:
            return await self._post_json(f"{self.mycobrain_url}/command", envelope)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Device command bridge unavailable: %s", exc)
            return {
                "status": "unavailable",
                "sensor_id": sensor_id,
                "command": command,
                "params": params or {},
                "reason": str(exc),
                "message": "MycoBrain command bridge does not currently expose a writable /command endpoint.",
                "mdp_message": envelope,
            }


# Backward-compatible alias for older imports.
ZeetachecClient = MaritimeSensorNetworkClient
