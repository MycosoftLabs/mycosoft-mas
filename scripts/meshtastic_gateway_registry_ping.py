#!/usr/bin/env python3
"""
Optional sidecar: POST a MAS device-registry heartbeat so Meshtastic gateways appear
alongside MycoBrain rows (metadata only — not mesh MDP).

Environment (required):
  MESHTASTIC_GATEWAY_REGISTRY_ID  — stable id, e.g. meshtastic-bridge-vm196

Environment (optional):
  MESHTASTIC_NODE_ID              — mesh node id string (!hex) if known
  MAS_URL                         — default http://192.168.0.188:8001
  MESHTASTIC_GATEWAY_NAME         — display name
  MESHTASTIC_SITE_LABEL           — stored in extra.site_label
  MESHTASTIC_GATEWAY_HOST         — LAN IP or hostname MAS can reach (default 192.168.0.196)
  MESHTASTIC_GATEWAY_PORT         — HTTP port for any co-located service (default 8003)

Exit 0 on HTTP 200 from POST /api/devices/heartbeat.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    device_id = (os.environ.get("MESHTASTIC_GATEWAY_REGISTRY_ID") or "").strip()
    node_id = (os.environ.get("MESHTASTIC_NODE_ID") or "").strip()
    if not device_id:
        print("MESHTASTIC_GATEWAY_REGISTRY_ID is required", file=sys.stderr)
        return 2

    mas_url = (os.environ.get("MAS_URL") or "http://192.168.0.188:8001").rstrip("/")
    host = (os.environ.get("MESHTASTIC_GATEWAY_HOST") or "192.168.0.196").strip()
    port = int(os.environ.get("MESHTASTIC_GATEWAY_PORT") or "8003")

    extra: dict = {
        "meshtastic_node_id": node_id or None,
        "site_label": (os.environ.get("MESHTASTIC_SITE_LABEL") or "").strip() or None,
        "registry_kind": "meshtastic_mqtt_gateway",
    }
    extra = {k: v for k, v in extra.items() if v is not None}

    body = {
        "device_id": device_id,
        "device_name": (os.environ.get("MESHTASTIC_GATEWAY_NAME") or "Meshtastic MQTT gateway").strip(),
        "device_role": "gateway",
        "host": host,
        "port": port,
        "firmware_version": "meshtastic-bridge-sidecar",
        "board_type": "service",
        "sensors": [],
        "capabilities": ["meshtastic", "mqtt"],
        "connection_type": "lan",
        "ingestion_source": "wifi",
        "extra": extra,
    }

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{mas_url}/api/devices/heartbeat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            out = resp.read().decode("utf-8", errors="replace")
            print(out)
            return 0 if resp.status == 200 else 1
    except urllib.error.HTTPError as e:
        print(e.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except OSError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
