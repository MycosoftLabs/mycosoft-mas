#!/usr/bin/env python3
"""
Field MycoBrain heartbeat bridge — probes LAN agents (:8787) and registers with MAS.

Run on any host that can reach 192.168.0.123 and 192.168.0.228 (dev PC, MAS VM, or
a small always-on LAN box). Posts to POST {MAS}/api/devices/heartbeat every 30s so
Earth Simulator and /api/devices/network work on production without direct LAN probes.

Usage:
  python scripts/field_mycobrain_heartbeat_bridge.py
  python scripts/field_mycobrain_heartbeat_bridge.py --once

Environment:
  MAS_API_URL          default http://192.168.0.188:8001
  MYCOBRAIN_OPERATOR_URLS  comma-separated agent URLs (8787)
  FIELD_HEARTBEAT_INTERVAL  seconds (default 30)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("field_mycobrain_heartbeat")

FIELD_DEPLOYMENTS: List[Dict[str, Any]] = [
    {
        "registry_id": "mycobrain-mushroom1-jetson-123",
        "name": "Mushroom 1",
        "role": "mushroom1",
        "host_ip": "192.168.0.123",
        "agent_url": "http://192.168.0.123:8787",
        "location": "32.715736,-117.161087",
        "mdp_device_id": "mycobrain-sidea-10b41d",
        "board_type": "jetson_orin",
    },
    {
        "registry_id": "mycobrain-hyphae1-jetson-228",
        "name": "Hyphae 1",
        "role": "hyphae1",
        "host_ip": "192.168.0.228",
        "agent_url": "http://192.168.0.228:8787",
        "location": "32.640278,-117.085833",
        "mdp_device_id": "mycobrain-sidea-10b41d",
        "board_type": "jetson_orin",
    },
]


def _operator_urls() -> List[str]:
    raw = os.environ.get(
        "MYCOBRAIN_OPERATOR_URLS",
        "http://192.168.0.123:8787,http://192.168.0.228:8787",
    )
    return [u.strip().rstrip("/") for u in raw.split(",") if u.strip()]


def _mas_url() -> str:
    return os.environ.get("MAS_API_URL", "http://192.168.0.188:8001").rstrip("/")


def probe_agent(client: httpx.Client, agent_url: str) -> Optional[Dict[str, Any]]:
    try:
        r = client.get(f"{agent_url}/api/status", timeout=7.0)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception as exc:
        logger.debug("Probe failed %s: %s", agent_url, exc)
        return None


def build_heartbeat(deployment: Dict[str, Any], status: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    reading = (status or {}).get("lastSensorReading") or {}
    online = bool(status and status.get("serialConnected") is True)
    fw = reading.get("fw_version") or "unknown"

    telemetry = None
    if reading:
        telemetry = {
            "temperature_c": reading.get("temperature_c_comp") or reading.get("ambient_temperature_c"),
            "humidity_pct": reading.get("humidity_pct_comp") or reading.get("ambient_humidity_pct"),
            "pressure_hpa": reading.get("pressure_hpa"),
            "iaq": reading.get("iaq"),
            "eco2_ppm": reading.get("eco2_ppm"),
            "gas_resistance_ohm": reading.get("gas_resistance_ohm"),
            "sensor_slot": reading.get("sensor_slot"),
            "captured_at": reading.get("ts") or status.get("lastHeartbeat"),
        }

    return {
        "device_id": deployment["registry_id"],
        "device_name": deployment["name"],
        "device_display_name": deployment["name"],
        "device_role": deployment["role"],
        "host": deployment["host_ip"],
        "port": 8787,
        "firmware_version": fw,
        "board_type": deployment["board_type"],
        "sensors": ["bme688_ambient", "bme688_environment"],
        "capabilities": ["mqtt", "mdp_command", "telemetry_stream", "openclaw"],
        "location": deployment["location"],
        "connection_type": "lan",
        "ingestion_source": "operator-http" if online else "field-bridge",
        "extra": {
            "agent_url": deployment["agent_url"],
            "api_kind": "agent",
            "mdp_device_id": reading.get("device_id") or deployment["mdp_device_id"],
            "online": online,
            "latest_telemetry": telemetry,
            "field_bridge": True,
            "last_probe_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def post_heartbeat(client: httpx.Client, payload: Dict[str, Any]) -> None:
    url = f"{_mas_url()}/api/devices/heartbeat"
    r = client.post(url, json=payload, timeout=15.0)
    r.raise_for_status()
    logger.info(
        "MAS heartbeat ok: %s online=%s",
        payload["device_id"],
        payload.get("extra", {}).get("online"),
    )


def run_cycle(client: httpx.Client) -> int:
    url_by_host = {d["host_ip"]: d["agent_url"] for d in FIELD_DEPLOYMENTS}
    ok = 0
    for dep in FIELD_DEPLOYMENTS:
        agent_url = url_by_host.get(dep["host_ip"]) or dep["agent_url"]
        status = probe_agent(client, agent_url)
        hb = build_heartbeat(dep, status)
        try:
            post_heartbeat(client, hb)
            ok += 1
        except Exception as exc:
            logger.error("Heartbeat failed for %s: %s", dep["registry_id"], exc)
    return ok


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="Field MycoBrain → MAS heartbeat bridge")
    parser.add_argument("--once", action="store_true", help="Single cycle then exit")
    args = parser.parse_args()

    interval = int(os.environ.get("FIELD_HEARTBEAT_INTERVAL", "30"))
    logger.info("MAS=%s operators=%s interval=%ss", _mas_url(), _operator_urls(), interval)

    with httpx.Client() as client:
        if args.once:
            n = run_cycle(client)
            return 0 if n > 0 else 1

        while True:
            run_cycle(client)
            time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())
